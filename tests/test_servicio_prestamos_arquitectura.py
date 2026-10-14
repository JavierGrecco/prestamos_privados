"""Guardas arquitectónicas para el límite de ServicioPrestamos."""

import ast
from pathlib import Path
from types import SimpleNamespace

from aplicacion.servicios.prestamos import ServicioPrestamos

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "aplicacion" / "servicios" / "prestamos.py"
COMPOSITION = ROOT / "infraestructura" / "composicion" / "prestamos.py"
UI_ALTA = ROOT / "ui" / "pagina_alta_prestamo.py"
UI_PRESTAMOS = ROOT / "ui" / "pagina_prestamos.py"


def test_servicio_prestamos_depende_de_puertos_y_no_de_infraestructura():
    """La orquestación de préstamos no debe crear repositorios ni abrir SQLite."""
    fuente = SERVICE.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(SERVICE))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "ServicioPrestamos debe depender de contratos de aplicación, no de "
        "repositorios concretos:\\n- " + "\\n- ".join(problemas)
    )
    for detalle in (
        "BaseDatos",
        "PersonaRepo",
        "PrestamoRepo",
        "ParticipacionRepo",
        "LedgerRepo",
        "AuditoriaRepo",
    ):
        assert detalle not in fuente


def test_pantallas_de_alta_y_prestamos_usan_la_composicion_publica():
    for archivo in (UI_ALTA, UI_PRESTAMOS):
        fuente = archivo.read_text(encoding="utf-8")
        assert "crear_servicio_prestamos(db)" in fuente
        assert "ServicioPrestamos(db)" not in fuente
        assert "from aplicacion.servicios.prestamos import ServicioPrestamos" not in fuente

    composicion = COMPOSITION.read_text(encoding="utf-8")
    assert "UnidadTrabajoPrestamosSQLite(db)" in composicion
    for repositorio in (
        "PersonaRepo(db)",
        "PrestamoRepo(db)",
        "ParticipacionRepo(db)",
        "LedgerRepo(db)",
        "AuditoriaRepo(db)",
    ):
        assert repositorio in composicion


def test_pruebas_de_atomicidad_consumen_la_composicion_publica():
    atomicidad = (
        ROOT / "tests" / "test_servicio_prestamo_atomicidad.py"
    ).read_text(encoding="utf-8")
    ciclo_vida = (ROOT / "tests" / "test_prestamo_lifecycle.py").read_text(
        encoding="utf-8"
    )
    assert "crear_servicio_prestamos(db)" in atomicidad
    assert "ServicioPrestamos(db)" not in atomicidad
    assert "crear_servicio_prestamos(db)" in ciclo_vida
    assert "ServicioPrestamos(db)" not in ciclo_vida



class _PrestamosFalsos:
    """Repositorio pequeño para probar el caso de uso sin abrir SQLite."""

    def obtener(self, prestamo_id: int):
        if prestamo_id != 12:
            return None
        return SimpleNamespace(estado="ACTIVO")

    def version_activa(self, prestamo_id: int):
        return 3 if prestamo_id == 12 else None

    def cuotas(self, version_id: int):
        if version_id != 3:
            return ()
        return (SimpleNamespace(estado="PAGADA"), SimpleNamespace(estado="ANULADA"))


def test_servicio_prestamos_funciona_con_colaboradores_falsos_sin_sqlite():
    servicio = ServicioPrestamos(
        personas=object(),
        prestamos=_PrestamosFalsos(),
        participaciones=object(),
        ledger=object(),
        auditoria=object(),
        unidad_trabajo=object(),
    )

    assert servicio.puede_finalizar(12) is True
    assert "EN_MORA" in servicio.opciones_de_estado(12)
