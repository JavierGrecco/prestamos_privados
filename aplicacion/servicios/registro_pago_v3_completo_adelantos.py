"""G5: registro V3 completo con RAI/RNI explícitos."""
from __future__ import annotations

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import ResultadoRegistroPagoV3, fingerprint_command
from aplicacion.servicios.plan_pago_v3_devengamientos import calcular_plan_pago_con_devengamientos
from dominio.adelanto_v3 import planificar_adelanto_v3
from dominio.politica_pago import PoliticaImputacionPago
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
)
from dominio.tipos import TipoRecalculo, SistemaAmortizacion


class RegistrarPagoV3CompletoConAdelantos:
    def __init__(
        self,
        repositorio,
        politica_interes_capital: PoliticaInteresCapitalPendiente,
        politica_mora: PoliticaMoraContractualV3 | None = None,
        politica_pago: PoliticaImputacionPago | None = None,
        *,
        recalcular_rai_fn=None,
        recalcular_rni_fn=None,
        sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
    ):
        self._repo = repositorio
        self._politica = politica_interes_capital
        self._politica_mora = politica_mora
        self._politica_pago = politica_pago
        self._recalcular_rai = recalcular_rai_fn
        self._recalcular_rni = recalcular_rni_fn
        self._sistema = sistema

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

            cuota_ids = tuple(o.cuota_id for o in estado.obligaciones)
            ultimos = self._repo.ultimo_hasta_interes_capital_por_cuotas(
                command.prestamo_id, cuota_ids
            )
            ultimos_mora = self._repo.ultimo_hasta_mora_contractual_por_cuotas(
                command.prestamo_id, cuota_ids
            )
            resultado_plan = calcular_plan_pago_con_devengamientos(
                estado=estado, fecha_valor=command.fecha_valor, monto_recibido=command.monto,
                politica_interes_capital=self._politica,
                politica_mora=self._politica_mora,
                ultimo_hasta_por_cuota=ultimos,
                ultimo_hasta_mora_por_cuota=ultimos_mora,
                politica_pago=self._politica_pago,
            )

            plan_adelanto = None
            if resultado_plan.plan.excedente.monto > 0:
                if command.opcion_adelanto not in ("RAI", "RNI"):
                    raise ErrorValidacion("El excedente requiere elegir RAI o RNI")
                objetivo = max(resultado_plan.plan.obligaciones_afectadas, key=lambda o: (o.numero_cuota, o.cuota_id))
                futuras = self._repo.cuotas_futuras_para_adelanto(
                    command.prestamo_id, objetivo.numero_cuota + 1
                )
                tipo = TipoRecalculo(command.opcion_adelanto)
                if not futuras:
                    raise ErrorValidacion("El pago tiene excedente pero no existen cuotas futuras para aplicar el adelanto")
                plan_adelanto = planificar_adelanto_v3(
                    tipo=tipo,
                    cuota_objetivo_numero=objetivo.numero_cuota,
                    cuotas_futuras=futuras,
                    monto_adelanto=resultado_plan.plan.excedente.monto,
                    tasa_anual=self._politica.politica.tasa_anual,
                    modalidad_tasa=self._politica.politica.modalidad_tasa,
                    sistema=self._sistema,
                    recalcular_rai_fn=self._recalcular_rai,
                    recalcular_rni_fn=self._recalcular_rni,
                )
                pago_id = self._repo.persistir_pago_y_devengamientos_y_adelanto(
                    command, resultado_plan, plan_adelanto,
                    fingerprint=fingerprint, revision_esperada=revision,
                )
                self._repo.persistir_adelanto_sin_transaccion(
                    prestamo_id=command.prestamo_id, pago_id=pago_id,
                    plan=plan_adelanto, fecha=command.fecha_real, usuario=command.usuario,
                )
            else:
                if command.opcion_adelanto is not None:
                    raise ErrorValidacion("No existe excedente al cual aplicar RAI/RNI")
                pago_id = self._repo.persistir_pago_y_devengamientos(
                    command, resultado_plan,
                    fingerprint=fingerprint, revision_esperada=revision,
                )

            correlacion_id = self._repo.correlacion_ledger_pago(pago_id)
            self._repo.persistir_distribucion_inversores(
                prestamo_id=command.prestamo_id, pago_id=pago_id,
                monto=resultado_plan.plan.monto_pago_recibido, fecha=command.fecha_real,
                correlacion_id=correlacion_id, usuario=command.usuario,
            )
            self._repo.commit()
            return ResultadoRegistroPagoV3(pago_id, revision, False, fingerprint, resultado_plan.plan)
        except Exception:
            self._repo.rollback()
            raise
