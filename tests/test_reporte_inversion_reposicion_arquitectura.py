"""Guardas de arquitectura para el reporte de reposición e inversión."""

import ast
from pathlib import Path

import pytest

from aplicacion.servicios.reporte_inversion_reposicion import (
    ServicioReporteInversionReposicion,
)
from dominio import ErrorValidacion


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "servicios" / "reporte_inversion_reposicion.py"


def test_servicio_de_reporte_no_importa_sqlite_ni_repositorios():
    """La aplicación solo coordina el puerto; los SELECT quedan en infraestructura."""
    fuente = TARGET.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(TARGET))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue

        for modulo in modulos:
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "El informe de reposición debe depender de un puerto público, no de SQLite:\\n- "
        + "\\n- ".join(problemas)
    )
    for detalle in ("BaseDatos", "PlanesReposicionRepo", "self._db", "self._repo"):
        assert detalle not in fuente


class _LectorSinPlan:
    """Lector falso para comprobar validaciones sin inicializar SQLite."""

    def obtener_plan(self, plan_id):
        return None


def test_reporte_valida_plan_inexistente_sin_sqlite():
    servicio = ServicioReporteInversionReposicion(_LectorSinPlan())

    with pytest.raises(ErrorValidacion, match="El plan seleccionado no existe"):
        servicio.obtener(999)
