from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "corregir_tipos_v3_compat.py"


def cargar_modulo():
    spec = importlib.util.spec_from_file_location("fix_tipos", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_agrega_simbolos_solo_si_faltan(tmp_path):
    mod = cargar_modulo()
    root = tmp_path
    path = root / "dominio" / "tipos.py"
    path.parent.mkdir()
    path.write_text(
        "from decimal import Decimal\nfrom enum import Enum\n"
        "CENT = Decimal('0.01')\nPRECISION_TASA = Decimal('0.00000001')\n"
        "class ConceptoImputacion(str, Enum):\n    CAPITAL = 'CAPITAL'\n"
        "ORDEN_DEFAULT_IMPUTACION = [ConceptoImputacion.CAPITAL]\n",
        encoding="utf-8",
    )

    changed, symbols = mod.aplicar(path)
    assert changed is True
    assert symbols == ["ZERO", "TipoRecalculo"]
    text = path.read_text(encoding="utf-8")
    assert 'ZERO = Decimal("0")' in text
    assert 'class TipoRecalculo(str, Enum):' in text
    assert 'RAI = "RAI"' in text and 'RNI = "RNI"' in text

    changed2, symbols2 = mod.aplicar(path)
    assert changed2 is False
    assert symbols2 == []


def test_no_altera_archivo_si_ya_esta_compatible(tmp_path):
    mod = cargar_modulo()
    path = tmp_path / "tipos.py"
    original = (
        "from decimal import Decimal\nfrom enum import Enum\n"
        "CENT = Decimal('0.01')\nPRECISION_TASA = Decimal('0.00000001')\n"
        "ZERO = Decimal('0')\n\n"
        "class TipoRecalculo(str, Enum):\n    RAI = 'RAI'\n    RNI = 'RNI'\n"
    )
    path.write_text(original, encoding="utf-8")
    changed, symbols = mod.aplicar(path)
    assert changed is False
    assert symbols == []
    assert path.read_text(encoding="utf-8") == original
