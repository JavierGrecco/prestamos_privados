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
    "origen",
    "fuente",
    "fuente_cotizacion",
    "referencia_documental",
    "comentario",
    "observacion",
    "actor",
    "nombre_plan",
    "plan_nombre",
    "concepto",
    "detalle",
    "mensaje",
    "error",
    "texto",
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
    "origen",
    "fuente_cotizacion",
    "referencia_documental",
    "concepto",
    "detalle",
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
    "origen",
    "fuente_cotizacion",
    "referencia_documental",
    "concepto",
    "detalle",
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


def _es_extraccion_directa_de_texto(nodo: ast.AST) -> bool:
    """Detecta solo una lectura directa de campo textual editable."""
    if isinstance(nodo, ast.Attribute):
        return nodo.attr in ATRIBUTOS_FUENTE_TEXTO_NO_CONFIABLE
    if isinstance(nodo, ast.Subscript):
        clave = nodo.slice
        return (
            isinstance(clave, ast.Constant)
            and isinstance(clave.value, str)
            and clave.value in ATRIBUTOS_FUENTE_TEXTO_NO_CONFIABLE
        )
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


def _expresion_es_texto_no_confiable(
    nodo: ast.AST,
    nombres_tenidos: set[str] | frozenset[str],
) -> bool:
    """Sigue texto sensible a través de contenedores y operaciones de unión.

    Deliberadamente no sigue operaciones aritméticas ni condiciones: se busca
    detectar transporte de texto hacia HTML sin convertir importes, porcentajes
    o etiquetas derivadas en falsos positivos.
    """
    if _es_llamada_de_escape(nodo):
        return False
    if _es_extraccion_directa_de_texto(nodo):
        return True
    if isinstance(nodo, ast.Name):
        return (
            nodo.id in nombres_tenidos
            or nodo.id in NOMBRES_TEXTO_NO_CONFIABLE
        )
    if isinstance(nodo, ast.JoinedStr):
        return any(
            _expresion_es_texto_no_confiable(parte.value, nombres_tenidos)
            for parte in nodo.values
            if isinstance(parte, ast.FormattedValue)
        )
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return (
            _expresion_es_texto_no_confiable(nodo.left, nombres_tenidos)
            or _expresion_es_texto_no_confiable(nodo.right, nombres_tenidos)
        )
    if isinstance(nodo, (ast.List, ast.Tuple, ast.Set)):
        return any(
            _expresion_es_texto_no_confiable(elemento, nombres_tenidos)
            for elemento in nodo.elts
        )
    if isinstance(nodo, ast.Dict):
        return any(
            _expresion_es_texto_no_confiable(elemento, nombres_tenidos)
            for elemento in [*nodo.keys, *nodo.values]
            if elemento is not None
        )
    if isinstance(nodo, ast.Call):
        funcion = nodo.func
        if isinstance(funcion, ast.Attribute) and funcion.attr in {
            "join", "strip", "lstrip", "rstrip", "replace", "lower",
            "upper", "capitalize", "casefold", "title",
        }:
            return (
                _expresion_es_texto_no_confiable(funcion.value, nombres_tenidos)
                or any(
                    _expresion_es_texto_no_confiable(argumento, nombres_tenidos)
                    for argumento in nodo.args
                )
            )
        if isinstance(funcion, ast.Name) and funcion.id == "str":
            return any(
                _expresion_es_texto_no_confiable(argumento, nombres_tenidos)
                for argumento in nodo.args
            )
        return False
    if isinstance(nodo, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        locales = set(nombres_tenidos)
        for generador in nodo.generators:
            if _expresion_es_texto_no_confiable(generador.iter, locales):
                locales.update(_nombres_objetivo(generador.target))
        expresiones = (
            [nodo.key, nodo.value]
            if isinstance(nodo, ast.DictComp)
            else [nodo.elt]
        )
        return any(
            _expresion_es_texto_no_confiable(expresion, locales)
            for expresion in expresiones
        )
    return False


def _variables_tenidas(ambito: ast.AST) -> set[str]:
    """Propaga texto sensible por alias, colecciones y llamadas a join().

    Los valores envueltos en escape()/escapar_texto_html() dejan de estar
    marcados. No se propagan cálculos numéricos ni etiquetas derivadas.
    """
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

    # Un punto fijo permite seguir cadenas locales como:
    # persona.nombre -> lista_texto -> ''.join(lista_texto) -> plantilla.
    cambio = True
    while cambio:
        cambio = False
        for objetivos, expresion in asignaciones:
            if objetivos and _expresion_es_texto_no_confiable(expresion, tenidas):
                nuevas = objetivos - tenidas
                if nuevas:
                    tenidas.update(nuevas)
                    cambio = True
    return tenidas


def _contiene_marcado_html(nodo: ast.AST) -> bool:
    """Detecta marcado HTML literal dentro de una expresión de Python."""
    return any(
        isinstance(parte, ast.Constant)
        and isinstance(parte.value, str)
        and re.search(r"</?[A-Za-z][^>]*>", parte.value)
        for parte in ast.walk(nodo)
    )


def _parece_plantilla_html(nodo: ast.AST) -> bool:
    """Reconoce f-strings, concatenaciones y llamadas directas a str.format."""
    if not _contiene_marcado_html(nodo):
        return False
    if isinstance(nodo, ast.JoinedStr):
        return True
    if isinstance(nodo, ast.BinOp):
        return isinstance(nodo.op, ast.Add)
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
        return (
            nodo.func.attr in {"format", "join"}
            and _contiene_marcado_html(
                nodo.func.value if nodo.func.attr == "format" else nodo
            )
        )
    return False


def _partes_de_concatenacion(nodo: ast.AST) -> list[ast.AST]:
    """Separa una concatenación de strings sin entrar en otras operaciones."""
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return _partes_de_concatenacion(nodo.left) + _partes_de_concatenacion(
            nodo.right
        )
    return [nodo]


def _expresiones_dinamicas_html(nodo: ast.AST) -> list[ast.AST]:
    """Devuelve los valores que se insertan en una plantilla HTML reconocida."""
    if isinstance(nodo, ast.JoinedStr):
        return [
            parte.value
            for parte in ast.walk(nodo)
            if isinstance(parte, ast.FormattedValue)
        ]
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return [
            parte
            for parte in _partes_de_concatenacion(nodo)
            if not isinstance(parte, ast.Constant)
        ]
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
        if nodo.func.attr == "format" and _contiene_marcado_html(nodo.func.value):
            return list(nodo.args) + [kw.value for kw in nodo.keywords]
        if nodo.func.attr == "join" and _contiene_marcado_html(nodo):
            return list(nodo.args)
    return []


def _hallar_interpolaciones_sin_escape(
    arbol: ast.Module,
    fuente: str,
    ruta_relativa: str,
) -> list[str]:
    problemas: list[str] = []
    for ambito in _ambitos(arbol):
        tenidas = _variables_tenidas(ambito)
        for nodo in _nodos_del_ambito(ambito):
            if not _parece_plantilla_html(nodo):
                continue
            for expresion in _expresiones_dinamicas_html(nodo):
                if _es_llamada_de_escape(expresion):
                    continue
                if _expresion_es_texto_no_confiable(expresion, tenidas):
                    segmento = (
                        ast.get_source_segment(fuente, expresion)
                        or ast.dump(expresion)
                    )
                    linea = getattr(expresion, "lineno", nodo.lineno)
                    problemas.append(
                        f"{ruta_relativa}:{linea}: falta escape explícito "
                        f"para {segmento}"
                    )
    # La misma interpolación puede pertenecer a dos niveles de una
    # concatenación; mostrarla una sola vez facilita corregir el hallazgo.
    return list(dict.fromkeys(problemas))



def _es_llamada_de_clase_css_segura(nodo: ast.AST) -> bool:
    if not isinstance(nodo, ast.Call):
        return False
    funcion = nodo.func
    return (
        isinstance(funcion, ast.Name) and funcion.id == "clase_css_segura"
    ) or (
        isinstance(funcion, ast.Attribute) and funcion.attr == "clase_css_segura"
    )


def _variables_clase_css_seguras(ambito: ast.AST) -> set[str]:
    """Sigue alias locales cuyo valor ya fue validado por una lista permitida."""
    seguras: set[str] = set()
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

    cambio = True
    while cambio:
        cambio = False
        for objetivos, expresion in asignaciones:
            validada = _es_llamada_de_clase_css_segura(expresion) or (
                isinstance(expresion, ast.Name) and expresion.id in seguras
            )
            if validada:
                nuevas = objetivos - seguras
                if nuevas:
                    seguras.update(nuevas)
                    cambio = True
    return seguras


def _plantilla_html_con_marcadores(
    nodo: ast.AST,
) -> tuple[str, dict[str, ast.AST]] | None:
    """Convierte f-strings y concatenaciones en texto + marcadores AST."""
    partes: list[str] = []
    expresiones: dict[str, ast.AST] = {}

    def agregar(expresion: ast.AST) -> None:
        if isinstance(expresion, ast.Constant) and isinstance(expresion.value, str):
            partes.append(expresion.value)
        elif isinstance(expresion, ast.JoinedStr):
            for parte in expresion.values:
                if isinstance(parte, ast.Constant) and isinstance(parte.value, str):
                    partes.append(parte.value)
                elif isinstance(parte, ast.FormattedValue):
                    agregar_dinamico(parte.value)
        elif isinstance(expresion, ast.BinOp) and isinstance(expresion.op, ast.Add):
            agregar(expresion.left)
            agregar(expresion.right)
        else:
            agregar_dinamico(expresion)

    def agregar_dinamico(expresion: ast.AST) -> None:
        marcador = f"__PP_HTML_DYNAMIC_{len(expresiones)}__"
        while marcador in "".join(partes):
            marcador += "_"
        partes.append(marcador)
        expresiones[marcador] = expresion

    agregar(nodo)
    plantilla = "".join(partes)
    if not expresiones or not re.search(r"</?[A-Za-z][^>]*>", plantilla):
        return None
    return plantilla, expresiones


_ATRIBUTOS_HTML_SENSIBLES = {
    "style",
    "href",
    "src",
    "srcset",
    "action",
    "formaction",
    "poster",
    "xlink:href",
}


def _hallar_atributos_dinamicos_sin_validacion(
    arbol: ast.Module,
    fuente: str,
    ruta_relativa: str,
) -> list[str]:
    """Rechaza atributos activos/URL dinámicos y exige whitelist para class.

    El escape de comillas protege la sintaxis del atributo, pero no valida
    clases CSS, URLs, estilos ni handlers JavaScript. Solo class dispone
    aquí de un validador contextual específico.
    """
    problemas: list[str] = []
    patron_tag = re.compile(r"<[A-Za-z][^>]*>")
    patron_atributo = re.compile(
        r"""([A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*(["'])(.*?)\2""",
        re.DOTALL,
    )

    for ambito in _ambitos(arbol):
        clases_seguras = _variables_clase_css_seguras(ambito)
        for nodo in _nodos_del_ambito(ambito):
            if not isinstance(nodo, (ast.JoinedStr, ast.BinOp)):
                continue
            if not _parece_plantilla_html(nodo):
                continue
            resultado = _plantilla_html_con_marcadores(nodo)
            if resultado is None:
                continue
            plantilla, expresiones = resultado
            for tag in patron_tag.findall(plantilla):
                marcadores_en_tag = {
                    marcador: expresion
                    for marcador, expresion in expresiones.items()
                    if marcador in tag
                }
                if not marcadores_en_tag:
                    continue

                marcadores_en_atributos: set[str] = set()
                for coincidencia in patron_atributo.finditer(tag):
                    atributo = coincidencia.group(1).lower()
                    valor = coincidencia.group(3)
                    marcadores = [
                        marcador for marcador in marcadores_en_tag
                        if marcador in valor
                    ]
                    if not marcadores:
                        continue
                    marcadores_en_atributos.update(marcadores)

                    for marcador in marcadores:
                        expresion = expresiones[marcador]
                        linea = getattr(expresion, "lineno", nodo.lineno)
                        segmento = (
                            ast.get_source_segment(fuente, expresion)
                            or ast.dump(expresion)
                        )
                        if atributo == "class":
                            validada = _es_llamada_de_clase_css_segura(expresion) or (
                                isinstance(expresion, ast.Name)
                                and expresion.id in clases_seguras
                            )
                            if not validada:
                                problemas.append(
                                    f"{ruta_relativa}:{linea}: la clase HTML dinámica "
                                    f"no pasa por clase_css_segura(): {segmento}"
                                )
                        elif (
                            atributo in _ATRIBUTOS_HTML_SENSIBLES
                            or atributo.startswith("on")
                        ):
                            problemas.append(
                                f"{ruta_relativa}:{linea}: no se permite interpolación "
                                f"dinámica en el atributo HTML {atributo}: {segmento}"
                            )

                # Una interpolación en el nombre del atributo, o fuera de un
                # valor de atributo reconocido, podría construir markup activo.
                fuera_de_valores = set(marcadores_en_tag) - marcadores_en_atributos
                if fuera_de_valores:
                    for marcador in sorted(fuera_de_valores):
                        expresion = expresiones[marcador]
                        linea = getattr(expresion, "lineno", nodo.lineno)
                        problemas.append(
                            f"{ruta_relativa}:{linea}: interpolación en la estructura "
                            "de una etiqueta HTML; usar markup estático"
                        )

    return list(dict.fromkeys(problemas))


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
        problemas.extend(
            _hallar_atributos_dinamicos_sin_validacion(
                arbol,
                fuente,
                str(archivo.relative_to(UI_ROOT.parent)),
            )
        )

    assert not problemas, (
        "Se detectaron campos de texto sin escape o atributos HTML dinámicos sin validar en f-strings, "
        "concatenaciones o llamadas a .format(), incluso cuando el HTML se guarda "
        "en una variable o el dato "
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


def test_el_contrato_no_marca_calculos_ni_etiquetas_derivadas_como_texto_crudo():
    fuente = (
        "def render(persona, monto, capital):\n"
        "    porcentaje = (monto / capital * 100) if capital > 0 else 0\n"
        "    icono = '👤' if persona.nombre else '⚠'\n"
        "    alias_icono = icono\n"
        "    plantilla = f'<span>{alias_icono} {porcentaje:.1f}%</span>'\n"
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
    interpolaciones = [
        nodo for nodo in ast.walk(plantilla) if isinstance(nodo, ast.FormattedValue)
    ]

    assert "porcentaje" not in tenidas
    assert "icono" not in tenidas
    assert "alias_icono" not in tenidas
    assert all(
        not _menciona_texto_no_confiable(nodo.value, tenidas)
        for nodo in interpolaciones
    )


def test_el_contrato_detecta_texto_no_confiable_en_concatenaciones_html():
    fuente = (
        "def render(persona):\n"
        "    plantilla = '<span>' + persona.nombre + '</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba.py"
    )

    assert any("persona.nombre" in problema for problema in problemas)


def test_el_contrato_detecta_texto_no_confiable_en_format_html():
    fuente = (
        "def render(persona):\n"
        "    plantilla = '<span>{}</span>'.format(persona.nombre)\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba.py"
    )

    assert any("persona.nombre" in problema for problema in problemas)


def test_el_contrato_acepta_escape_en_concatenaciones_y_format_html():
    fuente = (
        "def render(persona):\n"
        "    primera = '<span>' + escape(persona.nombre) + '</span>'\n"
        "    segunda = '<span>{}</span>'.format(escape(persona.nombre))\n"
        "    render_html(primera)\n"
        "    render_html(segunda)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba.py"
    )

    assert not problemas, "\n".join(problemas)

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



def test_el_contrato_detecta_texto_sensible_transportado_por_lista_y_join():
    fuente = (
        "def render(persona):\n"
        "    nombre_local = persona.nombre\n"
        "    partes = [nombre_local]\n"
        "    combinado = ''.join(partes)\n"
        "    plantilla = '<span>' + combinado + '</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_join.py"
    )

    assert any("combinado" in problema for problema in problemas)


def test_el_contrato_acepta_lista_escapada_antes_de_join():
    fuente = (
        "def render(persona):\n"
        "    partes = [escape(persona.nombre)]\n"
        "    combinado = ''.join(partes)\n"
        "    plantilla = '<span>' + combinado + '</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_join_seguro.py"
    )

    assert not problemas, "\\n".join(problemas)


def test_el_contrato_detecta_valores_iterados_no_escapados_antes_de_join():
    fuente = (
        "def render(texto):\n"
        "    partes = [nombre for nombre in texto]\n"
        "    plantilla = '<span>' + ','.join(partes) + '</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_join_iterado.py"
    )

    assert any("partes" in problema for problema in problemas)


def test_el_contrato_detecta_texto_dinamico_en_atributos_html():
    fuente = (
        "def render(persona):\n"
        "    clase = persona.nombre\n"
        "    estilo = persona.nota\n"
        "    plantilla = f'<div class=\"{clase}\" style=\"{estilo}\"></div>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_atributos.py"
    )

    assert len(problemas) == 2
    assert any("clase" in problema for problema in problemas)
    assert any("estilo" in problema for problema in problemas)


def test_el_contrato_detecta_texto_sensible_transformado_con_strip():
    fuente = (
        "def render(persona):\n"
        "    nombre_limpio = persona.nombre.strip()\n"
        "    plantilla = f'<span>{nombre_limpio}</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_strip.py"
    )

    assert any("nombre_limpio" in problema for problema in problemas)


def test_el_contrato_acepta_escape_antes_de_transformar_con_strip():
    fuente = (
        "def render(persona):\n"
        "    nombre_seguro = escape(persona.nombre).strip()\n"
        "    plantilla = f'<span>{nombre_seguro}</span>'\n"
        "    render_html(plantilla)\n"
    )
    problemas = _hallar_interpolaciones_sin_escape(
        ast.parse(fuente), fuente, "ui/prueba_strip_seguro.py"
    )

    assert not problemas, "\\n".join(problemas)


def test_el_contrato_rechaza_atributos_html_dinamicos_sin_validacion():
    fuente = """
def render(nombre, estilo, url):
    plantilla = (
        f'<div class="{nombre}" style="{estilo}" href="{url}" '
        f'src="{url}" onclick="{nombre}"></div>'
    )
    render_html(plantilla)
"""
    problemas = _hallar_atributos_dinamicos_sin_validacion(
        ast.parse(fuente), fuente, "ui/prueba_atributos_activos.py"
    )

    assert len(problemas) == 5
    assert any("clase_css_segura" in problema for problema in problemas)
    assert any("style" in problema for problema in problemas)
    assert any("href" in problema for problema in problemas)
    assert any("src" in problema for problema in problemas)
    assert any("onclick" in problema for problema in problemas)


def test_el_contrato_acepta_clase_dinamica_validada_y_alias_local():
    fuente = """
def render():
    candidata = "color-rojo"
    clase_validada = componentes.clase_css_segura(
        candidata,
        permitidas=("color-rojo", "color-verde"),
        alternativa="color-verde",
    )
    alias_seguro = clase_validada
    plantilla = f'<div class="{alias_seguro}"></div>'
    render_html(plantilla)
"""
    arbol = ast.parse(fuente)
    problemas = _hallar_atributos_dinamicos_sin_validacion(
        arbol, fuente, "ui/prueba_clase_validada.py"
    )

    assert not problemas, "\n".join(problemas)


def test_el_contrato_no_acepta_escape_html_como_validador_de_url_o_estilo():
    fuente = """
def render(persona):
    destino = escape(persona.destino)
    estilo = escape(persona.nota)
    plantilla = f'<a href="{destino}" style="{estilo}">abrir</a>'
    render_html(plantilla)
"""
    problemas = _hallar_atributos_dinamicos_sin_validacion(
        ast.parse(fuente), fuente, "ui/prueba_escape_no_es_url.py"
    )

    assert len(problemas) == 2
    assert any("href" in problema for problema in problemas)
    assert any("style" in problema for problema in problemas)
