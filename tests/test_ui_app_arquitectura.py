"""Guardas arquitectónicas para el punto de entrada Streamlit."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ui" / "app.py"


def test_punto_de_entrada_usa_servicio_de_personas_y_no_repositorios():
    fuente = APP.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(APP))
    imports_prohibidos: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name == "infraestructura.repositorios" or alias.name.startswith(
                    "infraestructura.repositorios."
                ):
                    imports_prohibidos.append(f"línea {nodo.lineno}: {alias.name}")
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo == "infraestructura.repositorios" or modulo.startswith(
                "infraestructura.repositorios."
            ):
                imports_prohibidos.append(f"línea {nodo.lineno}: {modulo}")

    assert not imports_prohibidos, (
        "La UI raíz debe usar composición, no importar repositorios concretos:\\n- "
        + "\\n- ".join(imports_prohibidos)
    )
    assert "from infraestructura.composicion.personas import crear_servicio_personas" in fuente
    assert "PersonaRepo" not in fuente


def test_main_reutiliza_la_lista_de_personas_en_el_encabezado():
    """El flujo principal consulta una vez y pasa la misma lista al encabezado."""
    fuente = APP.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(APP))
    main = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
        and nodo.name == "main"
    )

    consulta_en_main = False
    pasa_lista_al_encabezado = False

    for nodo in ast.walk(main):
        if isinstance(nodo, ast.Assign) and any(
            isinstance(objetivo, ast.Name) and objetivo.id == "personas"
            for objetivo in nodo.targets
        ):
            llamada = nodo.value
            if isinstance(llamada, ast.Call) and isinstance(llamada.func, ast.Attribute):
                base = llamada.func.value
                if (
                    llamada.func.attr == "listar"
                    and isinstance(base, ast.Call)
                    and isinstance(base.func, ast.Name)
                    and base.func.id == "crear_servicio_personas"
                ):
                    consulta_en_main = True

        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
            if nodo.func.id == "renderizar_barra_superior":
                pasa_lista_al_encabezado = any(
                    kw.arg == "personas"
                    and isinstance(kw.value, ast.Name)
                    and kw.value.id == "personas"
                    for kw in nodo.keywords
                )

    assert consulta_en_main
    assert pasa_lista_al_encabezado


def test_barra_superior_mantiene_compatibilidad_con_llamadas_sin_lista():
    fuente = APP.read_text(encoding="utf-8")
    assert "personas: list | None = None" in fuente
    assert "if personas is None:" in fuente
    assert "personas = crear_servicio_personas(db).listar()" in fuente

def test_punto_de_entrada_delega_apertura_y_no_importa_sqlite():
    """La UI presenta el estado; infraestructura/composicion controla el ciclo."""
    fuente = APP.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(APP))
    importaciones_prohibidas = []
    referencias_concretas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name in {"infraestructura.db", "infraestructura.migraciones"}:
                    importaciones_prohibidas.append(
                        f"línea {nodo.lineno}: {alias.name}"
                    )
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo in {"infraestructura.db", "infraestructura.migraciones"}:
                importaciones_prohibidas.append(
                    f"línea {nodo.lineno}: {modulo}"
                )
        elif isinstance(nodo, ast.Name) and nodo.id == "BaseDatos":
            referencias_concretas.append(f"línea {nodo.lineno}: BaseDatos")
        elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
            if nodo.func.id in {
                "BaseDatos",
                "aplicar_migraciones",
                "inspeccionar_estado_migraciones",
            }:
                referencias_concretas.append(
                    f"línea {nodo.lineno}: {nodo.func.id}(...)"
                )

    assert importaciones_prohibidas == []
    assert referencias_concretas == []
    assert (
        "from infraestructura.composicion.apertura_base_datos import"
        in fuente
    )
    assert "abrir_base_datos_para_aplicacion(ruta)" in fuente
    assert "EstadoAperturaBaseDatos.MIGRACION_PENDIENTE" in fuente

def test_conexion_sqlite_cacheada_es_exclusiva_de_la_sesion_y_se_libera():
    """Evita compartir conexión y estado de transacción entre sesiones."""
    arbol = ast.parse(APP.read_text(encoding="utf-8"), filename=str(APP))
    abrir_db = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "abrir_db"
    )
    decorador = next(
        nodo for nodo in abrir_db.decorator_list
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "cache_resource"
    )
    opciones = {kw.arg: kw.value for kw in decorador.keywords}

    assert isinstance(opciones.get("scope"), ast.Constant)
    assert opciones["scope"].value == "session"
    assert isinstance(opciones.get("on_release"), ast.Name)
    assert opciones["on_release"].id == "liberar_recurso_db"
