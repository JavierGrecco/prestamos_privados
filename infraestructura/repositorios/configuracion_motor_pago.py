"""Repositorio de configuración operacional del modo del motor de pagos."""

from datetime import datetime

class ConfiguracionMotorPagoRepo:
    """Acceso al singleton de configuración del modo efectivo."""

    def __init__(self, db) -> None:
        self.db = db

    def obtener(self) -> dict:
        fila = self.db.consultar_uno(
            """
            SELECT id, modo, revision, actualizado_en, actualizado_por
            FROM configuracion_motor_pago
            WHERE id = 1
            """
        )
        if fila is None:
            raise RuntimeError("La configuración del motor de pagos no está inicializada")
        return dict(fila)

    def actualizar(
        self,
        *,
        modo: str,
        usuario: str,
        revision_esperada: int,
    ) -> dict:
        if modo not in {"LEGACY", "SOMBRA", "V3"}:
            raise ValueError(f"Modo de motor de pagos inválido: {modo!r}")
        nuevo_modo = modo
        ahora = datetime.now().isoformat(timespec="seconds")

        with self.db.transaccion():
            cursor = self.db.ejecutar(
                """
                UPDATE configuracion_motor_pago
                   SET modo = ?,
                       revision = revision + 1,
                       actualizado_en = ?,
                       actualizado_por = ?
                 WHERE id = 1
                   AND revision = ?
                """,
                (nuevo_modo, ahora, usuario, revision_esperada),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "La configuración del motor cambió concurrentemente; "
                    "vuelva a consultar el estado antes de aplicar el cambio"
                )

            return self.obtener()
