"""Preview canónico del Motor V3 para la pantalla de pagos.

El servicio es de solo lectura. Construye exactamente el PlanPago V3 que la
ruta de registro utilizará y, para comparación, consulta la simulación histórica
sin ejecutar ninguna escritura.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from aplicacion.servicios.plan_pago_v3_devengamientos import (
    ResultadoPlanPagoV3Devengamientos,
    calcular_plan_pago_con_devengamientos,
)
from aplicacion.consultas.deuda_proximo_pago import ServicioDeudaProximoPago
from dominio.adelanto_v3 import PlanAdelantoV3, planificar_adelanto_v3
from dominio.escenarios_pago import DeudaPago, ResultadoPago, simular_pago
from dominio.excepciones import ErrorValidacion
from dominio.tipos import (
    ConvencionDias,
    ModalidadTasa,
    SistemaAmortizacion,
    TipoRecalculo,
)
from infraestructura.repositorios import PrestamoRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)


ZERO = Decimal("0.00")


class EstadoComparacionPreview(str, Enum):
    """Estado estable de la comparación entre previews."""

    EQUIVALENTE = "EQUIVALENTE"
    DIVERGENCIA = "DIVERGENCIA"


@dataclass(frozen=True)
class ComparacionPreviewPago:
    """Comparación económica entre preview Legacy y preview V3."""

    coincidente: bool
    total_deuda_legacy: Decimal
    total_deuda_v3: Decimal
    diferencia_total_deuda: Decimal
    mora_legacy: Decimal
    mora_v3: Decimal
    interes_legacy: Decimal
    interes_v3: Decimal
    capital_legacy: Decimal
    capital_v3: Decimal
    excedente_legacy: Decimal
    excedente_v3: Decimal

    @property
    def estado(self) -> EstadoComparacionPreview:
        return (
            EstadoComparacionPreview.EQUIVALENTE
            if self.coincidente
            else EstadoComparacionPreview.DIVERGENCIA
        )

    @property
    def diferencias(self) -> tuple[str, ...]:
        diferencias: list[str] = []
        if self.total_deuda_legacy != self.total_deuda_v3:
            diferencias.append("DEUDA_TOTAL")
        if self.mora_legacy != self.mora_v3:
            diferencias.append("MORA")
        if self.interes_legacy != self.interes_v3:
            diferencias.append("INTERES")
        if self.capital_legacy != self.capital_v3:
            diferencias.append("CAPITAL")
        if self.excedente_legacy != self.excedente_v3:
            diferencias.append("EXCEDENTE")
        return tuple(diferencias)


@dataclass(frozen=True)
class PreviewPagoV3:
    """Resultado completo del preview V3, sin efectos secundarios."""

    resultado_plan: ResultadoPlanPagoV3Devengamientos
    plan_adelanto: PlanAdelantoV3 | None
    comparacion_legacy: ComparacionPreviewPago | None
    resultado_legacy: ResultadoPago | None

    @property
    def plan(self):
        return self.resultado_plan.plan


class ServicioPreviewPagoV3:
    """Construye el mismo resultado financiero que utilizará el registro V3."""

    def __init__(self, db) -> None:
        self._db = db

    def previsualizar(
        self,
        *,
        prestamo_id: int,
        monto: Decimal,
        fecha_valor: date,
        opcion_adelanto: str | None = None,
        comparar_legacy: bool = True,
    ) -> PreviewPagoV3:
        prestamo_repo = PrestamoRepo(self._db)
        prestamo = prestamo_repo.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no existe")

        tasa = prestamo_repo.info_tasa_activa(prestamo_id)
        if tasa is None:
            raise ErrorValidacion(
                f"El préstamo {prestamo_id} no tiene una tasa activa"
            )

        try:
            modalidad = ModalidadTasa(tasa["modalidad"])
            convencion = ConvencionDias(str(prestamo.convencion_dias).lower())
            sistema = SistemaAmortizacion(str(prestamo.sistema).lower())
        except ValueError as exc:
            raise ErrorValidacion(
                "La configuración del préstamo no es compatible con V3"
            ) from exc

        repositorio = RepositorioRegistroPagoSQLiteV3(self._db)
        estado = repositorio.obtener_estado_pago(prestamo_id)
        ultimos = repositorio.ultimo_hasta_interes_capital_por_cuotas(
            prestamo_id,
            tuple(o.cuota_id for o in estado.obligaciones),
        )

        from dominio.devengamiento_v3 import PoliticaInteres

        from dominio.politica_devengamiento_v3 import (
            PoliticaInteresCapitalPendiente,
            PoliticaMoraContractualV3,
        )

        politica = PoliticaInteresCapitalPendiente(
            PoliticaInteres(
                tasa_anual=tasa["tasa_anual"],
                modalidad_tasa=modalidad,
                convencion_dias=convencion,
            )
        )

        resultado_plan = calcular_plan_pago_con_devengamientos(
            estado=estado,
            fecha_valor=fecha_valor,
            monto_recibido=monto,
            politica_interes_capital=politica,
            politica_mora=PoliticaMoraContractualV3(),
            ultimo_hasta_por_cuota=ultimos,
        )

        plan_adelanto = None
        if resultado_plan.plan.excedente.monto > ZERO:
            if opcion_adelanto is not None:
                if opcion_adelanto not in ("RAI", "RNI"):
                    raise ErrorValidacion(
                        "La opción de adelanto debe ser RAI o RNI"
                    )
                objetivo = max(
                    resultado_plan.plan.obligaciones_afectadas,
                    key=lambda o: (o.numero_cuota, o.cuota_id),
                )
                futuras = repositorio.cuotas_futuras_para_adelanto(
                    prestamo_id,
                    objetivo.numero_cuota + 1,
                )
                if not futuras:
                    raise ErrorValidacion(
                        "El excedente no tiene cuotas futuras para reestructurar"
                    )
                plan_adelanto = planificar_adelanto_v3(
                    tipo=TipoRecalculo(opcion_adelanto),
                    cuota_objetivo_numero=objetivo.numero_cuota,
                    cuotas_futuras=futuras,
                    monto_adelanto=resultado_plan.plan.excedente.monto,
                    tasa_anual=tasa["tasa_anual"],
                    modalidad_tasa=modalidad,
                    sistema=sistema,
                )

        resultado_legacy = None
        comparacion = None
        if comparar_legacy:
            resultado_legacy = self._simular_legacy(
                prestamo_id=prestamo_id,
                monto=monto,
                fecha_valor=fecha_valor,
            )
            comparacion = _comparar(
                resultado_plan,
                resultado_legacy,
                obligaciones=estado.obligaciones,
            )

        return PreviewPagoV3(
            resultado_plan=resultado_plan,
            plan_adelanto=plan_adelanto,
            comparacion_legacy=comparacion,
            resultado_legacy=resultado_legacy,
        )

    def _simular_legacy(
        self,
        *,
        prestamo_id: int,
        monto: Decimal,
        fecha_valor: date,
    ) -> ResultadoPago:
        deuda = ServicioDeudaProximoPago(self._db).calcular(
            prestamo_id,
            fecha_valor,
        )
        if deuda is None:
            raise ErrorValidacion("El préstamo no tiene cuotas pendientes")

        deuda_pago = DeudaPago(
            cuota_interes=deuda["cuota_interes"],
            cuota_capital=deuda["cuota_capital"],
            arrastre_interes=deuda["arrastre_interes"],
            arrastre_capital=deuda["arrastre_capital"],
            arrastre_mora=deuda["arrastre_mora"],
            interes_extra=deuda["interes_extra"],
            mora_nueva=deuda["mora_nueva"],
        )

        info_tasa = PrestamoRepo(self._db).info_tasa_activa(prestamo_id)
        if info_tasa is None:
            raise ErrorValidacion("Falta la tasa activa del préstamo")

        from dominio.tipos import ModalidadTasa
        from dominio.devengamiento_v3 import PoliticaInteres
        from dominio.interes import tasa_mensual

        tasa_mensual_legacy = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )
        return simular_pago(
            monto=monto,
            deuda=deuda_pago,
            tasa_mensual=tasa_mensual_legacy,
        )


def _comparar(
    resultado_plan: ResultadoPlanPagoV3Devengamientos,
    legacy: ResultadoPago,
    *,
    obligaciones,
) -> ComparacionPreviewPago:
    plan = resultado_plan.plan
    mora_v3 = plan.aplicado_mora
    interes_v3 = plan.aplicado_interes
    capital_v3 = plan.monto_a_capital
    excedente_v3 = plan.excedente.monto

    devengamientos = resultado_plan.devengamientos_nuevos
    total_v3 = money(
        sum(
            (
                obligacion.saldo.total
                + sum(
                    (d.monto for d in devengamientos.get(obligacion.cuota_id, ())),
                    ZERO,
                )
            )
            for obligacion in obligaciones
        )
    )

    return ComparacionPreviewPago(
        coincidente=(
            legacy.total_deuda == total_v3
            and legacy.aplicado_mora == mora_v3
            and legacy.aplicado_interes == interes_v3
            and legacy.aplicado_capital == capital_v3
            and legacy.excedente == excedente_v3
        ),
        total_deuda_legacy=legacy.total_deuda,
        total_deuda_v3=total_v3,
        diferencia_total_deuda=money(total_v3 - legacy.total_deuda),
        mora_legacy=legacy.aplicado_mora,
        mora_v3=mora_v3,
        interes_legacy=legacy.aplicado_interes,
        interes_v3=interes_v3,
        capital_legacy=legacy.aplicado_capital,
        capital_v3=capital_v3,
        excedente_legacy=legacy.excedente,
        excedente_v3=excedente_v3,
    )


def money(valor: Decimal) -> Decimal:
    from dominio.tipos import money as normalizar_money

    return normalizar_money(valor)
