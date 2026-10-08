"""Pruebas del reporte financiero personal consolidado."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.reporte_financiero_persona import (
    ServicioReporteFinancieroPersona,
)
from aplicacion.servicios.exportaciones import ServicioExportaciones
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _persona(personas, nombre, documento, rol):
    persona_id = personas.crear(
        nombre=nombre,
        apellido="Reporte",
        documento=documento,
    )
    personas.agregar_rol(persona_id, rol)
    return persona_id


def test_reporte_sin_operaciones_no_inventa_datos(tmp_path: Path):
    with BaseDatos(tmp_path / "reporte_vacio.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        persona = _persona(personas, "Ana", "99994001", "DEUDOR")

        reporte = ServicioReporteFinancieroPersona(db).obtener(
            persona,
            fecha_corte=date(2026, 10, 8),
            inflacion_mensual_supuesta=Decimal("0.05"),
            horizonte_meses=6,
        )

    assert reporte.nombre_persona == "Ana Reporte"
    assert reporte.posicion.capital_invertido == Decimal("0.00")
    assert reporte.posicion.capital_deuda_pendiente == Decimal("0.00")
    assert reporte.posicion.posicion_neta_capital == Decimal("0.00")
    assert reporte.planificacion.cobros_estimados_total == Decimal("0.00")
    assert reporte.planificacion.pagos_estimados_total == Decimal("0.00")
    assert reporte.rendimiento.inversor is None
    assert reporte.rendimiento.deudor is None
    assert not reporte.escenarios.flujos_proyectados


def test_reporte_consolida_plan_escenarios_y_exportacion(tmp_path: Path):
    ruta = tmp_path / "reporte_completo.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Carlos", "99994002", "DEUDOR")
        inversor = _persona(personas, "Lucía", "99994003", "INVERSOR")

        ServicioPrestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("150000.00"),
            plazo_meses=6,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 10, 8),
            inversores=[{"persona_id": inversor, "monto": Decimal("150000.00")}],
            usuario="test",
            destino="Reporte completo",
        )

        antes = db.consultar_uno("SELECT COUNT(*) n FROM auditoria")["n"]

        reporte = ServicioReporteFinancieroPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 10, 8),
            inflacion_mensual_supuesta=Decimal("0.05"),
            horizonte_meses=6,
        )
        csv = ServicioExportaciones(db).reporte_financiero_persona_csv(
            inversor,
            fecha_corte=date(2026, 10, 8),
            inflacion_mensual_supuesta=Decimal("0.05"),
            horizonte_meses=6,
        )

        despues = db.consultar_uno("SELECT COUNT(*) n FROM auditoria")["n"]

    assert reporte.posicion.capital_invertido == Decimal("150000.00")
    assert reporte.planificacion.cobros_estimados_total > Decimal("150000.00")
    assert len(reporte.escenarios.resultados) == 4
    assert reporte.escenarios.flujos_proyectados
    assert "Posición" in csv
    assert "Plan futuro" in csv
    assert "Escenario" in csv
    assert "Rendimiento" in csv
    assert despues == antes
