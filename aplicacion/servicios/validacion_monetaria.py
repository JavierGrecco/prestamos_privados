"""Validación de importes monetarios en las fronteras de aplicación."""
from decimal import Decimal, InvalidOperation

from .excepciones import ErrorDatosInvalidos

_CENTAVO = Decimal("0.01")


def validar_importe_centavos(valor: Decimal, etiqueta: str) -> None:
    """Rechaza importes no finitos o que contienen fracciones de centavo.

    No redondea silenciosamente. De esta forma el monto persistido coincide
    exactamente con los importes usados por la imputación y el ledger.
    """
    if not isinstance(valor, Decimal):
        raise ErrorDatosInvalidos(
            f"{etiqueta} debe ser Decimal; no se admite float ni otro tipo numérico"
        )
    if not valor.is_finite():
        raise ErrorDatosInvalidos(f"{etiqueta} debe ser un importe Decimal finito")

    try:
        centavos = valor.quantize(_CENTAVO)
    except InvalidOperation as exc:
        raise ErrorDatosInvalidos(
            f"{etiqueta} está fuera del rango monetario admitido"
        ) from exc

    if centavos != valor:
        raise ErrorDatosInvalidos(
            f"{etiqueta} debe expresarse en centavos exactos; "
            "no se admiten fracciones de centavo"
        )
