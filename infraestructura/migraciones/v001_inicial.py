"""
Migración inicial: schema completo del core del sistema.

Crea las tablas fundamentales:
  - personas y roles
  - préstamos, versiones de tasa, cuotas
  - participaciones de inversores
  - pagos e imputaciones
  - ledger de doble entrada
  - tipos de cambio
  - auditoría

Decisiones de diseño importantes:

1. **Los montos se guardan como TEXT, no REAL.**
   SQLite no tiene un tipo Decimal nativo. Guardar como REAL (float)
   introduciría los mismos errores de precisión que evitamos en
   Python. Guardar como TEXT preserva la representación exacta:
   Decimal("100.55") se guarda como "100.55" y se lee idéntico.
   Es más lento para ordenar y sumar, pero en esta app la
   performance no es crítica.

2. **Los porcentajes también son TEXT.**
   Mismo razonamiento: 0.5, 0.25, 0.33333333... no se representan
   bien en binario. Como TEXT preservamos la precisión.

3. **El ledger tiene triggers de inmutabilidad.**
   SQLite permite crear triggers que abortan UPDATE y DELETE.
   Esto es una defensa en profundidad: aunque el código de la
   aplicación tuviera un bug y emitiera un DELETE, la base lo
   rechaza.

4. **Todas las fechas son TEXT en formato ISO 8601.**
   ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS) es ordenable
   alfabéticamente y comparable con strings. Es el estándar de facto
   para SQLite y evita problemas de zona horaria.
"""


def aplicar(db) -> None:
    """
    Aplica la migración inicial completa.

    Parámetros:
        db: instancia de BaseDatos ya abierta.
    """
    # ============================================================
    # PERSONAS Y ROLES
    # ============================================================
    db.ejecutar("""
        CREATE TABLE personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL DEFAULT '',
            documento TEXT UNIQUE,
            telefono TEXT,
            email TEXT,
            domicilio TEXT,
            notas TEXT,
            estado TEXT NOT NULL DEFAULT 'ACTIVO'
                CHECK (estado IN ('ACTIVO', 'INACTIVO')),
            creado_en TEXT NOT NULL,
            actualizado_en TEXT
        )
    """)

    db.ejecutar("""
        CREATE TABLE roles_persona (
            persona_id INTEGER NOT NULL REFERENCES personas(id)
                ON DELETE RESTRICT,
            rol TEXT NOT NULL
                CHECK (rol IN ('INVERSOR', 'DEUDOR', 'GARANTE', 'ADMIN')),
            fecha_alta TEXT NOT NULL,
            fecha_baja TEXT,
            motivo_baja TEXT,
            PRIMARY KEY (persona_id, rol)
        )
    """)

    # ============================================================
    # PRÉSTAMOS
    # ============================================================
    db.ejecutar("""
        CREATE TABLE prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            deudor_id INTEGER NOT NULL REFERENCES personas(id)
                ON DELETE RESTRICT,
            moneda_contractual TEXT NOT NULL DEFAULT 'ARS'
                CHECK (moneda_contractual IN ('ARS')),
            capital_original TEXT NOT NULL,
            plazo_meses INTEGER NOT NULL CHECK (plazo_meses > 0),
            sistema TEXT NOT NULL
                CHECK (sistema IN ('FRANCES', 'ALEMAN', 'INTERES_ONLY', 'PERSONALIZADO')),
            convencion_dias TEXT NOT NULL
                CHECK (convencion_dias IN ('MENSUAL', 'ACTUAL_365', 'ACTUAL_360', '30_360', 'ACTUAL_ACTUAL')),
            tc_inicial TEXT,
            fecha_inicio TEXT NOT NULL,
            fecha_fin_estimada TEXT,
            estado TEXT NOT NULL DEFAULT 'ACTIVO'
                CHECK (estado IN ('BORRADOR', 'ACTIVO', 'EN_MORA', 'REFINANCIADO', 'CANCELADO', 'FINALIZADO', 'ANULADO')),
            destino TEXT,
            descripcion TEXT,
            creado_en TEXT NOT NULL,
            actualizado_en TEXT
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_prestamos_deudor ON prestamos(deudor_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_prestamos_estado ON prestamos(estado)
    """)

    db.ejecutar("""
        CREATE TABLE versiones_tasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id)
                ON DELETE RESTRICT,
            version INTEGER NOT NULL,
            fecha_desde TEXT NOT NULL,
            fecha_hasta TEXT,
            tasa_anual TEXT NOT NULL,
            modalidad_tasa TEXT NOT NULL
                CHECK (modalidad_tasa IN ('TNA', 'TEA')),
            motivo TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL,
            UNIQUE (prestamo_id, version)
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_versiones_prestamo ON versiones_tasa(prestamo_id)
    """)

    db.ejecutar("""
        CREATE TABLE cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL REFERENCES versiones_tasa(id)
                ON DELETE RESTRICT,
            numero INTEGER NOT NULL CHECK (numero > 0),
            fecha_vencimiento TEXT NOT NULL,
            capital_inicial TEXT NOT NULL,
            interes TEXT NOT NULL,
            capital TEXT NOT NULL,
            cuota TEXT NOT NULL,
            saldo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE'
                CHECK (estado IN ('PENDIENTE', 'PAGADA', 'PARCIAL', 'VENCIDA', 'REESTRUCTURADA', 'ANULADA')),
            creado_en TEXT NOT NULL,
            UNIQUE (version_id, numero)
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_cuotas_version ON cuotas(version_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_cuotas_vencimiento ON cuotas(fecha_vencimiento)
    """)
    db.ejecutar("""
        CREATE INDEX idx_cuotas_estado ON cuotas(estado)
    """)

    # ============================================================
    # PARTICIPACIONES DE INVERSORES
    # ============================================================
    db.ejecutar("""
        CREATE TABLE participaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id)
                ON DELETE RESTRICT,
            inversor_id INTEGER NOT NULL REFERENCES personas(id)
                ON DELETE RESTRICT,
            capital_aportado TEXT NOT NULL,
            moneda_aporte TEXT NOT NULL DEFAULT 'ARS'
                CHECK (moneda_aporte IN ('ARS')),
            tc_aporte TEXT,
            capital_usd_ref TEXT,
            porcentaje TEXT NOT NULL,
            fecha_aporte TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'ACTIVA'
                CHECK (estado IN ('ACTIVA', 'TRANSFERIDA', 'LIQUIDADA', 'ANULADA')),
            creado_en TEXT NOT NULL
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_participaciones_prestamo ON participaciones(prestamo_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_participaciones_inversor ON participaciones(inversor_id)
    """)

    # ============================================================
    # PAGOS E IMPUTACIONES
    # ============================================================
    db.ejecutar("""
        CREATE TABLE pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id)
                ON DELETE RESTRICT,
            fecha_real TEXT NOT NULL,
            fecha_valor TEXT NOT NULL,
            fecha_registro TEXT NOT NULL,
            moneda_pago TEXT NOT NULL DEFAULT 'ARS'
                CHECK (moneda_pago IN ('ARS')),
            monto_moneda_pago TEXT NOT NULL,
            tc_aplicado TEXT,
            monto_moneda_contractual TEXT NOT NULL,
            monto_usd_ref TEXT,
            medio TEXT,
            referencia TEXT,
            nota TEXT,
            estado TEXT NOT NULL DEFAULT 'VALIDA'
                CHECK (estado IN ('VALIDA', 'ANULADA')),
            motivo_anulacion TEXT,
            creado_por TEXT
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_pagos_prestamo ON pagos(prestamo_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_pagos_fecha ON pagos(fecha_real)
    """)

    db.ejecutar("""
        CREATE TABLE imputaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pago_id INTEGER NOT NULL REFERENCES pagos(id)
                ON DELETE RESTRICT,
            cuota_id INTEGER REFERENCES cuotas(id)
                ON DELETE RESTRICT,
            concepto TEXT NOT NULL
                CHECK (concepto IN ('GASTO', 'PENALIZACION', 'MORA', 'INTERES', 'CAPITAL')),
            monto TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_imputaciones_pago ON imputaciones(pago_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_imputaciones_cuota ON imputaciones(cuota_id)
    """)

    # ============================================================
    # LEDGER (inmutable)
    # ============================================================
    db.ejecutar("""
        CREATE TABLE ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad TEXT NOT NULL
                CHECK (entidad IN ('PRESTAMO', 'INVERSOR', 'PAGO', 'CUOTA')),
            entidad_id INTEGER NOT NULL,
            tipo_movimiento TEXT NOT NULL,
            debe TEXT NOT NULL DEFAULT '0',
            haber TEXT NOT NULL DEFAULT '0',
            fecha TEXT NOT NULL,
            metadata TEXT,
            correlacion_id TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_ledger_entidad ON ledger(entidad, entidad_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_ledger_fecha ON ledger(fecha)
    """)
    db.ejecutar("""
        CREATE INDEX idx_ledger_correlacion ON ledger(correlacion_id)
    """)

    # Triggers de inmutabilidad. El ledger es append-only:
    # se puede INSERT, pero nunca UPDATE ni DELETE.
    # Si el código intenta, la base rechaza la operación.
    db.ejecutar("""
        CREATE TRIGGER impedir_update_ledger
        BEFORE UPDATE ON ledger
        BEGIN
            SELECT RAISE(ABORT, 'El ledger es inmutable. Use una anulacion para revertir.');
        END
    """)

    db.ejecutar("""
        CREATE TRIGGER impedir_delete_ledger
        BEFORE DELETE ON ledger
        BEGIN
            SELECT RAISE(ABORT, 'El ledger es inmutable. No se permite DELETE.');
        END
    """)

    # Los pagos no se borran: se anulan. El UPDATE sí está permitido
    # (para cambiar el estado de VALIDA a ANULADA), pero el DELETE no.
    db.ejecutar("""
        CREATE TRIGGER impedir_delete_pagos
        BEFORE DELETE ON pagos
        BEGIN
            SELECT RAISE(ABORT, 'Los pagos no se eliminan. Use estado=ANULADA.');
        END
    """)

    # ============================================================
    # TIPOS DE CAMBIO
    # ============================================================
    db.ejecutar("""
        CREATE TABLE tipos_cambio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            fuente TEXT NOT NULL,
            valor TEXT NOT NULL,
            es_manual INTEGER NOT NULL DEFAULT 0
                CHECK (es_manual IN (0, 1)),
            creado_por TEXT,
            creado_en TEXT NOT NULL,
            UNIQUE (fecha, fuente)
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_tc_fecha ON tipos_cambio(fecha)
    """)

    # ============================================================
    # AUDITORÍA
    # ============================================================
    db.ejecutar("""
        CREATE TABLE auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            usuario TEXT NOT NULL,
            operacion TEXT NOT NULL,
            entidad TEXT NOT NULL,
            entidad_id INTEGER,
            datos_anteriores TEXT,
            datos_nuevos TEXT,
            motivo TEXT,
            correlacion_id TEXT NOT NULL
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_auditoria_fecha ON auditoria(fecha)
    """)
    db.ejecutar("""
        CREATE INDEX idx_auditoria_entidad ON auditoria(entidad, entidad_id)
    """)
    db.ejecutar("""
        CREATE INDEX idx_auditoria_correlacion ON auditoria(correlacion_id)
    """)