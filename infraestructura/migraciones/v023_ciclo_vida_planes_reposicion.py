"""Migración v023: identidad, versiones y ciclo de vida de planes de reposición."""

from ..db import BaseDatos


def aplicar(db: BaseDatos) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS planes_reposicion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 120),
            tipo_plan TEXT NOT NULL CHECK (
                tipo_plan IN ('REPOSICION_INTERNA', 'PRESTAMO_ENTRE_PERSONAS')
            ),
            fecha_desembolso TEXT NOT NULL,
            capital_original_ars TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'CERRADO')),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL,
            actualizado_en TEXT NOT NULL,
            cerrado_por TEXT,
            cerrado_en TEXT
        )
        """
    )
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS planes_reposicion_versiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES planes_reposicion(id) ON DELETE RESTRICT,
            numero_version INTEGER NOT NULL CHECK (numero_version > 0),
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL,
            origen_snapshot_id INTEGER UNIQUE
                REFERENCES planes_reposicion_snapshots(id) ON DELETE RESTRICT,
            UNIQUE (plan_id, numero_version)
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_planes_reposicion_estado_actualizado
        ON planes_reposicion (estado, actualizado_en DESC, id DESC)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_planes_reposicion_versiones_plan
        ON planes_reposicion_versiones (plan_id, numero_version DESC)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_guard_update
        BEFORE UPDATE ON planes_reposicion
        WHEN
            NEW.nombre IS NOT OLD.nombre OR
            NEW.tipo_plan IS NOT OLD.tipo_plan OR
            NEW.fecha_desembolso IS NOT OLD.fecha_desembolso OR
            NEW.capital_original_ars IS NOT OLD.capital_original_ars OR
            NEW.creado_por IS NOT OLD.creado_por OR
            NEW.creado_en IS NOT OLD.creado_en OR
            (
                NEW.estado IS NOT OLD.estado AND
                NOT (OLD.estado = 'ACTIVO' AND NEW.estado = 'CERRADO')
            ) OR
            (
                OLD.estado = 'CERRADO' AND (
                    NEW.actualizado_en IS NOT OLD.actualizado_en OR
                    NEW.cerrado_por IS NOT OLD.cerrado_por OR
                    NEW.cerrado_en IS NOT OLD.cerrado_en
                )
            ) OR
            (
                OLD.estado = 'ACTIVO' AND NEW.estado = 'CERRADO' AND (
                    NEW.cerrado_por IS NULL OR length(trim(NEW.cerrado_por)) = 0 OR
                    NEW.cerrado_en IS NULL OR length(trim(NEW.cerrado_en)) = 0
                )
            )
        BEGIN
            SELECT RAISE(ABORT, 'los datos del plan son inmutables; solo se permite cerrar un plan activo');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_no_delete
        BEFORE DELETE ON planes_reposicion
        BEGIN
            SELECT RAISE(ABORT, 'los planes de reposición se conservan como historial');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_version_no_update
        BEFORE UPDATE ON planes_reposicion_versiones
        BEGIN
            SELECT RAISE(ABORT, 'las versiones de reposición son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_version_no_delete
        BEFORE DELETE ON planes_reposicion_versiones
        BEGIN
            SELECT RAISE(ABORT, 'las versiones de reposición son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_version_insert_guard
        BEFORE INSERT ON planes_reposicion_versiones
        WHEN
            COALESCE(
                (SELECT estado FROM planes_reposicion WHERE id = NEW.plan_id),
                'INEXISTENTE'
            ) <> 'ACTIVO' OR
            NEW.numero_version <> COALESCE(
                (
                    SELECT MAX(numero_version) + 1
                    FROM planes_reposicion_versiones
                    WHERE plan_id = NEW.plan_id
                ),
                1
            )
        BEGIN
            SELECT RAISE(ABORT, 'el plan debe estar activo y la versión debe ser consecutiva');
        END
        """
    )

    # Los snapshots v022 se convierten en planes versionados, conservando su origen.
    filas = db.consultar(
        """
        SELECT id, nombre, tipo_plan, fecha_desembolso, capital_original_ars,
               snapshot_json, snapshot_sha256, creado_por, creado_en
        FROM planes_reposicion_snapshots ORDER BY id
        """
    )
    for fila in filas:
        existente = db.consultar_uno(
            "SELECT id FROM planes_reposicion_versiones WHERE origen_snapshot_id = ?",
            (int(fila["id"]),),
        )
        if existente is not None:
            continue
        creado_en = str(fila["creado_en"])
        db.ejecutar(
            """
            INSERT INTO planes_reposicion (
                nombre, tipo_plan, fecha_desembolso, capital_original_ars,
                estado, creado_por, creado_en, actualizado_en
            ) VALUES (?, ?, ?, ?, 'ACTIVO', ?, ?, ?)
            """,
            (
                str(fila["nombre"]), str(fila["tipo_plan"]),
                str(fila["fecha_desembolso"]), str(fila["capital_original_ars"]),
                str(fila["creado_por"]), creado_en, creado_en,
            ),
        )
        plan_id = db.ultimo_id_insertado()
        db.ejecutar(
            """
            INSERT INTO planes_reposicion_versiones (
                plan_id, numero_version, snapshot_json, snapshot_sha256,
                creado_por, creado_en, origen_snapshot_id
            ) VALUES (?, 1, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, str(fila["snapshot_json"]), str(fila["snapshot_sha256"]),
                str(fila["creado_por"]), creado_en, int(fila["id"]),
            ),
        )
