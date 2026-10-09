"""Condiciones contractuales inmutables para carencia inicial.

Este modelo prepara la persistencia de términos ya simulados. No crea un
préstamo ni define por sí solo la imputación de pagos. La versión operativa
inicial admite solamente tratamientos cuyo interés diferido puede seguir
separado del capital.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from .carencia import calcular_interes_carencia_simple
from .excepciones import ErrorValidacion
from .tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion, money


TRATAMIENTOS_CARENCIA_OPERATIVOS = frozenset({
    "SIN_INTERES",
    "DIFERIR_SIMPLE_PRIMERA_CUOTA",
    "DIFERIR_SIMPLE_DISTRIBUIDO",
})


@dataclass(frozen=True, slots=True)
class CondicionesCarencia:
    """Términos financieros calculados y listos para snapshot contractual."""

    capital_original: Decimal
    tasa_anual: Decimal
    modalidad_tasa: ModalidadTasa
    convencion_dias: ConvencionDias
    sistema: SistemaAmortizacion
    meses_carencia: int
    fecha_desembolso: date
    fecha_fin_carencia: date
    fecha_primer_vencimiento: date
    plazo_amortizacion_meses: int
    tratamiento: str
    interes_simple_referencia: Decimal
    interes_carencia_debido: Decimal
    interes_carencia_no_cobrado: Decimal

    def payload(self) -> dict[str, str | int]:
        """Representación estable solo de los términos económicos pactados."""
        return {
            "esquema_snapshot": 1,
            "capital_original": format(money(self.capital_original), ".2f"),
            "tasa_anual": format(self.tasa_anual.normalize(), "f"),
            "modalidad_tasa": self.modalidad_tasa.value,
            "convencion_dias": self.convencion_dias.value,
            "sistema": self.sistema.value,
            "meses_carencia": self.meses_carencia,
            "fecha_desembolso": self.fecha_desembolso.isoformat(),
            "fecha_fin_carencia": self.fecha_fin_carencia.isoformat(),
            "fecha_primer_vencimiento": self.fecha_primer_vencimiento.isoformat(),
            "plazo_amortizacion_meses": self.plazo_amortizacion_meses,
            "tratamiento": self.tratamiento,
            "interes_simple_referencia": format(
                money(self.interes_simple_referencia), ".2f"
            ),
            "interes_carencia_debido": format(
                money(self.interes_carencia_debido), ".2f"
            ),
            "interes_carencia_no_cobrado": format(
                money(self.interes_carencia_no_cobrado), ".2f"
            ),
        }


def json_canonico(payload: dict) -> str:
    """Serializa JSON determinista para que el hash sea repetible."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def hash_snapshot(payload_o_json: dict | str) -> str:
    """Calcula SHA-256 hexadecimal de un payload/dato JSON canónico."""
    contenido = (
        json_canonico(payload_o_json)
        if isinstance(payload_o_json, dict)
        else payload_o_json
    )
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def verificar_hash_snapshot(snapshot_json: str, snapshot_sha256: str) -> bool:
    """Comprueba que un snapshot almacenado conserva sus bytes canónicos."""
    try:
        payload = json.loads(snapshot_json)
    except (TypeError, json.JSONDecodeError):
        return False
    return (
        json_canonico(payload) == snapshot_json
        and hash_snapshot(snapshot_json) == snapshot_sha256
    )


def crear_condiciones_carencia(
    *,
    capital_original: Decimal,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    sistema: SistemaAmortizacion,
    meses_carencia: int,
    fecha_desembolso: date,
    plazo_amortizacion_meses: int,
    tratamiento: str,
) -> CondicionesCarencia:
    """Valida términos y calcula importes de interés de carencia.

    El primer vencimiento regular es un mes después del fin de carencia.
    Solo acepta tratamientos preparados para una futura integración con
    imputación de intereses separada. El pago de intereses durante la carencia
    requiere cuotas de gracia propias y la capitalización continúa fuera del
    contrato operativo.
    """
    if capital_original <= 0:
        raise ErrorValidacion("El capital original debe ser mayor a cero")
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if meses_carencia <= 0:
        raise ErrorValidacion("La carencia contractual debe ser de al menos un mes")
    if plazo_amortizacion_meses <= 0:
        raise ErrorValidacion("El plazo de amortización debe ser mayor a cero")
    if tratamiento not in TRATAMIENTOS_CARENCIA_OPERATIVOS:
        raise ErrorValidacion(
            "El tratamiento aún no está habilitado para contratos reales. "
            "Se admite SIN_INTERES, DIFERIR_SIMPLE_PRIMERA_CUOTA o "
            "DIFERIR_SIMPLE_DISTRIBUIDO."
        )
    if sistema not in {SistemaAmortizacion.FRANCES, SistemaAmortizacion.ALEMAN}:
        raise ErrorValidacion(
            "La carencia contractual inicial solo admite amortización FRANCES o ALEMAN"
        )

    fecha_fin = fecha_desembolso + relativedelta(months=meses_carencia)
    fecha_primer_vencimiento = fecha_fin + relativedelta(months=1)
    resultado = calcular_interes_carencia_simple(
        capital=capital_original,
        tasa_anual=tasa_anual,
        modalidad=modalidad_tasa,
        convencion=convencion_dias,
        fecha_inicio=fecha_desembolso,
        fecha_fin=fecha_fin,
    )
    interes_referencia = money(resultado.interes_total)

    if tratamiento == "SIN_INTERES":
        interes_debido = Decimal("0.00")
        interes_no_cobrado = interes_referencia
    else:
        interes_debido = interes_referencia
        interes_no_cobrado = Decimal("0.00")

    return CondicionesCarencia(
        capital_original=money(capital_original),
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
        sistema=sistema,
        meses_carencia=meses_carencia,
        fecha_desembolso=fecha_desembolso,
        fecha_fin_carencia=fecha_fin,
        fecha_primer_vencimiento=fecha_primer_vencimiento,
        plazo_amortizacion_meses=plazo_amortizacion_meses,
        tratamiento=tratamiento,
        interes_simple_referencia=interes_referencia,
        interes_carencia_debido=money(interes_debido),
        interes_carencia_no_cobrado=money(interes_no_cobrado),
    )
