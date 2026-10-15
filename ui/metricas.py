"""Compatibilidad para las métricas usadas por la pantalla principal.

El cálculo vive en aplicación y la lectura SQLite vive en infraestructura.
Este módulo conserva los nombres históricos que importa la UI y mantiene
aquí solamente las funciones de presentación y formato.
"""
from decimal import Decimal

from aplicacion.consultas.metricas_principales import (
    INFLACION_MENSUAL_DEFAULT,
    MetricasPrincipales,
    _detalle_deuda,
    _detalle_inversion,
    _veredicto,
)
from infraestructura.composicion.metricas_principales import (
    crear_servicio_metricas_principales,
)


def calcular_metricas(
    db,
    persona_id: int,
    inflacion_mensual: Decimal = INFLACION_MENSUAL_DEFAULT,
) -> MetricasPrincipales:
    """Devuelve las métricas mediante el servicio de aplicación compuesto.

    Se conserva la firma que ya utiliza la pantalla principal. La UI no crea
    repositorios ni consulta tablas directamente.
    """
    servicio = crear_servicio_metricas_principales(db)
    return servicio.obtener(persona_id, inflacion_mensual)


def formatear_pesos(valor: Decimal) -> str:
    """Formatea un Decimal como $ 1.234.567,89."""
    negativo = valor < 0
    valor_abs = abs(valor)
    entero, decimales = f"{valor_abs:.2f}".split(".")
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    signo = "-" if negativo else ""
    return f"{signo}$ {entero_con_puntos},{decimales}"


def formatear_pesos_con_signo(valor: Decimal) -> str:
    """Formatea pesos e incluye el signo cuando el valor no es cero."""
    if valor > 0:
        return "+ " + formatear_pesos(valor)
    if valor < 0:
        return "- " + formatear_pesos(abs(valor))
    return formatear_pesos(valor)


def color_para_veredicto(veredicto: str) -> str:
    """Devuelve la clase visual asociada al resultado."""
    return {
        "creciendo": "color-verde",
        "achicandose": "color-rojo",
        "estable": "color-neutro",
    }.get(veredicto, "color-neutro")


def emoji_para_veredicto(veredicto: str) -> str:
    """Devuelve el icono de apoyo para el resultado."""
    return {
        "creciendo": "🟢",
        "achicandose": "🔴",
        "estable": "⚪",
    }.get(veredicto, "⚪")


__all__ = [
    "INFLACION_MENSUAL_DEFAULT",
    "MetricasPrincipales",
    "calcular_metricas",
    "formatear_pesos",
    "formatear_pesos_con_signo",
    "color_para_veredicto",
    "emoji_para_veredicto",
]
