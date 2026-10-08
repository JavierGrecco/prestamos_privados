"""Regresiones para la política de schema mínimo del preflight V3."""
from pathlib import Path

from aplicacion.servicios.preflight_motor_pago_v3 import (
    VERSION_MINIMA_SCHEMA_V3,
    PreflightMotorPagoV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


def test_preflight_por_defecto_usa_schema_minimo_canonico(tmp_path: Path):
    ruta = tmp_path / "schema-policy.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        with db.transaccion():
            db.ejecutar("DELETE FROM migraciones WHERE version >= ?", (VERSION_MINIMA_SCHEMA_V3,))

        resultado = PreflightMotorPagoV3(db).evaluar()

    criterio_schema = resultado.criterios[0]
    assert criterio_schema.nombre == "schema"
    assert criterio_schema.cumplido is False
    assert f"mínimo requerido v{VERSION_MINIMA_SCHEMA_V3:03d}" in criterio_schema.detalle


def test_configuracion_y_readiness_importan_el_mismo_baseline():
    from aplicacion.servicios.configuracion_motor_pago import (
        VERSION_MINIMA_SCHEMA_V3 as VERSION_CONFIG,
    )
    from aplicacion.servicios.precheck_canary_motor_pago_v3 import (
        VERSION_MINIMA_SCHEMA_V3 as VERSION_READINESS,
    )

    assert VERSION_CONFIG == VERSION_MINIMA_SCHEMA_V3
    assert VERSION_READINESS == VERSION_MINIMA_SCHEMA_V3
