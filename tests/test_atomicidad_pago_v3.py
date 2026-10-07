"""H2: demuestra atomicidad de la ruta V3 completa ante fallas inyectadas.

Las pruebas provocan una excepción después de etapas críticas y verifican que
el rollback deja la base exactamente igual al snapshot tomado antes de iniciar
la operación.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from aplicacion.servicios.registro_pago_v3_completo import RegistrarPagoV3Completo
from dominio.devengamiento_v3 import PoliticaInteres
from dominio.politica_devengamiento_v3 import PoliticaInteresCapitalPendiente
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)
from infraestructura.repositorios import PersonaRepo


class _RepositorioConFallo:
    """Decorador de test que inyecta una falla después de una etapa."""

    def __init__(self, interno, etapa: str) -> None:
        self._interno = interno
        self._etapa = etapa

    def __getattr__(self, nombre):
        return getattr(self._interno, nombre)

    def persistir_pago_y_devengamientos(self, *args, **kwargs):
        resultado = self._interno.persistir_pago_y_devengamientos(*args, **kwargs)
        if self._etapa == "DESPUES_PERSISTENCIA":
            raise RuntimeError("fallo H2 después de persistir pago y devengamientos")
        return resultado

    def persistir_distribucion_inversores(self, *args, **kwargs):
        resultado = self._interno.persistir_distribucion_inversores(*args, **kwargs)
        if self._etapa == "DESPUES_DISTRIBUCION":
            raise RuntimeError("fallo H2 después de persistir distribución")
        return resultado


def _crear_prestamo(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="H2")
    inversor_a = personas.crear(nombre="Inversor", apellido="A")
    inversor_b = personas.crear(nombre="Inversor", apellido="B")

    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_a, "monto": Decimal("600000")},
            {"persona_id": inversor_b, "monto": Decimal("400000")},
        ],
        usuario="h2",
        destino="Escenario H2",
    )


def _snapshot_db(db: BaseDatos):
    """Snapshot determinista de las tablas de aplicación."""
    tablas = db.consultar(
        """SELECT name
           FROM sqlite_master
           WHERE type = 'table'
             AND name NOT LIKE 'sqlite_%'
           ORDER BY name"""
    )
    snapshot = []
    for tabla in tablas:
        nombre = str(tabla["name"])
        filas = db.consultar(f'SELECT * FROM "{nombre}" ORDER BY rowid')
        snapshot.append(
            (nombre, tuple(tuple(fila) for fila in filas))
        )
    return tuple(snapshot)


def _crear_servicio_v3_con_fallo(db: BaseDatos, etapa: str):
    politica = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=Decimal("0.30"),
            modalidad_tasa=ModalidadTasa.TNA,
            convencion_dias=ConvencionDias.ACTUAL_365,
        )
    )
    repositorio = _RepositorioConFallo(
        RepositorioRegistroPagoSQLiteV3(db), etapa
    )
    return RegistrarPagoV3Completo(repositorio, politica)


def _command_para_pago(db: BaseDatos, prestamo_id: int) -> RegistrarPagoCommand:
    deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None
    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="h2",
        idempotency_key="H2-ATOMICIDAD",
    )


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "h2.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.mark.parametrize(
    "etapa",
    ["DESPUES_PERSISTENCIA", "DESPUES_DISTRIBUCION"],
)
def test_h2_falla_despues_de_etapa_critica_revierte_toda_la_operacion(db, etapa):
    prestamo_id = _crear_prestamo(db)
    command = _command_para_pago(db, prestamo_id)
    antes = _snapshot_db(db)

    servicio = _crear_servicio_v3_con_fallo(db, etapa)

    with pytest.raises(RuntimeError, match="fallo H2"):
        servicio.ejecutar(command)

    despues = _snapshot_db(db)
    assert despues == antes
