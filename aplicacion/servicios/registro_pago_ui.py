"""Frontera de aplicación para usar el motor de pagos desde la UI.

La UI no decide reglas financieras. Este servicio prepara el comando, resuelve
el modo protegido y delega la ejecución a los casos de uso existentes.

Modos:

- LEGACY: escritura histórica, sin V3.
- SOMBRA: Legacy sigue siendo efectivo y V3 se ejecuta sobre el snapshot previo.
- V3: escritura efectiva V3, solo si el preflight está aprobado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.configuracion_motor_pago import (
    ServicioConfiguracionMotorPago,
)
from aplicacion.servicios.feature_flag_motor_pago_v3 import (
    DecisionModoMotorPagoV3,
    resolver_modo_motor_pago_v3,
)
from aplicacion.servicios.fabrica_sombra_pago_v3_sqlite import (
    crear_puente_sombra_pago_v3_sqlite,
)
from aplicacion.servicios.fabrica_registro_pago_v3 import (
    crear_registrador_pago_v3_completo_con_adelantos,
)
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    ResultadoPuenteMotorPagoV3,
)
from aplicacion.servicios.preflight_motor_pago_v3 import (
    PreflightMotorPagoV3,
    ResultadoPreflightV3,
)
from aplicacion.servicios.pagos import ServicioPagos
from dominio.excepciones import ErrorValidacion
from dominio.tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion
from infraestructura.repositorios import PrestamoRepo


@dataclass(frozen=True)
class ResultadoPagoUI:
    """Resultado normalizado para la UI, sin exponer infraestructura."""

    pago_id: int
    modo: ModoMotorPagoV3
    resultado_efectivo: object
    plan_sombra_v3: object | None = None
    divergencia: str | None = None
    error_sombra: str | None = None
    error_observabilidad: str | None = None
    preflight: ResultadoPreflightV3 | None = None


@dataclass(frozen=True)
class EstadoMotorPagoUI:
    """Estado visible del motor de pagos para una sesión de UI."""

    decision: DecisionModoMotorPagoV3
    preflight: ResultadoPreflightV3 | None


class ServicioRegistroPagoUI:
    """Punto único de entrada de la UI al registro de pagos."""

    def __init__(self, db) -> None:
        self._db = db
        self._configuracion = ServicioConfiguracionMotorPago(db)

    def evaluar_preflight(self) -> ResultadoPreflightV3:
        return PreflightMotorPagoV3(self._db).evaluar()

    def modo_actual(self) -> ModoMotorPagoV3:
        return self._configuracion.obtener().modo

    def cambiar_modo(
        self,
        *,
        nuevo_modo: ModoMotorPagoV3 | str,
        usuario: str,
        motivo: str,
    ):
        return self._configuracion.cambiar(
            nuevo_modo=nuevo_modo,
            usuario=usuario,
            motivo=motivo,
        )

    def resolver_modo(
        self,
        solicitado: ModoMotorPagoV3 | str | None,
    ) -> EstadoMotorPagoUI:
        preflight = self.evaluar_preflight() if solicitado == ModoMotorPagoV3.V3 or solicitado == "V3" else None
        decision = resolver_modo_motor_pago_v3(
            solicitado=solicitado,
            preflight=preflight,
        )
        return EstadoMotorPagoUI(decision=decision, preflight=preflight)

    def nuevo_idempotency_key(self) -> str:
        return str(uuid4())

    def crear_command(
        self,
        *,
        prestamo_id: int,
        monto: Decimal,
        fecha_real: date,
        usuario: str,
        medio: str | None,
        referencia: str | None,
        nota: str | None,
        opcion_adelanto: str | None,
        idempotency_key: str | None,
        revision_prestamo: int | None = None,
    ) -> RegistrarPagoCommand:
        return RegistrarPagoCommand(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_real=fecha_real,
            fecha_valor=fecha_real,
            usuario=usuario,
            medio=medio,
            referencia=referencia,
            nota=nota,
            opcion_adelanto=opcion_adelanto,
            idempotency_key=idempotency_key,
            revision_prestamo=revision_prestamo,
        )

    def registrar(
        self,
        *,
        command: RegistrarPagoCommand,
        modo: ModoMotorPagoV3,
        preflight: ResultadoPreflightV3 | None = None,
    ) -> ResultadoPagoUI:
        modo_efectivo = self.modo_actual()
        if ModoMotorPagoV3(modo) is not modo_efectivo:
            raise ErrorValidacion(
                "El modo del motor cambió desde la pantalla de registro. "
                "Vuelva a iniciar la operación con el modo efectivo actual."
            )

        decision = resolver_modo_motor_pago_v3(
            solicitado=modo,
            preflight=preflight,
        )

        if decision.modo is ModoMotorPagoV3.LEGACY:
            resultado = ServicioPagos(self._db).registrar_pago(
                prestamo_id=command.prestamo_id,
                monto=command.monto,
                fecha_real=command.fecha_real,
                usuario=command.usuario,
                medio=command.medio,
                referencia=command.referencia,
                nota=command.nota,
                opcion_adelanto=command.opcion_adelanto,
            )
            return ResultadoPagoUI(
                pago_id=int(resultado),
                modo=decision.modo,
                resultado_efectivo=resultado,
            )

        if decision.modo is ModoMotorPagoV3.SOMBRA:
            puente = crear_puente_sombra_pago_v3_sqlite(self._db)
            resultado_sombra: ResultadoPuenteMotorPagoV3 = puente.ejecutar(command)
            if not isinstance(resultado_sombra.resultado_efectivo, int):
                raise ErrorValidacion(
                    "El registrador efectivo de SOMBRA no devolvió un pago_id válido"
                )
            return ResultadoPagoUI(
                pago_id=int(resultado_sombra.resultado_efectivo),
                modo=decision.modo,
                resultado_efectivo=resultado_sombra.resultado_efectivo,
                plan_sombra_v3=resultado_sombra.plan_sombra_v3,
                divergencia=(
                    None
                    if resultado_sombra.divergencia is None
                    else resultado_sombra.divergencia.resumen
                ),
                error_sombra=resultado_sombra.error_sombra,
                error_observabilidad=resultado_sombra.error_observabilidad,
                preflight=preflight,
            )

        if preflight is None:
            raise ErrorValidacion("V3 requiere un resultado de preflight")

        prestamo = PrestamoRepo(self._db).obtener(command.prestamo_id)
        if prestamo is None:
            raise ErrorValidacion(
                f"El préstamo {command.prestamo_id} no existe"
            )

        info_tasa = PrestamoRepo(self._db).info_tasa_activa(command.prestamo_id)
        if info_tasa is None:
            raise ErrorValidacion(
                f"El préstamo {command.prestamo_id} no tiene tasa activa"
            )

        try:
            modalidad = ModalidadTasa(info_tasa["modalidad"])
            convencion = ConvencionDias(str(prestamo.convencion_dias).lower())
            sistema = SistemaAmortizacion(str(prestamo.sistema).lower())
        except ValueError as exc:
            raise ErrorValidacion(
                "La configuración del préstamo no es compatible con V3"
            ) from exc

        registrador = crear_registrador_pago_v3_completo_con_adelantos(
            self._db,
            tasa_anual=Decimal(info_tasa["tasa_anual"]),
            modalidad_tasa=modalidad,
            convencion_dias=convencion,
            sistema=sistema,
        )
        resultado_v3 = registrador.ejecutar(command)
        return ResultadoPagoUI(
            pago_id=int(resultado_v3.pago_id),
            modo=decision.modo,
            resultado_efectivo=resultado_v3,
            preflight=preflight,
        )
