"""
Cálculo de las métricas principales que se muestran en la pantalla.

Este módulo traduce los datos crudos de la base de datos en los
números que el usuario ve. Toda la lógica de "qué significa este
número" vive acá, no en la UI.

El número principal del sistema es el "efecto neto real":
  cuánto crece o decrece el patrimonio del usuario por año,
  en poder de compra, sumando sus inversiones y sus deudas.

La idea es responder a la pregunta:
  "¿Mi plata está ganando o perdiendo?"
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from infraestructura.db import BaseDatos
from infraestructura.repositorios import (
    PersonaRepo,
    PrestamoRepo,
    ParticipacionRepo,
    LedgerRepo,
)


@dataclass
class MetricasPrincipales:
    """
    Resultado del cálculo de las métricas de la pantalla principal.

    Atributos:
        capital_invertido: suma de todos los aportes activos.
        capital_adeudado: suma de saldos pendientes de préstamos.
        efecto_inversion: cuánto aporta la inversión al año (real).
        efecto_deuda: cuánto aporta la deuda al año (real).
        efecto_neto: suma de ambos. Es EL número grande.
        veredicto: 'creciendo' | 'achicandose' | 'estable'.
        mensaje_principal: frase para mostrar bajo el número.
        detalle_inversion: texto explicativo de la inversión.
        detalle_deuda: texto explicativo de la deuda.
        inflacion_mensual: inflación usada en el cálculo.
    """
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


# Inflación mensual de referencia para los cálculos.
# En una versión futura esto viene del IPC del INDEC o de la
# configuración del usuario. Por ahora, un valor conservador.
INFLACION_MENSUAL_DEFAULT = Decimal("0.05")


def calcular_metricas(
    db: BaseDatos,
    persona_id: int,
    inflacion_mensual: Decimal = INFLACION_MENSUAL_DEFAULT,
) -> MetricasPrincipales:
    """
    Calcula las métricas principales para una persona.

    Suma todas sus posiciones como inversor y como deudor, y
    calcula el efecto neto real de cada una.
    """
    # 1. Capital invertido: suma de participaciones activas
    participaciones_repo = ParticipacionRepo(db)
    participaciones = participaciones_repo.por_inversor(persona_id)
    participaciones_activas = [p for p in participaciones if p.estado == "ACTIVA"]
    capital_invertido = sum(
        (p.capital_aportado for p in participaciones_activas),
        Decimal("0"),
    )

    # 2. Capital adeudado: saldo pendiente de préstamos donde
    # la persona es deudora
    prestamos_repo = PrestamoRepo(db)
    prestamos_como_deudor = prestamos_repo.listar(deudor_id=persona_id)
    capital_adeudado = Decimal("0")
    for prestamo in prestamos_como_deudor:
        if prestamo.estado not in ("ACTIVO", "EN_MORA"):
            continue
        version_id = prestamos_repo.version_activa(prestamo.id)
        if version_id is None:
            continue
        cuotas = prestamos_repo.cuotas(version_id)
        cuotas_pendientes = [
            c for c in cuotas
            if c.estado in ("PENDIENTE", "PARCIAL", "VENCIDA")
        ]
        if cuotas_pendientes:
            capital_adeudado += cuotas_pendientes[0].capital_inicial

    # 3. Efecto real de la inversión:
    # Por ahora asumimos un rendimiento real del 0% (empata con
    # inflación). En una versión futura se calcula con XIRR real.
    rendimiento_real_inversion = Decimal("0")
    efecto_inversion = capital_invertido * rendimiento_real_inversion

    # 4. Efecto real de la deuda (licuación):
    # (1 + inflación) / (1 + tasa) - 1
    # Si es positivo, la deuda se licúa a favor del deudor.
    efecto_deuda = Decimal("0")
    if capital_adeudado > 0 and prestamos_como_deudor:
        # Tomamos el primer préstamo activo para calcular la tasa
        prestamo_activo = next(
            (p for p in prestamos_como_deudor
             if p.estado in ("ACTIVO", "EN_MORA")),
            None,
        )
        if prestamo_activo:
            version_id = prestamos_repo.version_activa(prestamo_activo.id)
            if version_id is not None:
                fila = db.consultar_uno(
                    "SELECT tasa_anual, modalidad_tasa FROM versiones_tasa WHERE id = ?",
                    (version_id,),
                )
                if fila:
                    tasa_anual = Decimal(fila["tasa_anual"])
                    # Si es TNA, convertir a tasa mensual, si es TEA, idem
                    if fila["modalidad_tasa"] == "TNA":
                        tasa_mensual = tasa_anual / Decimal("12")
                    else:
                        # TEA a TEM
                        tasa_mensual = (
                            Decimal(str((1 + float(tasa_anual)) ** (1/12) - 1))
                        )
                    # Anualizamos ambos para el cálculo del efecto real
                    inflacion_anual = (Decimal("1") + inflacion_mensual) ** 12 - Decimal("1")
                    factor_tasa = (Decimal("1") + tasa_mensual) ** 12 - Decimal("1")
                    if factor_tasa > 0:
                        efecto_real = (
                            (Decimal("1") + inflacion_anual)
                            / (Decimal("1") + factor_tasa)
                            - Decimal("1")
                        )
                        efecto_deuda = capital_adeudado * efecto_real

    efecto_neto = efecto_inversion + efecto_deuda

    # 5. Veredicto y mensajes
    veredicto, mensaje = _veredicto(efecto_neto)
    detalle_inv = _detalle_inversion(capital_invertido, rendimiento_real_inversion)
    detalle_deu = _detalle_deuda(capital_adeudado, efecto_deuda)

    return MetricasPrincipales(
        capital_invertido=capital_invertido,
        capital_adeudado=capital_adeudado,
        efecto_inversion=efecto_inversion,
        efecto_deuda=efecto_deuda,
        efecto_neto=efecto_neto,
        veredicto=veredicto,
        mensaje_principal=mensaje,
        detalle_inversion=detalle_inv,
        detalle_deuda=detalle_deu,
        inflacion_mensual=inflacion_mensual,
    )


def _veredicto(efecto_neto: Decimal) -> tuple[str, str]:
    """
    Determina el veredicto y el mensaje según el efecto neto.

    Los umbrales:
      >  $10.000 al año  → está creciendo
      < -$10.000 al año  → está achicándose
      entre esos dos     → está estable
    """
    umbral = Decimal("10000")
    if efecto_neto > umbral:
        return "creciendo", "Este año tu plata está creciendo"
    elif efecto_neto < -umbral:
        return "achicandose", "Este año tu plata se está achicando"
    else:
        return "estable", "Este año tu plata está estable"


def _detalle_inversion(capital: Decimal, rendimiento_real: Decimal) -> str:
    """Genera el texto explicativo de la inversión."""
    if capital == 0:
        return "Todavía no tenés inversiones activas."

    if rendimiento_real > Decimal("0.02"):
        return "Le está ganando a la inflación"
    elif rendimiento_real < Decimal("-0.02"):
        return "La inflación le está ganando"
    else:
        return "Va al ritmo de la inflación"


def _detalle_deuda(capital: Decimal, efecto: Decimal) -> str:
    """Genera el texto explicativo de la deuda."""
    if capital == 0:
        return "Todavía no tenés deudas activas."

    if efecto > Decimal("0"):
        return "Se achica sola con la inflación"
    elif efecto < Decimal("0"):
        return "Crece más rápido que la inflación"
    else:
        return "Crece al ritmo de la inflación"


def formatear_pesos(valor: Decimal) -> str:
    """
    Formatea un Decimal como $ 1.234.567,89.

    Si el valor es negativo, mantiene el signo.
    """
    negativo = valor < 0
    valor_abs = abs(valor)
    entero, decimales = f"{valor_abs:.2f}".split(".")
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    signo = "-" if negativo else ""
    return f"{signo}$ {entero_con_puntos},{decimales}"


def formatear_pesos_con_signo(valor: Decimal) -> str:
    """Igual que formatear_pesos pero siempre muestra + o -."""
    if valor > 0:
        return "+ " + formatear_pesos(valor)
    elif valor < 0:
        return "- " + formatear_pesos(abs(valor))
    else:
        return formatear_pesos(valor)


def color_para_veredicto(veredicto: str) -> str:
    """Devuelve el color CSS según el veredicto."""
    return {
        "creciendo": "color-verde",
        "achicandose": "color-rojo",
        "estable": "color-neutro",
    }.get(veredicto, "color-neutro")


def emoji_para_veredicto(veredicto: str) -> str:
    """Devuelve el emoji según el veredicto."""
    return {
        "creciendo": "🟢",
        "achicandose": "🔴",
        "estable": "⚪",
    }.get(veredicto, "⚪")