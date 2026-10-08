"""Pruebas del preview canónico de pagos V3."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.preview_pago_v3 import ServicioPreviewPagoV3
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


def _db_con_prestamo(tmp_path: Path) -> BaseDatos:
    db = BaseDatos(tmp_path / "preview.db")
    db.abrir()
    aplicar_migraciones(db)

    db.ejecutar(
        "INSERT INTO personas (nombre, creado_en) VALUES ('Deudor', '2026-01-01')"
    )
    deudor = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES ('PR-PREVIEW', ?, 'ARS', '1000.00', 12, 'FRANCES', 'MENSUAL',
                '2026-10-01', 'ACTIVO', '2026-10-01')
        """,
        (deudor,),
    )
    prestamo = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO versiones_tasa
        (prestamo_id, version, fecha_desde, tasa_anual, modalidad_tasa, creado_en)
        VALUES (?, 1, '2026-10-01', '0.24', 'TNA', '2026-10-01')
        """,
        (prestamo,),
    )
    version = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO cuotas
        (version_id, numero, fecha_vencimiento, capital_inicial, interes, capital,
         cuota, saldo, monto_pendiente, interes_pendiente, capital_pendiente,
         mora_pendiente, fue_mora, tuvo_pago_parcial, fue_recalculada, estado,
         creado_en)
        VALUES (?, 1, '2026-11-01', '1000.00', '20.00', '80.00', '100.00',
                '80.00', '0.00', '0.00', '0.00', '0.00', 0, 0, 0,
                'PENDIENTE', '2026-10-01')
        """,
        (version,),
    )
    db.ejecutar(
        """
        INSERT INTO cuotas
        (version_id, numero, fecha_vencimiento, capital_inicial, interes, capital,
         cuota, saldo, monto_pendiente, interes_pendiente, capital_pendiente,
         mora_pendiente, fue_mora, tuvo_pago_parcial, fue_recalculada, estado,
         creado_en)
        VALUES (?, 2, '2026-12-01', '920.00', '18.00', '82.00', '100.00',
                '100.00', '0.00', '0.00', '100.00', '0.00', 0, 0, 0,
                'PENDIENTE', '2026-10-01')
        """,
        (version,),
    )
    return db


def test_preview_v3_no_persiste_y_compara_con_legacy(tmp_path: Path):
    db = _db_con_prestamo(tmp_path)
    try:
        antes = db.consultar("SELECT name FROM sqlite_master ORDER BY name")

        preview = ServicioPreviewPagoV3(db).previsualizar(
            prestamo_id=1,
            monto=Decimal("50.00"),
            fecha_valor=date(2026, 11, 1),
        )

        assert preview.plan.monto_pago_recibido == Decimal("50.00")
        assert preview.plan.aplicado_interes == Decimal("20.00")
        assert preview.plan.aplicado_mora == Decimal("0.00")
        assert preview.plan.monto_a_capital == Decimal("30.00")
        assert preview.plan.excedente.monto == Decimal("0.00")
        assert preview.comparacion_legacy is not None
        assert preview.comparacion_legacy.coincidente is True

        despues = db.consultar("SELECT name FROM sqlite_master ORDER BY name")
        assert antes == despues
        assert db.consultar_uno("SELECT COUNT(*) n FROM pagos")["n"] == 0
    finally:
        db.cerrar()


def test_preview_v3_explica_excedente_sin_decidir_rai_rni(tmp_path: Path):
    db = _db_con_prestamo(tmp_path)
    try:
        preview = ServicioPreviewPagoV3(db).previsualizar(
            prestamo_id=1,
            monto=Decimal("150.00"),
            fecha_valor=date(2026, 11, 1),
            opcion_adelanto=None,
        )

        assert preview.plan.excedente.monto == Decimal("50.00")
        assert preview.plan_adelanto is None

        preview_rai = ServicioPreviewPagoV3(db).previsualizar(
            prestamo_id=1,
            monto=Decimal("150.00"),
            fecha_valor=date(2026, 11, 1),
            opcion_adelanto="RAI",
        )
        assert preview_rai.plan_adelanto is not None
        assert preview_rai.plan_adelanto.tipo.value == "RAI"
    finally:
        db.cerrar()
