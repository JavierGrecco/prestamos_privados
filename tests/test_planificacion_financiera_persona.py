"""Pruebas de planificación financiera personal."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.planificacion_financiera_persona import (
    ServicioPlanificacionFinancieraPersona,
)
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _persona(personas, nombre, documento, rol):
    persona_id = personas.crear(
        nombre=nombre,
        apellido="Plan",
        documento=documento,
    )
    personas.agregar_rol(persona_id, rol)
    return persona_id


def _crear_prestamo(db, deudor_id, inversor_id, capital, fecha_inicio):
    ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=capital,
        plazo_meses=6,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=fecha_inicio,
        inversores=[{"persona_id": inversor_id, "monto": capital}],
        usuario="test",
        destino="Planificación",
    )


def test_plan_de_deudor_muestra_pagos_futuros_y_reserva(
    tmp_path: Path,
):
    ruta = tmp_path / "plan_deuda.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Ana", "99991001", "DEUDOR")
        inversor = _persona(personas, "Pedro", "99991002", "INVERSOR")

        _crear_prestamo(
            db,
            deudor,
            inversor,
            Decimal("300000.00"),
            date(2026, 10, 8),
        )

        plan = ServicioPlanificacionFinancieraPersona(db).obtener(
            deudor,
            fecha_corte=date(2026, 10, 8),
            horizonte_meses=6,
        )

    assert plan.horizonte_meses == 6
    assert len(plan.movimientos_mensuales) == 6
    assert plan.cobros_estimados_total == Decimal("0.00")
    assert plan.pagos_estimados_total > Decimal("300000.00")
    assert plan.neto_estimado_total < Decimal("0.00")
    assert plan.reserva_sugerida > Decimal("0.00")
    assert plan.mes_mas_exigente is not None
    assert plan.pagos_estimados_total == -plan.neto_estimado_total


def test_plan_de_inversor_muestra_cobros_futuros(
    tmp_path: Path,
):
    ruta = tmp_path / "plan_inversion.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Carlos", "99991003", "DEUDOR")
        inversor = _persona(personas, "Lucía", "99991004", "INVERSOR")

        _crear_prestamo(
            db,
            deudor,
            inversor,
            Decimal("180000.00"),
            date(2026, 10, 8),
        )

        plan = ServicioPlanificacionFinancieraPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 10, 8),
            horizonte_meses=6,
        )

    assert plan.cobros_estimados_total > Decimal("180000.00")
    assert plan.pagos_estimados_total == Decimal("0.00")
    assert plan.neto_estimado_total == plan.cobros_estimados_total
    assert plan.reserva_sugerida == Decimal("0.00")
    assert all(not mes.requiere_reserva for mes in plan.movimientos_mensuales)


def test_plan_rechaza_horizonte_fuera_de_rango(tmp_path: Path):
    ruta = tmp_path / "plan_validacion.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        persona = _persona(personas, "Eva", "99991005", "DEUDOR")

        servicio = ServicioPlanificacionFinancieraPersona(db)

        for horizonte in (0, 61):
            try:
                servicio.obtener(
                    persona,
                    fecha_corte=date(2026, 10, 8),
                    horizonte_meses=horizonte,
                )
            except ValueError:
                pass
            else:
                raise AssertionError(
                    f"Se esperaba ValueError para horizonte {horizonte}"
                )
