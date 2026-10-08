"""Regresiones de terminología financiera visible en alta de préstamo."""

from pathlib import Path


def test_ayuda_de_tasa_usa_tna_y_tea():
    source = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pagina_alta_prestamo.py"
    ).read_text(encoding="utf-8")

    assert "| Tasa nominal anual (TNA) |" in source
    assert "| Tasa efectiva anual (TEA) |" in source
    assert "tasa simple" not in source.lower()
    assert "tasa compuesta" not in source.lower()
