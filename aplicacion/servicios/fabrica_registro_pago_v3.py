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
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
)
from dominio.tipos import ConvencionDias, ModalidadTasa
from .registro_pago_v3 import RegistrarPagoV3
from .registro_pago_v3_devengamientos import RegistrarPagoV3ConDevengamientos
from .registro_pago_v3_completo import RegistrarPagoV3Completo


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
):
    politica = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
            convencion_dias=convencion_dias,
        )
    )
    return RegistrarPagoV3ConDevengamientos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        PoliticaMoraContractualV3(),
    )


def crear_registrador_pago_v3_completo(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
):
    """Construye la ruta V3 con devengamientos y distribución a inversores."""
    politica = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
            convencion_dias=convencion_dias,
        )
    )
    return RegistrarPagoV3Completo(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        PoliticaMoraContractualV3(),
    )


def crear_registrador_pago_v3_completo_con_adelantos(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    sistema=None,
    recalcular_rai_fn=None,
    recalcular_rni_fn=None,
):
    """Construye V3 completo con RAI/RNI y recalculación histórica."""
    from dominio.tipos import SistemaAmortizacion
    politica = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
            convencion_dias=convencion_dias,
        )
    )
    return __import__(
        'aplicacion.servicios.registro_pago_v3_completo_adelantos',
        fromlist=['RegistrarPagoV3CompletoConAdelantos'],
    ).RegistrarPagoV3CompletoConAdelantos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        PoliticaMoraContractualV3(),
        recalcular_rai_fn=recalcular_rai_fn,
        recalcular_rni_fn=recalcular_rni_fn,
        sistema=sistema or SistemaAmortizacion.FRANCES,
    )
