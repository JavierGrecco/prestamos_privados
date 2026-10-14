"""Guardas de arquitectura para el comparador M7."""

import ast
from pathlib import Path

from aplicacion.consultas.comparador_decisiones_financieras import (
    ComparadorDecisionesFinancierasQuery,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "consultas" / "comparador_decisiones_financieras.py"


def test_comparador_no_importa_sqlite_ni_repositorios():
    """El comparador opera mediante contratos, no detalles de persistencia."""
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
        "El comparador M7 debe depender de contratos públicos:\\n- "
        + "\\n- ".join(problemas)
    )
    for detalle in ("BaseDatos", "PersonaRepo", "PrestamoRepo", "ParticipacionRepo"):
        assert detalle not in fuente
    assert "self._db" not in fuente
    assert ".consultar(" not in fuente


class _DatosComparadorVacios:
    """Lector falso para verificar el comparador sin abrir SQLite."""

    def persona_existe(self, persona_id):
        return persona_id == 7

    def prestamos_por_deudor(self, persona_id):
        return ()

    def participaciones_por_inversor(self, persona_id):
        return ()

    def prestamo_por_id(self, prestamo_id):
        return None

    def tasa_activa(self, prestamo_id):
        return None


def test_listado_de_alternativas_se_puede_probar_sin_sqlite():
    consulta = ComparadorDecisionesFinancierasQuery(
        datos=_DatosComparadorVacios(),
        analisis=object(),
    )

    assert consulta.listar_alternativas(7) == ()
