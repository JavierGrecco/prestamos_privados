"""Regresiones del ciclo de vida de la conexión SQLite en Streamlit."""

import ast
from pathlib import Path


def test_abrir_db_no_se_comparte_con_cache_resource():
    source = (
        Path(__file__).resolve().parents[1] / "ui" / "app.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    abrir_db = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "abrir_db"
    )
    decoradores = [
        getattr(d, "attr", None)
        for d in abrir_db.decorator_list
    ]
    assert "cache_resource" not in decoradores


def test_main_cierra_la_conexion_en_finally():
    source = (
        Path(__file__).resolve().parents[1] / "ui" / "app.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    assert any(
        isinstance(node, ast.Try) and any(
            isinstance(finally_node, ast.Expr)
            and isinstance(finally_node.value, ast.Call)
            and isinstance(finally_node.value.func, ast.Attribute)
            and finally_node.value.func.attr == "cerrar"
            for finally_node in node.finalbody
        )
        for node in ast.walk(main)
    )
