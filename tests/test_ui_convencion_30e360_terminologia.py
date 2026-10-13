"""La UI identifica correctamente la convención 30E/360 ISDA y sus ajustes."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _leer(ruta: str) -> str:
    return (ROOT / ruta).read_text(encoding="utf-8")


def test_alta_no_presenta_30e360_isda_como_si_todos_los_periodos_fueran_30_dias():
    alta = _leer("ui/pagina_alta_prestamo.py")
    dominio = _leer("dominio/amortizacion.py")

    assert '"TREINTA_360": "30E/360 ISDA (ajuste de fin de mes)"' in alta
    assert "**30E/360 ISDA (ajuste de fin de mes)**" in alta
    assert "el último día de febrero, se conserva el día real" in alta
    assert "Todos los meses se cuentan como de 30 días." not in alta
    assert '"TREINTA_360": "Mes de 30 días"' not in alta
    assert "La convención histórica TREINTA_360" in dominio
    assert "no debe presentarse como intercambiable" in dominio


def test_simulador_usa_la_misma_terminologia_30e360_isda():
    simulador = _leer("ui/pagina_simulador_carencia.py")

    assert "30E/360 ISDA (ajuste de fin de mes)" in simulador
    assert "30E/360 cuenta meses de 30 días" not in simulador
    assert "vencimiento final en febrero conserva su día real" in simulador
