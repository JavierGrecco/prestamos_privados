"""Guardas arquitectónicas para la consulta del estado de cuotas."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSULTA = ROOT / "aplicacion" / "consultas" / "estado_cuotas_con_arrastre.py"
FACHADA = ROOT / "aplicacion" / "servicios" / "pagos.py"


def test_consulta_de_estado_de_cuotas_depende_de_contratos_y_no_de_sqlite():
    arbol = ast.parse(CONSULTA.read_text(encoding="utf-8"), filename=str(CONSULTA))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue

        for modulo in modulos:
            if modulo and modulo.split(".", maxsplit=1)[0] in {
                "infraestructura",
                "sqlite3",
            }:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert problemas == [], "\\n".join(problemas)
    assert "RepositorioLecturaPrestamoPago" in CONSULTA.read_text(encoding="utf-8")
    assert "RepositorioPoliticaPagoLectura" in CONSULTA.read_text(encoding="utf-8")


def test_fachada_publica_delega_el_estado_de_cuotas_sin_reimplementar_calculos():
    arbol = ast.parse(FACHADA.read_text(encoding="utf-8"), filename=str(FACHADA))
    clase = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.ClassDef) and nodo.name == "ServicioPagos"
    )
    metodo = next(
        nodo for nodo in clase.body
        if isinstance(nodo, ast.FunctionDef)
        and nodo.name == "estado_cuotas_con_arrastre"
    )

    assert len(metodo.body) == 2  # docstring y delegación
    llamada = metodo.body[1].value
    assert isinstance(llamada, ast.Call)
    assert isinstance(llamada.func, ast.Attribute)
    assert llamada.func.attr == "obtener"
    assert isinstance(llamada.func.value, ast.Attribute)
    assert llamada.func.value.attr == "_consulta_estado_cuotas_con_arrastre"
