"""Persistencia SQLite transaccional para cambiar y auditar el modo del motor."""

from __future__ import annotations

from aplicacion.puertos.configuracion_motor_pago import (
    EstadoConfiguracionMotorPago,
    ModoMotorPagoV3,
)
from infraestructura.db import BaseDatos
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.configuracion_motor_pago import (
    ConfiguracionMotorPagoRepo,
)


class ConfiguracionMotorPagoSQLite:
    """Adapta los repositorios existentes a un cambio de modo atómico y auditable.

    La actualización, el control de revisión y la entrada de auditoría comparten
    una única transacción exterior. Los repositorios pueden abrir sus propias
    transacciones anidadas, pero la confirmación final depende de esta unidad.
    """

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._repo = ConfiguracionMotorPagoRepo(db)
        self._auditoria = AuditoriaRepo(db)

    def obtener(self) -> EstadoConfiguracionMotorPago:
        return _estado_desde_fila(self._repo.obtener())

    def cambiar_y_auditar(
        self,
        *,
        nuevo_modo: ModoMotorPagoV3,
        usuario: str,
        motivo: str,
        revision_esperada: int,
        correlacion_id: str,
    ) -> None:
        with self._db.transaccion():
            anterior = self._repo.obtener()
            nueva = self._repo.actualizar(
                modo=nuevo_modo.value,
                usuario=usuario,
                revision_esperada=revision_esperada,
            )
            self._auditoria.registrar(
                usuario=usuario,
                operacion="MOTOR_PAGO_MODO_CAMBIADO",
                entidad="CONFIGURACION_MOTOR_PAGO",
                entidad_id=1,
                correlacion_id=correlacion_id,
                datos_anteriores={
                    "modo": anterior["modo"],
                    "revision": anterior["revision"],
                },
                datos_nuevos={
                    "modo": nueva["modo"],
                    "revision": nueva["revision"],
                },
                motivo=motivo,
            )


def _estado_desde_fila(fila: dict) -> EstadoConfiguracionMotorPago:
    return EstadoConfiguracionMotorPago(
        modo=ModoMotorPagoV3(fila["modo"]),
        revision=int(fila["revision"]),
        actualizado_en=str(fila["actualizado_en"]),
        actualizado_por=str(fila["actualizado_por"]),
    )
