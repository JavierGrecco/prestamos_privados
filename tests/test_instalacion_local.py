"""Pruebas de los comandos de instalación e inicio local reproducible."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
import pytest
from scripts import iniciar_local, preparar_entorno


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "ui").mkdir()
    (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (root / "requirements.txt").write_text("", encoding="utf-8")
    (root / "requirements-dev.txt").write_text("", encoding="utf-8")
    (root / "scripts" / "migrar_base.py").write_text("", encoding="utf-8")
    (root / "ui" / "app.py").write_text("", encoding="utf-8")
    (root / ".venv").mkdir()
    return root


def _done(args, *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def _payload(resultado: str, **extra) -> str:
    return json.dumps({"resultado": resultado, "migraciones_pendientes": [], **extra})


def test_preparador_exige_raiz_del_checkout(tmp_path: Path):
    root = _root(tmp_path)
    error = preparar_entorno.error_raiz(root, tmp_path)
    assert error is not None
    assert "raíz" in error.lower()


def test_preparador_rechaza_python_anterior_a_311():
    assert preparar_entorno.version_soportada((3, 10, 14)) is False
    assert preparar_entorno.version_soportada((3, 11, 0)) is True
    assert preparar_entorno.version_soportada((3, 14, 1)) is True


@pytest.mark.parametrize("windows,relative", [
    (True, Path(".venv") / "Scripts" / "python.exe"),
    (False, Path(".venv") / "bin" / "python"),
])
def test_preparador_resuelve_interprete_del_entorno(tmp_path: Path, windows: bool, relative: Path):
    assert preparar_entorno.ruta_python_venv(tmp_path, windows) == tmp_path / relative


def test_preparador_crea_venv_instala_dev_y_verifica_dependencias(tmp_path: Path):
    root = _root(tmp_path)
    import shutil
    shutil.rmtree(root / ".venv")
    llamadas: list[list[str]] = []

    class Builder:
        def create(self, path: Path):
            python = path / "bin" / "python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("fake interpreter", encoding="utf-8")

    def runner(args, **kwargs):
        llamadas.append(args)
        if "-c" in args:
            return _done(args, stdout="3.11")
        return _done(args, stdout="No broken requirements found.")

    mensajes: list[str] = []
    codigo = preparar_entorno.ejecutar(
        [], root=root, cwd=root, version_actual=(3, 11, 9),
        windows=False, env_builder=Builder(), runner=runner,
        output=mensajes.append,
    )
    assert codigo == 0
    assert (root / ".venv" / "bin" / "python").is_file()
    assert any("install" in args and "requirements-dev.txt" in args for args in llamadas)
    assert any(args[-3:] == ["-m", "pip", "check"] for args in llamadas)
    assert any("La base SQLite no fue creada" in mensaje for mensaje in mensajes)


def test_preparador_rechaza_venv_incompleto_sin_borrarlo(tmp_path: Path):
    root = _root(tmp_path)
    mensajes: list[str] = []
    codigo = preparar_entorno.ejecutar(
        [], root=root, cwd=root, version_actual=(3, 11, 1),
        windows=False,
        runner=lambda *args, **kwargs: pytest.fail("no debe instalar dependencias"),
        output=mensajes.append,
    )
    assert codigo == 2
    assert (root / ".venv").is_dir()
    assert any("No se borró ni reemplazó nada" in mensaje for mensaje in mensajes)


def test_inicio_exige_entorno_virtual_de_este_checkout(tmp_path: Path):
    root = _root(tmp_path)
    mensajes: list[str] = []
    codigo = iniciar_local.ejecutar(
        ["--db", "datos/prueba.db"], root=root, cwd=root,
        ejecutable=str(root / "python"), prefix=tmp_path / "global",
        base_prefix=tmp_path / "global",
        runner=lambda *args, **kwargs: pytest.fail("no debe ejecutar procesos"),
        output=mensajes.append,
    )
    assert codigo == 2
    assert any("entorno .venv" in mensaje for mensaje in mensajes)


def test_inicio_inicializa_solo_una_base_nueva(tmp_path: Path):
    root = _root(tmp_path)
    db = root / "datos" / "nueva.db"
    llamadas: list[tuple[list[str], dict]] = []

    def runner(args, **kwargs):
        llamadas.append((args, kwargs))
        if "scripts.migrar_base" in args:
            migraciones = [x for x in llamadas if "scripts.migrar_base" in x[0]]
            if "--aplicar" in args:
                return _done(args, stdout=_payload("APLICADA"))
            if len(migraciones) == 1:
                return _done(args, stdout=_payload("BASE_INEXISTENTE"))
            return _done(args, stdout=_payload("ACTUALIZADA"))
        if "streamlit" in args:
            return _done(args)
        return _done(args, stdout="3.11")

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/nueva.db"], root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 0
    migraciones = [args for args, _ in llamadas if "scripts.migrar_base" in args]
    assert "--aplicar" in migraciones[1]
    assert "--backup" not in migraciones[1]
    ui = next((args, kwargs) for args, kwargs in llamadas if "streamlit" in args)
    assert ui[1]["env"]["PRESTAMOS_DB_PATH"] == str(db.resolve())
    assert ui[1]["env"]["PRESTAMOS_AUTH_MODE"] == "local"


def test_inicio_inicializa_archivo_sqlite_vacio_sin_backup(tmp_path: Path):
    root = _root(tmp_path)
    llamadas: list[list[str]] = []
    estados = iter([
        _payload("REQUIERE_MIGRACION", es_base_nueva=True),
        _payload("APLICADA"),
        _payload("ACTUALIZADA"),
    ])

    def runner(args, **kwargs):
        llamadas.append(args)
        if "scripts.migrar_base" in args:
            return _done(args, stdout=next(estados))
        if "streamlit" in args:
            return _done(args)
        return _done(args)

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/vacia.db"], root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 0
    migraciones = [args for args in llamadas if "scripts.migrar_base" in args]
    assert len(migraciones) == 3
    assert "--aplicar" in migraciones[1]
    assert "--backup" not in migraciones[1]
    assert any("streamlit" in args for args in llamadas)


def test_inicio_base_actualizada_lanza_login_con_la_ruta_seleccionada(tmp_path: Path):
    root = _root(tmp_path)
    llamadas: list[tuple[list[str], dict]] = []

    def runner(args, **kwargs):
        llamadas.append((args, kwargs))
        if "scripts.migrar_base" in args:
            return _done(args, stdout=_payload("ACTUALIZADA"))
        if "streamlit" in args:
            return _done(args)
        return _done(args)

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/cartera-existente.db"], root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 0
    migraciones = [args for args, _ in llamadas if "scripts.migrar_base" in args]
    assert len(migraciones) == 1
    assert "--aplicar" not in migraciones[0]
    ui = next((args, kwargs) for args, kwargs in llamadas if "streamlit" in args)
    assert ui[1]["env"]["PRESTAMOS_DB_PATH"] == str((root / "datos/cartera-existente.db").resolve())


def test_inicio_no_migra_base_existente_sin_autorizacion(tmp_path: Path):
    root = _root(tmp_path)
    llamadas: list[list[str]] = []

    def runner(args, **kwargs):
        llamadas.append(args)
        return _done(args, stdout=_payload("REQUIERE_MIGRACION"))

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/existente.db"], root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 2
    assert len(llamadas) == 1
    assert not any("streamlit" in args for args in llamadas)
    assert "--aplicar" not in llamadas[0]


def test_inicio_actualiza_base_existente_solo_con_backup_explicito(tmp_path: Path):
    root = _root(tmp_path)
    llamadas: list[tuple[list[str], dict]] = []
    estados = iter(["REQUIERE_MIGRACION", "APLICADA", "ACTUALIZADA"])

    def runner(args, **kwargs):
        llamadas.append((args, kwargs))
        if "scripts.migrar_base" in args:
            return _done(args, stdout=_payload(next(estados)))
        if "streamlit" in args:
            return _done(args)
        return _done(args)

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/existente.db", "--actualizar-migraciones",
         "--backup", "backups/antes.db"],
        root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 0
    migraciones = [args for args, _ in llamadas if "scripts.migrar_base" in args]
    assert len(migraciones) == 3
    assert "--aplicar" in migraciones[1]
    assert "--backup" in migraciones[1]
    assert str((root / "backups" / "antes.db").resolve()) in migraciones[1]


def test_inicio_detiene_base_con_historial_invalido(tmp_path: Path):
    root = _root(tmp_path)
    llamadas: list[list[str]] = []

    def runner(args, **kwargs):
        llamadas.append(args)
        return _done(args, stdout=_payload("RECHAZADO_HISTORIAL"))

    codigo = iniciar_local.ejecutar(
        ["--db", "datos/ambigua.db"], root=root, cwd=root,
        ejecutable=str(root / ".venv" / "bin" / "python"),
        prefix=root / ".venv", base_prefix=tmp_path / "python-base",
        runner=runner, output=lambda _: None,
    )
    assert codigo == 2
    assert len(llamadas) == 1
    assert not any("streamlit" in args for args in llamadas)
