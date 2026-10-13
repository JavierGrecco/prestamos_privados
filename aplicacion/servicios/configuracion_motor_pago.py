"""Caso de uso para activar y revertir el modo del Motor de Pagos."""

from __future__ import annotations

from uuid import uuid4

from aplicacion.puertos.configuracion_motor_pago import (
    EstadoConfiguracionMotorPago,
    GatePreflightConfiguracion,
    ModoMotorPagoV3,
    PersistenciaConfiguracionMotorPago,
)
from aplicacion.servicios.excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido
from aplicacion.puertos.preflight_motor_pago_v3 import VERSION_MINIMA_SCHEMA_V3


class ServicioConfiguracionMotorPago:
    """Administra el modo efectivo mediante un puerto transaccional y un gate."""

    def __init__(
        self,
        *,
        persistencia: PersistenciaConfiguracionMotorPago,
        preflight: GatePreflightConfiguracion,
    ) -> None:
        self._persistencia = persistencia
        self._preflight = preflight

    def obtener(self) -> EstadoConfiguracionMotorPago:
        return self._persistencia.obtener()

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
            preflight = self._preflight.evaluar()
            if not preflight.apto:
                raise ErrorEstadoInvalido(
                    "No se puede activar V3: el preflight no está aprobado. "
                    + " | ".join(preflight.motivos_rechazo)
                )

        self._persistencia.cambiar_y_auditar(
            nuevo_modo=modo,
            usuario=usuario.strip(),
            motivo=motivo.strip(),
            revision_esperada=actual.revision,
            correlacion_id=str(uuid4()),
        )
        return self.obtener()
