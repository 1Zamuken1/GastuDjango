import secrets

from django.conf import settings
from django.db import models

from movimientos.models import ModeloBase


def generar_alias():
    """
    Genera un alias aleatorio para la direccion de captura.

    Usa letras minusculas y digitos sin caracteres ambiguos (0/o, 1/l),
    para que el usuario pueda dictarlo o copiarlo sin errores.

    Returns:
        str: alias de 10 caracteres.
    """
    alfabeto = 'abcdefghijkmnpqrstuvwxyz23456789'
    return ''.join(secrets.choice(alfabeto) for _ in range(10))


class BuzonCaptura(ModeloBase):
    """
    Direccion de correo personal a la que el usuario reenvia las alertas de su banco.
    Origen: el usuario la activa desde la seccion de captura automatica.
    Destino: servidor SMTP propio, que enruta cada correo por su alias.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buzon_captura',
    )
    alias = models.CharField(max_length=32, unique=True, default=generar_alias)
    verificado = models.BooleanField(
        default=False,
        help_text='True cuando ya llego al menos un correo de un banco soportado.',
    )
    codigo_reenvio_gmail = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Codigo del correo de confirmacion de reenvio de Gmail.',
    )
    enlace_reenvio_gmail = models.URLField(max_length=500, blank=True, default='')
    ultimo_correo_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Buzon de captura'
        verbose_name_plural = 'Buzones de captura'

    def __str__(self):
        return f'{self.alias} ({self.usuario})'

    @property
    def direccion(self):
        """
        Direccion completa que el usuario debe usar en su filtro de reenvio.

        Returns:
            str: alias@dominio configurado en CAPTURA_DOMINIO.
        """
        return f'{self.alias}@{settings.CAPTURA_DOMINIO}'

    def regenerar_alias(self):
        """Reemplaza el alias por uno nuevo; el anterior deja de recibir correos."""
        self.alias = generar_alias()
        self.verificado = False
        self.codigo_reenvio_gmail = ''
        self.enlace_reenvio_gmail = ''
        self.save(update_fields=['alias', 'verificado', 'codigo_reenvio_gmail', 'enlace_reenvio_gmail'])


class CorreoEntrante(models.Model):
    """
    Correo recibido en un buzon de captura, antes y despues de procesarse.
    El texto se conserva solo para depurar parsers y se borra a los 30 dias.
    """

    class Estado(models.TextChoices):
        PROCESADO = 'PROCESADO', 'Procesado'
        IGNORADO = 'IGNORADO', 'Ignorado'
        ERROR = 'ERROR', 'Error'

    buzon = models.ForeignKey(BuzonCaptura, on_delete=models.CASCADE, related_name='correos')
    message_id = models.CharField(max_length=255, blank=True, default='')
    remitente = models.CharField(max_length=255)
    asunto = models.CharField(max_length=255, blank=True, default='')
    texto = models.TextField(blank=True, default='')
    dkim_valido = models.BooleanField(default=False)
    estado = models.CharField(max_length=10, choices=Estado.choices)
    detalle = models.CharField(max_length=255, blank=True, default='')
    recibido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Correo entrante'
        verbose_name_plural = 'Correos entrantes'
        ordering = ['-recibido_en']

    def __str__(self):
        return f'{self.remitente} - {self.asunto[:40]}'


class MovimientoDetectado(ModeloBase):
    """
    Movimiento bancario extraido de un correo, pendiente de que el usuario lo confirme.
    Origen: captura_bancaria.services.procesar_correo.
    Destino: movimientos.Movimiento al confirmarse.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        DESCARTADO = 'DESCARTADO', 'Descartado'

    class Tipo(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        EGRESO = 'EGRESO', 'Egreso'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='movimientos_detectados',
    )
    correo = models.ForeignKey(
        CorreoEntrante, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='detectados',
    )
    banco = models.CharField(max_length=40)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    operacion = models.CharField(
        max_length=30,
        help_text='Tipo de operacion bancaria: compra, transferencia, retiro, pago, abono.',
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    comercio = models.CharField(max_length=120, blank=True, default='')
    fecha_transaccion = models.DateTimeField()
    producto = models.CharField(
        max_length=40, blank=True, default='',
        help_text='Producto bancario sin el numero completo, ej: T.Cred *1234.',
    )
    categoria_sugerida = models.ForeignKey(
        'categorias.Categoria', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    movimiento = models.OneToOneField(
        'movimientos.Movimiento', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='detectado',
    )
    metodo = models.CharField(
        max_length=10, default='REGLAS',
        help_text='Como se leyo la alerta: REGLAS (parser del banco) o IA (Groq).',
    )
    hash_unico = models.CharField(max_length=64)
    resuelto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Movimiento detectado'
        verbose_name_plural = 'Movimientos detectados'
        ordering = ['-fecha_transaccion']
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'hash_unico'], name='detectado_unico_por_usuario'),
        ]

    def __str__(self):
        return f'{self.tipo} ${self.monto} {self.comercio} ({self.estado})'


class ReglaComercio(ModeloBase):
    """
    Categoria aprendida para un comercio o contraparte, por usuario.
    Se crea o actualiza cada vez que el usuario confirma un movimiento detectado.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reglas_comercio',
    )
    comercio_normalizado = models.CharField(max_length=120)
    tipo = models.CharField(max_length=10, choices=MovimientoDetectado.Tipo.choices)
    categoria = models.ForeignKey('categorias.Categoria', on_delete=models.CASCADE, related_name='+')
    auto_confirmar = models.BooleanField(default=False)
    veces_usada = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Regla de comercio'
        verbose_name_plural = 'Reglas de comercio'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'comercio_normalizado', 'tipo'],
                name='regla_unica_por_comercio',
            ),
        ]

    def __str__(self):
        return f'{self.comercio_normalizado} -> {self.categoria.nombre}'
