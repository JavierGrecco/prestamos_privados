"""Guardas arquitectónicas para la consulta de simulación de adelanto."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSULTA = ROOT / "aplicacion" / "consultas" / "simulacion_adelanto_legacy.py"
FACHADA = ROOT / "aplicacion" / "servicios" / "pagos.py"


def test_consulta_de_adelanto_depende_de_contratos_y_no_de_sqlite():
    fuente = CONSULTA.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(CONSULTA))
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
    assert "RepositorioLecturaPrestamoPago" in fuente
    assert "CalculadorDeudaParaSimulacion" in fuente


def test_fachada_publica_delega_simulacion_sin_rehacer_calculos():
    arbol = ast.parse(FACHADA.read_text(encoding="utf-8"), filename=str(FACHADA))
    clase = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.ClassDef) and nodo.name == "ServicioPagos"
    )
    metodo = next(
        nodo for nodo in clase.body
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "simular_adelanto"
    )

    assert len(metodo.body) == 2
    llamada = metodo.body[1].value
    assert isinstance(llamada, ast.Call)
    assert isinstance(llamada.func, ast.Attribute)
    assert llamada.func.attr == "simular"
    assert isinstance(llamada.func.value, ast.Attribute)
    assert llamada.func.value.attr == "_consulta_simulacion_adelanto_legacy"
