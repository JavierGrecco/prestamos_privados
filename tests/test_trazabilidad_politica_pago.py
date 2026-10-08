"""Regresiones para la trazabilidad histórica de la política aplicada a pagos."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.migraciones import v016_politica_pago_en_pago
from infraestructura.migraciones.gestor import _cargar_migraciones
from infraestructura.repositorios import PagoRepo, PersonaRepo, PoliticaPagoRepo
from dominio.politica_pago import PoliticaImputacionPago
from dominio.tipos import ConceptoImputacion


def _crear_prestamo(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor", apellido="T")
    inversor = personas.crear(nombre="Inversor", apellido="T")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor, "monto": Decimal("1000000")}],
        usuario="test",
    )


def test_pago_legacy_conserva_la_version_de_politica_que_regia_en_su_fecha(tmp_path: Path):
    with BaseDatos(tmp_path / "versiones.db") as db:
        aplicar_migraciones(db)
        prestamo_id = _crear_prestamo(db)
        repo = PoliticaPagoRepo(db)

        politica_v1_id, _ = repo.obtener_vigente_con_id(
            prestamo_id,
            date(2026, 2, 1),
        )
        pago_1 = ServicioPagos(db).registrar_pago(
            prestamo_id=prestamo_id,
            monto=Decimal("5000.00"),
            fecha_real=date(2026, 2, 1),
            usuario="test",
        )

        politica_v2_id = repo.crear_version(
            prestamo_id,
            date(2026, 3, 1),
            PoliticaImputacionPago(
                orden_waterfall=(
                    ConceptoImputacion.CAPITAL,
                    ConceptoImputacion.INTERES,
                    ConceptoImputacion.MORA,
                )
            ),
            usuario="test",
        )
        pago_2 = ServicioPagos(db).registrar_pago(
            prestamo_id=prestamo_id,
            monto=Decimal("5000.00"),
            fecha_real=date(2026, 3, 1),
            usuario="test",
        )

        assert PagoRepo(db).obtener(pago_1).politica_pago_id == politica_v1_id
        assert PagoRepo(db).obtener(pago_2).politica_pago_id == politica_v2_id


def test_v016_backfill_asocia_pago_historico_a_politica_vigente(tmp_path: Path):
    with BaseDatos(tmp_path / "backfill.db") as db:
        migraciones = _cargar_migraciones()
        db.ejecutar(
            """
            CREATE TABLE IF NOT EXISTS migraciones (
                version INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                aplicada_en TEXT NOT NULL,
                hash TEXT
            )
            """
        )
        for version, nombre, funcion in migraciones[:15]:
            with db.transaccion():
                funcion(db)
                db.ejecutar(
                    "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                    (version, nombre, "2026-10-08T00:00:00"),
                )

        db.ejecutar(
            "INSERT INTO personas (nombre, apellido, creado_en) VALUES ('D', 'B', '2026-01-01')"
        )
        db.ejecutar(
            """
            INSERT INTO prestamos
            (numero, deudor_id, capital_original, plazo_meses, sistema,
             convencion_dias, fecha_inicio, estado, creado_en)
            VALUES ('PR-HIST-1', 1, '1000', 12, 'FRANCES',
                    'MENSUAL', '2026-01-01', 'ACTIVO', '2026-01-01')
            """
        )
        db.ejecutar(
            """
            INSERT INTO pagos
            (prestamo_id, fecha_real, fecha_valor, fecha_registro,
             moneda_pago, monto_moneda_pago, monto_moneda_contractual)
            VALUES (1, '2026-02-01', '2026-02-01', '2026-02-01T10:00:00',
                    'ARS', '100', '100')
            """
        )

        politica_id = db.consultar_uno(
            """
            SELECT id
            FROM politicas_pago
            WHERE prestamo_id = 1
              AND vigente_desde <= '2026-02-01'
              AND (vigente_hasta IS NULL OR vigente_hasta > '2026-02-01')
            ORDER BY version DESC
            LIMIT 1
            """
        )["id"]

        v016_politica_pago_en_pago.aplicar(db)

        pago = db.consultar_uno(
            "SELECT politica_pago_id FROM pagos WHERE id = 1"
        )
        assert pago["politica_pago_id"] == politica_id
