from datetime import date
from decimal import Decimal
import pytest

from dominio.politica_pago import (
    BaseMoraPago,
    EstrategiaObligacionesPago,
    ORDEN_WATERFALL_CANONICO,
    PoliticaImputacionPago,
)
from dominio.tipos import ConceptoImputacion, ConvencionDias
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.politicas_pago import PoliticaPagoRepo


def test_politica_canonica_es_determinista():
    politica = PoliticaImputacionPago.canonica()

    assert politica.estrategia_obligaciones is EstrategiaObligacionesPago.VENCIDA_MAS_ANTIGUA
    assert politica.orden_waterfall == ORDEN_WATERFALL_CANONICO
    assert politica.interes_compensatorio_post_vencimiento is True
    assert politica.mora_habilitada is True
    assert politica.mora_tasa_anual == Decimal("0.50000000")
    assert politica.mora_base is BaseMoraPago.CUOTA_CONTRACTUAL
    assert politica.mora_convencion_dias is ConvencionDias.ACTUAL_365
    assert politica.capitalizacion_intereses is False


def test_migracion_crea_politica_para_prestamo_existente(tmp_path):
    ruta = tmp_path / "politica.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        db.ejecutar(
            """
            INSERT INTO personas (nombre, creado_en)
            VALUES ('D', '2026-10-08')
            """
        )
        db.ejecutar(
            """
            INSERT INTO prestamos
            (numero, deudor_id, capital_original, plazo_meses, sistema,
             convencion_dias, fecha_inicio, estado, creado_en)
            VALUES ('PR-000001', 1, '1000', 12, 'FRANCES',
                    'MENSUAL', '2026-10-08', 'ACTIVO', '2026-10-08')
            """
        )
        politica = PoliticaPagoRepo(db).obtener_vigente(1, date(2026, 10, 9))

        assert politica.orden_waterfall == (
            ConceptoImputacion.MORA,
            ConceptoImputacion.INTERES,
            ConceptoImputacion.CAPITAL,
        )
        assert politica.mora_tasa_anual == Decimal("0.50000000")


def test_nuevo_prestamo_recibe_politica_automatica_por_trigger(tmp_path):
    ruta = tmp_path / "politica_nueva.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        db.ejecutar(
            """
            INSERT INTO personas (nombre, creado_en)
            VALUES ('D', '2026-10-08')
            """
        )
        db.ejecutar(
            """
            INSERT INTO prestamos
            (numero, deudor_id, capital_original, plazo_meses, sistema,
             convencion_dias, fecha_inicio, estado, creado_en)
            VALUES ('PR-000001', 1, '1000', 12, 'FRANCES',
                    'MENSUAL', '2026-10-08', 'ACTIVO', '2026-10-08')
            """
        )
        fila = db.consultar_uno(
            "SELECT version, vigente_hasta FROM politicas_pago WHERE prestamo_id = 1"
        )
        assert fila["version"] == 1
        assert fila["vigente_hasta"] is None


def test_repositorio_reconstruye_politica_versionada(tmp_path):
    ruta = tmp_path / "version.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        db.ejecutar(
            "INSERT INTO personas (nombre, creado_en) VALUES ('D', '2026-10-08')"
        )
        db.ejecutar(
            """
            INSERT INTO prestamos
            (numero, deudor_id, capital_original, plazo_meses, sistema,
             convencion_dias, fecha_inicio, estado, creado_en)
            VALUES ('PR-000001', 1, '1000', 12, 'FRANCES',
                    'MENSUAL', '2026-10-08', 'ACTIVO', '2026-10-08')
            """
        )
        repo = PoliticaPagoRepo(db)
        nueva = PoliticaImputacionPago(
            orden_waterfall=(
                ConceptoImputacion.INTERES,
                ConceptoImputacion.CAPITAL,
                ConceptoImputacion.MORA,
            ),
            interes_compensatorio_post_vencimiento=False,
            mora_habilitada=False,
        )
        repo.crear_version(
            1,
            date(2026, 11, 1),
            nueva,
            usuario="admin",
        )

        anterior = db.consultar_uno(
            "SELECT version, vigente_hasta FROM politicas_pago WHERE prestamo_id=1 ORDER BY version"
        )
        actual = repo.obtener_vigente(1, date(2026, 11, 2))

        assert anterior["version"] == 1
        assert anterior["vigente_hasta"] == "2026-11-01"
        assert actual.orden_waterfall == nueva.orden_waterfall
        assert actual.interes_compensatorio_post_vencimiento is False
        assert actual.mora_habilitada is False

 
def test_politica_rechaza_waterfall_incompleto():
    with pytest.raises(Exception, match="MORA, INTERES y CAPITAL"):
        PoliticaImputacionPago(
            orden_waterfall=(
                ConceptoImputacion.INTERES,
                ConceptoImputacion.CAPITAL,
            )
        )


def test_politica_rechaza_conceptos_no_soportados():
    from dominio.excepciones import ErrorValidacion

    with pytest.raises(ErrorValidacion, match="no soporta"):
        PoliticaImputacionPago(
            orden_waterfall=(
                ConceptoImputacion.GASTO,
                ConceptoImputacion.INTERES,
                ConceptoImputacion.CAPITAL,
            )
        )


def test_cambio_de_politica_queda_auditado(tmp_path):
    ruta = tmp_path / "auditoria.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        db.ejecutar(
            "INSERT INTO personas (nombre, creado_en) VALUES ('D', '2026-10-08')"
        )
        db.ejecutar(
            """
            INSERT INTO prestamos
            (numero, deudor_id, capital_original, plazo_meses, sistema,
             convencion_dias, fecha_inicio, estado, creado_en)
            VALUES ('PR-000001', 1, '1000', 12, 'FRANCES',
                    'MENSUAL', '2026-10-08', 'ACTIVO', '2026-10-08')
            """
        )
        repo = PoliticaPagoRepo(db)
        repo.crear_version(
            1,
            date(2026, 11, 1),
            PoliticaImputacionPago(mora_habilitada=False),
            usuario="admin",
        )
        auditoria = db.consultar_uno(
            """
            SELECT operacion, entidad, entidad_id, usuario
            FROM auditoria
            WHERE operacion = 'POLITICA_PAGO_VERSION_CREADA'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        assert auditoria["operacion"] == "POLITICA_PAGO_VERSION_CREADA"
        assert auditoria["entidad"] == "POLITICA_PAGO"
        assert auditoria["usuario"] == "admin"
        assert auditoria["entidad_id"] > 0
