"""Fábrica de la ruta de registro de pagos V3.

Permite que Streamlit/otros entrypoints obtengan el caso de uso completo sin
conocer el adaptador SQLite concreto. Todavía no reemplaza el servicio legacy.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Any

from infraestructura.db import BaseDatos
from infraestructura.repositorios.registro_pago_v3 import RepositorioRegistroPagoSQLiteV3
from dominio.devengamiento_v3 import PoliticaInteres
from dominio.politica_pago import PoliticaImputacionPago
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
)
from dominio.tipos import ConvencionDias, ModalidadTasa
from .registro_pago_v3 import RegistrarPagoV3
from .registro_pago_v3_devengamientos import RegistrarPagoV3ConDevengamientos
from .registro_pago_v3_completo import RegistrarPagoV3Completo



def _resolver_politicas_v3(
    politica_pago: PoliticaImputacionPago | None,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
):
    politica_pago = politica_pago or PoliticaImputacionPago.canonica()
    politica_interes = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
            convencion_dias=convencion_dias,
        )
    )
    politica_mora = (
        PoliticaMoraContractualV3(
            tasa_anual=politica_pago.mora_tasa_anual,
            convencion_dias=politica_pago.mora_convencion_dias,
            base=politica_pago.mora_base,
        )
        if politica_pago.mora_habilitada
        else None
    )
    return politica_interes, politica_mora, politica_pago

def crear_registrador_pago_v3(
    db: BaseDatos,
    calculador_plan: Callable[..., Any] | None = None,
) -> RegistrarPagoV3:
    """Construye el caso de uso V3 con SQLite como infraestructura."""
    repositorio = RepositorioRegistroPagoSQLiteV3(db)
    if calculador_plan is None:
        return RegistrarPagoV3(repositorio)
    return RegistrarPagoV3(repositorio, calculador_plan)


def crear_registrador_pago_v3_con_devengamientos(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
):
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return RegistrarPagoV3ConDevengamientos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
    )


def crear_registrador_pago_v3_completo(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
):
    """Construye la ruta V3 con devengamientos y distribución a inversores."""
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return RegistrarPagoV3Completo(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
    )


def crear_registrador_pago_v3_completo_con_adelantos(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
    sistema=None,
    recalcular_rai_fn=None,
    recalcular_rni_fn=None,
):
    """Construye V3 completo con RAI/RNI y recalculación histórica."""
    from dominio.tipos import SistemaAmortizacion
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return __import__(
        'aplicacion.servicios.registro_pago_v3_completo_adelantos',
        fromlist=['RegistrarPagoV3CompletoConAdelantos'],
    ).RegistrarPagoV3CompletoConAdelantos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
        recalcular_rai_fn=recalcular_rai_fn,
        recalcular_rni_fn=recalcular_rni_fn,
        sistema=sistema or SistemaAmortizacion.FRANCES,
    )
