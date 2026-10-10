"""H4: verifica compatibilidad de v010 sobre una base financiera existente.

La base se construye hasta v009, se carga con un préstamo y un pago Legacy,
y recién después se aplica v010. La migración debe agregar capacidad técnica
sin modificar ningún hecho financiero existente.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual
from infraestructura.migraciones import gestor
from infraestructura.migraciones.v010_devengamientos_v3 import aplicar as aplicar_v010
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

    prestamo_id = ServicioPrestamos(db).crear_completo(
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

    servicio = ServicioPagos(db)
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


def _snapshot_economico(db: BaseDatos):
    snapshot = []
    for tabla in TABLAS_ECONOMICAS:
        filas = db.consultar(f'SELECT * FROM "{tabla}" ORDER BY rowid')
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
        antes = _snapshot_economico(db)

        with db.transaccion():
            aplicar_v010(db)
            db.ejecutar(
                "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                (10, "devengamientos_v3", "2026-10-07T00:00:00"),
            )

        despues = _snapshot_economico(db)

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


def test_h4_migraciones_completas_sobre_base_v010_son_idempotentes(tmp_path: Path):
    ruta = tmp_path / "base_existente_v009.db"

    with BaseDatos(ruta) as db:
        _aplicar_hasta_v009(db)
        _crear_datos_existentes(db)
        aplicar_v010(db)

        # El gestor completa idempotentemente las migraciones restantes hasta el esquema vigente.
        pendientes = aplicar_migraciones(db)
        assert pendientes == list(range(10, 27))
        assert version_actual(db) == 26

        antes_segunda = _snapshot_economico(db)
        assert aplicar_migraciones(db) == []
        assert _snapshot_economico(db) == antes_segunda
