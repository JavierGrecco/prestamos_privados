"""Regresiones de atomicidad para el alta completa de préstamos.

Si una etapa posterior falla, no deben quedar préstamo, tasa, cuotas,
participaciones, movimientos de ledger ni eventos de auditoría parciales.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos, ErrorTransaccion
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def alta_base(tmp_path: Path) -> tuple[Path, int, int]:
    """Prepara personas en una base migrada y la deja lista para el servicio."""
    ruta = tmp_path / "alta-atomica.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Deudor",
            apellido="Prueba atomica",
            documento="99881001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")

        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="Prueba atomica",
            documento="99881002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

    return ruta, deudor_id, inversor_id


def _crear_alta(
    servicio: ServicioPrestamos,
    deudor_id: int,
    inversor_id: int,
) -> int:
    return servicio.crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("10000.00"),
        plazo_meses=3,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": Decimal("10000.00")}
        ],
        usuario="test-atomicidad",
    )


def _assert_sin_registros_parciales(db: BaseDatos) -> None:
    """Comprueba que el rollback cubrió todas las escrituras del alta."""
    for tabla in (
        "prestamos",
        "versiones_tasa",
        "cuotas",
        "participaciones",
        "ledger",
        "auditoria",
        "condiciones_carencia",
    ):
        total = db.consultar_uno(f"SELECT COUNT(*) AS total FROM {tabla}")["total"]
        assert total == 0, f"quedaron {total} registros en {tabla}"

    assert db.consultar("PRAGMA foreign_key_check") == []
    assert db.verificar_integridad_completa() is True


def test_alta_completa_revierte_todo_si_falla_el_ledger(
    alta_base: tuple[Path, int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ruta, deudor_id, inversor_id = alta_base
    with BaseDatos(ruta) as db:
        servicio = ServicioPrestamos(db)
        registrar_original = servicio.ledger.registrar_operacion

        def registrar_y_fallar(**kwargs) -> None:
            registrar_original(**kwargs)
            raise RuntimeError("fallo inyectado después del ledger")

        monkeypatch.setattr(
            servicio.ledger,
            "registrar_operacion",
            registrar_y_fallar,
        )

        with pytest.raises(ErrorTransaccion, match="fallo inyectado"):
            _crear_alta(servicio, deudor_id, inversor_id)

        _assert_sin_registros_parciales(db)


def test_alta_completa_revierte_todo_si_falla_la_activacion_final(
    alta_base: tuple[Path, int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ruta, deudor_id, inversor_id = alta_base
    with BaseDatos(ruta) as db:
        servicio = ServicioPrestamos(db)
        actualizar_original = servicio.prestamos.actualizar_estado

        def actualizar_y_fallar(prestamo_id: int, nuevo_estado: str) -> None:
            actualizar_original(prestamo_id, nuevo_estado)
            if nuevo_estado == "ACTIVO":
                raise RuntimeError("fallo inyectado al activar el préstamo")

        monkeypatch.setattr(
            servicio.prestamos,
            "actualizar_estado",
            actualizar_y_fallar,
        )

        with pytest.raises(ErrorTransaccion, match="fallo inyectado"):
            _crear_alta(servicio, deudor_id, inversor_id)

        _assert_sin_registros_parciales(db)
