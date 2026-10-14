"""Guardas de arquitectura del coordinador de escritura Legacy."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manejador_registro_pago_legacy_depende_de_puertos_y_no_de_sql():
    archivo = ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "El manejador debe depender de contratos de aplicación: "
        + ", ".join(problemas)
    )
    assert "self.db" not in fuente
    assert "SELECT " not in fuente
    assert "INSERT INTO" not in fuente
    assert "UPDATE pagos" not in fuente
    assert "self.unidad_trabajo.transaccion()" in fuente
    assert "self.pagos.actualizar_datos_adelanto(" in fuente


def test_fachada_historica_delega_el_registro_transaccional():
    archivo = ROOT / "aplicacion" / "servicios" / "pagos.py"
    fuente = archivo.read_text(encoding="utf-8")

    assert (
        "self._manejador_registro_pago_legacy.registrar_en_transaccion("
        in fuente
    )
    assert (
        "self._manejador_registro_pago_legacy.registrar_pago_atomico("
        in fuente
    )
    assert "with self.db.transaccion(inmediata=True)" not in fuente
    assert "def _aplicar_adelanto(" not in fuente
    assert "def _distribuir_a_inversores(" not in fuente


def test_manejador_es_dueno_de_la_transaccion_inmediata_y_la_idempotencia():
    handler = (
        ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    ).read_text(encoding="utf-8")

    assert "def registrar_pago_atomico(" in handler
    assert "self.unidad_trabajo.transaccion(inmediata=True)" in handler
    assert "self._normalizar_idempotencia(" in handler
    assert "self._buscar_pago_idempotente(" in handler
    assert "def buscar_reintento_idempotente(" in handler


def test_composicion_oficial_ensambla_repositorios_fuera_de_la_fachada():
    composicion = (
        ROOT / "infraestructura" / "composicion" / "servicio_pagos_legacy.py"
    ).read_text(encoding="utf-8")
    composicion_ui = (
        ROOT / "infraestructura" / "composicion" / "registro_pago.py"
    ).read_text(encoding="utf-8")

    for repo in (
        "PrestamoRepo(db)",
        "PagoRepo(db)",
        "ParticipacionRepo(db)",
        "LedgerRepo(db)",
        "AuditoriaRepo(db)",
        "RecalculoRepo(db)",
        "PoliticaPagoRepo(db)",
    ):
        assert repo in composicion
    assert (
        "crear_servicio_pagos_legacy(db).registrar_pago(**kwargs)"
        in composicion_ui
    )
    assert "ServicioPagos(db)" not in composicion_ui
