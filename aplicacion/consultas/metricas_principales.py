"""Cálculo de las métricas principales a partir de una lectura preparada.

Este módulo no conoce SQLite ni repositorios. Recibe los datos que necesita
y explica, de forma consistente, cómo se obtiene el resultado mostrado en el
resumen de la persona.
"""
from dataclasses import dataclass
from decimal import Decimal


INFLACION_MENSUAL_DEFAULT = Decimal("0.05")


@dataclass(frozen=True)
class DatosMetricasPrincipales:
    """Datos financieros mínimos obtenidos por una consulta de lectura."""

    capital_invertido: Decimal
    capital_adeudado: Decimal
    tasa_anual: Decimal | None = None
    modalidad_tasa: str | None = None


@dataclass
class MetricasPrincipales:
    """Resultado que la pantalla principal explica a la persona."""

    capital_invertido: Decimal
    capital_adeudado: Decimal
    efecto_inversion: Decimal
    efecto_deuda: Decimal
    efecto_neto: Decimal
    veredicto: str
    mensaje_principal: str
    detalle_inversion: str
    detalle_deuda: str
    inflacion_mensual: Decimal


def calcular_metricas_principales(
    datos: DatosMetricasPrincipales,
    inflacion_mensual: Decimal = INFLACION_MENSUAL_DEFAULT,
) -> MetricasPrincipales:
    """Calcula el efecto anual estimado con los datos de la persona.

    Se conserva la regla vigente: la inversión se considera al ritmo de la
    inflación hasta que exista una estimación de rendimiento aprobada. Para
    la deuda se compara la inflación anualizada con la tasa del primer
    préstamo activo que entrega la consulta de lectura.

    Esta extracción no cambia la fórmula ni la selección actual de tasa.
    """
    capital_invertido = datos.capital_invertido
    capital_adeudado = datos.capital_adeudado

    # Hasta incorporar el rendimiento real aprobado, la inversión empata con
    # la inflación. No se presenta una ganancia que todavía no se calculó.
    rendimiento_real_inversion = Decimal("0")
    efecto_inversion = capital_invertido * rendimiento_real_inversion

    efecto_deuda = Decimal("0")
    if (
        capital_adeudado > 0
        and datos.tasa_anual is not None
        and datos.modalidad_tasa is not None
    ):
        tasa_anual = datos.tasa_anual
        if datos.modalidad_tasa == "TNA":
            tasa_mensual = tasa_anual / Decimal("12")
        else:
            # Se conserva la conversión histórica de TEA a TEM. Su precisión
            # debe revisarse como tarea separada, con pruebas financieras
            # propias, para no mezclar esa decisión con esta modularización.
            tasa_mensual = Decimal(
                str((1 + float(tasa_anual)) ** (1 / 12) - 1)
            )

        inflacion_anual = (
            (Decimal("1") + inflacion_mensual) ** 12 - Decimal("1")
        )
        factor_tasa = (
            (Decimal("1") + tasa_mensual) ** 12 - Decimal("1")
        )
        if factor_tasa > 0:
            efecto_real = (
                (Decimal("1") + inflacion_anual)
                / (Decimal("1") + factor_tasa)
                - Decimal("1")
            )
            efecto_deuda = capital_adeudado * efecto_real

    efecto_neto = efecto_inversion + efecto_deuda
    veredicto, mensaje = _veredicto(efecto_neto)

    return MetricasPrincipales(
        capital_invertido=capital_invertido,
        capital_adeudado=capital_adeudado,
        efecto_inversion=efecto_inversion,
        efecto_deuda=efecto_deuda,
        efecto_neto=efecto_neto,
        veredicto=veredicto,
        mensaje_principal=mensaje,
        detalle_inversion=_detalle_inversion(
            capital_invertido,
            rendimiento_real_inversion,
        ),
        detalle_deuda=_detalle_deuda(capital_adeudado, efecto_deuda),
        inflacion_mensual=inflacion_mensual,
    )


def _veredicto(efecto_neto: Decimal) -> tuple[str, str]:
    """Traduce el resultado anual a una explicación fácil de entender."""
    umbral = Decimal("10000")
    if efecto_neto > umbral:
        return "creciendo", "Este año tu plata está creciendo"
    if efecto_neto < -umbral:
        return "achicandose", "Este año tu plata se está achicando"
    return "estable", "Este año tu plata está estable"


def _detalle_inversion(capital: Decimal, rendimiento_real: Decimal) -> str:
    """Explica qué significa el rendimiento disponible."""
    if capital == 0:
        return "Todavía no tenés inversiones activas."
    if rendimiento_real > Decimal("0.02"):
        return "Le está ganando a la inflación"
    if rendimiento_real < Decimal("-0.02"):
        return "La inflación le está ganando"
    return "Va al ritmo de la inflación"


def _detalle_deuda(capital: Decimal, efecto: Decimal) -> str:
    """Explica cómo se compara la deuda con la inflación."""
    if capital == 0:
        return "Todavía no tenés deudas activas."
    if efecto > Decimal("0"):
        return "Se achica sola con la inflación"
    if efecto < Decimal("0"):
        return "Crece más rápido que la inflación"
    return "Crece al ritmo de la inflación"


__all__ = [
    "DatosMetricasPrincipales",
    "INFLACION_MENSUAL_DEFAULT",
    "MetricasPrincipales",
    "calcular_metricas_principales",
]
