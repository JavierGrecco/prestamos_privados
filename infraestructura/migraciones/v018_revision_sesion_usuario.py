"""Migración v018: permite revocar sesiones locales existentes.

La revisión de sesión no es un secreto: funciona como versión de credenciales y
permisos. Un cambio de contraseña, rol o estado aumenta su valor y obliga a
volver a iniciar sesión en la próxima petición de esa sesión Streamlit.
"""


def aplicar(db) -> None:
    db.ejecutar(
        """
        ALTER TABLE usuarios_app
        ADD COLUMN revision_sesion INTEGER NOT NULL DEFAULT 1
            CHECK (revision_sesion > 0)
        """
    )
