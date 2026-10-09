"""Migración v021: prepara snapshot contractual de carencia.

La migración es aditiva. Las cuotas anteriores reciben componentes de carencia
en cero y sus importes/fechas existentes no se recalculan. La tabla de
condiciones registra snapshots versionados, inmutables y verificables.
"""


def _columnas(db, tabla: str) -> set[str]:
    return {str(fila["name"]) for fila in db.consultar(f"PRAGMA table_info({tabla})")}


def aplicar(db) -> None:
    columnas = _columnas(db, "cuotas")
    if "interes_carencia" not in columnas:
        db.ejecutar(
            "ALTER TABLE cuotas ADD COLUMN interes_carencia TEXT NOT NULL DEFAULT '0.00'"
        )
    if "interes_carencia_pendiente" not in columnas:
        db.ejecutar(
            "ALTER TABLE cuotas ADD COLUMN interes_carencia_pendiente TEXT NOT NULL DEFAULT '0.00'"
        )

    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS condiciones_carencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL
                REFERENCES prestamos(id) ON DELETE RESTRICT,
            version_tasa_id INTEGER NOT NULL
                REFERENCES versiones_tasa(id) ON DELETE RESTRICT,
            version_contrato INTEGER NOT NULL CHECK (version_contrato > 0),
            version_snapshot INTEGER NOT NULL DEFAULT 1 CHECK (version_snapshot = 1),
            tratamiento TEXT NOT NULL CHECK (
                tratamiento IN (
                    'SIN_INTERES',
                    'DIFERIR_SIMPLE_PRIMERA_CUOTA',
                    'DIFERIR_SIMPLE_DISTRIBUIDO'
                )
            ),
            capital_original TEXT NOT NULL,
            tasa_anual TEXT NOT NULL,
            modalidad_tasa TEXT NOT NULL CHECK (modalidad_tasa IN ('TNA', 'TEA')),
            convencion_dias TEXT NOT NULL CHECK (
                convencion_dias IN (
                    'MENSUAL', 'ACTUAL_365', 'ACTUAL_360',
                    'ACTUAL_ACTUAL', '30_360', 'TREINTA_360'
                )
            ),
            sistema TEXT NOT NULL CHECK (sistema IN ('FRANCES', 'ALEMAN')),
            meses_carencia INTEGER NOT NULL CHECK (meses_carencia > 0),
            fecha_desembolso TEXT NOT NULL,
            fecha_fin_carencia TEXT NOT NULL,
            fecha_primer_vencimiento TEXT NOT NULL,
            plazo_amortizacion_meses INTEGER NOT NULL
                CHECK (plazo_amortizacion_meses > 0),
            interes_simple_referencia TEXT NOT NULL,
            interes_carencia_debido TEXT NOT NULL,
            interes_carencia_no_cobrado TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL
                CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL,
            UNIQUE (prestamo_id, version_contrato),
            CHECK (fecha_fin_carencia > fecha_desembolso),
            CHECK (fecha_primer_vencimiento > fecha_fin_carencia)
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_condiciones_carencia_prestamo
        ON condiciones_carencia (prestamo_id, version_contrato)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_condiciones_carencia_version_tasa
        ON condiciones_carencia (version_tasa_id)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_condiciones_carencia_no_update
        BEFORE UPDATE ON condiciones_carencia
        BEGIN
            SELECT RAISE(ABORT, 'condiciones_carencia es inmutable; cree una nueva versión');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_condiciones_carencia_no_delete
        BEFORE DELETE ON condiciones_carencia
        BEGIN
            SELECT RAISE(ABORT, 'condiciones_carencia es inmutable; no se puede borrar');
        END
        """
    )
