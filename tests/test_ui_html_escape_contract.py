"""Comprueba que los campos de texto de riesgo no lleguen crudos al HTML."""

import ast
from pathlib import Path


UI_ROOT = Path(__file__).resolve().parents[1] / "ui"

# Son campos que pueden venir de datos editables, históricos o externos.
CAMPOS_TEXTO_NO_CONFIABLE = {
    "nombre",
    "apellido",
    "nombre_completo",
    "destino",
    "descripcion",
    "detalle_inversion",
    "detalle_deuda",
    "nota",
    "motivo",
    "motivo_anulacion",
    "referencia",
    "medio",
    "creado_por",
    "usuario",
    "resumen",
    "titulo",
    "impacto",
    "icono",
    "correlacion_id",
    "primera_observacion",
    "ultima_observacion",
    "estado_humano",
    "rol_humano",
    "prestamo_numero",
    "tipo",
    "operacion",
    "moneda",
}

ATRIBUTOS_TEXTO_NO_CONFIABLE = CAMPOS_TEXTO_NO_CONFIABLE | {"numero"}

NOMBRES_TEXTO_NO_CONFIABLE = {
    "e",  # excepción de Python en bloques try/except
    "exc",
    "advertencia",
    "motivos",
    "diferentes",
    "orden",
}

FUNCIONES_DE_ESCAPE = {"escapar_texto_html", "escape"}


def _es_llamada_de_escape(nodo: ast.AST) -> bool:
    if not isinstance(nodo, ast.Call):
        return False
    funcion = nodo.func
    if isinstance(funcion, ast.Name):
        return funcion.id in FUNCIONES_DE_ESCAPE
    return isinstance(funcion, ast.Attribute) and funcion.attr in FUNCIONES_DE_ESCAPE


def _menciona_texto_no_confiable(nodo: ast.AST) -> bool:
    for parte in ast.walk(nodo):
        if isinstance(parte, ast.Attribute) and parte.attr in ATRIBUTOS_TEXTO_NO_CONFIABLE:
            return True
        if isinstance(parte, ast.Name) and parte.id in NOMBRES_TEXTO_NO_CONFIABLE:
            return True
        if isinstance(parte, ast.Subscript):
            clave = parte.slice
            if (
                isinstance(clave, ast.Constant)
                and isinstance(clave.value, str)
                and clave.value in CAMPOS_TEXTO_NO_CONFIABLE
            ):
                return True
    return False


def _llamada_permite_html(nodo: ast.Call) -> bool:
    funcion = nodo.func
    es_renderer = (
        isinstance(funcion, ast.Attribute) and funcion.attr == "render_html"
    )
    es_markdown_html = (
        isinstance(funcion, ast.Attribute)
        and funcion.attr == "markdown"
        and any(
            kw.arg == "unsafe_allow_html"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for kw in nodo.keywords
        )
    )
    return es_renderer or es_markdown_html


def _fstrings_de_un_nodo(nodo: ast.AST) -> list[ast.JoinedStr]:
    return [x for x in ast.walk(nodo) if isinstance(x, ast.JoinedStr)]


def test_las_plantillas_html_escapan_campos_de_texto_no_confiable():
    problemas = []

    for archivo in sorted(UI_ROOT.glob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))

        for llamada in ast.walk(arbol):
            if not isinstance(llamada, ast.Call) or not _llamada_permite_html(llamada):
                continue
            if not llamada.args:
                continue

            for plantilla in _fstrings_de_un_nodo(llamada.args[0]):
                for valor in (
                    parte for parte in ast.walk(plantilla)
                    if isinstance(parte, ast.FormattedValue)
                ):
                    expresion = valor.value
                    if _es_llamada_de_escape(expresion):
                        continue
                    if _menciona_texto_no_confiable(expresion):
                        segmento = ast.get_source_segment(
                            archivo.read_text(encoding="utf-8"), expresion
                        ) or ast.dump(expresion)
                        problemas.append(
                            f"{archivo.relative_to(UI_ROOT.parent)}:"
                            f"{valor.lineno}: falta escape explícito para {segmento}"
                        )

    assert not problemas, (
        "Se detectaron campos de texto de riesgo interpolados en HTML sin escape. "
        "Usá componentes.escapar_texto_html() o html.escape():\n- "
        + "\n- ".join(problemas)
    )
