"""Vista humana y de solo lectura del estado financiero de una persona.

Este módulo no calcula reglas financieras nuevas. Toma hechos y read models ya
existentes y los transforma en información sencilla para la persona que está
consultando su situación como deudora, inversora o ambas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from aplicacion.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoQuery,
)
from infraestructura.db import BaseDatos
from infraestructura.repositorios import ParticipacionRepo, PersonaRepo, PrestamoRepo


ZERO = Decimal("0.00")

ESTADOS_VISIBLES = {
    "BORRADOR": False,
    "ACTIVO": True,
    "EN_MORA": True,
    "FINALIZADO": True,
    "CANCELADO": True,
    "REFINANCIADO": True,
}

ESTADO_HUMANO = {
    "ACTIVO": "En curso",
    "EN_MORA": "Hay un atraso",
    "FINALIZADO": "Finalizado",
    "CANCELADO": "Cancelado",
    "REFINANCIADO": "Refinanciado",
}

ROL_HUMANO = {
    "DEUDOR": "Préstamo",
    "INVERSOR": "Inversión",
}


@dataclass(frozen=True)
class PosicionPrestamoHumana:
    """Una posición que la persona puede entender y consultar."""

    prestamo_id: int
    prestamo_numero: str
    rol: str
    destino: str | None
    estado: str
    estado_humano: str
    monto_principal: Decimal
    porcentaje_inversor: Decimal | None
    capital_pendiente: Decimal | None
    cobrado_real: Decimal
    proximo_monto: Decimal | None
    proxima_fecha: date | None
    cuotas_cerradas: int | None
    cuotas_totales: int | None
    advertencia: str | None = None

    @property
    def rol_humano(self) -> str:
        return ROL_HUMANO.get(self.rol, self.rol)

    @property
    def tiene_proximo_movimiento(self) -> bool:
        return self.proximo_monto is not None and self.proxima_fecha is not None


@dataclass(frozen=True)
class ActividadHumana:
    """Actividad real, expresada con lenguaje cotidiano."""

    fecha: date
    texto: str
    monto: Decimal
    prestamo_numero: str
    rol: str


@dataclass(frozen=True)
class ResumenHumanoPersona:
    """Read model amigable para una persona."""

    persona_id: int
    nombre: str
    roles: tuple[str, ...]
    posiciones: tuple[PosicionPrestamoHumana, ...]
    actividad_reciente: tuple[ActividadHumana, ...]
    capital_invertido: Decimal
    capital_pendiente_deuda: Decimal
    proximo_cobro: tuple[date, Decimal] | None
    proximo_pago: tuple[date, Decimal] | None
    advertencias: tuple[str, ...]


class VistaHumanaPersonaQuery:
    """Construye la vista humana sin escribir ni recalcular reglas financieras."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._personas = PersonaRepo(db)
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)
        self._detalle = DetalleFinancieroPrestamoQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
    ) -> ResumenHumanoPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")

        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        roles = tuple(sorted(set(self._personas.roles(persona_id))))

        analisis = self._analisis.obtener(
            persona_id,
            fecha_corte=corte,
        )

        reales_por_posicion = _agrupar_flujos(analisis.flujos_reales)
        proyectados_por_posicion = _agrupar_flujos(analisis.flujos_proyectados)

        participaciones_activas = [
            p
            for p in self._participaciones.por_inversor(persona_id)
            if p.estado == "ACTIVA"
        ]
        participaciones_por_prestamo: dict[int, list] = {}
        for participacion in participaciones_activas:
            participaciones_por_prestamo.setdefault(
                participacion.prestamo_id, []
            ).append(participacion)

        posiciones: list[PosicionPrestamoHumana] = []
        claves: set[tuple[int, str]] = set()

        for prestamo in self._prestamos.listar(deudor_id=persona_id):
            if not ESTADOS_VISIBLES.get(prestamo.estado, False):
                continue
            clave = (prestamo.id, "DEUDOR")
            claves.add(clave)
            posiciones.append(
                self._posicion_deudor(
                    prestamo.id,
                    reales_por_posicion.get(clave, ()),
                    proyectados_por_posicion.get(clave, ()),
                )
            )

        for prestamo_id, aportes in participaciones_por_prestamo.items():
            prestamo = self._prestamos.obtener(prestamo_id)
            if prestamo is None or not ESTADOS_VISIBLES.get(prestamo.estado, False):
                continue

            clave = (prestamo.id, "INVERSOR")
            if clave in claves:
                continue
            claves.add(clave)
            posiciones.append(
                self._posicion_inversor(
                    prestamo.id,
                    aportes,
                    reales_por_posicion.get(clave, ()),
                    proyectados_por_posicion.get(clave, ()),
                )
            )

        posiciones.sort(
            key=lambda p: (
                p.estado in {"FINALIZADO", "CANCELADO", "REFINANCIADO"},
                p.prestamo_numero,
                p.rol,
            )
        )

        actividad = tuple(
            sorted(
                (_actividad_desde_flujo(f) for f in analisis.flujos_reales),
                key=lambda x: (x.fecha, x.prestamo_numero),
                reverse=True,
            )[:8]
        )

        proximo_cobro = _proximo_movimiento(
            (
                (p.proxima_fecha, p.proximo_monto)
                for p in posiciones
                if p.rol == "INVERSOR" and p.proxima_fecha and p.proximo_monto
            )
        )
        proximo_pago = _proximo_movimiento(
            (
                (p.proxima_fecha, p.proximo_monto)
                for p in posiciones
                if p.rol == "DEUDOR" and p.proxima_fecha and p.proximo_monto
            )
        )

        nombre = getattr(persona, "nombre_completo", None) or (
            f"{persona.nombre} {persona.apellido}".strip()
        )

        return ResumenHumanoPersona(
            persona_id=persona.id,
            nombre=nombre,
            roles=roles,
            posiciones=tuple(posiciones),
            actividad_reciente=actividad,
            capital_invertido=analisis.resumen.capital_aportado_activo,
            capital_pendiente_deuda=analisis.resumen.capital_deudor_pendiente,
            proximo_cobro=proximo_cobro,
            proximo_pago=proximo_pago,
            advertencias=tuple(dict.fromkeys(analisis.advertencias)),
        )

    def _posicion_deudor(
        self,
        prestamo_id: int,
        reales: tuple[FlujoCajaFinanciero, ...],
        proyectados: tuple[FlujoCajaFinanciero, ...],
    ) -> PosicionPrestamoHumana:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {prestamo_id} no existe")

        detalle = _obtener_detalle_seguro(self._detalle, prestamo_id)
        proximo = _primero(proyectados)

        if detalle is None:
            return PosicionPrestamoHumana(
                prestamo_id=prestamo.id,
                prestamo_numero=prestamo.numero,
                rol="DEUDOR",
                destino=prestamo.destino,
                estado=prestamo.estado,
                estado_humano=ESTADO_HUMANO.get(prestamo.estado, prestamo.estado),
                monto_principal=prestamo.capital_original,
                porcentaje_inversor=None,
                capital_pendiente=None,
                cobrado_real=ZERO,
                proximo_monto=_monto_abs(proximo),
                proxima_fecha=proximo.fecha if proximo else None,
                cuotas_cerradas=None,
                cuotas_totales=None,
                advertencia="El detalle financiero todavía no está disponible para este préstamo.",
            )

        cuotas_cerradas = sum(c.estado == "PAGADA" for c in detalle.cuotas)

        return PosicionPrestamoHumana(
            prestamo_id=prestamo.id,
            prestamo_numero=prestamo.numero,
            rol="DEUDOR",
            destino=prestamo.destino,
            estado=prestamo.estado,
            estado_humano=ESTADO_HUMANO.get(prestamo.estado, prestamo.estado),
            monto_principal=detalle.resumen.capital_original,
            porcentaje_inversor=None,
            capital_pendiente=detalle.resumen.capital_pendiente,
            cobrado_real=ZERO,
            proximo_monto=_monto_abs(proximo),
            proxima_fecha=proximo.fecha if proximo else None,
            cuotas_cerradas=cuotas_cerradas,
            cuotas_totales=len(detalle.cuotas),
        )

    def _posicion_inversor(
        self,
        prestamo_id: int,
        aportes: list,
        reales: tuple[FlujoCajaFinanciero, ...],
        proyectados: tuple[FlujoCajaFinanciero, ...],
    ) -> PosicionPrestamoHumana:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {prestamo_id} no existe")

        aporte = sum((p.capital_aportado for p in aportes), ZERO)
        porcentaje = sum((p.porcentaje for p in aportes), ZERO) or None
        cobrado = sum(
            (f.monto_ars for f in reales if f.monto_ars > ZERO),
            ZERO,
        )
        proximo = _primero(proyectados)

        detalle = _obtener_detalle_seguro(self._detalle, prestamo_id)
        cuotas_cerradas = (
            sum(c.estado == "PAGADA" for c in detalle.cuotas)
            if detalle is not None
            else None
        )

        return PosicionPrestamoHumana(
            prestamo_id=prestamo.id,
            prestamo_numero=prestamo.numero,
            rol="INVERSOR",
            destino=prestamo.destino,
            estado=prestamo.estado,
            estado_humano=ESTADO_HUMANO.get(prestamo.estado, prestamo.estado),
            monto_principal=aporte,
            porcentaje_inversor=porcentaje,
            capital_pendiente=None,
            cobrado_real=cobrado,
            proximo_monto=_monto_abs(proximo),
            proxima_fecha=proximo.fecha if proximo else None,
            cuotas_cerradas=cuotas_cerradas,
            cuotas_totales=len(detalle.cuotas) if detalle is not None else None,
        )


def _agrupar_flujos(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> dict[tuple[int, str], tuple[FlujoCajaFinanciero, ...]]:
    agrupados: dict[tuple[int, str], list[FlujoCajaFinanciero]] = {}
    for flujo in flujos:
        if flujo.prestamo_id <= 0:
            continue
        clave = (flujo.prestamo_id, flujo.rol.upper())
        agrupados.setdefault(clave, []).append(flujo)
    return {k: tuple(v) for k, v in agrupados.items()}


def _actividad_desde_flujo(flujo: FlujoCajaFinanciero) -> ActividadHumana:
    if flujo.rol == "deudor":
        if flujo.tipo == "DESEMBOLSO":
            texto = "Recibiste el dinero del préstamo"
        elif flujo.tipo == "PAGO":
            texto = "Registraste un pago"
        else:
            texto = "Hubo un movimiento de tu préstamo"
    else:
        if flujo.tipo == "APORTE":
            texto = "Invertiste en un préstamo"
        elif flujo.tipo == "COBRO":
            texto = "Cobraste una cuota"
        else:
            texto = "Hubo un movimiento de tu inversión"

    return ActividadHumana(
        fecha=flujo.fecha,
        texto=texto,
        monto=abs(flujo.monto_ars),
        prestamo_numero=flujo.prestamo_numero,
        rol=flujo.rol.upper(),
    )


def _primero(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> FlujoCajaFinanciero | None:
    return min(flujos, key=lambda f: (f.fecha, f.tipo)) if flujos else None


def _monto_abs(flujo: FlujoCajaFinanciero | None) -> Decimal | None:
    return abs(flujo.monto_ars) if flujo is not None else None


def _proximo_movimiento(
    movimientos,
) -> tuple[date, Decimal] | None:
    validos = [(fecha, monto) for fecha, monto in movimientos if fecha and monto]
    return min(validos, key=lambda x: x[0]) if validos else None


def _obtener_detalle_seguro(query, prestamo_id: int):
    try:
        return query.obtener(prestamo_id)
    except ValueError:
        return None
