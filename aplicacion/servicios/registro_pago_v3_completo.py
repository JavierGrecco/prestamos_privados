"""G4: registro V3 + devengamientos + distribución a inversores."""
from __future__ import annotations

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import ResultadoRegistroPagoV3, fingerprint_command
from aplicacion.servicios.plan_pago_v3_devengamientos import calcular_plan_pago_con_devengamientos
from dominio.excepciones import ErrorInvariante


class RegistrarPagoV3Completo:
    def __init__(self, repositorio, politica_interes_capital):
        self._repo = repositorio
        self._politica = politica_interes_capital

    def ejecutar(self, command: RegistrarPagoCommand) -> ResultadoRegistroPagoV3:
        fingerprint = fingerprint_command(command)
        self._repo.begin()
        try:
            if command.idempotency_key:
                existente = self._repo.buscar_idempotencia(command.idempotency_key)
                if existente is not None:
                    if existente.fingerprint != fingerprint:
                        raise ErrorInvariante("La idempotency_key ya fue utilizada con un payload diferente")
                    self._repo.commit()
                    return ResultadoRegistroPagoV3(existente.pago_id, None, True, fingerprint, None)

            estado = self._repo.obtener_estado_pago(command.prestamo_id)
            revision = estado.revision_prestamo
            if command.revision_prestamo is not None and command.revision_prestamo != revision:
                raise ErrorInvariante("Conflicto de revisión del préstamo: el estado cambió antes de registrar")

            ultimos = self._repo.ultimo_hasta_interes_capital_por_cuotas(
                command.prestamo_id, tuple(o.cuota_id for o in estado.obligaciones)
            )
            resultado = calcular_plan_pago_con_devengamientos(
                estado=estado, fecha_valor=command.fecha_valor, monto_recibido=command.monto,
                politica_interes_capital=self._politica, ultimo_hasta_por_cuota=ultimos,
            )
            pago_id = self._repo.persistir_pago_y_devengamientos(
                command, resultado, fingerprint=fingerprint, revision_esperada=revision,
            )
            correlacion_id = self._repo.correlacion_ledger_pago(pago_id)
            self._repo.persistir_distribucion_inversores(
                prestamo_id=command.prestamo_id, pago_id=pago_id,
                monto=resultado.plan.monto_pago_recibido, fecha=command.fecha_real,
                correlacion_id=correlacion_id, usuario=command.usuario,
            )
            self._repo.commit()
            return ResultadoRegistroPagoV3(pago_id, revision, False, fingerprint, resultado.plan)
        except Exception:
            self._repo.rollback()
            raise
