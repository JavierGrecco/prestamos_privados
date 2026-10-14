"""Guardas y pruebas sin SQLite para la vista humana de Mi espacio."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from aplicacion.consultas.vista_humana_persona import VistaHumanaPersonaQuery
from aplicacion.puertos.vista_humana_persona import PersonaVistaHumana


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "consultas" / "vista_humana_persona.py"


def test_vista_humana_no_importa_sqlite_ni_repositorios():
    """La vista coordina contratos; la composición decide los adaptadores."""
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
        "Mi espacio debe depender de contratos públicos, no de infraestructura:\\n- "
        + "\\n- ".join(problemas)
    )
    for detalle in ("BaseDatos", "PersonaRepo", "PrestamoRepo", "ParticipacionRepo"):
        assert detalle not in fuente
    assert "self._db" not in fuente


class _DatosVistaHumanaFalsos:
    def persona_por_id(self, persona_id):
        if persona_id != 7:
            return None
        return PersonaVistaHumana(id=7, nombre="Ana", apellido="Ejemplo")

    def roles_por_persona(self, persona_id):
        return ("DEUDOR", "INVERSOR")

    def prestamos_por_deudor(self, persona_id):
        return ()

    def prestamo_por_id(self, prestamo_id):
        return None

    def participaciones_por_inversor(self, persona_id):
        return ()


class _AnalisisSinMovimientos:
    def obtener(self, persona_id, *, fecha_corte=None):
        return SimpleNamespace(
            flujos_reales=(),
            flujos_proyectados=(),
            resumen=SimpleNamespace(
                capital_aportado_activo=Decimal("0.00"),
                capital_deudor_pendiente=Decimal("0.00"),
            ),
            advertencias=(),
        )


class _DetalleNoUsado:
    def obtener(self, prestamo_id):
        raise AssertionError("No debe consultarse detalle sin préstamos.")


def test_vista_humana_se_prueba_sin_sqlite():
    consulta = VistaHumanaPersonaQuery(
        datos=_DatosVistaHumanaFalsos(),
        detalle=_DetalleNoUsado(),
        analisis=_AnalisisSinMovimientos(),
    )

    vista = consulta.obtener(
        7,
        fecha_corte=date(2026, 10, 14),
    )

    assert vista.persona_id == 7
    assert vista.nombre == "Ana Ejemplo"
    assert vista.roles == ("DEUDOR", "INVERSOR")
    assert vista.posiciones == ()
    assert vista.actividad_reciente == ()
    assert vista.capital_invertido == Decimal("0.00")
    assert vista.capital_pendiente_deuda == Decimal("0.00")
    assert vista.advertencias == ()
