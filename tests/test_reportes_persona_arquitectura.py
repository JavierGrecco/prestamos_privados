"""Guardas de arquitectura para los reportes financieros por persona."""

import ast
from pathlib import Path

import pytest

from aplicacion.servicios.reportes_persona import ServicioReportesPersona


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "servicios" / "reportes_persona.py"


def test_servicio_de_reportes_no_importa_sqlite_ni_repositorios():
    """La identidad se obtiene mediante un contrato de aplicación."""
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
        "El servicio de reportes debe depender de contratos públicos:\\n- "
        + "\\n- ".join(problemas)
    )
    assert "BaseDatos" not in fuente
    assert "PersonaRepo" not in fuente
    assert "self._personas.obtener(" not in fuente


class _PersonaNoEncontrada:
    """Lector falso para probar la validación sin abrir SQLite."""

    def persona_para_reporte(self, persona_id):
        return None


def test_servicio_de_reportes_valida_persona_sin_sqlite():
    servicio = ServicioReportesPersona(
        personas=_PersonaNoEncontrada(),
        posicion=object(),
        planificacion=object(),
        rendimiento=object(),
        escenarios=object(),
    )

    with pytest.raises(ValueError, match="La persona 999 no existe"):
        servicio.obtener(999)
