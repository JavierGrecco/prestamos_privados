"""H4: verifica compatibilidad de v010 sobre una base financiera existente.

La base se construye hasta v009, se carga con un préstamo y un pago Legacy,
y recién después se aplica v010. La migración debe agregar capacidad técnica
sin modificar ningún hecho financiero existente.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.composicion.servicio_pagos_legacy import crear_servicio_pagos_legacy
from infraestructura import BaseDatos
from infraestructura.migraciones import (
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
    version_actual,
    version_destino_migraciones,
)
from infraestructura.migraciones import gestor
from infraestructura.repositorios import PersonaRepo


TABLAS_ECONOMICAS = (
    "personas",
    "roles_persona",
    "prestamos",
    "versiones_tasa",
    "cuotas",
    "participaciones",
    "pagos",
    "imputaciones",
    "ledger",
    "tipos_cambio",
    "auditoria",
)


def _aplicar_hasta_v009(db: BaseDatos) -> None:
    db.ejecutar(
        """CREATE TABLE IF NOT EXISTS migraciones (
            version INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            aplicada_en TEXT NOT NULL,
            hash TEXT
        )"""
    )

    for version, nombre, funcion in gestor._cargar_migraciones()[:9]:
        with db.transaccion():
            funcion(db)
            db.ejecutar(
                "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                (version, nombre, f"2026-10-01T00:00:{version:02d}"),
            )


def _crear_datos_existentes(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Existente")
    inversor_id = personas.crear(nombre="Inversor", apellido="Existente")

    prestamo_id = crear_servicio_prestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="h4",
        destino="Base existente H4",
    )

    servicio = crear_servicio_pagos_legacy(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None

    servicio.registrar_pago(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        usuario="legacy-h4",
    )
    return prestamo_id


def _columnas_economicas_existentes(
    db: BaseDatos,
) -> dict[str, tuple[str, ...]]:
    """Congela las columnas presentes antes del upgrade, no las que agrega después."""
    return {
        tabla: tuple(
            str(fila["name"])
            for fila in db.consultar(f'PRAGMA table_info("{tabla}")')
        )
        for tabla in TABLAS_ECONOMICAS
    }


def _snapshot_economico(
    db: BaseDatos,
    columnas_por_tabla: dict[str, tuple[str, ...]],
):
    """Captura exactamente los campos históricos disponibles en el origen."""
    snapshot = []
    for tabla in TABLAS_ECONOMICAS:
        columnas = columnas_por_tabla[tabla]
        seleccion = ", ".join(f'"{columna}"' for columna in columnas)
        filas = db.consultar(
            f'SELECT {seleccion} FROM "{tabla}" ORDER BY rowid'
        )
        snapshot.append((tabla, tuple(tuple(fila) for fila in filas)))
    return tuple(snapshot)


def _snapshot_tablas_v010(db: BaseDatos):
    tablas = db.consultar(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='devengamientos'"
    )
    assert len(tablas) == 1

    indices = {
        str(fila["name"])
        for fila in db.consultar("PRAGMA index_list(devengamientos)")
    }
    triggers = {
        str(fila["name"])
        for fila in db.consultar(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_devengamientos_%'"
        )
    }
    return indices, triggers


def test_h4_aplicar_v010_sobre_base_v009_no_modifica_economia(tmp_path: Path):
    ruta = tmp_path / "base_existente_v009.db"

    with BaseDatos(ruta) as db:
        _aplicar_hasta_v009(db)
        assert version_actual(db) == 9

        prestamo_id = _crear_datos_existentes(db)
        columnas_originales = _columnas_economicas_existentes(db)
        antes = _snapshot_economico(db, columnas_originales)

        with db.transaccion():
            db.ejecutar(
                "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                (10, "devengamientos_v3", "2026-10-07T00:00:00"),
            )
        from infraestructura.migraciones.v010_devengamientos_v3 import aplicar as aplicar_v010
        with db.transaccion():
            aplicar_v010(db)

        despues = _snapshot_economico(db, columnas_originales)

        assert despues == antes
        assert version_actual(db) == 10

        indices, triggers = _snapshot_tablas_v010(db)
        assert "idx_devengamientos_prestamo_fecha" in indices
        assert "idx_devengamientos_cuota_fecha" in indices
        assert {"trg_devengamientos_no_update", "trg_devengamientos_no_delete"} <= triggers

        cuota = db.consultar_uno(
            """SELECT estado, mora_pendiente, interes_pendiente, capital_pendiente, monto_pendiente
               FROM cuotas
               WHERE version_id = (
                   SELECT id FROM versiones_tasa WHERE prestamo_id = ? ORDER BY id DESC LIMIT 1
               )
               ORDER BY numero
               LIMIT 1""",
            (prestamo_id,),
        )
        assert cuota is not None


def test_h4_upgrade_completo_v009_a_v026_preserva_hechos_economicos(
    tmp_path: Path,
) -> None:
    """Ejecuta el gestor real desde v009 y conserva los campos financieros históricos."""
    ruta = tmp_path / "base_existente_v009.db"

    with BaseDatos(ruta) as db:
        _aplicar_hasta_v009(db)
        assert version_actual(db) == 9

        prestamo_id = _crear_datos_existentes(db)
        columnas_originales = _columnas_economicas_existentes(db)
        antes = _snapshot_economico(db, columnas_originales)

        # No se invocan migraciones individuales: el gestor coordina la cadena
        # completa v010..v026 y registra cada versión en la misma transacción.
        pendientes = aplicar_migraciones(db)
        assert pendientes == list(range(10, version_destino_migraciones() + 1))
        assert version_actual(db) == version_destino_migraciones() == 26

        despues = _snapshot_economico(db, columnas_originales)
        assert despues == antes

        # v015 crea una política inicial y v016 la asocia al pago histórico
        # solo cuando su vigencia cubre la fecha valor del movimiento.
        pago = db.consultar_uno(
            """
            SELECT id, prestamo_id, fecha_valor, politica_pago_id
            FROM pagos
            WHERE prestamo_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (prestamo_id,),
        )
        assert pago is not None
        assert pago["politica_pago_id"] is not None
        politica = db.consultar_uno(
            """
            SELECT prestamo_id, vigente_desde, vigente_hasta
            FROM politicas_pago
            WHERE id = ?
            """,
            (pago["politica_pago_id"],),
        )
        assert politica is not None
        assert politica["prestamo_id"] == prestamo_id
        assert politica["vigente_desde"] <= pago["fecha_valor"]
        assert (
            politica["vigente_hasta"] is None
            or politica["vigente_hasta"] > pago["fecha_valor"]
        )

        tablas_finales = {
            str(fila["name"])
            for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "politicas_pago",
            "usuarios_app",
            "garantias_prestamo",
            "condiciones_carencia",
            "planes_reposicion_snapshots",
            "planes_reposicion",
            "planes_reposicion_versiones",
            "aportes_reposicion",
            "flujos_inversion_reposicion",
            "valuaciones_inversion_reposicion",
            "correcciones_auditables",
        } <= tablas_finales

        historial = [
            int(fila["version"])
            for fila in db.consultar(
                "SELECT version FROM migraciones ORDER BY version"
            )
        ]
        assert historial == list(range(1, 27))

        estado = inspeccionar_estado_migraciones(db)
        assert estado.historial_valido is True
        assert estado.version_actual == estado.version_destino == 26
        assert estado.pendientes == ()

        assert db.consultar("PRAGMA foreign_key_check") == []
        assert db.verificar_integridad_completa() is True

        # Una segunda ejecución no aplica cambios ni muta ningún hecho histórico.
        assert aplicar_migraciones(db) == []
        assert _snapshot_economico(db, columnas_originales) == antes

