"""Caracterización multi-escenario del preview Legacy/V3.

Estas pruebas convierten la equivalencia del preview en un contrato observable.
No retiran Legacy: identifican explícitamente si una divergencia aparece en un
escenario financiero representativo.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.preview_pago import ServicioPreviewPago
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _db_con_prestamo(tmp_path: Path) -> BaseDatos:
    ruta = tmp_path / "preview-matriz.db"
    db = BaseDatos(ruta)
    db.abrir()
    aplicar_migraciones(db)

    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor", apellido="J17-4")
    inversor = personas.crear(nombre="Inversor", apellido="J17-4")

    ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("1000000"),
        plazo_meses=6,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 10, 1),
        inversores=[{"persona_id": inversor, "monto": Decimal("1000000")}],
        usuario="j17-4",
    )
    return db


@pytest.mark.parametrize(
    ("nombre", "monto", "fecha", "opcion", "debe_coincidir"),
    [
        ("cuota_exacta", Decimal("100000"), date(2026, 11, 1), None, True),
        ("pago_parcial", Decimal("50000"), date(2026, 11, 1), None, True),
        ("pago_vencido", Decimal("50000"), date(2026, 12, 1), None, False),
        ("excedente_sin_decidir", Decimal("300000"), date(2026, 11, 1), None, True),
        ("adelanto_rai", Decimal("300000"), date(2026, 11, 1), "RAI", True),
        ("adelanto_rni", Decimal("300000"), date(2026, 11, 1), "RNI", True),
    ],
)
def test_preview_caracteriza_escenario_y_conserva_equivalencia(
    tmp_path: Path,
    nombre: str,
    monto: Decimal,
    fecha: date,
    opcion: str | None,
    debe_coincidir: bool,
):
    db = _db_con_prestamo(tmp_path)
    try:
        preview = ServicioPreviewPago(db).previsualizar_por_modo(
            modo="V3",
            prestamo_id=1,
            monto=monto,
            fecha_real=fecha,
            fecha_valor=fecha,
            opcion_adelanto=opcion,
        )

        assert preview.comparacion_legacy is not None, nombre
        assert preview.comparacion_legacy.coincidente is debe_coincidir, (
            f"{nombre}: "
            f"deuda={preview.comparacion_legacy.diferencia_total_deuda}, "
            f"mora={preview.comparacion_legacy.mora_v3 - preview.comparacion_legacy.mora_legacy}, "
            f"interes={preview.comparacion_legacy.interes_v3 - preview.comparacion_legacy.interes_legacy}, "
            f"capital={preview.comparacion_legacy.capital_v3 - preview.comparacion_legacy.capital_legacy}, "
            f"excedente={preview.comparacion_legacy.excedente_v3 - preview.comparacion_legacy.excedente_legacy}"
        )

        if opcion is None:
            assert preview.plan_adelanto is None

        if opcion in ("RAI", "RNI"):
            assert preview.plan_adelanto is not None
            assert preview.plan_adelanto.tipo.value == opcion

        assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == 0
    finally:
        db.cerrar()


def test_preview_con_arrastre_despues_de_un_pago_parcial(tmp_path: Path):
    db = _db_con_prestamo(tmp_path)
    try:
        servicio_legacy = ServicioPagos(db)
        servicio_legacy.registrar_pago(
            prestamo_id=1,
            monto=Decimal("50000"),
            fecha_real=date(2026, 11, 1),
            usuario="j17-4",
        )

        preview = ServicioPreviewPago(db).previsualizar_por_modo(
            modo="V3",
            prestamo_id=1,
            monto=Decimal("50000"),
            fecha_real=date(2026, 12, 1),
            fecha_valor=date(2026, 12, 1),
        )

        assert preview.comparacion_legacy is not None
        assert preview.comparacion_legacy.coincidente is False
        assert (
            preview.comparacion_legacy.interes_v3
            < preview.comparacion_legacy.interes_legacy
        )
        assert (
            preview.comparacion_legacy.capital_v3
            > preview.comparacion_legacy.capital_legacy
        )
        assert (
            preview.comparacion_legacy.diferencia_total_deuda == Decimal("0.00")
        )

        assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == 1
    finally:
        db.cerrar()
