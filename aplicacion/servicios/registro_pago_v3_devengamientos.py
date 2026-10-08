"""G3: registro V3 con devengamientos dentro de la misma transacción."""
from __future__ import annotations

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import ResultadoRegistroPagoV3, fingerprint_command
from aplicacion.servicios.plan_pago_v3_devengamientos import calcular_plan_pago_con_devengamientos
from dominio.excepciones import ErrorInvariante
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
)


class RegistrarPagoV3ConDevengamientos:
    def __init__(
        self,
        repositorio,
        politica_interes_capital: PoliticaInteresCapitalPendiente,
        politica_mora: PoliticaMoraContractualV3 | None = None,
    ):
        self._repositorio = repositorio
        self._politica = politica_interes_capital
        self._politica_mora = politica_mora

    def ejecutar(self, command: RegistrarPagoCommand) -> ResultadoRegistroPagoV3:
        fingerprint = fingerprint_command(command)
        self._repositorio.begin()
        try:
            if command.idempotency_key:
                existente = self._repositorio.buscar_idempotencia(command.idempotency_key)
                if existente is not None:
                    if existente.fingerprint != fingerprint:
                        raise ErrorInvariante("La idempotency_key ya fue utilizada con un payload diferente")
                    self._repositorio.commit()
                    return ResultadoRegistroPagoV3(
                        pago_id=existente.pago_id,
                        revision_utilizada=None,
                        es_repeticion_idempotente=True,
                        fingerprint=fingerprint,
                        plan=None,
                    )

            estado = self._repositorio.obtener_estado_pago(command.prestamo_id)
            revision = estado.revision_prestamo
            if command.revision_prestamo is not None and command.revision_prestamo != revision:
                raise ErrorInvariante("Conflicto de revisión del préstamo: el estado cambió antes de registrar")

            ultimos = self._repositorio.ultimo_hasta_interes_capital_por_cuotas(
                command.prestamo_id, tuple(o.cuota_id for o in estado.obligaciones)
            )
            resultado_plan = calcular_plan_pago_con_devengamientos(
                estado=estado,
                fecha_valor=command.fecha_valor,
                monto_recibido=command.monto,
                politica_interes_capital=self._politica,
                politica_mora=self._politica_mora,
                ultimo_hasta_por_cuota=ultimos,
            )
            pago_id = self._repositorio.persistir_pago_y_devengamientos(
                command,
                resultado_plan,
                fingerprint=fingerprint,
                revision_esperada=revision,
            )
            if pago_id <= 0:
                raise ErrorInvariante("La persistencia devolvió un pago_id inválido")
            self._repositorio.commit()
            return ResultadoRegistroPagoV3(
                pago_id=pago_id,
                revision_utilizada=revision,
                es_repeticion_idempotente=False,
                fingerprint=fingerprint,
                plan=resultado_plan.plan,
            )
        except Exception:
            self._repositorio.rollback()
            raise
