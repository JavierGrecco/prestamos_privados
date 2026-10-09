"""Migración v017: cuentas locales de acceso a la aplicación.

Las cuentas de acceso son distintas de las personas del negocio: un usuario
puede operar el sistema sin ser deudor ni inversor. Las contraseñas se guardan
solo como hash derivado; nunca en texto plano.
"""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE usuarios_app (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL
                CHECK (rol IN ('ADMIN', 'OPERADOR', 'LECTURA')),
            password_hash TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            intentos_login_fallidos INTEGER NOT NULL DEFAULT 0
                CHECK (intentos_login_fallidos >= 0),
            bloqueado_hasta TEXT,
            ultimo_acceso_en TEXT,
            creado_en TEXT NOT NULL,
            actualizado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX idx_usuarios_app_rol_activo
        ON usuarios_app (rol, activo)
        """
    )
