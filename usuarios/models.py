from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    Manager personalizado para el modelo Usuario.
    Usa email como campo de identificación en lugar de username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Crea y guarda un usuario con el email y contraseña dados."""
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Crea y guarda un superusuario con el email y contraseña dados."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser de Django.
    El campo de autenticacion principal es EMAIL, no el username.
    El username se conserva como nombre de pantalla y permite duplicados.
    AbstractUser ya provee: username, email, password, first_name,
    last_name, is_active, is_staff, date_joined.
    """

    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        USER = 'USER', 'Usuario'

    # Sobreescribimos username para quitar la restriccion unique
    username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='nombre de usuario',
        help_text='Nombre visible en la app. No tiene que ser unico.',
    )

    # Email se convierte en el campo de autenticacion principal
    email = models.EmailField(
        unique=True,
        verbose_name='correo electronico',
        error_messages={
            'unique': 'Ya existe una cuenta con este correo electronico.',
        },
    )

    telefono = models.CharField(max_length=20, blank=True, null=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.USER)

    # Campo preparado para futura integracion OAuth2 con Google (django-allauth)
    google_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Google ID (OAuth)',
        help_text='Identificador de la cuenta Google vinculada. Usado por django-allauth.',
    )

    # El campo de autenticacion es el email
    USERNAME_FIELD = 'email'
    # username es campo requerido al crear superusuario via comando
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def nombre_usuario(self):
        """Devuelve el nombre de usuario o la parte local del email si no tiene username."""
        return self.username or self.email.split('@')[0]


class Preferencias(models.Model):
    """
    Configuracion de alertas y notificaciones de un usuario.
    Origen: creada automaticamente al registrar un Usuario.
    Destino: modulo de Notificaciones para evaluar umbrales.
    """

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='preferencias'
    )

    umbral_advertencia_porcentaje = models.IntegerField(default=80)
    egreso_grande_porcentaje = models.IntegerField(default=30)

    alerta_egreso_grande = models.BooleanField(default=True)
    alerta_deficit = models.BooleanField(default=True)
    alerta_patron_inusual = models.BooleanField(default=True)
    alerta_presupuesto = models.BooleanField(default=True)
    alerta_aporte_proximo = models.BooleanField(default=True)
    alerta_aporte_dias_anticipacion = models.IntegerField(default=3)

    def __str__(self):
        return f'Preferencias de {self.usuario.email}'