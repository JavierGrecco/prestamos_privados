"""Regresión de migración v021 sobre una base con hechos financieros reales.

Se construye el esquema v020, se crea un préstamo y se registra un pago antes
de migrar. Las columnas nuevas pueden aparecer, pero no deben cambiar ningún
campo financiero histórico ni reescribir eventos de ledger/auditoría.
"""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual
from infraestructura.migraciones.gestor import (
    _asegurar_tabla_migraciones,
    _cargar_migraciones,
)
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


def _crear_base_en_version(ruta: Path, version_objetivo: int) -> None:
    """Construye una base histórica ejecutando migraciones en orden."""
    with BaseDatos(ruta) as db:
        _asegurar_tabla_migraciones(db)
        for version, nombre, migrar in _cargar_migraciones():
            if version > version_objetivo:
                break
            with db.transaccion():
                migrar(db)
                db.ejecutar(
                    """
                    INSERT INTO migraciones (version, nombre, aplicada_en)
                    VALUES (?, ?, ?)
                    """,
                    (version, nombre, datetime(2026, 10, 8).isoformat()),
                )


def _crear_prestamo_con_pago(db: BaseDatos) -> int:
    """Crea datos económicos con las APIs de aplicación, no con SQL artificial."""
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Histórico")
    inversor_id = personas.crear(nombre="Inversor", apellido="Histórico")

    prestamo_id = ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000.00"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": Decimal("1000000.00")}
        ],
        usuario="test-migracion-v021",
        destino="Prueba de preservación histórica",
    )

    pagos = ServicioPagos(db)
    deuda = pagos.calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None
    pagos.registrar_pago(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        usuario="test-migracion-v021",
    )
    return prestamo_id


def _snapshot_campos_existentes(db: BaseDatos) -> tuple:
    """Captura columnas que existen antes de migrar, ignorando solo las nuevas."""
    snapshot = []
    for tabla in TABLAS_ECONOMICAS:
        columnas = [
            str(fila["name"])
            for fila in db.consultar(f'PRAGMA table_info("{tabla}")')
        ]
        seleccion = ", ".join(f'"{columna}"' for columna in columnas)
        filas = db.consultar(
            f'SELECT {seleccion} FROM "{tabla}" ORDER BY rowid'
        )
        snapshot.append(
            (tabla, tuple(tuple(fila) for fila in filas))
        )
    return tuple(snapshot)


def test_upgrade_v020_preserva_prestamo_pago_ledger_y_auditoria(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "base-v020-con-operacion.db"
    _crear_base_en_version(ruta, 20)

    with BaseDatos(ruta) as db:
        assert version_actual(db) == 20
        prestamo_id = _crear_prestamo_con_pago(db)
        antes = _snapshot_campos_existentes(db)

        # La v021 añade campos de carencia; las siguientes migraciones crean
        # capacidades nuevas. Ninguna debe reescribir los hechos preexistentes.
        aplicadas = aplicar_migraciones(db)
        despues = _snapshot_campos_existentes(db)

        assert aplicadas == [21, 22, 23, 24, 25]
        assert antes == despues
        assert version_actual(db) == 25

        filas_carencia = db.consultar(
            """
            SELECT interes_carencia, interes_carencia_pendiente
            FROM cuotas
            WHERE version_id = (
                SELECT id FROM versiones_tasa
                WHERE prestamo_id = ?
                ORDER BY version DESC LIMIT 1
            )
            ORDER BY numero
            """,
            (prestamo_id,),
        )
        assert len(filas_carencia) == 12
        assert all(
            fila["interes_carencia"] == "0.00"
            and fila["interes_carencia_pendiente"] == "0.00"
            for fila in filas_carencia
        )
        assert db.consultar("PRAGMA foreign_key_check") == []
        assert db.verificar_integridad_completa() is True

        # Reintentar el actualizador no repite migraciones ni muta los hechos.
        assert aplicar_migraciones(db) == []
        assert _snapshot_campos_existentes(db) == antes
