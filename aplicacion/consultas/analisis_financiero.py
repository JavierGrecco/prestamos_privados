"""Read model financiero para la UI.

Este módulo no escribe en SQLite y no redefine las fórmulas del dominio.
Construye una vista financiera de una persona a partir de hechos persistidos y
separa claramente flujos reales de proyecciones.

Las proyecciones se presentan como contractuales: no incluyen mora futura ni
cambios de tasa que todavía no existan en la base.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dominio.analisis_cambiario import calcular_rendimiento_real
from dominio.escenarios import (
    EscenarioMacro,
    ResultadoEscenario,
    comparar_escenarios,
    escenarios_predefinidos_argentina,
)
from dominio.licuacion import valor_real
from dominio.tipos import ModalidadTasa, SistemaAmortizacion, money
from dominio.xirr import xirr
from aplicacion.puertos.analisis_financiero import (
    ConsultaAnalisisFinanciero,
    CuotaAnalisis,
)


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class FlujoCajaFinanciero:
    """Flujo de caja normalizado para análisis y UI."""

    fecha: date
    monto_ars: Decimal
    tipo: str
    origen: str
    rol: str
    prestamo_id: int
    prestamo_numero: str
    real: bool
    tc_ars_usd: Decimal | None = None
    monto_usd_explicito: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "monto_ars", money(self.monto_ars))
        if self.tc_ars_usd is not None:
            tc = Decimal(str(self.tc_ars_usd))
            if tc <= ZERO:
                raise ValueError("El tipo de cambio debe ser mayor a cero")
            object.__setattr__(self, "tc_ars_usd", tc)
        if self.monto_usd_explicito is not None:
            usd = money(self.monto_usd_explicito)
            object.__setattr__(
                self,
                "monto_usd_explicito",
                usd if self.monto_ars >= ZERO else -usd,
            )

    @property
    def monto_usd(self) -> Decimal | None:
        if self.monto_usd_explicito is not None:
            return self.monto_usd_explicito
        if self.tc_ars_usd is None or self.tc_ars_usd <= ZERO:
            return None
        return money(abs(self.monto_ars) / self.tc_ars_usd) * (
            Decimal("-1") if self.monto_ars < ZERO else Decimal("1")
        )


@dataclass(frozen=True)
class ResumenPosicionFinanciera:
    capital_aportado_activo: Decimal
    capital_deudor_pendiente: Decimal
    posicion_neta_capital: Decimal
    cobros_inversor_reales: Decimal
    pagos_deudor_reales: Decimal
    xirr_inversor: Decimal | None
    xirr_deudor: Decimal | None
    xirr_inversor_usd: Decimal | None
    xirr_deudor_usd: Decimal | None
    rendimiento_real_inversor: Decimal | None
    rendimiento_real_deudor: Decimal | None

    @property
    def tiene_posicion_inversora(self) -> bool:
        return self.capital_aportado_activo > ZERO

    @property
    def tiene_deuda(self) -> bool:
        return self.capital_deudor_pendiente > ZERO


@dataclass(frozen=True)
class ResultadoAnalisisFinanciero:
    persona_id: int
    fecha_corte: date
    inflacion_mensual_supuesto: Decimal
    resumen: ResumenPosicionFinanciera
    flujos_reales: tuple[FlujoCajaFinanciero, ...]
    flujos_proyectados: tuple[FlujoCajaFinanciero, ...]
    advertencias: tuple[str, ...]

    @property
    def entradas_reales(self) -> Decimal:
        return money(
            sum((f.monto_ars for f in self.flujos_reales if f.monto_ars > ZERO), ZERO)
        )

    @property
    def salidas_reales(self) -> Decimal:
        return money(
            sum((-f.monto_ars for f in self.flujos_reales if f.monto_ars < ZERO), ZERO)
        )

    @property
    def neto_real(self) -> Decimal:
        return money(sum((f.monto_ars for f in self.flujos_reales), ZERO))

    @property
    def valor_real_proyectado(self) -> Decimal:
        total = ZERO
        for flujo in self.flujos_proyectados:
            meses = _meses_desde(self.fecha_corte, flujo.fecha)
            total += valor_real(
                abs(flujo.monto_ars),
                self.inflacion_mensual_supuesto,
                meses,
            )
        return money(total)


@dataclass(frozen=True)
class ResultadoEscenariosUI:
    prestamo_id: int
    resultados: tuple[ResultadoEscenario, ...]


class AnalisisFinancieroQuery:
    """Consulta financiera de solo lectura."""

    def __init__(self, consulta: ConsultaAnalisisFinanciero) -> None:
        """Recibe las lecturas persistidas por un contrato, no por SQLite."""
        self._consulta = consulta

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesto: Decimal = Decimal("0.05"),
    ) -> ResultadoAnalisisFinanciero:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        corte = fecha_corte or date.today()
        inflacion = Decimal(str(inflacion_mensual_supuesto))
        if inflacion <= Decimal("-1"):
            raise ValueError("La inflación mensual debe ser mayor a -100%")

        prestamos_deudor = [
            p for p in self._consulta.prestamos_por_deudor(persona_id)
            if p.estado in ("ACTIVO", "EN_MORA")
        ]
        todas_participaciones = self._consulta.participaciones_por_inversor(persona_id)
        participaciones = [
            p for p in todas_participaciones
            if p.estado == "ACTIVA"
        ]
        participaciones_historicas = [
            p for p in todas_participaciones
            if p.estado != "ANULADA"
        ]

        reales: list[FlujoCajaFinanciero] = []
        proyectados: list[FlujoCajaFinanciero] = []
        advertencias: list[str] = []

        reales.extend(
            self._flujos_deudor_reales(
                prestamos_deudor,
                persona_id,
                corte,
            )
        )
        reales.extend(
            self._flujos_inversor_reales(
                participaciones_historicas,
                persona_id,
                corte,
                advertencias,
            )
        )

        proyectados.extend(
            self._flujos_deudor_proyectados(
                prestamos_deudor,
                persona_id,
                corte,
            )
        )
        proyectados.extend(
            self._flujos_inversor_proyectados(
                participaciones,
                persona_id,
                corte,
            )
        )

        reales = sorted(reales, key=lambda f: (f.fecha, f.prestamo_id, f.tipo))
        proyectados = sorted(
            proyectados,
            key=lambda f: (f.fecha, f.prestamo_id, f.tipo),
        )

        capital_aportado = money(
            sum((p.capital_aportado for p in participaciones), ZERO)
        )
        capital_deudor = self._capital_deudor_pendiente(prestamos_deudor)

        flujos_inv = [
            (f.fecha, f.monto_ars)
            for f in reales
            if f.rol == "inversor"
        ]
        flujos_deu = [
            (f.fecha, f.monto_ars)
            for f in reales
            if f.rol == "deudor"
        ]
        flujos_inv_usd = _flujos_usd_completos(reales, "inversor")
        flujos_deu_usd = _flujos_usd_completos(reales, "deudor")

        xirr_inv = _xirr_seguro(flujos_inv)
        xirr_deu = _xirr_seguro(flujos_deu)
        xirr_inv_usd = _xirr_seguro(flujos_inv_usd)
        xirr_deu_usd = _xirr_seguro(flujos_deu_usd)

        inflacion_anual = (Decimal("1") + inflacion) ** 12 - Decimal("1")
        resumen = ResumenPosicionFinanciera(
            capital_aportado_activo=capital_aportado,
            capital_deudor_pendiente=capital_deudor,
            posicion_neta_capital=money(capital_aportado - capital_deudor),
            cobros_inversor_reales=money(
                sum(
                    (f.monto_ars for f in reales
                     if f.rol == "inversor" and f.monto_ars > ZERO),
                    ZERO,
                )
            ),
            pagos_deudor_reales=money(
                sum(
                    (-f.monto_ars for f in reales
                     if f.rol == "deudor" and f.monto_ars < ZERO),
                    ZERO,
                )
            ),
            xirr_inversor=xirr_inv,
            xirr_deudor=xirr_deu,
            xirr_inversor_usd=xirr_inv_usd,
            xirr_deudor_usd=xirr_deu_usd,
            rendimiento_real_inversor=_rendimiento_real_seguro(
                xirr_inv,
                inflacion_anual,
            ),
            rendimiento_real_deudor=_rendimiento_real_seguro(
                xirr_deu,
                inflacion_anual,
            ),
        )

        if capital_aportado > ZERO and xirr_inv is None:
            advertencias.append(
                "Todavía no hay suficientes flujos inversores con signos "
                "opuestos para calcular XIRR."
            )
        if capital_deudor > ZERO and xirr_deu is None:
            advertencias.append(
                "Todavía no hay suficientes flujos del deudor con signos "
                "opuestos para calcular XIRR."
            )

        if any(f.monto_usd is None for f in reales if f.rol == "inversor"):
            advertencias.append(
                "Hay flujos reales del inversor sin conversión USD explícita; "
                "no se muestra XIRR USD parcial."
            )
        if any(f.monto_usd is None for f in reales if f.rol == "deudor"):
            advertencias.append(
                "Hay flujos reales del deudor sin conversión USD explícita; "
                "no se muestra XIRR USD parcial."
            )

        return ResultadoAnalisisFinanciero(
            persona_id=persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
            resumen=resumen,
            flujos_reales=tuple(reales),
            flujos_proyectados=tuple(proyectados),
            advertencias=tuple(dict.fromkeys(advertencias)),
        )

    def escenarios_para_prestamo(
        self,
        prestamo_id: int,
        escenarios: tuple[EscenarioMacro, ...] | None = None,
    ) -> ResultadoEscenariosUI:
        prestamo = self._consulta.prestamo_por_id(prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {prestamo_id} no existe")

        tasa = self._consulta.tasa_activa(prestamo_id)
        if tasa is None:
            raise ValueError("El préstamo no tiene una tasa activa")

        try:
            modalidad = ModalidadTasa(tasa.modalidad)
            sistema = SistemaAmortizacion(str(prestamo.sistema).lower())
        except ValueError as exc:
            raise ValueError(
                "La configuración del préstamo no es compatible con el simulador"
            ) from exc

        escenarios = escenarios or tuple(escenarios_predefinidos_argentina())
        resultados = comparar_escenarios(
            capital=prestamo.capital_original,
            tasa_anual=tasa.tasa_anual,
            modalidad=modalidad,
            meses=prestamo.plazo_meses,
            fecha_inicio=prestamo.fecha_inicio,
            escenarios=escenarios,
            sistema=sistema,
            tc_inicial=prestamo.tc_inicial,
        )
        return ResultadoEscenariosUI(
            prestamo_id=prestamo_id,
            resultados=tuple(resultados),
        )

    def _flujos_deudor_reales(
        self,
        prestamos,
        persona_id: int,
        corte: date,
    ) -> list[FlujoCajaFinanciero]:
        """Reconstruye desembolsos y pagos con datos ya normalizados por el puerto."""
        reales: list[FlujoCajaFinanciero] = []
        for prestamo in prestamos:
            if prestamo.fecha_inicio is not None and prestamo.fecha_inicio <= corte:
                reales.append(
                    FlujoCajaFinanciero(
                        fecha=prestamo.fecha_inicio,
                        monto_ars=money(prestamo.capital_original),
                        tipo="DESEMBOLSO",
                        origen="CONTRACTUAL",
                        rol="deudor",
                        prestamo_id=prestamo.id,
                        prestamo_numero=prestamo.numero,
                        real=True,
                        tc_ars_usd=prestamo.tc_inicial,
                    )
                )

            for pago in self._consulta.pagos_validos_de_prestamo(prestamo.id, corte):
                reales.append(
                    FlujoCajaFinanciero(
                        fecha=pago.fecha_real,
                        monto_ars=-money(pago.monto_moneda_contractual),
                        tipo="PAGO",
                        origen="REAL",
                        rol="deudor",
                        prestamo_id=prestamo.id,
                        prestamo_numero=prestamo.numero,
                        real=True,
                        tc_ars_usd=pago.tc_aplicado,
                        monto_usd_explicito=pago.monto_usd_ref,
                    )
                )
        return reales

    def _flujos_inversor_reales(
        self,
        participaciones,
        persona_id: int,
        corte: date,
        advertencias: list[str],
    ) -> list[FlujoCajaFinanciero]:
        """Reconstruye aportes y cobros históricos sin consultar SQLite aquí."""
        reales: list[FlujoCajaFinanciero] = []
        for participacion in participaciones:
            if participacion.fecha_aporte is not None and participacion.fecha_aporte <= corte:
                tc = participacion.tc_aporte
                if tc is None and participacion.capital_usd_ref:
                    tc = money(participacion.capital_aportado / participacion.capital_usd_ref)
                reales.append(
                    FlujoCajaFinanciero(
                        fecha=participacion.fecha_aporte,
                        monto_ars=-money(participacion.capital_aportado),
                        tipo="APORTE",
                        origen="REAL",
                        rol="inversor",
                        prestamo_id=participacion.prestamo_id,
                        prestamo_numero=self._consulta.numero_prestamo(
                            participacion.prestamo_id
                        ),
                        real=True,
                        tc_ars_usd=tc,
                    )
                )

        for cobro in self._consulta.cobros_de_inversor(persona_id, corte):
            pago_id = _pago_id_desde_metadata(cobro.metadata)
            prestamo_id = None
            fecha = cobro.fecha
            tc = None
            monto_usd_explicito = None
            numero = "—"

            if pago_id is not None:
                pago = self._consulta.pago_para_cobro(pago_id)
                if pago is not None:
                    prestamo_id = pago.prestamo_id
                    fecha = pago.fecha_real
                    tc = pago.tc_aplicado
                    monto_usd_explicito = pago.monto_usd_ref
                    numero = pago.prestamo_numero

            if prestamo_id is None:
                advertencias.append(
                    "Se encontró un cobro de inversor sin pago correlacionado; "
                    "se mantiene en el cashflow pero no puede asociarse a un préstamo."
                )
                prestamo_id = 0

            reales.append(
                FlujoCajaFinanciero(
                    fecha=fecha,
                    monto_ars=money(cobro.debe),
                    tipo="COBRO",
                    origen="REAL",
                    rol="inversor",
                    prestamo_id=prestamo_id,
                    prestamo_numero=numero,
                    real=True,
                    tc_ars_usd=tc,
                    monto_usd_explicito=monto_usd_explicito,
                )
            )
        return reales

    def _flujos_deudor_proyectados(
        self,
        prestamos,
        persona_id: int,
        corte: date,
    ) -> list[FlujoCajaFinanciero]:
        """Convierte cuotas pendientes en proyecciones, sin consultar SQL."""
        proyectados: list[FlujoCajaFinanciero] = []
        for prestamo in prestamos:
            version_id = self._consulta.version_activa(prestamo.id)
            if version_id is None:
                continue
            cuotas = self._consulta.cuotas_proyectadas(version_id, corte)
            for cuota in cuotas:
                monto = _saldo_cuota_proyectado(cuota)
                if monto <= ZERO:
                    continue
                proyectados.append(
                    FlujoCajaFinanciero(
                        fecha=cuota.fecha_vencimiento,
                        monto_ars=-monto,
                        tipo="CUOTA_PROYECTADA",
                        origen="PROYECCION_CONTRACTUAL",
                        rol="deudor",
                        prestamo_id=prestamo.id,
                        prestamo_numero=prestamo.numero,
                        real=False,
                    )
                )
        return proyectados

    def _flujos_inversor_proyectados(
        self,
        participaciones,
        persona_id: int,
        corte: date,
    ) -> list[FlujoCajaFinanciero]:
        """Proyecta la parte de cobro del inversor a partir de cuotas pendientes."""
        porcentaje_por_prestamo: dict[int, Decimal] = {}
        for participacion in participaciones:
            porcentaje_por_prestamo[participacion.prestamo_id] = money(
                porcentaje_por_prestamo.get(participacion.prestamo_id, ZERO)
                + participacion.porcentaje
            )

        proyectados: list[FlujoCajaFinanciero] = []
        for prestamo_id, porcentaje in porcentaje_por_prestamo.items():
            prestamo = self._consulta.prestamo_por_id(prestamo_id)
            if prestamo is None:
                continue
            version_id = self._consulta.version_activa(prestamo_id)
            if version_id is None:
                continue
            cuotas = self._consulta.cuotas_proyectadas(version_id, corte)
            for cuota in cuotas:
                monto = money(_saldo_cuota_proyectado(cuota) * porcentaje)
                if monto <= ZERO:
                    continue
                proyectados.append(
                    FlujoCajaFinanciero(
                        fecha=cuota.fecha_vencimiento,
                        monto_ars=monto,
                        tipo="COBRO_PROYECTADO",
                        origen="PROYECCION_CONTRACTUAL",
                        rol="inversor",
                        prestamo_id=prestamo.id,
                        prestamo_numero=prestamo.numero,
                        real=False,
                        # No inventamos un tipo de cambio futuro. La
                        # proyección USD se presenta mediante escenarios.
                        tc_ars_usd=None,
                    )
                )
        return proyectados

    def _capital_deudor_pendiente(self, prestamos) -> Decimal:
        """Suma el capital contractual pendiente en las cuotas que siguen abiertas."""
        total = ZERO
        for prestamo in prestamos:
            version_id = self._consulta.version_activa(prestamo.id)
            if version_id is None:
                continue
            for cuota in self._consulta.cuotas_pendientes_capital(version_id):
                total += _capital_pendiente_cuota(cuota)
        return money(total)


class ServicioAnalisisFinanciero:
    """Caso de uso de lectura para la UI."""

    def __init__(self, query: AnalisisFinancieroQuery) -> None:
        self._query = query

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesto: Decimal = Decimal("0.05"),
    ) -> ResultadoAnalisisFinanciero:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesto=inflacion_mensual_supuesto,
        )

    def escenarios_para_prestamo(self, prestamo_id: int) -> ResultadoEscenariosUI:
        return self._query.escenarios_para_prestamo(prestamo_id)


def _saldo_cuota_proyectado(fila: CuotaAnalisis) -> Decimal:
    pendiente = Decimal(str(fila.monto_pendiente or "0"))
    if pendiente > ZERO:
        return money(pendiente)
    if str(fila.estado) == "PENDIENTE" and not bool(fila.tuvo_pago_parcial):
        return money(
            Decimal(str(fila.interes_pendiente or "0"))
            + Decimal(str(fila.capital_pendiente or "0"))
            + Decimal(str(fila.mora_pendiente or "0"))
            or Decimal(str(fila.cuota))
        )
    return money(
        Decimal(str(fila.interes_pendiente or "0"))
        + Decimal(str(fila.capital_pendiente or "0"))
        + Decimal(str(fila.mora_pendiente or "0"))
    )


def _capital_pendiente_cuota(fila: CuotaAnalisis) -> Decimal:
    pendiente = Decimal(str(fila.capital_pendiente or "0"))
    if pendiente > ZERO:
        return money(pendiente)
    if str(fila.estado) == "PENDIENTE" and not bool(fila.tuvo_pago_parcial):
        return money(fila.capital)
    return ZERO


def _pago_id_desde_metadata(metadata) -> int | None:
    if not metadata:
        return None
    try:
        import json
        payload = json.loads(str(metadata))
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("pago_id") is None:
        return None
    try:
        pago_id = int(payload["pago_id"])
    except (TypeError, ValueError):
        return None
    return pago_id if pago_id > 0 else None


def _flujos_usd_completos(
    flujos: list[FlujoCajaFinanciero],
    rol: str,
) -> list[tuple[date, Decimal]] | None:
    """Devuelve flujos USD solo cuando la conversión es completa."""
    seleccionados = [f for f in flujos if f.rol == rol]
    if not seleccionados:
        return None
    if any(f.monto_usd is None for f in seleccionados):
        return None
    return [(f.fecha, f.monto_usd) for f in seleccionados if f.monto_usd is not None]


def _xirr_seguro(
    flujos: list[tuple[date, Decimal | None]] | None,
) -> Decimal | None:
    if flujos is None:
        return None
    normalizados = [
        (fecha, monto)
        for fecha, monto in flujos
        if monto is not None and monto != ZERO
    ]
    if len(normalizados) < 2:
        return None
    try:
        return xirr(normalizados)
    except Exception:
        return None


def _rendimiento_real_seguro(
    rendimiento: Decimal | None,
    inflacion_anual: Decimal,
) -> Decimal | None:
    if rendimiento is None:
        return None
    try:
        return calcular_rendimiento_real(rendimiento, inflacion_anual)
    except (ValueError, ZeroDivisionError):
        return None


def _meses_desde(desde: date, hasta: date) -> int:
    if hasta <= desde:
        return 0
    meses = (hasta.year - desde.year) * 12 + hasta.month - desde.month
    if hasta.day > desde.day:
        meses += 1
    return max(1, meses)
