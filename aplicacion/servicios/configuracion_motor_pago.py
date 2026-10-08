"""Caso de uso para activar y revertir el modo del Motor de Pagos."""

from __future__ import annotations

from dataclasses import dataclass

from aplicacion.servicios.excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido
from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.configuracion_motor_pago import (
    ConfiguracionMotorPagoRepo,
)
from infraestructura.repositorios.base import nuevo_correlacion_id


@dataclass(frozen=True)
class EstadoConfiguracionMotorPago:
    modo: ModoMotorPagoV3
    revision: int
    actualizado_en: str
    actualizado_por: str


class ServicioConfiguracionMotorPago:
    """Administra el modo persistente con preflight y auditoría."""

    def __init__(self, db) -> None:
        self._db = db
        self._repo = ConfiguracionMotorPagoRepo(db)
        self._auditoria = AuditoriaRepo(db)

    def obtener(self) -> EstadoConfiguracionMotorPago:
        fila = self._repo.obtener()
        return EstadoConfiguracionMotorPago(
            modo=ModoMotorPagoV3(fila["modo"]),
            revision=int(fila["revision"]),
            actualizado_en=str(fila["actualizado_en"]),
            actualizado_por=str(fila["actualizado_por"]),
        )

    def cambiar(
        self,
        *,
        nuevo_modo: ModoMotorPagoV3 | str,
        usuario: str,
        motivo: str,
    ) -> EstadoConfiguracionMotorPago:
        if not usuario or not usuario.strip():
            raise ErrorDatosInvalidos("Se requiere un usuario")
        if not motivo or not motivo.strip():
            raise ErrorDatosInvalidos("Se requiere un motivo para cambiar el modo")

        try:
            modo = ModoMotorPagoV3(nuevo_modo)
        except ValueError as exc:
            raise ErrorDatosInvalidos(
                f"Modo de motor de pagos inválido: {nuevo_modo!r}"
            ) from exc

        actual = self.obtener()
        if modo is actual.modo:
            return actual

        if modo is ModoMotorPagoV3.V3:
            preflight = PreflightMotorPagoV3(self._db).evaluar()
            if not preflight.apto:
                raise ErrorEstadoInvalido(
                    "No se puede activar V3: el preflight no está aprobado. "
                    + " | ".join(preflight.motivos_rechazo)
                )

        correlacion_id = nuevo_correlacion_id()
        with self._db.transaccion():
            nueva = self._repo.actualizar(
                modo=modo,
                usuario=usuario.strip(),
                revision_esperada=actual.revision,
            )
            self._auditoria.registrar(
                usuario=usuario.strip(),
                operacion="MOTOR_PAGO_MODO_CAMBIADO",
                entidad="CONFIGURACION_MOTOR_PAGO",
                entidad_id=1,
                correlacion_id=correlacion_id,
                datos_anteriores={
                    "modo": actual.modo.value,
                    "revision": actual.revision,
                },
                datos_nuevos={
                    "modo": nueva["modo"],
                    "revision": nueva["revision"],
                },
                motivo=motivo.strip(),
            )

        return self.obtener()
