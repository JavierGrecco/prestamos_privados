"""Guardas de arquitectura para el análisis financiero de persona."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.analisis_financiero import AnalisisFinancieroQuery


ROOT = Path(__file__).resolve().parents[1]


def test_read_model_financiero_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "analisis_financiero.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
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
        "El análisis financiero debe depender de contratos de aplicación, "
        "no de SQLite ni de infraestructura:\n- " + "\n- ".join(problemas)
    )
    assert ".consultar(" not in fuente
    assert "SELECT " not in fuente


class _ConsultaFinancieraVacia:
    """Doble de prueba que no necesita SQLite ni repositorios."""

    def prestamos_por_deudor(self, persona_id):
        return ()

    def participaciones_por_inversor(self, persona_id):
        return ()

    def cobros_de_inversor(self, persona_id, hasta):
        return ()


def test_analisis_financiero_puede_probarse_sin_base_de_datos():
    query = AnalisisFinancieroQuery(_ConsultaFinancieraVacia())

    resultado = query.obtener(
        7,
        fecha_corte=date(2026, 10, 13),
        inflacion_mensual_supuesto=Decimal("0.00"),
    )

    assert resultado.persona_id == 7
    assert resultado.fecha_corte == date(2026, 10, 13)
    assert resultado.flujos_reales == ()
    assert resultado.flujos_proyectados == ()
    assert resultado.resumen.capital_aportado_activo == Decimal("0.00")
    assert resultado.resumen.capital_deudor_pendiente == Decimal("0.00")
    assert resultado.resumen.xirr_inversor is None
    assert resultado.resumen.xirr_deudor is None
