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
    aplicador = (
        ROOT / "aplicacion" / "servicios" / "aplicador_adelanto_legacy.py"
    ).read_text(encoding="utf-8")
    assert "self._aplicador_adelanto_legacy.aplicar(" in fuente
    assert "self._pagos.actualizar_datos_adelanto(" in aplicador


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


def test_todos_los_ensamblados_legacy_usan_la_fabrica_de_infraestructura():
    raiz_composicion = ROOT / "infraestructura" / "composicion"
    preview = (raiz_composicion / "preview_pagos.py").read_text(encoding="utf-8")
    sombra = (raiz_composicion / "registradores_pago.py").read_text(encoding="utf-8")

    assert "crear_servicio_pagos_legacy(db)" in preview
    assert "ServicioPagosConSimulacion(db)" not in preview
    assert "crear_servicio_pagos_legacy(db)" in sombra
    assert "ServicioPagos(db)" not in sombra


def test_no_se_construyen_servicios_de_pago_fuera_de_la_fabrica_oficial():
    """Toda composición productiva Legacy debe pasar por infraestructura.

    El constructor ServicioPagos(db) continúa disponible como compatibilidad
    temporal, pero las pantallas, scripts y otros ensamblados productivos no
    deben crear el servicio directamente.
    """
    raices = (
        "aplicacion",
        "infraestructura/composicion",
        "ui",
        "scripts",
    )
    fabrica_oficial = (
        "infraestructura/composicion/servicio_pagos_legacy.py"
    )
    llamadas_no_permitidas = []

    for raiz in raices:
        for archivo in sorted((ROOT / raiz).rglob("*.py")):
            ruta = archivo.relative_to(ROOT).as_posix()
            if ruta == fabrica_oficial:
                continue
            fuente = archivo.read_text(encoding="utf-8")
            if "ServicioPagos" not in fuente:
                continue
            arbol = ast.parse(fuente, filename=str(archivo))
            for nodo in ast.walk(arbol):
                if not isinstance(nodo, ast.Call):
                    continue
                if isinstance(nodo.func, ast.Name):
                    nombre = nodo.func.id
                elif isinstance(nodo.func, ast.Attribute):
                    nombre = nodo.func.attr
                else:
                    continue
                if nombre in {"ServicioPagos", "ServicioPagosConSimulacion"}:
                    llamadas_no_permitidas.append(
                        f"{ruta}:{nodo.lineno} construye {nombre} directamente"
                    )

    assert llamadas_no_permitidas == [], "\n".join(llamadas_no_permitidas)


def test_constructor_directo_en_pruebas_solo_en_caracterizacion_y_compatibilidad():
    """Solo la prueba dedicada de composición usa el constructor histórico.

    La caracterización funcional usa la fábrica oficial igual que los flujos
    productivos; la compatibilidad sigue cubierta en un lugar explícito.
    """
    permitidos = {
        # Única excepción: prueba explícita del puente histórico de compatibilidad.
        "tests/test_composicion_servicio_pagos.py",
    }
    problemas = []
    for archivo in sorted((ROOT / "tests").rglob("*.py")):
        ruta = archivo.relative_to(ROOT).as_posix()
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            if isinstance(nodo.func, ast.Name):
                nombre = nodo.func.id
            elif isinstance(nodo.func, ast.Attribute):
                nombre = nodo.func.attr
            else:
                continue
            if nombre not in {"ServicioPagos", "ServicioPagosConSimulacion"}:
                continue
            if ruta not in permitidos:
                problemas.append(f"{ruta}:{nodo.lineno} construye {nombre} directamente")

    assert problemas == [], "\\n".join(problemas)



def test_distribucion_a_inversores_esta_separada_y_conserva_la_frontera():
    """El reparto no debe volver a crecer dentro del coordinador transaccional."""
    manejador = (
        ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    ).read_text(encoding="utf-8")
    distribuidor = (
        ROOT / "aplicacion" / "servicios" / "distribucion_pago_legacy.py"
    ).read_text(encoding="utf-8")
    arbol = ast.parse(distribuidor, filename="distribucion_pago_legacy.py")
    importaciones_prohibidas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {"infraestructura", "sqlite3", "ui", "streamlit"}:
                importaciones_prohibidas.append(
                    f"línea {nodo.lineno}: importa {modulo}"
                )

    assert not importaciones_prohibidas, "\n".join(importaciones_prohibidas)
    assert "self._distribuidor_pago_legacy.distribuir(" in manejador
    assert "def _distribuir_a_inversores(" in manejador  # punto de extensión histórico
    assert "for parte in partes" not in manejador
    assert "self._ledger.registrar_operacion(" in distribuidor
    assert "transaccion(" not in distribuidor



def test_aplicacion_de_adelanto_esta_separada_y_no_abre_transacciones():
    """El manejador delega RAI/RNI y el colaborador no conoce la infraestructura."""
    handler = (
        ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    ).read_text(encoding="utf-8")
    archivo = (
        ROOT / "aplicacion" / "servicios" / "aplicador_adelanto_legacy.py"
    )
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
            if modulo and modulo.split(".", 1)[0] in {"infraestructura", "sqlite3", "ui", "streamlit"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, "\\n".join(problemas)
    assert "self._aplicador_adelanto_legacy.aplicar(" in handler
    assert "recalcular_rai" not in handler
    assert "recalcular_rni" not in handler
    assert "self._prestamos.borrar_cuotas_pendientes_desde(" in fuente
    assert "self._recalculos.registrar(" in fuente
    assert "transaccion(" not in fuente
    assert "INSERT INTO" not in fuente
    assert "UPDATE " not in fuente


def test_preparacion_de_cuota_objetivo_e_imputaciones_esta_separada_y_es_pura():
    """El manejador delega el armado de los cambios sin mover la persistencia."""
    handler = (
        ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    ).read_text(encoding="utf-8")
    archivo = (
        ROOT / "aplicacion" / "servicios"
        / "preparacion_cuota_objetivo_pago_legacy.py"
    )
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    prohibidas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {
                "infraestructura", "sqlite3", "ui", "streamlit"
            }:
                prohibidas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not prohibidas, "\\n".join(prohibidas)
    assert "self._preparador_cuota_objetivo.preparar(" in handler
    assert "imputaciones = list(resultado_cuota_objetivo.imputaciones)" in handler
    assert "nueva_mora_obj = deuda[" not in handler
    assert "imputaciones = []" not in handler
    assert "transaccion(" not in fuente
    assert "SELECT " not in fuente
    assert "INSERT INTO" not in fuente
    assert "UPDATE " not in fuente



def test_preparacion_de_cuotas_anteriores_esta_separada_y_es_pura():
    """El manejador delega el waterfall sin mover persistencia ni transacción."""
    handler = (
        ROOT / "aplicacion" / "servicios" / "registro_pago_legacy.py"
    ).read_text(encoding="utf-8")
    archivo = (
        ROOT / "aplicacion" / "servicios"
        / "preparacion_cuotas_anteriores_pago_legacy.py"
    )
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    prohibidas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {
                "infraestructura", "sqlite3", "ui", "streamlit"
            }:
                prohibidas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not prohibidas, "\\n".join(prohibidas)
    assert "self._preparador_cuotas_anteriores.preparar(" in handler
    assert "for c in todas_las_cuotas:" not in handler
    assert "for cuota in cuotas:" in fuente
    assert "orden_waterfall" in fuente
    assert "transaccion(" not in fuente
    assert "SELECT " not in fuente
    assert "INSERT INTO" not in fuente
    assert "UPDATE " not in fuente
