"""Regresiones de terminología y defaults financieros de la UI."""

from pathlib import Path


def test_alta_no_presenta_tna_como_tasa_simple():
    path = Path(__file__).resolve().parents[1] / "ui" / "pagina_alta_prestamo.py"
    source = path.read_text(encoding="utf-8")

    assert "Tasa simple (TNA)" not in source
    assert "Tasa nominal anual (TNA)" in source
    assert "Tasa efectiva anual (TEA)" in source


def test_alta_no_inventa_tipo_de_cambio_inicial():
    path = Path(__file__).resolve().parents[1] / "ui" / "pagina_alta_prestamo.py"
    source = path.read_text(encoding="utf-8")

    assert 'key="alta_tc"' in source
    assert "min_value=0.0, value=0.0" in source
    assert "value=1500.0" not in source
