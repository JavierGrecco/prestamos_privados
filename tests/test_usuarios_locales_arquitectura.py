"""Guardas de arquitectura para autenticación y cuentas locales."""

import ast
from pathlib import Path

from aplicacion.puertos.usuarios_locales import UsuarioApp
from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "aplicacion" / "servicios" / "usuarios_locales.py"


def test_servicio_de_usuarios_no_importa_sqlite_ni_repositorios():
    """La lógica de cuentas debe operar sobre contratos, no sobre SQLite."""
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
        "ServicioUsuariosLocales debe depender de puertos de aplicación, no de "
        "SQLite o repositorios concretos:\\n- " + "\\n- ".join(problemas)
    )
    for detalle in (
        "BaseDatos",
        "UsuarioAppRepo",
        "PersonaRepo",
        "AuditoriaRepo",
        "ErrorTransaccion",
        "sqlite3",
    ):
        assert detalle not in fuente


def test_la_ui_y_el_comando_offline_usan_la_composicion():
    """Ni la pantalla de acceso ni la de usuarios construyen el servicio con db."""
    archivos = (
        ROOT / "ui" / "autenticacion_local.py",
        ROOT / "ui" / "pagina_usuarios.py",
        ROOT / "scripts" / "restablecer_password_local.py",
        ROOT / "tests" / "ui_auth_helpers.py",
    )
    problemas: list[str] = []

    for archivo in archivos:
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente, filename=str(archivo))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
                if nodo.func.id == "ServicioUsuariosLocales":
                    problemas.append(
                        f"{archivo.relative_to(ROOT)}:{nodo.lineno}: "
                        "construye el servicio directamente"
                    )

    pantalla_usuarios = (ROOT / "ui" / "pagina_usuarios.py").read_text(
        encoding="utf-8"
    )
    if "infraestructura.repositorios.personas" in pantalla_usuarios:
        problemas.append("ui/pagina_usuarios.py: importa PersonaRepo directamente")

    assert not problemas, (
        "Los consumidores deben usar infraestructura/composicion/usuarios_locales.py:\\n- "
        + "\\n- ".join(problemas)
    )
    assert "crear_servicio_usuarios_locales" in (
        ROOT / "ui" / "autenticacion_local.py"
    ).read_text(encoding="utf-8")
    assert "crear_consulta_personas_usuarios_locales" in pantalla_usuarios


class _UsuariosFalsos:
    """Sustituto pequeño del repositorio para demostrar que el caso de uso no abre SQLite."""

    def __init__(self):
        self._usuario = UsuarioApp(
            id=7,
            username="admin",
            nombre="Admin local",
            rol="ADMIN",
            activo=True,
            intentos_login_fallidos=0,
            bloqueado_hasta=None,
            ultimo_acceso_en=None,
            creado_en="2026-10-14T00:00:00+00:00",
            actualizado_en="2026-10-14T00:00:00+00:00",
            revision_sesion=1,
        )

    def cantidad(self):
        return 1

    def listar(self):
        return (self._usuario,)

    def obtener(self, usuario_id):
        return self._usuario if usuario_id == self._usuario.id else None


def test_lecturas_basicas_de_usuarios_se_prueban_sin_sqlite():
    servicio = ServicioUsuariosLocales(
        usuarios=_UsuariosFalsos(),
        personas=object(),
        auditoria=object(),
        unidad_trabajo=object(),
    )

    assert servicio.cantidad() == 1
    assert servicio.listar() == (servicio.obtener(7),)
    assert servicio.obtener(999) is None


def test_modelo_publico_conserva_la_ruta_de_importacion_historica():
    from infraestructura.repositorios.usuarios_app import UsuarioApp as UsuarioAppInfra

    assert UsuarioAppInfra is UsuarioApp
