"""
Tests del sistema de migraciones y del schema inicial.

Validan que:
  - Las migraciones se aplican en orden.
  - No se aplican dos veces.
  - Todas las tablas del core se crean.
  - Los índices existen.
  - Los triggers de inmutabilidad funcionan.
  - Las constraints (CHECK, UNIQUE, FK) se respetan.
"""
from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual


@pytest.fixture
def db(tmp_path: Path):
    """Crea una base temporal con las migraciones aplicadas."""
    ruta = tmp_path / "test.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


class TestMigraciones:
    def test_primera_aplicacion(self, tmp_path):
        """La primera vez se aplican todas las migraciones."""
        ruta = tmp_path / "test.db"
        with BaseDatos(ruta) as db:
            aplicadas = aplicar_migraciones(db)
            assert aplicadas == list(range(1, 13))
            assert version_actual(db) == 12

    def test_segunda_aplicacion_no_hace_nada(self, tmp_path):
        """La segunda vez no hay nada pendiente."""
        ruta = tmp_path / "test.db"
        with BaseDatos(ruta) as db:
            aplicar_migraciones(db)
            aplicadas = aplicar_migraciones(db)
            assert aplicadas == []
            assert version_actual(db) == 12

    def test_historial_de_migraciones_es_completo_y_ordenado(self, tmp_path):
        """El historial registra exactamente v001..v012 en orden."""
        ruta = tmp_path / "test.db"
        with BaseDatos(ruta) as db:
            aplicar_migraciones(db)
            filas = db.consultar(
                "SELECT version, nombre FROM migraciones ORDER BY version"
            )

            assert [fila["version"] for fila in filas] == list(range(1, 13))
            assert [fila["nombre"] for fila in filas] == [
                "inicial",
                "monto_pendiente",
                "pendientes_desglosados",
                "pagos_adelantos",
                "tuvo_pago_parcial",
                "interes_extra_generado",
                "cuota_objetivo_recalculo",
                "fue_recalculada",
                "registro_pago_v3",
                "devengamientos_v3",
                "observaciones_sombra_v3",
                "ejecuciones_sombra_v3",
            ]

    def test_version_actual_sin_migraciones(self, tmp_path):
        """Sin migraciones, la versión es 0."""
        ruta = tmp_path / "test.db"
        with BaseDatos(ruta) as db:
            assert version_actual(db) == 0


class TestTablasCreadas:
    def _tabla_existe(self, db, nombre: str) -> bool:
        fila = db.consultar_uno(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,),
        )
        return fila is not None

    def test_todas_las_tablas_del_core(self, db):
        """Verifica que existan todas las tablas del dominio."""
        tablas_esperadas = [
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
            "migraciones",
            "observaciones_sombra_v3",
            "ejecuciones_sombra_v3",
        ]
        for tabla in tablas_esperadas:
            assert self._tabla_existe(db, tabla), f"Falta la tabla {tabla}"


class TestTriggersInmutabilidad:
    def test_no_se_puede_borrar_del_ledger(self, db):
        """El ledger rechaza DELETE."""
        with db.transaccion():
            db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber, fecha, correlacion_id, creado_en)
                VALUES ('PRESTAMO', 1, 'APORTE', '100', '0', '2026-01-01', 'test-1', '2026-01-01')
                """
            )
        with pytest.raises(Exception) as exc:
            db.ejecutar("DELETE FROM ledger WHERE id = 1")
        assert "inmutable" in str(exc.value).lower()

    def test_no_se_puede_actualizar_el_ledger(self, db):
        """El ledger rechaza UPDATE."""
        with db.transaccion():
            db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber, fecha, correlacion_id, creado_en)
                VALUES ('PRESTAMO', 1, 'APORTE', '100', '0', '2026-01-01', 'test-1', '2026-01-01')
                """
            )
        with pytest.raises(Exception) as exc:
            db.ejecutar("UPDATE ledger SET debe = '200' WHERE id = 1")
        assert "inmutable" in str(exc.value).lower()

    def test_no_se_puede_borrar_pago(self, db):
        """Los pagos rechazan DELETE. Se anulan cambiando estado."""
        # Necesitamos crear un préstamo primero por la FK
        with db.transaccion():
            db.ejecutar(
                "INSERT INTO personas (nombre, creado_en) VALUES ('Test', '2026-01-01')"
            )
            persona_id = db.ultimo_id_insertado()
            db.ejecutar(
                """
                INSERT INTO prestamos
                (numero, deudor_id, capital_original, plazo_meses, sistema,
                 convencion_dias, fecha_inicio, creado_en)
                VALUES ('PR-001', ?, '1000', 12, 'FRANCES', 'MENSUAL', '2026-01-01', '2026-01-01')
                """,
                (persona_id,),
            )
            prestamo_id = db.ultimo_id_insertado()
            db.ejecutar(
                """
                INSERT INTO pagos
                (prestamo_id, fecha_real, fecha_valor, fecha_registro,
                 monto_moneda_pago, monto_moneda_contractual)
                VALUES (?, '2026-02-01', '2026-02-01', '2026-02-01', '100', '100')
                """,
                (prestamo_id,),
            )
        with pytest.raises(Exception) as exc:
            db.ejecutar("DELETE FROM pagos WHERE id = 1")
        assert "eliminan" in str(exc.value).lower()


class TestConstraints:
    def test_documento_unico(self, db):
        """No se pueden crear dos personas con el mismo documento."""
        with db.transaccion():
            db.ejecutar(
                "INSERT INTO personas (nombre, documento, creado_en) VALUES ('A', '123', '2026-01-01')"
            )
        with pytest.raises(Exception):
            db.ejecutar(
                "INSERT INTO personas (nombre, documento, creado_en) VALUES ('B', '123', '2026-01-01')"
            )

    def test_estado_invalido_rechazado(self, db):
        """El CHECK de estado rechaza valores no permitidos."""
        with pytest.raises(Exception):
            db.ejecutar(
                """
                INSERT INTO personas (nombre, estado, creado_en)
                VALUES ('A', 'ESTADO_INVALIDO', '2026-01-01')
                """
            )

    def test_rol_invalido_rechazado(self, db):
        """El CHECK de rol rechaza roles no permitidos."""
        with db.transaccion():
            db.ejecutar(
                "INSERT INTO personas (nombre, creado_en) VALUES ('A', '2026-01-01')"
            )
            persona_id = db.ultimo_id_insertado()
        with pytest.raises(Exception):
            db.ejecutar(
                "INSERT INTO roles_persona (persona_id, rol, fecha_alta) VALUES (?, 'ROL_RARO', '2026-01-01')",
                (persona_id,),
            )

    def test_plazo_positivo_requerido(self, db):
        """El CHECK de plazo rechaza valores <= 0."""
        with db.transaccion():
            db.ejecutar(
                "INSERT INTO personas (nombre, creado_en) VALUES ('A', '2026-01-01')"
            )
            persona_id = db.ultimo_id_insertado()
        with pytest.raises(Exception):
            db.ejecutar(
                """
                INSERT INTO prestamos
                (numero, deudor_id, capital_original, plazo_meses, sistema,
                 convencion_dias, fecha_inicio, creado_en)
                VALUES ('PR-001', ?, '1000', 0, 'FRANCES', 'MENSUAL', '2026-01-01', '2026-01-01')
                """,
                (persona_id,),
            )

    def test_fk_deudor_valida(self, db):
        """No se puede crear un préstamo con un deudor inexistente."""
        with pytest.raises(Exception):
            db.ejecutar(
                """
                INSERT INTO prestamos
                (numero, deudor_id, capital_original, plazo_meses, sistema,
                 convencion_dias, fecha_inicio, creado_en)
                VALUES ('PR-001', 99999, '1000', 12, 'FRANCES', 'MENSUAL', '2026-01-01', '2026-01-01')
                """
            )


class TestIndices:
    def _indice_existe(self, db, nombre: str) -> bool:
        fila = db.consultar_uno(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (nombre,),
        )
        return fila is not None

    def test_indices_principales(self, db):
        """Verifica que existan los índices clave."""
        indices = [
            "idx_prestamos_deudor",
            "idx_prestamos_estado",
            "idx_cuotas_vencimiento",
            "idx_cuotas_estado",
            "idx_participaciones_inversor",
            "idx_pagos_prestamo",
            "idx_ledger_entidad",
            "idx_ledger_correlacion",
            "idx_auditoria_correlacion",
        ]
        for indice in indices:
            assert self._indice_existe(db, indice), f"Falta el índice {indice}"


class TestSchemaV3RegistroPago:
    def _columnas(self, db, tabla: str) -> set[str]:
        return {fila["name"] for fila in db.consultar(f"PRAGMA table_info({tabla})")}

    def test_revision_prestamo_e_idempotencia(self, db):
        assert "revision_prestamo" in self._columnas(db, "prestamos")
        columnas = self._columnas(db, "pagos")
        assert {
            "idempotency_key",
            "idempotency_fingerprint",
            "motor_version",
            "plan_hash",
            "plan_json",
        } <= columnas

    def test_trazabilidad_de_imputaciones_v3(self, db):
        assert {
            "origen",
            "referencias_devengamiento",
        } <= self._columnas(db, "imputaciones")

    def test_indice_unico_de_idempotencia(self, db):
        fila = db.consultar_uno(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("ux_pagos_idempotency_key",),
        )
        assert fila is not None


class TestSchemaDevengamientosV3:
    def _columnas(self, db, tabla: str) -> set[str]:
        return {fila["name"] for fila in db.consultar(f"PRAGMA table_info({tabla})")}

    def test_tabla_y_columnas_de_devengamientos(self, db):
        assert "devengamientos" in self._tablas(db)
        assert {
            "prestamo_id", "cuota_id", "concepto", "monto",
            "fecha_desde", "fecha_hasta", "origen", "referencia",
            "base", "tasa_anual", "modalidad_tasa", "convencion_dias",
            "dias", "fraccion_anual", "huella", "motor_version", "creado_en",
        } <= self._columnas(db, "devengamientos")

    def _tablas(self, db) -> set[str]:
        return {fila["name"] for fila in db.consultar(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}

    def test_indices_de_devengamientos(self, db):
        indices = {
            fila["name"] for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_devengamientos_prestamo_fecha" in indices
        assert "idx_devengamientos_cuota_fecha" in indices

    def test_triggers_de_inmutabilidad_de_devengamientos(self, db):
        triggers = {
            fila["name"] for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        assert "trg_devengamientos_no_update" in triggers
        assert "trg_devengamientos_no_delete" in triggers

    def test_indice_unico_de_huella_de_devengamiento(self, db):
        filas = db.consultar("PRAGMA index_list(devengamientos)")
        assert any(fila["name"] == "sqlite_autoindex_devengamientos_1" and fila["unique"] for fila in filas)
