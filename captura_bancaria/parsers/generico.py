"""
Parser generico para bancos sin parser de reglas propio: identifica el banco por
el dominio del remitente y extrae el movimiento con IA.

Los dominios son los conocidos publicamente para cada entidad; hay que
confirmarlos con correos reales a medida que los usuarios los reenvien.
"""
from .ia import parsear_con_ia

BANCOS = [
    ('Davivienda', ('davivienda.com',)),
    ('BBVA', ('bbva.com.co', 'bbvanet.com.co')),
    ('Banco de Bogotá', ('bancodebogota.com.co',)),
    ('Banco de Occidente', ('bancodeoccidente.com.co',)),
    ('Banco Popular', ('bancopopular.com.co',)),
    ('AV Villas', ('avvillas.com.co',)),
    ('Scotiabank Colpatria', ('scotiabankcolpatria.com',)),
    ('Banco Falabella', ('bancofalabella.com.co',)),
    ('Itaú', ('itau.co',)),
    ('Nequi', ('nequi.com.co',)),
    ('Daviplata', ('daviplata.com',)),
    ('Nu', ('nu.com.co',)),
    ('Lulo Bank', ('lulobank.com',)),
]


class ParserGenerico:
    """Parser de un banco identificado solo por dominio, que lee con IA."""

    USA_IA = True

    def __init__(self, nombre, dominios):
        self.NOMBRE = nombre
        self.DOMINIOS = dominios

    def es_remitente(self, remitente: str, texto: str) -> bool:
        dominio = remitente.lower().rsplit('@', 1)[-1]
        return any(dominio == d or dominio.endswith('.' + d) for d in self.DOMINIOS)

    def parsear(self, asunto: str, texto: str):
        return parsear_con_ia(self.NOMBRE, asunto, texto)


PARSERS_GENERICOS = [ParserGenerico(nombre, dominios) for nombre, dominios in BANCOS]
