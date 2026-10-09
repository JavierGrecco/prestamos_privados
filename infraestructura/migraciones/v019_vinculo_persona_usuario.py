"""Migración v019: vinculación opcional entre cuenta local y persona financiera.

La asociación permite personalizar el contexto de Mi espacio. No asigna
capacidades ni intenta inferir la persona a partir del nombre del usuario.
Las cuentas existentes permanecen desvinculadas.
"""


def aplicar(db) -> None:
    db.ejecutar(
        """
        ALTER TABLE usuarios_app
        ADD COLUMN persona_id INTEGER
            REFERENCES personas(id) ON DELETE SET NULL
        """
    )
    db.ejecutar(
        """
        CREATE INDEX idx_usuarios_app_persona
        ON usuarios_app (persona_id)
        """
    )
