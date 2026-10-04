"""
Tests de los repositorios de pagos, ledger, TC y auditoría.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import (
    PersonaRepo,
    PrestamoRepo,
    PagoRepo,
    LedgerRepo,
    TipoCambioRepo,
    AuditoriaRepo,
)


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "test.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.fixture
def contexto(db):
    """Crea un préstamo listo para usar en los tests."""
    personas = PersonaRepo(db)
    prestamos = PrestamoRepo(db)

    deudor_id = personas.crear(nombre="Juan")
    prestamo_id = prestamos.crear(
        deudor_id=deudor_id,
        capital_original=Decimal("1000000"),
        plazo_meses=12,
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
    )
    return {
        "db": db,
        "prestamo_id": prestamo_id,
        "deudor_id": deudor_id,
        "pago_repo": PagoRepo(db),
        "ledger_repo": LedgerRepo(db),
        "tc_repo": TipoCambioRepo(db),
        "auditoria_repo": AuditoriaRepo(db),
    }


# ================================================================
# Pagos
# ================================================================

class TestPagoRepo:

    def test_registrar_pago_simple(self, contexto):
        """Registra un pago con una sola imputación."""
        repo = contexto["pago_repo"]
        pid = repo.registrar(
            prestamo_id=contexto["prestamo_id"],
            fecha_real=date(2026, 2, 1),
            monto_moneda_pago=Decimal("100000"),
            imputaciones=[
                {"cuota_id": None, "concepto": "INTERES", "monto": Decimal("100000")},
            ],
        )
        pago = repo.obtener(pid)
        assert pago is not None
        assert pago.monto_moneda_pago == Decimal("100000")
        assert pago.estado == "VALIDA"

    def test_registrar_pago_con_multiples_imputaciones(self, contexto):
        """Un pago puede cubrir interés y capital."""
        repo = contexto["pago_repo"]
        pid = repo.registrar(
            prestamo_id=contexto["prestamo_id"],
            fecha_real=date(2026, 2, 1),
            monto_moneda_pago=Decimal("849031.53"),
            imputaciones=[
                {"cuota_id": None, "concepto": "INTERES", "monto": Decimal("500000")},
                {"cuota_id": None, "concepto": "CAPITAL", "monto": Decimal("349031.53")},
            ],
        )
        imps = repo.imputaciones_de(pid)
        assert len(imps) == 2
        assert imps[0].concepto == "INTERES"
        assert imps[1].concepto == "CAPITAL"

    def test_monto_positivo(self, contexto):
        """Rechaza montos <= 0."""
        repo = contexto["pago_repo"]
        with pytest.raises(ValueError):
            repo.registrar(
                prestamo_id=contexto["prestamo_id"],
                fecha_real=date(2026, 2, 1),
                monto_moneda_pago=Decimal("0"),
                imputaciones=[{"cuota_id": None, "concepto": "INTERES", "monto": 0}],
            )

    def test_imputaciones_obligatorias(self, contexto):
        """Un pago sin imputaciones es inválido."""
        repo = contexto["pago_repo"]
        with pytest.raises(ValueError):
            repo.registrar(
                prestamo_id=contexto["prestamo_id"],
                fecha_real=date(2026, 2, 1),
                monto_moneda_pago=Decimal("1000"),
                imputaciones=[],
            )

    def test_suma_imputaciones_igual_monto(self, contexto):
        """Si la suma de imputaciones ≠ monto, se rechaza."""
        repo = contexto["pago_repo"]
        with pytest.raises(ValueError) as exc:
            repo.registrar(
                prestamo_id=contexto["prestamo_id"],
                fecha_real=date(2026, 2, 1),
                monto_moneda_pago=Decimal("1000"),
                imputaciones=[
                    {"cuota_id": None, "concepto": "INTERES", "monto": Decimal("500")},
                    # Falta cubrir 500
                ],
            )
        assert "no coincide" in str(exc.value).lower()

    def test_anular_pago(self, contexto):
        """Anular cambia el estado pero no borra."""
        repo = contexto["pago_repo"]
        pid = repo.registrar(
            prestamo_id=contexto["prestamo_id"],
            fecha_real=date(2026, 2, 1),
            monto_moneda_pago=Decimal("1000"),
            imputaciones=[
                {"cuota_id": None, "concepto": "INTERES", "monto": Decimal("1000")},
            ],
        )
        repo.anular(pid, motivo="Duplicado")
        pago = repo.obtener(pid)
        assert pago.estado == "ANULADA"
        assert pago.motivo_anulacion == "Duplicado"
        # Las imputaciones siguen ahí
        assert len(repo.imputaciones_de(pid)) == 1

    def test_anular_sin_motivo_falla(self, contexto):
        """Se requiere un motivo para anular."""
        repo = contexto["pago_repo"]
        pid = repo.registrar(
            prestamo_id=contexto["prestamo_id"],
            fecha_real=date(2026, 2, 1),
            monto_moneda_pago=Decimal("1000"),
            imputaciones=[
                {"cuota_id": None, "concepto": "INTERES", "monto": Decimal("1000")},
            ],
        )
        with pytest.raises(ValueError):
            repo.anular(pid, motivo="")


# ================================================================
# Ledger
# ================================================================

class TestLedgerRepo:

    def test_movimiento_simple(self, contexto):
        """Registra un movimiento y lo recupera."""
        repo = contexto["ledger_repo"]
        mid = repo.registrar_movimiento(
            entidad="PRESTAMO",
            entidad_id=contexto["prestamo_id"],
            tipo_movimiento="APORTE",
            debe=Decimal("1000000"),
            haber=Decimal("0"),
            fecha=date(2026, 1, 1),
            correlacion_id="test-001",
        )
        movs = repo.por_entidad("PRESTAMO", contexto["prestamo_id"])
        assert len(movs) == 1
        assert movs[0].debe == Decimal("1000000")
        assert movs[0].haber == Decimal("0")

    def test_doble_entrada_cuadra(self, contexto):
        """Una operación con debe=haber se acepta."""
        repo = contexto["ledger_repo"]
        ids, corr = repo.registrar_operacion([
            {
                "entidad": "PRESTAMO",
                "entidad_id": contexto["prestamo_id"],
                "tipo_movimiento": "DESEMBOLSO",
                "debe": Decimal("1000000"),
                "haber": Decimal("0"),
                "fecha": date(2026, 1, 1),
            },
            {
                "entidad": "INVERSOR",
                "entidad_id": contexto["deudor_id"],
                "tipo_movimiento": "APORTE",
                "debe": Decimal("0"),
                "haber": Decimal("1000000"),
                "fecha": date(2026, 1, 1),
            },
        ])
        assert len(ids) == 2
        assert corr is not None

    def test_doble_entrada_no_cuadra(self, contexto):
        """Una operación donde debe ≠ haber se rechaza."""
        repo = contexto["ledger_repo"]
        with pytest.raises(ValueError) as exc:
            repo.registrar_operacion([
                {
                    "entidad": "PRESTAMO",
                    "entidad_id": contexto["prestamo_id"],
                    "tipo_movimiento": "DESEMBOLSO",
                    "debe": Decimal("1000000"),
                    "haber": Decimal("0"),
                    "fecha": date(2026, 1, 1),
                },
                {
                    "entidad": "INVERSOR",
                    "entidad_id": contexto["deudor_id"],
                    "tipo_movimiento": "APORTE",
                    "debe": Decimal("0"),
                    "haber": Decimal("500000"),  # no cuadra
                    "fecha": date(2026, 1, 1),
                },
            ])
        assert "no cuadra" in str(exc.value).lower()

    def test_inmutabilidad_del_ledger(self, contexto):
        """El ledger no acepta UPDATE ni DELETE."""
        repo = contexto["ledger_repo"]
        repo.registrar_movimiento(
            entidad="PRESTAMO",
            entidad_id=contexto["prestamo_id"],
            tipo_movimiento="APORTE",
            debe=Decimal("100"),
            haber=Decimal("0"),
            fecha=date(2026, 1, 1),
            correlacion_id="x",
        )
        db = contexto["db"]
        with pytest.raises(Exception):
            db.ejecutar("UPDATE ledger SET debe = '200' WHERE id = 1")
        with pytest.raises(Exception):
            db.ejecutar("DELETE FROM ledger WHERE id = 1")

    def test_saldo_por_entidad(self, contexto):
        """El saldo se calcula sumando movimientos."""
        repo = contexto["ledger_repo"]
        # Debe 100
        repo.registrar_movimiento(
            entidad="PRESTAMO",
            entidad_id=contexto["prestamo_id"],
            tipo_movimiento="DESEMBOLSO",
            debe=Decimal("100"),
            haber=Decimal("0"),
            fecha=date(2026, 1, 1),
            correlacion_id="x",
        )
        # Haber 30
        repo.registrar_movimiento(
            entidad="PRESTAMO",
            entidad_id=contexto["prestamo_id"],
            tipo_movimiento="PAGO_CAPITAL",
            debe=Decimal("0"),
            haber=Decimal("30"),
            fecha=date(2026, 2, 1),
            correlacion_id="y",
        )
        saldo = repo.saldo("PRESTAMO", contexto["prestamo_id"])
        # Saldo = debe - haber = 100 - 30 = 70
        assert saldo == Decimal("70")

    def test_verificar_cuadre(self, contexto):
        """El ledger debe cuadrar globalmente."""
        repo = contexto["ledger_repo"]
        repo.registrar_operacion([
            {"entidad": "PRESTAMO", "entidad_id": 1, "tipo_movimiento": "X",
             "debe": Decimal("100"), "haber": Decimal("0"), "fecha": date(2026, 1, 1)},
            {"entidad": "INVERSOR", "entidad_id": 1, "tipo_movimiento": "X",
             "debe": Decimal("0"), "haber": Decimal("100"), "fecha": date(2026, 1, 1)},
        ])
        assert repo.verificar_cuadre() is True

    def test_por_correlacion(self, contexto):
        """Se pueden recuperar los movimientos de una operación."""
        repo = contexto["ledger_repo"]
        _, corr = repo.registrar_operacion([
            {"entidad": "PRESTAMO", "entidad_id": 1, "tipo_movimiento": "A",
             "debe": Decimal("10"), "haber": Decimal("0"), "fecha": date(2026, 1, 1)},
            {"entidad": "INVERSOR", "entidad_id": 1, "tipo_movimiento": "A",
             "debe": Decimal("0"), "haber": Decimal("10"), "fecha": date(2026, 1, 1)},
        ])
        movs = repo.por_correlacion(corr)
        assert len(movs) == 2


# ================================================================
# Tipos de cambio
# ================================================================

class TestTipoCambioRepo:

    def test_registrar_y_obtener(self, contexto):
        """Registra un TC y lo recupera."""
        repo = contexto["tc_repo"]
        repo.registrar(date(2026, 1, 1), "BCRA_A3500", Decimal("1500"))
        tc = repo.obtener(date(2026, 1, 1), "BCRA_A3500")
        assert tc is not None
        assert tc.valor == Decimal("1500")
        assert tc.fuente == "BCRA_A3500"

    def test_actualizar_existente(self, contexto):
        """Si se registra el mismo día y fuente, se actualiza."""
        repo = contexto["tc_repo"]
        id1 = repo.registrar(date(2026, 1, 1), "MANUAL", Decimal("1500"))
        id2 = repo.registrar(date(2026, 1, 1), "MANUAL", Decimal("1600"))
        assert id1 == id2
        tc = repo.obtener(date(2026, 1, 1), "MANUAL")
        assert tc.valor == Decimal("1600")

    def test_ultimo(self, contexto):
        """Devuelve la cotización más reciente."""
        repo = contexto["tc_repo"]
        repo.registrar(date(2026, 1, 1), "MANUAL", Decimal("1500"))
        repo.registrar(date(2026, 2, 1), "MANUAL", Decimal("1600"))
        repo.registrar(date(2026, 3, 1), "MANUAL", Decimal("1700"))
        ult = repo.ultimo("MANUAL")
        assert ult.valor == Decimal("1700")

    def test_valor_positivo(self, contexto):
        """Rechaza valores <= 0."""
        repo = contexto["tc_repo"]
        with pytest.raises(ValueError):
            repo.registrar(date(2026, 1, 1), "MANUAL", Decimal("0"))

    def test_por_rango(self, contexto):
        """Devuelve las cotizaciones de un rango."""
        repo = contexto["tc_repo"]
        for i in range(1, 6):
            repo.registrar(date(2026, 1, i), "MANUAL", Decimal(str(1500 + i)))
        rango = repo.por_rango("MANUAL", date(2026, 1, 2), date(2026, 1, 4))
        assert len(rango) == 3


# ================================================================
# Auditoría
# ================================================================

class TestAuditoriaRepo:

    def test_registrar_entrada(self, contexto):
        """Registra una entrada de auditoría."""
        repo = contexto["auditoria_repo"]
        aid = repo.registrar(
            usuario="admin",
            operacion="CAMBIO_TASA",
            entidad="PRESTAMO",
            entidad_id=contexto["prestamo_id"],
            correlacion_id="test-001",
            datos_anteriores={"tasa": "0.30"},
            datos_nuevos={"tasa": "0.27"},
            motivo="Reducción por refinanciación",
        )
        entradas = repo.por_entidad("PRESTAMO", contexto["prestamo_id"])
        assert len(entradas) == 1
        assert entradas[0].usuario == "admin"
        assert entradas[0].operacion == "CAMBIO_TASA"

    def test_datos_se_serializan_como_json(self, contexto):
        """Los datos anteriores y nuevos se guardan como JSON."""
        repo = contexto["auditoria_repo"]
        repo.registrar(
            usuario="admin",
            operacion="TEST",
            entidad="PRESTAMO",
            entidad_id=1,
            correlacion_id="x",
            datos_anteriores={"a": 1, "b": "texto"},
            datos_nuevos={"a": 2},
        )
        entradas = repo.por_entidad("PRESTAMO", 1)
        assert entradas[0].datos_anteriores is not None
        assert '"a": 1' in entradas[0].datos_anteriores

    def test_usuario_obligatorio(self, contexto):
        """Se requiere usuario."""
        repo = contexto["auditoria_repo"]
        with pytest.raises(ValueError):
            repo.registrar(
                usuario="",
                operacion="TEST",
                entidad="PRESTAMO",
                entidad_id=1,
                correlacion_id="x",
            )

    def test_por_correlacion(self, contexto):
        """Se pueden ver todas las entradas de una operación."""
        repo = contexto["auditoria_repo"]
        repo.registrar("admin", "OP1", "PRESTAMO", 1, "corr-1")
        repo.registrar("admin", "OP2", "PRESTAMO", 1, "corr-1")
        entradas = repo.por_correlacion("corr-1")
        assert len(entradas) == 2