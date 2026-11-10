"""
Neutraliza la inyeccion de formulas en las exportaciones CSV y Excel.

Excel, LibreOffice y Google Sheets ejecutan como formula cualquier celda que empiece
por =, +, -, @ (o tabulador / retorno). Las descripciones las escribe el usuario o
llegan de correos capturados, asi que se antepone un apostrofo, que la hoja muestra
como texto literal (recomendacion de OWASP para CSV injection).
"""
PREFIJOS_FORMULA = ('=', '+', '-', '@', '\t', '\r')


def texto_seguro(valor):
    """Devuelve el valor listo para una celda; solo modifica textos que parecen formula."""
    if isinstance(valor, str) and valor.startswith(PREFIJOS_FORMULA):
        return "'" + valor
    return valor
