"""Comprueba que los campos de texto de riesgo no lleguen crudos al HTML."""

import ast
import re
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


def _menciona_texto_no_confiable(
    nodo: ast.AST,
    nombres_tenidos: set[str] | frozenset[str] = frozenset(),
) -> bool:
    for parte in ast.walk(nodo):
        if isinstance(parte, ast.Attribute) and parte.attr in ATRIBUTOS_TEXTO_NO_CONFIABLE:
            return True
        if isinstance(parte, ast.Name) and (
            parte.id in NOMBRES_TEXTO_NO_CONFIABLE or parte.id in nombres_tenidos
        ):
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



# Solo estas propiedades se consideran fuente de texto editable para la
# propagación por alias. Se dejan fuera agregados financieros y enums (por
# ejemplo, "impacto", "tipo" o "moneda") para no tratar importes derivados como
# texto arbitrario solo porque comparten un objeto o una condición.
ATRIBUTOS_FUENTE_TEXTO_NO_CONFIABLE = {
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
    "titulo",
    "correlacion_id",
    "primera_observacion",
    "ultima_observacion",
    "estado_humano",
    "rol_humano",
    "prestamo_numero",
    "mensaje",
    "fuente",
    "comentario",
    "observacion",
    "actor",
    "nombre_plan",
    "plan_nombre",
    "texto",
}

# Parámetros escalares que habitualmente transportan texto escrito o editable.
# No incluir nombres de objetos agregados (por ejemplo "resumen" o "usuario")
# ni etiquetas calculadas como "icono": hacerlo propagaría la marca a importes.
ARGUMENTOS_TEXTO_NO_CONFIABLE = {
    "nombre",
    "apellido",
    "nombre_completo",
    "destino",
    "descripcion",
    "nota",
    "motivo",
    "motivo_anulacion",
    "referencia",
    "medio",
    "creado_por",
    "mensaje",
    "error",
    "fuente",
    "comentario",
    "observacion",
    "titulo",
    "texto",
}


def _nodos_del_ambito(raiz: ast.AST):
    """Recorre un módulo o función, sin mezclar variables de otros ámbitos."""
    yield raiz
    for hijo in ast.iter_child_nodes(raiz):
        if hijo is not raiz and isinstance(
            hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
        ):
            continue
        yield from _nodos_del_ambito(hijo)


def _ambitos(arbol: ast.Module) -> list[ast.AST]:
    """Devuelve ámbitos independientes para evitar propagar taint entre funciones."""
    resultado: list[ast.AST] = [arbol]
    resultado.extend(
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
    )
    return resultado


def _iterar_fuentes_fuera_de_escapes(nodo: ast.AST):
    """Recorre una expresión omitiendo los subárboles ya escapados explícitamente."""
    if isinstance(nodo, ast.Call) and _es_llamada_de_escape(nodo):
        return
    yield nodo
    for hijo in ast.iter_child_nodes(nodo):
        yield from _iterar_fuentes_fuera_de_escapes(hijo)


def _menciona_fuente_texto_no_confiable(
    nodo: ast.AST,
    nombres_tenidos: set[str] | frozenset[str] = frozenset(),
) -> bool:
    """Reconoce fuentes textuales y respeta las llamadas de escape explícitas."""
    for parte in _iterar_fuentes_fuera_de_escapes(nodo):
        if isinstance(parte, ast.Attribute) and parte.attr in ATRIBUTOS_FUENTE_TEXTO_NO_CONFIABLE:
            return True
        if isinstance(parte, ast.Name) and (
            parte.id in ARGUMENTOS_TEXTO_NO_CONFIABLE or parte.id in nombres_tenidos
        ):
            return True
        if isinstance(parte, ast.Subscript):
            clave = parte.slice
            if (
                isinstance(clave, ast.Constant)
                and isinstance(clave.value, str)
                and clave.value in ATRIBUTOS_FUENTE_TEXTO_NO_CONFIABLE
            ):
                return True
    return False


def _nombres_objetivo(nodo: ast.AST) -> set[str]:
    if isinstance(nodo, ast.Name):
        return {nodo.id}
    if isinstance(nodo, (ast.Tuple, ast.List)):
        resultado: set[str] = set()
        for elemento in nodo.elts:
            resultado.update(_nombres_objetivo(elemento))
        return resultado
    return set()


def _variables_tenidas(ambito: ast.AST) -> set[str]:
    """Propaga marcas de datos no confiables por asignaciones y alias locales."""
    tenidas: set[str] = set()
    if isinstance(ambito, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        argumentos = getattr(ambito, "args", None)
        if argumentos is not None:
            todos = (
                list(argumentos.posonlyargs)
                + list(argumentos.args)
                + list(argumentos.kwonlyargs)
            )
            if argumentos.vararg:
                todos.append(argumentos.vararg)
            if argumentos.kwarg:
                todos.append(argumentos.kwarg)
            tenidas.update(
                argumento.arg for argumento in todos
                if argumento.arg in ARGUMENTOS_TEXTO_NO_CONFIABLE
            )

    asignaciones: list[tuple[set[str], ast.AST]] = []
    for nodo in _nodos_del_ambito(ambito):
        if isinstance(nodo, ast.Assign):
            asignaciones.extend(
                (_nombres_objetivo(objetivo), nodo.value) for objetivo in nodo.targets
            )
        elif isinstance(nodo, ast.AnnAssign) and nodo.value is not None:
            asignaciones.append((_nombres_objetivo(nodo.target), nodo.value))
        elif isinstance(nodo, ast.NamedExpr):
            asignaciones.append((_nombres_objetivo(nodo.target), nodo.value))
        elif isinstance(nodo, (ast.For, ast.AsyncFor)):
            asignaciones.append((_nombres_objetivo(nodo.target), nodo.iter))

    # Grafo de dependencias: evita volver a recorrer el AST una vez por cada
    # alias. La marca se propaga por cola en tiempo lineal respecto del grafo.
    dependientes: dict[str, set[str]] = {}
    for objetivos, expresion in asignaciones:
        if not objetivos or _es_llamada_de_escape(expresion):
            continue
        nombres_referenciados = {
            parte.id for parte in ast.walk(expresion) if isinstance(parte, ast.Name)
        }
        if _menciona_fuente_texto_no_confiable(expresion):
            tenidas.update(objetivos)
        for nombre in nombres_referenciados:
            dependientes.setdefault(nombre, set()).update(objetivos)

    pendientes = list(tenidas)
    while pendientes:
        fuente = pendientes.pop()
        for objetivo in dependientes.get(fuente, ()):
            if objetivo not in tenidas:
                tenidas.add(objetivo)
                pendientes.append(objetivo)
    return tenidas


def _parece_plantilla_html(nodo: ast.JoinedStr) -> bool:
    return any(
        isinstance(parte, ast.Constant)
        and isinstance(parte.value, str)
        and re.search(r"</?[A-Za-z][^>]*>", parte.value)
        for parte in ast.walk(nodo)
    )


def _hallar_interpolaciones_sin_escape(
    arbol: ast.Module,
    fuente: str,
    ruta_relativa: str,
) -> list[str]:
    problemas: list[str] = []
    for ambito in _ambitos(arbol):
        tenidas = _variables_tenidas(ambito)
        for nodo in _nodos_del_ambito(ambito):
            if not isinstance(nodo, ast.JoinedStr) or not _parece_plantilla_html(nodo):
                continue
            for valor in (
                parte for parte in ast.walk(nodo)
                if isinstance(parte, ast.FormattedValue)
            ):
                expresion = valor.value
                if _es_llamada_de_escape(expresion):
                    continue
                if _menciona_texto_no_confiable(expresion, tenidas):
                    segmento = ast.get_source_segment(fuente, expresion) or ast.dump(expresion)
                    problemas.append(
                        f"{ruta_relativa}:{valor.lineno}: falta escape explícito "
                        f"para {segmento}"
                    )
    return problemas


def test_las_plantillas_html_escapan_campos_de_texto_no_confiable():
    problemas = []

    for archivo in sorted(UI_ROOT.glob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))
        problemas.extend(
            _hallar_interpolaciones_sin_escape(
                arbol,
                fuente,
                str(archivo.relative_to(UI_ROOT.parent)),
            )
        )

    assert not problemas, (
        "Se detectaron campos de texto de riesgo interpolados en plantillas HTML "
        "sin escape, incluso cuando el HTML se guarda en una variable o el dato "
        "viaja por uno o más alias. Usá componentes.escapar_texto_html() o "
        "html.escape():\n- "
        + "\n- ".join(problemas)
    )


def test_el_contrato_detecta_aliases_de_texto_no_confiable():
    fuente = (
        "def render(persona):\n"
        "    nombre_local = persona.nombre\n"
        "    alias_nombre = nombre_local\n"
        "    plantilla = f'<span>{alias_nombre}</span>'\n"
        "    render_html(plantilla)\n"
    )
    arbol = ast.parse(fuente)
    ambito = next(
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "render"
    )
    tenidas = _variables_tenidas(ambito)
    plantilla = next(
        nodo for nodo in ast.walk(ambito)
        if isinstance(nodo, ast.JoinedStr) and _parece_plantilla_html(nodo)
    )
    interpolacion = next(
        nodo for nodo in ast.walk(plantilla)
        if isinstance(nodo, ast.FormattedValue)
    )

    assert {"nombre_local", "alias_nombre"} <= tenidas
    assert _menciona_texto_no_confiable(interpolacion.value, tenidas)

def test_las_pantallas_no_pueden_crear_fragmentos_html_confiables_directamente():
    constructores = {
        "FragmentoHTMLConfiable",
        "fragmento_html_confiable",
        "_crear_fragmento_html_confiable",
    }
    problemas = []

    for archivo in sorted(UI_ROOT.glob("*.py")):
        if archivo.name == "componentes.py":
            continue

        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module in {
                "ui.componentes",
                "componentes",
            }:
                for alias in nodo.names:
                    if alias.name in constructores:
                        problemas.append(
                            f"{archivo.relative_to(UI_ROOT.parent)}:{nodo.lineno}: "
                            f"import directo de {alias.name}"
                        )

            if not isinstance(nodo, ast.Call):
                continue

            funcion = nodo.func
            nombre = (
                funcion.id
                if isinstance(funcion, ast.Name)
                else funcion.attr
                if isinstance(funcion, ast.Attribute)
                else None
            )
            if nombre in constructores:
                problemas.append(
                    f"{archivo.relative_to(UI_ROOT.parent)}:{nodo.lineno}: "
                    f"construcción directa mediante {nombre}"
                )

    assert not problemas, (
        "Las pantallas deben usar componentes que escapan y validan sus valores; "
        "no deben elevar texto o HTML arbitrario a fragmento confiable:\n- "
        + "\n- ".join(problemas)
    )

