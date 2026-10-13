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


def _modulos_importados(nodo: ast.AST) -> list[str]:
    """Obtiene los nombres de módulo de imports normales y relativos."""
    if isinstance(nodo, ast.Import):
        return [alias.name for alias in nodo.names]
    if isinstance(nodo, ast.ImportFrom) and nodo.module:
        return [nodo.module]
    return []


def test_el_dominio_no_importa_capas_externas_ni_adaptadores():
    """Evita que las reglas financieras queden atadas a UI o persistencia."""
    problemas: list[str] = []

    for archivo in sorted(DOMINIO.rglob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))

        for nodo in ast.walk(arbol):
            for modulo in _modulos_importados(nodo):
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
    """Los adaptadores usan puertos públicos, no implementaciones de aplicación."""
    infraestructura = ROOT / "infraestructura"
    problemas: list[str] = []

    for archivo in sorted(infraestructura.rglob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            else:
                continue

            for modulo in modulos:
                if modulo == "aplicacion.servicios" or modulo.startswith(
                    "aplicacion.servicios."
                ):
                    ruta = archivo.relative_to(ROOT)
                    problemas.append(
                        f"{ruta}:{nodo.lineno}: importa '{modulo}', "
                        "una implementación de aplicación"
                    )

    assert not problemas, (
        "Los repositorios deben depender de puertos/contratos estables, no de "
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
