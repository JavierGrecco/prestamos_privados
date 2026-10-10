"""Pruebas para el informe independiente de reposición e inversión."""
import csv as csv_lib
import json
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from dominio import ErrorValidacion

from aplicacion.servicios.reporte_inversion_reposicion import (
    ServicioReporteInversionReposicion,
    _texto_csv_seguro,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


def _crear_plan(repo: PlanesReposicionRepo) -> int:
    return repo.guardar_snapshot(
        nombre="Autocrédito para vehículo",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=400),
        capital_original_ars=Decimal("12000000.00"),
        datos={
            "esquema_snapshot": 1,
            "tipo_plan": "REPOSICION_INTERNA",
            "supuestos": {"benchmark": "Cartera alternativa declarada"},
            "resultado": {"cuotas": []},
            "sensibilidad": [],
        },
        creado_por="admin",
    )


def test_informe_de_plan_separa_reposicion_inversion_y_valuacion(tmp_path):
    ruta = tmp_path / "informe-plan-inversion.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = _crear_plan(repo)

        aporte_id = repo.registrar_aporte(
            plan_id,
            fecha_aporte=date.today() - timedelta(days=20),
            monto_ars=Decimal("1500000.00"),
            cotizacion_ars_por_usd=Decimal("1500.000000"),
            naturaleza_cotizacion="SUPUESTO",
            fuente_cotizacion="",
            referencia="=HYPERLINK(\"https://example.invalid\",\"ver reserva\")",
            nota="Aporte separado para cubrir cuotas futuras",
            creado_por="admin",
        )
        flujo_id = repo.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=date.today() - timedelta(days=365),
            tipo_flujo="APORTE_INVERSION",
            moneda="USD",
            monto_original=Decimal("1000.00"),
            naturaleza_cotizacion="NO_APLICA",
            referencia="Aporte real a cartera",
            creado_por="admin",
        )
        repo.registrar_valoracion_inversion(
            plan_id,
            fecha_valuacion=date.today(),
            moneda="USD",
            valor_original=Decimal("1100.00"),
            naturaleza_cotizacion="NO_APLICA",
            referencia="Valor declarado al cierre",
            creado_por="admin",
        )

        auditoria_antes = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM auditoria"
        )["cantidad"]
        servicio = ServicioReporteInversionReposicion(db)
        reporte = servicio.obtener(plan_id)
        markdown = servicio.markdown(reporte)
        payload = json.loads(servicio.json(reporte))
        csv_text = servicio.csv_detalle(reporte)
        auditoria_despues = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM auditoria"
        )["cantidad"]

        assert reporte.plan.id == plan_id
        assert reporte.fecha_corte == date.today()
        assert reporte.total_aportes_reposicion_ars == Decimal("1500000.00")
        assert reporte.total_aportes_reposicion_usd_ref == Decimal("1000.00")
        assert reporte.resumen.aportes_inversion_usd_ref == Decimal("1000.00")
        assert reporte.resumen.valor_mercado_final_usd_ref == Decimal("1100.00")
        assert reporte.resumen.resultado_total_usd_ref == Decimal("100.00")
        assert reporte.resumen.xirr_anual is not None

        # Aunque ambas cantidades equivalen a USD 1.000 de referencia, pertenecen
        # a categorías diferentes y nunca se suman automáticamente una con otra.
        assert len(reporte.aportes_reposicion) == 1
        assert reporte.aportes_reposicion[0].id == aporte_id
        assert len(reporte.flujos_inversion) == 1
        assert reporte.flujos_inversion[0].id == flujo_id
        assert payload["alcance"]["separado_de_posicion_personal"] is True
        assert payload["alcance"]["valuacion_abierta_es_ganancia_realizada"] is False
        assert len(payload["aportes_reposicion"]) == 1
        assert len(payload["flujos_inversion"]) == 1
        assert payload["resumen"]["total_aportes_reposicion_usd_ref"] == "1000.00"
        assert payload["resumen"]["aportes_inversion_usd_ref"] == "1000.00"

        assert "Aportes destinados a reponer capital" in markdown
        assert "Inversión declarada y rendimiento reportado" in markdown
        assert "no es una ganancia realizada" in markdown
        assert "separado" in markdown.lower()
        assert "1.500.000,00 ARS" in markdown
        assert "dirección XIRR: salida de dinero (flujo negativo)" in markdown
        assert "APORTE_REPOSICION" in csv_text
        assert "FLUJO_INVERSION" in csv_text
        assert "VALUACION" in csv_text
        assert payload["flujos_inversion"][0]["direccion_xirr"] == "SALIDA_NEGATIVA"
        filas_csv = list(csv_lib.reader(StringIO(csv_text)))
        assert "direccion_xirr" in filas_csv[0]
        assert all(len(fila) == len(filas_csv[0]) for fila in filas_csv)
        fila_aporte = next(fila for fila in filas_csv if fila[0] == "APORTE_REPOSICION")
        assert fila_aporte[9].startswith("'=HYPERLINK(")
        assert auditoria_despues == auditoria_antes


def test_informe_rechaza_plan_inexistente(tmp_path):
    ruta = tmp_path / "informe-plan-inexistente.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        servicio = ServicioReporteInversionReposicion(db)
        with pytest.raises(ErrorValidacion, match="no existe"):
            servicio.obtener(99999)


@pytest.mark.parametrize(
    "texto",
    [
        "=1+1",
        "+SUM(A1:A2)",
        "-CMD(...)",
        "@SUM(A1:A2)",
        "  =HYPERLINK(\"https://example.invalid\",\"abrir\")",
        "\t=1+1",
        "\u00a0=1+1",
    ],
)
def test_texto_csv_neutraliza_prefijos_de_formula(texto):
    assert _texto_csv_seguro(texto) == "'" + texto


def test_texto_csv_conserva_texto_normal():
    assert _texto_csv_seguro("Movimiento bancario 25") == "Movimiento bancario 25"
