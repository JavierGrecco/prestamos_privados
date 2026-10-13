"""Reglas arquitectónicas mínimas que deben permanecer estables.

El dominio contiene reglas financieras puras. No puede depender de Streamlit,
SQLite, servicios de aplicación ni adaptadores de infraestructura. Este test
inspecciona imports estáticos; no pretende detectar imports dinámicos construidos
en tiempo de ejecución, por lo que se complementará con revisiones y otras reglas.
"""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMINIO = ROOT / "dominio"

# Estas capas están fuera del dominio. Si una regla necesita una de ellas,
# debe recibir un dato o una dependencia explícita desde una capa externa.
MODULOS_PROHIBIDOS = {
    "aplicacion",
    "infraestructura",
    "ui",
    "streamlit",
    "sqlite3",
}


def _paquete_de_archivo(archivo: Path) -> str:
    """Resuelve el paquete Python al que pertenece un archivo del repositorio."""
    partes = list(archivo.relative_to(ROOT).with_suffix("").parts)
    if partes and partes[-1] == "__init__":
        partes.pop()
    return ".".join(partes)


def _modulos_importados(nodo: ast.AST, paquete: str) -> list[str]:
    """Resuelve imports absolutos y relativos para que ninguna regla los eluda."""
    if isinstance(nodo, ast.Import):
        return [alias.name for alias in nodo.names]

    if not isinstance(nodo, ast.ImportFrom):
        return []

    if nodo.level == 0:
        return [nodo.module] if nodo.module else []

    partes_paquete = paquete.split(".") if paquete else []
    niveles_a_subir = nodo.level - 1
    prefijo = partes_paquete[: max(0, len(partes_paquete) - niveles_a_subir)]

    if nodo.module:
        sufijo = nodo.module.split(".")
        return [".".join(prefijo + sufijo)]

    # from . import submodulo también es una dependencia estática explícita.
    return [
        ".".join(prefijo + [alias.name])
        for alias in nodo.names
        if alias.name != "*"
    ]


def test_el_dominio_no_importa_capas_externas_ni_adaptadores():
    """Evita que las reglas financieras queden atadas a UI o persistencia."""
    problemas: list[str] = []

    for archivo in sorted(DOMINIO.rglob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))

        paquete = _paquete_de_archivo(archivo)
        for nodo in ast.walk(arbol):
            for modulo in _modulos_importados(nodo, paquete):
                raiz = modulo.split(".", maxsplit=1)[0]
                if raiz in MODULOS_PROHIBIDOS:
                    ruta = archivo.relative_to(ROOT)
                    problemas.append(
                        f"{ruta}:{nodo.lineno}: importa '{modulo}', "
                        "que no está permitido dentro del dominio"
                    )

    assert not problemas, (
        "El dominio debe contener reglas financieras independientes de UI, "
        "aplicación e infraestructura. Corrige la dependencia o documenta y "
        "revisa el límite antes de cambiar esta regla:\n- "
        + "\n- ".join(problemas)
    )



def test_la_infraestructura_no_importa_servicios_concretos():
    """Los adaptadores no importan servicios; la raíz de composición sí puede ensamblarlos."""
    infraestructura = ROOT / "infraestructura"
    raiz_composicion = infraestructura / "composicion"
    problemas: list[str] = []

    for archivo in sorted(infraestructura.rglob("*.py")):
        # La raíz de composición es la única excepción intencional: su función
        # es conectar contratos y adaptadores con servicios concretos. No se
        # permite esta dependencia en repositorios ni en otros adaptadores.
        if archivo.is_relative_to(raiz_composicion):
            continue

        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))

        paquete = _paquete_de_archivo(archivo)
        for nodo in ast.walk(arbol):
            for modulo in _modulos_importados(nodo, paquete):
                if modulo == "aplicacion.servicios" or modulo.startswith(
                    "aplicacion.servicios."
                ):
                    ruta = archivo.relative_to(ROOT)
                    problemas.append(
                        f"{ruta}:{nodo.lineno}: importa '{modulo}', "
                        "una implementación de aplicación"
                    )

    assert not problemas, (
        "La infraestructura debe depender de puertos/contratos estables, no de "
        "servicios concretos. Mueve el contrato o documenta una excepción revisada:\n- "
        + "\n- ".join(problemas)
    )


def test_los_servicios_conservan_las_importaciones_de_contratos_anteriores():
    """Permite mover los contratos sin romper consumidores durante la transición."""
    from aplicacion.puertos.registro_pago_v3 import (
        EstadoRegistroPagoV3 as EstadoPuerto,
        IdempotenciaPagoV3 as IdempotenciaPuerto,
        RepositorioRegistroPagoV3 as RepositorioPuerto,
    )
    from aplicacion.puertos.sombra_pago_v3 import (
        DivergenciaMotorPagoV3 as DivergenciaPuerto,
        EjecucionSombraMotorPagoV3 as EjecucionPuerto,
        ResultadoEjecucionSombraV3 as ResultadoSombraPuerto,
    )
    from aplicacion.servicios.registro_pago_v3 import (
        EstadoRegistroPagoV3,
        IdempotenciaPagoV3,
        RepositorioRegistroPagoV3,
    )
    from aplicacion.servicios.puente_motor_pago_v3 import (
        DivergenciaMotorPagoV3,
        EjecucionSombraMotorPagoV3,
        ResultadoEjecucionSombraV3,
    )

    assert EstadoRegistroPagoV3 is EstadoPuerto
    assert IdempotenciaPagoV3 is IdempotenciaPuerto
    assert RepositorioRegistroPagoV3 is RepositorioPuerto
    assert DivergenciaMotorPagoV3 is DivergenciaPuerto
    assert EjecucionSombraMotorPagoV3 is EjecucionPuerto
    assert ResultadoEjecucionSombraV3 is ResultadoSombraPuerto



def test_los_puertos_no_dependen_de_servicios_concretos_ni_adaptadores():
    """Los contratos públicos no deben conocer implementaciones ni detalles de despliegue."""
    puertos = ROOT / "aplicacion" / "puertos"
    archivos = sorted(puertos.rglob("*.py"))
    assert archivos, "Debe existir al menos un módulo en aplicacion/puertos."

    problemas: list[str] = []
    modulos_prohibidos = {"infraestructura", "ui", "streamlit", "sqlite3"}

    for archivo in archivos:
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))
        paquete = _paquete_de_archivo(archivo)

        for nodo in ast.walk(arbol):
            for modulo in _modulos_importados(nodo, paquete):
                raiz = modulo.split(".", maxsplit=1)[0]
                es_servicio_concreto = (
                    modulo == "aplicacion.servicios"
                    or modulo.startswith("aplicacion.servicios.")
                )
                if raiz in modulos_prohibidos or es_servicio_concreto:
                    ruta = archivo.relative_to(ROOT)
                    problemas.append(
                        f"{ruta}:{nodo.lineno}: importa '{modulo}', "
                        "dependencia prohibida para un contrato público"
                    )

    assert not problemas, (
        "Los puertos deben depender de contratos y tipos estables, no de servicios "
        "concretos, infraestructura, UI o SQLite. Corrige el límite antes de "
        "agregar una excepción:\n- "
        + "\n- ".join(problemas)
    )


def test_la_pantalla_de_pago_no_importa_repositorios_financieros():
    """La UI usa consultas/casos de uso públicos, no repositorios de persistencia."""
    archivo = ROOT / "ui" / "pagina_registrar_pago.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            if modulo == "infraestructura.repositorios" or modulo.startswith(
                "infraestructura.repositorios."
            ):
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}' directamente"
                )

    assert not problemas, (
        "La pantalla de registro de pagos no debe conocer los repositorios. "
        "Publica la consulta necesaria desde aplicación y úsala desde la UI:\\n- "
        + "\\n- ".join(problemas)
    )


def test_la_consulta_de_deuda_depende_de_un_puerto_y_no_de_sqlite():
    """La consulta reutilizable recibe lecturas por contrato, no crea repositorios."""
    archivo = ROOT / "aplicacion" / "consultas" / "deuda_proximo_pago.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "La consulta de deuda debe depender del puerto de lectura. La composición "
        "del adaptador concreto debe ocurrir fuera de este módulo:\\n- "
        + "\\n- ".join(problemas)
    )


def test_fachada_preview_no_compone_repositorios_concretos():
    """La fachada de aplicación recibe colaboradores; infraestructura los ensambla."""
    archivo = ROOT / "aplicacion" / "consultas" / "preview_pago.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "La fachada de preview pertenece a aplicación y no debe crear "
        "repositorios/adaptadores concretos. Usa el punto de composición "
        "de infraestructura:\\n- "
        + "\\n- ".join(problemas)
    )


def test_preview_v3_no_importa_adaptadores_de_infraestructura():
    """El preview V3 recibe sus lectores; SQLite se ensambla fuera de aplicación."""
    archivo = ROOT / "aplicacion" / "consultas" / "preview_pago_v3.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "El preview V3 debe depender de puertos públicos, no de adaptadores "
        "concretos. Ensambla SQLite desde infraestructura/composicion/pagos.py:\\n- "
        + "\\n- ".join(problemas)
    )


def test_servicio_registro_pago_ui_recibe_colaboradores_y_no_compone_sqlite():
    """El caso de uso de registro no debe construir repositorios ni fábricas SQLite."""
    archivo = ROOT / "aplicacion" / "servicios" / "registro_pago_ui.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []
    modulos_concretos_prohibidos = {
        "infraestructura",
        "sqlite3",
        "infraestructura.composicion.registradores_pago",
    }

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            es_fabrica_concreta = modulo in modulos_concretos_prohibidos
            if raiz in {"infraestructura", "sqlite3"} or es_fabrica_concreta:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "ServicioRegistroPagoUI debe recibir sus colaboradores desde el punto "
        "de composición local, no crear repositorios ni fábricas SQLite:\\n- "
        + "\\n- ".join(problemas)
    )


def test_las_pantallas_usan_la_composicion_para_crear_el_servicio_de_registro():
    """Evita que una pantalla vuelva a construir el caso de uso con una conexión."""
    archivos = (
        ROOT / "ui" / "pagina_registrar_pago.py",
        ROOT / "ui" / "pagina_motor_v3.py",
    )
    problemas: list[str] = []

    for archivo in archivos:
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            funcion = nodo.func
            if isinstance(funcion, ast.Name) and funcion.id == "ServicioRegistroPagoUI":
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    "construye ServicioRegistroPagoUI directamente"
                )

    assert not problemas, (
        "Las pantallas deben usar crear_servicio_registro_pago_ui desde la "
        "composición de infraestructura:\\n- " + "\\n- ".join(problemas)
    )


def test_preflight_v3_depende_de_contratos_y_no_de_adaptadores():
    """Los lectores de esquema, integridad y métricas se inyectan desde composición."""
    archivo = ROOT / "aplicacion" / "servicios" / "preflight_motor_pago_v3.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "PreflightMotorPagoV3 debe recibir lectores por contrato. La composición "
        "SQLite queda en infraestructura/composicion/pagos.py:\\n- "
        + "\\n- ".join(problemas)
    )


def test_readiness_canary_recibe_preflight_y_configuracion_por_contrato():
    """Readiness no debe volver a construir servicios o adaptadores con SQLite."""
    archivo = ROOT / "aplicacion" / "servicios" / "precheck_canary_motor_pago_v3.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "Readiness debe recibir el preflight y la configuración desde composición; "
        "no construirlos sobre una conexión SQLite:\\n- "
        + "\\n- ".join(problemas)
    )


def test_servicio_metricas_sombra_depende_de_consulta_publica():
    """La capa de aplicación no construye consultas de infraestructura."""
    archivo = ROOT / "aplicacion" / "servicios" / "metricas_sombra_v3.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "ServicioMetricasSombraV3 debe recibir la consulta por un contrato público, "
        "no construir el adaptador concreto:\\n- "
        + "\\n- ".join(problemas)
    )


def test_configuracion_motor_pago_depende_de_persistencia_por_contrato():
    """La regla de modo no debe construir repositorios ni transacciones SQLite."""
    archivo = ROOT / "aplicacion" / "servicios" / "configuracion_motor_pago.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    paquete = _paquete_de_archivo(archivo)
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        for modulo in _modulos_importados(nodo, paquete):
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(
                    f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                    f"importa '{modulo}'"
                )

    assert not problemas, (
        "ServicioConfiguracionMotorPago debe usar el puerto transaccional; "
        "los repositorios y la auditoría quedan en infraestructura/adaptadores:\\n- "
        + "\\n- ".join(problemas)
    )


def test_las_fabricas_sqlite_de_pago_viven_en_composicion():
    """Las fábricas que construyen repositorios concretos no pertenecen a aplicación."""
    rutas_prohibidas = (
        ROOT / "aplicacion" / "servicios" / "fabrica_registro_pago_v3.py",
        ROOT / "aplicacion" / "servicios" / "fabrica_sombra_pago_v3_sqlite.py",
    )
    existentes = [
        str(ruta.relative_to(ROOT))
        for ruta in rutas_prohibidas
        if ruta.exists()
    ]

    assert not existentes, (
        "Las fábricas SQLite de registro deben vivir en "
        "infraestructura/composicion/registradores_pago.py. Rutas antiguas "
        "encontradas:\\n- " + "\\n- ".join(existentes)
    )
