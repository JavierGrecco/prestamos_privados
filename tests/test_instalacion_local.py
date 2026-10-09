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
    (root / "scripts" / "migrar_base.py").write_text("", encoding="utf-8")
    (root / "ui" / "app.py").write_text("", encoding="utf-8")
    (root / ".venv").mkdir()
    return root


def _done(args, *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def _payload(resultado: str) -> str:
    return json.dumps({"resultado": resultado, "migraciones_pendientes": []})


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
