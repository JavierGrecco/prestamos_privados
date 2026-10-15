"""Pruebas del inventario automático de fronteras modulares."""

from pathlib import Path

from scripts.auditar_fronteras_modulares import analizar, a_json, a_markdown


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_detecta_dependencias_entre_capas_sql_y_constructores(tmp_path: Path):
    _write(tmp_path, "dominio/regla.py", "from infraestructura.db import BaseDatos\n")
    _write(
        tmp_path,
        "aplicacion/servicios/caso.py",
        (
            "from infraestructura.repositorios import PrestamoRepo\n"
            "def ejecutar(db):\n"
            "    repo = PrestamoRepo(db)\n"
            "    db.consultar('SELECT id FROM prestamos')\n"
        ),
    )
    _write(
        tmp_path,
        "ui/pagina.py",
        "from infraestructura.repositorios.personas import PersonaRepo\n"
        "def render(db):\n"
        "    return PersonaRepo(db)\n",
    )

    informe = analizar(tmp_path)
    codigos = {hallazgo.codigo for hallazgo in informe.hallazgos}

    assert "DOM-DEPENDENCIA-ASCENDENTE" in codigos
    assert "APP-IMPORTA-DB-REPO" in codigos
    assert "CONSTRUYE-REPOSITORIO" in codigos
    assert "SQL-EN-CAPA-EXTERNA" in codigos
    assert "UI-ACCESO-INFRA-DIRECTO" in codigos
    assert informe.archivos_analizados == 3
    assert informe.errores_analisis == ()


def test_composicion_ui_se_clasifica_como_borde_y_no_como_repositorio(tmp_path: Path):
    _write(
        tmp_path,
        "ui/pagina.py",
        "from infraestructura.composicion.personas import crear_servicio_personas\n"
        "def render(db):\n"
        "    return crear_servicio_personas(db)\n",
    )

    informe = analizar(tmp_path)
    hallazgos = [h for h in informe.hallazgos if h.codigo == "UI-USA-COMPOSICION"]

    assert len(hallazgos) == 1
    assert hallazgos[0].estado == "BORDE_DE_COMPOSICION"
    assert all(h.codigo != "CONSTRUYE-REPOSITORIO" for h in informe.hallazgos)


def test_analizador_no_ejecuta_codigo_de_los_archivos(tmp_path: Path):
    marcador = tmp_path / "no-debe-crearse.txt"
    _write(
        tmp_path,
        "aplicacion/peligroso.py",
        f"raise RuntimeError('no ejecutar')\nopen({str(marcador)!r}, 'w').write('ejecutado')\n",
    )

    analizar(tmp_path)

    assert not marcador.exists()


def test_inventario_es_determinista_y_exportable(tmp_path: Path):
    _write(tmp_path, "dominio/a.py", "from ui import pantalla\n")
    _write(tmp_path, "ui/b.py", "from infraestructura.composicion import crear\n")

    first = analizar(tmp_path)
    second = analizar(tmp_path)

    assert first == second
    assert '"archivos_python": 2' in a_json(first)
    markdown = a_markdown(first)
    assert "Inventario automático de fronteras modulares" in markdown
    assert "DOM-DEPENDENCIA-ASCENDENTE" in markdown
    assert "UI-USA-COMPOSICION" in markdown


def test_inventario_del_repositorio_completo_no_deja_archivos_sin_analizar():
    root = Path(__file__).resolve().parents[1]
    informe = analizar(root)

    assert informe.archivos_python > 100
    assert informe.archivos_analizados == informe.archivos_python
    assert informe.errores_analisis == ()
    assert {"dominio", "aplicacion", "infraestructura", "ui", "scripts"} <= set(
        informe.archivos_por_capa
    )
