"""Contrato unificado del monto distribuible de un pago V3.

La distribución a inversores representa el cobro total recibido, no solamente
las imputaciones contractuales: cuando existe un excedente tratado como
adelanto, ese excedente también forma parte del cobro.
"""

from pathlib import Path
import ast


def test_las_dos_rutas_completas_usan_el_total_recibido_para_distribuir():
    archivos = (
        Path(__file__).resolve().parents[1]
        / "aplicacion"
        / "servicios"
        / "registro_pago_v3_completo.py",
        Path(__file__).resolve().parents[1]
        / "aplicacion"
        / "servicios"
        / "registro_pago_v3_completo_adelantos.py",
    )

    for archivo in archivos:
        source = archivo.read_text(encoding="utf-8")
        assert "monto_pago_recibido" in source
        assert "monto=command.monto" not in source
        assert "monto=resultado.plan.monto_aplicado" not in source
        assert "monto=resultado_plan.plan.monto_pago_recibido" in source or (
            archivo.name == "registro_pago_v3_completo.py"
            and "monto=resultado.plan.monto_pago_recibido" in source
        )


def test_no_hay_duplicacion_de_una_regla_distinta_en_las_rutas():
    rutas = [
        Path(__file__).resolve().parents[1]
        / "aplicacion"
        / "servicios"
        / "registro_pago_v3_completo.py",
        Path(__file__).resolve().parents[1]
        / "aplicacion"
        / "servicios"
        / "registro_pago_v3_completo_adelantos.py",
    ]
    textos = [p.read_text(encoding="utf-8") for p in rutas]
    assert all("monto=command.monto" not in t for t in textos)
    assert all("monto=resultado.plan.monto_aplicado" not in t for t in textos)
