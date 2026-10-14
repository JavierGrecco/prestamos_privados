"""Guardas de arquitectura y pruebas sin SQLite para ServicioPersonas."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from aplicacion.servicios.personas import ServicioPersonas


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "aplicacion" / "servicios" / "personas.py"


def test_servicio_personas_no_importa_repositorios_ni_sqlite():
    """Las reglas de personas trabajan sobre puertos de aplicación."""
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
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "ServicioPersonas debe depender de contratos, no de infraestructura:\\n- "
        + "\\n- ".join(problemas)
    )
    for nombre in (
        "BaseDatos",
        "PersonaRepo",
        "PrestamoRepo",
        "ParticipacionRepo",
        "GarantiaPrestamoRepo",
    ):
        assert nombre not in fuente


def test_ui_y_exportaciones_consumen_composicion_y_puerto_de_personas():
    pantalla = (ROOT / "ui" / "personas_view.py").read_text(encoding="utf-8")
    exportaciones = (ROOT / "aplicacion" / "servicios" / "exportaciones.py").read_text(
        encoding="utf-8"
    )
    composicion = (
        ROOT / "infraestructura" / "composicion" / "exportaciones.py"
    ).read_text(encoding="utf-8")

    assert "crear_servicio_personas(db)" in pantalla
    assert "ServicioPersonas(db)" not in pantalla
    assert "PersonaRepo" not in pantalla
    assert "ConsultaPersonasParaExportar" in exportaciones
    assert "ServicioPersonas(db)" not in exportaciones
    assert "personas=crear_servicio_personas(db)" in composicion


class _PersonasFalsas:
    def __init__(self):
        self.persona = object()
        self.roles_quitados: list[tuple[int, str, str]] = []
        self.creaciones: list[dict] = []

    def listar(self, estado=None, rol=None):
        return (self.persona,)

    def obtener(self, persona_id):
        return self.persona if persona_id == 1 else None

    def crear(self, **kwargs):
        self.creaciones.append(kwargs)
        return 1

    def actualizar(self, persona_id, **campos):
        return None

    def agregar_rol(self, persona_id, rol):
        return None

    def quitar_rol(self, persona_id, rol, motivo=""):
        self.roles_quitados.append((persona_id, rol, motivo))

    def roles(self, persona_id):
        return ()


class _PrestamosFalsos:
    def listar(self, estado=None, deudor_id=None):
        return ()

    def obtener(self, prestamo_id):
        return None


class _ParticipacionesFalsas:
    def por_inversor(self, inversor_id):
        return ()


class _GarantiasFalsas:
    def __init__(self, estado="INACTIVA"):
        self.estado = estado

    def por_garante(self, garante_id):
        return (SimpleNamespace(estado=self.estado),)


def crear_servicio_de_prueba(*, estado_garantia="INACTIVA"):
    personas = _PersonasFalsas()
    servicio = ServicioPersonas(
        personas=personas,
        prestamos=_PrestamosFalsos(),
        participaciones=_ParticipacionesFalsas(),
        garantias=_GarantiasFalsas(estado_garantia),
    )
    return servicio, personas


def test_servicio_personas_rechaza_baja_de_garante_con_garantia_activa_sin_sqlite():
    servicio, personas = crear_servicio_de_prueba(estado_garantia="ACTIVA")

    with pytest.raises(ValueError, match="garantías activas"):
        servicio.quitar_rol(1, "GARANTE")

    assert personas.roles_quitados == []


def test_servicio_personas_no_permite_asignar_admin_historico_sin_sqlite():
    servicio, personas = crear_servicio_de_prueba()

    with pytest.raises(ValueError, match="ADMIN es un rol histórico"):
        servicio.crear(nombre="Persona de prueba", roles=("ADMIN",))

    assert personas.creaciones == []
