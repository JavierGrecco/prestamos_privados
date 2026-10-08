"""Pruebas de exportaciones CSV de solo lectura."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios.auditoria import FiltrosAuditoria
from aplicacion.servicios.exportaciones import ServicioExportaciones
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import AuditoriaRepo, PersonaRepo
from infraestructura.repositorios.base import nuevo_correlacion_id


def crear_contexto(tmp_path: Path):
    ruta = tmp_path / "export.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = personas.crear(
            nombre="Ana María",
            apellido="García",
            documento="90000123",
        )
        inversor = personas.crear(
            nombre="José",
            apellido="Pérez",
            documento="90000456",
        )
        correlacion = nuevo_correlacion_id()
        AuditoriaRepo(db).registrar(
            usuario="operador",
            operacion="PRESTAMO_CREADO",
            entidad="PRESTAMO",
            entidad_id=1,
            correlacion_id=correlacion,
            datos_nuevos={"capital": "1000.00"},
            motivo="Alta",
        )
        prestamo_id = ServicioPrestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("1000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[{"persona_id": inversor, "monto": Decimal("1000.00")}],
            usuario="operador",
            destino="Prueba",
        )
        return ruta, prestamo_id


def test_exportaciones_generan_csv_legibles(tmp_path: Path):
    ruta, prestamo_id = crear_contexto(tmp_path)

    with BaseDatos(ruta) as db:
        servicio = ServicioExportaciones(db)

        auditoria = servicio.auditoria_csv(
            FiltrosAuditoria(entidad="PRESTAMO")
        )
        personas = servicio.personas_csv()
        amortizacion = servicio.amortizacion_csv(prestamo_id)

    assert auditoria.startswith(
        "id,fecha,usuario,operacion,entidad,entidad_id"
    )
    assert "PRESTAMO_CREADO" in auditoria
    assert personas.startswith(
        "id,nombre,apellido,documento,telefono,email,domicilio,estado,roles"
    )
    assert "Ana María" in personas
    assert "José" in personas
    assert amortizacion.startswith(
        "prestamo_id,prestamo_numero,cuota_id,numero,vencimiento,estado"
    )
    assert "1000.00" in amortizacion
    assert "2026-02" in amortizacion


def test_exportaciones_no_mutan_la_base(tmp_path: Path):
    ruta, prestamo_id = crear_contexto(tmp_path)

    with BaseDatos(ruta) as db:
        antes = db.consultar_uno(
            "SELECT COUNT(*) n FROM auditoria"
        )["n"]
        ServicioExportaciones(db).auditoria_csv()
        ServicioExportaciones(db).personas_csv()
        ServicioExportaciones(db).amortizacion_csv(prestamo_id)
        despues = db.consultar_uno(
            "SELECT COUNT(*) n FROM auditoria"
        )["n"]

    assert despues == antes
