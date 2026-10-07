"""Tests del auditor de APIs de pagos."""
from pathlib import Path

from scripts.auditar_apis_pago import analizar, agrupar


def test_detecta_imports_de_apis_candidatas(tmp_path: Path):
    (tmp_path / "consumidor.py").write_text(
        """
from aplicacion.servicios import ServicioPagos
from aplicacion.servicios.registro_pago_v3 import RegistrarPagoV3
from aplicacion.servicios.puente_motor_pago_v3 import PuenteMotorPagoV3
from dominio.motor_pagos_v3 import PlanPago
""",
        encoding="utf-8",
    )

    referencias = analizar(tmp_path)
    categorias = agrupar(referencias)

    assert any(
        r["simbolo"] == "aplicacion.servicios.ServicioPagos"
        for r in categorias["legacy"]
    )
    assert any(
        r["simbolo"].endswith("RegistrarPagoV3")
        for r in categorias["v3_registro"]
    )
    assert any(
        r["simbolo"].endswith("PuenteMotorPagoV3")
        for r in categorias["bridge"]
    )
    assert any(
        r["simbolo"] == "dominio.motor_pagos_v3.PlanPago"
        for r in categorias["plan_pago_duplicado"]
    )


def test_ignora_codigo_que_no_es_python(tmp_path: Path):
    (tmp_path / "README.txt").write_text(
        "from aplicacion.servicios import ServicioPagos",
        encoding="utf-8",
    )

    assert analizar(tmp_path) == ()


def test_no_ejecuta_imports_durante_el_analisis(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    (tmp_path / "peligroso.py").write_text(
        f"""
raise RuntimeError("no debe ejecutarse")
open({str(marker)!r}, "w").write("ejecutado")
""",
        encoding="utf-8",
    )

    analizar(tmp_path)

    assert not marker.exists()
