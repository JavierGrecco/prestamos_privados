"""Guardas arquitectónicas y pruebas de traducción de errores de garantías."""

import ast
from contextlib import contextmanager
import sqlite3
from pathlib import Path

import pytest

from aplicacion.puertos.garantias_prestamo import GarantiaActivaDuplicada
from aplicacion.servicios.garantias_prestamo import ServicioGarantiasPrestamo
from infraestructura.adaptadores.unidad_trabajo_garantias import (
    UnidadTrabajoGarantiasSQLite,
)
from infraestructura.excepciones import ErrorTransaccion


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "aplicacion" / "servicios" / "garantias_prestamo.py"
UI = ROOT / "ui" / "pagina_prestamos.py"
COMPOSITION = ROOT / "infraestructura" / "composicion" / "garantias_prestamo.py"


def test_servicio_garantias_no_importa_sqlite_ni_repositorios_concretos():
    """El caso de uso depende sólo de contratos de aplicación."""
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
        "ServicioGarantiasPrestamo debe usar puertos públicos, no infraestructura:\\n- "
        + "\\n- ".join(problemas)
    )
    for detalle in (
        "BaseDatos",
        "GarantiaPrestamoRepo",
        "PersonaRepo",
        "PrestamoRepo",
        "AuditoriaRepo",
        "ErrorTransaccion",
    ):
        assert detalle not in fuente


def test_ui_de_prestamos_usa_composicion_para_garantias():
    fuente = UI.read_text(encoding="utf-8")
    assert "crear_servicio_garantias_prestamo(db)" in fuente
    assert "ServicioGarantiasPrestamo(db)" not in fuente
    assert "from aplicacion.servicios.garantias_prestamo import" not in fuente
    ensamblado = COMPOSITION.read_text(encoding="utf-8")
    assert "UnidadTrabajoGarantiasSQLite(db)" in ensamblado
    assert "GarantiaPrestamoRepo(db)" in ensamblado


class _DBConflictoUnicidad:
    """Simula el envoltorio de BaseDatos cuando SQLite rechaza un duplicado."""

    @contextmanager
    def transaccion(self):
        yield
        causa = sqlite3.IntegrityError(
            "UNIQUE constraint failed: garantias_prestamo.prestamo_id, "
            "garantias_prestamo.garante_id"
        )
        raise ErrorTransaccion("Transacción abortada") from causa


class _DBErrorTecnico:
    @contextmanager
    def transaccion(self):
        yield
        causa = sqlite3.OperationalError("base ocupada")
        raise ErrorTransaccion("Transacción abortada") from causa


class _DBErrorNegocio:
    @contextmanager
    def transaccion(self):
        try:
            yield
        except ValueError as exc:
            raise ErrorTransaccion("Transacción abortada") from exc


def test_unidad_de_trabajo_traduce_unicidad_a_error_publico():
    unidad = UnidadTrabajoGarantiasSQLite(_DBConflictoUnicidad())

    with pytest.raises(GarantiaActivaDuplicada, match="garantía activa"):
        with unidad.transaccion():
            pass


def test_unidad_de_trabajo_no_oculta_errores_tecnicos():
    unidad = UnidadTrabajoGarantiasSQLite(_DBErrorTecnico())

    with pytest.raises(ErrorTransaccion) as capturado:
        with unidad.transaccion():
            pass

    assert isinstance(capturado.value.__cause__, sqlite3.OperationalError)


def test_unidad_de_trabajo_solo_desenvuelve_error_de_negocio_si_se_pide():
    unidad = UnidadTrabajoGarantiasSQLite(_DBErrorNegocio())

    with pytest.raises(ErrorTransaccion):
        with unidad.transaccion():
            raise ValueError("validación")

    with pytest.raises(ValueError, match="validación"):
        with unidad.transaccion(propagar_errores_de_negocio=True):
            raise ValueError("validación")


def test_ui_lista_nombres_de_garantes_por_servicio_publico_de_personas():
    """La pantalla presenta nombres mediante composición, no con PersonaRepo."""
    fuente = UI.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(UI))
    imports_persona_repo = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo == "infraestructura.repositorios" or modulo.startswith(
                "infraestructura.repositorios."
            ):
                for alias in nodo.names:
                    if alias.name == "PersonaRepo":
                        imports_persona_repo.append(nodo.lineno)

    assert imports_persona_repo == []
    assert (
        "from infraestructura.composicion.personas import crear_servicio_personas"
        in fuente
    )
    assert "crear_servicio_personas(db).listar()" in fuente
