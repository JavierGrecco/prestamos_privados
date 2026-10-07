"""Migración v010: almacenamiento de devengamientos V3."""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS devengamientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL,
            cuota_id INTEGER,
            concepto TEXT NOT NULL CHECK (concepto IN ('GASTO','PENALIZACION','MORA','INTERES','CAPITAL')),
            monto TEXT NOT NULL,
            fecha_desde TEXT NOT NULL,
            fecha_hasta TEXT NOT NULL,
            origen TEXT NOT NULL,
            referencia TEXT,
            base TEXT NOT NULL,
            tasa_anual TEXT NOT NULL,
            modalidad_tasa TEXT,
            convencion_dias TEXT,
            dias INTEGER NOT NULL DEFAULT 0,
            fraccion_anual TEXT NOT NULL DEFAULT '0',
            huella TEXT NOT NULL UNIQUE,
            motor_version TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_devengamientos_prestamo_fecha
        ON devengamientos(prestamo_id, fecha_hasta, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_devengamientos_cuota_fecha
        ON devengamientos(cuota_id, fecha_hasta, id)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_devengamientos_no_update
        BEFORE UPDATE ON devengamientos
        BEGIN
            SELECT RAISE(ABORT, 'Los devengamientos son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_devengamientos_no_delete
        BEFORE DELETE ON devengamientos
        BEGIN
            SELECT RAISE(ABORT, 'Los devengamientos no se eliminan');
        END
        """
    )
