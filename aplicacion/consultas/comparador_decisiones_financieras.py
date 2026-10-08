"""Comparador de decisiones financieras sobre operaciones registradas.

M7 reúne información que ya existe en los read models financieros para
comparar dos o más operaciones registradas por una persona.

No crea contratos, no modifica datos y no inventa proyecciones: reutiliza
cashflows de AnalisisFinancieroQuery y el cálculo XIRR del dominio.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from dominio.analisis_cambiario import calcular_rendimiento_real
from dominio.licuacion import valor_real
from dominio.tipos import money
from dominio.xirr import xirr
from infraestructura.db import BaseDatos
from infraestructura.repositorios import ParticipacionRepo, PersonaRepo, PrestamoRepo

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class AlternativaDisponible:
    clave: str
    prestamo_id: int
    prestamo_numero: str
    destino: str | None
    rol: str
    estado: str
    etiqueta: str


@dataclass(frozen=True)
class AlternativaComparada:
    clave: str
    prestamo_id: int
    prestamo_numero: str
    destino: str | None
    rol: str
    estado: str
    moneda: str
    capital_referencia: Decimal
    tasa_anual: Decimal | None
    modalidad_tasa: str | None
    sistema: str
    convencion_dias: str
    fecha_inicio: date | None
    flujo_real_neto: Decimal
    flujo_futuro_neto: Decimal
    valor_real_futuro: Decimal
    rendimiento_anualizado: Decimal | None
    rendimiento_real: Decimal | None
    cantidad_flujos_reales: int
    cantidad_flujos_futuros: int


@dataclass(frozen=True)
class ComparacionDecisionesFinancieras:
    persona_id: int
    fecha_corte: date
    horizonte_meses: int
    inflacion_mensual_supuesto: Decimal
    alternativas: tuple[AlternativaComparada, ...]
    homogenea: bool
    motivos_no_homogeneidad: tuple[str, ...]

    @property
    def cantidad_alternativas(self) -> int:
        return len(self.alternativas)


class ComparadorDecisionesFinancierasQuery:
    """Construye una comparación explícita de operaciones."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._personas = PersonaRepo(db)
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)

    def listar_alternativas(self, persona_id: int) -> tuple[AlternativaDisponible, ...]:
        self._validar_persona(persona_id)

        roles_por_prestamo: dict[int, set[str]] = {}

        for prestamo in self._prestamos.listar(deudor_id=persona_id):
            if prestamo.estado not in {"BORRADOR", "ANULADO"}:
                roles_por_prestamo.setdefault(prestamo.id, set()).add("DEUDOR")

        for participacion in self._participaciones.por_inversor(persona_id):
            if participacion.estado != "ANULADA":
                roles_por_prestamo.setdefault(participacion.prestamo_id, set()).add("INVERSOR")

        resultado: list[AlternativaDisponible] = []
        for prestamo_id, roles in sorted(roles_por_prestamo.items()):
            prestamo = self._prestamos.obtener(prestamo_id)
            if prestamo is None:
                continue

            rol = next(iter(roles)) if len(roles) == 1 else "AMBOS"
            destino = prestamo.destino or "Sin destino"
            resultado.append(
                AlternativaDisponible(
                    clave=f"{prestamo.id}:{rol}",
                    prestamo_id=prestamo.id,
                    prestamo_numero=prestamo.numero,
                    destino=prestamo.destino,
                    rol=rol,
                    estado=prestamo.estado,
                    etiqueta=f"{prestamo.numero} · {rol.lower()} · {destino}",
                )
            )

        return tuple(resultado)

    def comparar(
        self,
        persona_id: int,
        claves: tuple[str, ...],
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
        inflacion_mensual_supuesto: Decimal = Decimal("0.05"),
    ) -> ComparacionDecisionesFinancieras:
        self._validar_persona(persona_id)

        claves_unicas = tuple(dict.fromkeys(claves))
        if len(claves_unicas) < 2:
            raise ValueError("Seleccioná al menos dos alternativas")
        if len(claves_unicas) > 6:
            raise ValueError("Podés comparar como máximo seis alternativas")
        if horizonte_meses < 1 or horizonte_meses > 60:
            raise ValueError("horizonte_meses debe estar entre 1 y 60")

        inflacion = Decimal(str(inflacion_mensual_supuesto))
        if inflacion <= Decimal("-1"):
            raise ValueError("La inflación mensual debe ser mayor a -100%")

        corte = fecha_corte or date.today()
        disponibles = {a.clave: a for a in self.listar_alternativas(persona_id)}
        faltantes = [clave for clave in claves_unicas if clave not in disponibles]
        if faltantes:
            raise ValueError("Una o más alternativas ya no están disponibles para esta persona")

        analisis = self._analisis.obtener(
            persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
        )

        alternativas = tuple(
            self._comparar_alternativa(
                persona_id,
                disponibles[clave],
                analisis.flujos_reales,
                analisis.flujos_proyectados,
                inflacion,
                corte,
                horizonte_meses,
            )
            for clave in claves_unicas
        )
        homogenea, motivos = _evaluar_homogeneidad(alternativas)

        return ComparacionDecisionesFinancieras(
            persona_id=persona_id,
            fecha_corte=corte,
            horizonte_meses=horizonte_meses,
            inflacion_mensual_supuesto=inflacion,
            alternativas=alternativas,
            homogenea=homogenea,
            motivos_no_homogeneidad=motivos,
        )

    def _comparar_alternativa(
        self,
        persona_id: int,
        disponible: AlternativaDisponible,
        flujos_reales: tuple[FlujoCajaFinanciero, ...],
        flujos_proyectados: tuple[FlujoCajaFinanciero, ...],
        inflacion: Decimal,
        corte: date,
        horizonte_meses: int,
    ) -> AlternativaComparada:
        prestamo = self._prestamos.obtener(disponible.prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {disponible.prestamo_id} no existe")

        info_tasa = self._prestamos.info_tasa_activa(disponible.prestamo_id)
        reales = tuple(
            flujo
            for flujo in flujos_reales
            if flujo.prestamo_id == disponible.prestamo_id
            and _flujo_pertenece_a_rol(flujo, disponible.rol)
        )
        fin = _fin_horizonte(corte, horizonte_meses)
        futuros = tuple(
            flujo
            for flujo in flujos_proyectados
            if flujo.prestamo_id == disponible.prestamo_id
            and _flujo_pertenece_a_rol(flujo, disponible.rol)
            and corte < flujo.fecha <= fin
        )

        rendimiento = None if disponible.rol == "AMBOS" else _xirr_seguro(reales)
        inflacion_anual = (Decimal("1") + inflacion) ** 12 - Decimal("1")
        rendimiento_real = _rendimiento_real_seguro(rendimiento, inflacion_anual)

        capital = prestamo.capital_original
        if disponible.rol == "INVERSOR":
            capital = money(
                sum(
                    (
                        p.capital_aportado
                        for p in self._participaciones.por_inversor(persona_id)
                        if p.prestamo_id == prestamo.id and p.estado != "ANULADA"
                    ),
                    ZERO,
                )
            )

        return AlternativaComparada(
            clave=disponible.clave,
            prestamo_id=prestamo.id,
            prestamo_numero=prestamo.numero,
            destino=prestamo.destino,
            rol=disponible.rol,
            estado=prestamo.estado,
            moneda=prestamo.moneda_contractual,
            capital_referencia=money(capital),
            tasa_anual=info_tasa["tasa_anual"] if info_tasa else None,
            modalidad_tasa=info_tasa["modalidad"] if info_tasa else None,
            sistema=prestamo.sistema,
            convencion_dias=prestamo.convencion_dias,
            fecha_inicio=prestamo.fecha_inicio,
            flujo_real_neto=money(sum((f.monto_ars for f in reales), ZERO)),
            flujo_futuro_neto=money(sum((f.monto_ars for f in futuros), ZERO)),
            valor_real_futuro=money(
                sum((_valor_real_flujo(f, corte, inflacion) for f in futuros), ZERO)
            ),
            rendimiento_anualizado=rendimiento,
            rendimiento_real=rendimiento_real,
            cantidad_flujos_reales=len(reales),
            cantidad_flujos_futuros=len(futuros),
        )

    def _validar_persona(self, persona_id: int) -> None:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if self._personas.obtener(persona_id) is None:
            raise ValueError(f"La persona {persona_id} no existe")


class ServicioComparadorDecisionesFinancieras:
    """Caso de uso de lectura para comparar decisiones."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = ComparadorDecisionesFinancierasQuery(db)

    def listar_alternativas(self, persona_id: int) -> tuple[AlternativaDisponible, ...]:
        return self._query.listar_alternativas(persona_id)

    def comparar(
        self,
        persona_id: int,
        claves: tuple[str, ...],
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
        inflacion_mensual_supuesto: Decimal = Decimal("0.05"),
    ) -> ComparacionDecisionesFinancieras:
        return self._query.comparar(
            persona_id,
            claves,
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte_meses,
            inflacion_mensual_supuesto=inflacion_mensual_supuesto,
        )


def _flujo_pertenece_a_rol(flujo: FlujoCajaFinanciero, rol: str) -> bool:
    return rol == "AMBOS" or flujo.rol.upper() == rol


def _valor_real_flujo(
    flujo: FlujoCajaFinanciero,
    corte: date,
    inflacion: Decimal,
) -> Decimal:
    meses = _meses_desde(corte, flujo.fecha)
    valor = valor_real(abs(flujo.monto_ars), inflacion, meses)
    return money(valor if flujo.monto_ars >= ZERO else -valor)


def _meses_desde(desde: date, hasta: date) -> int:
    if hasta <= desde:
        return 0
    meses = (hasta.year - desde.year) * 12 + hasta.month - desde.month
    if hasta.day > desde.day:
        meses += 1
    return max(1, meses)


def _fin_horizonte(corte: date, horizonte_meses: int) -> date:
    primer_mes = date(corte.year, corte.month, 1)
    siguiente = _sumar_meses(primer_mes, horizonte_meses + 1)
    return siguiente - timedelta(days=1)


def _sumar_meses(fecha: date, cantidad: int) -> date:
    indice = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def _xirr_seguro(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> Decimal | None:
    normalizados = [
        (flujo.fecha, flujo.monto_ars)
        for flujo in flujos
        if flujo.monto_ars != ZERO
    ]
    if len(normalizados) < 2:
        return None
    if not any(monto < ZERO for _, monto in normalizados):
        return None
    if not any(monto > ZERO for _, monto in normalizados):
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


def _evaluar_homogeneidad(
    alternativas: tuple[AlternativaComparada, ...],
) -> tuple[bool, tuple[str, ...]]:
    if not alternativas:
        return False, ("No hay alternativas seleccionadas.",)

    referencia = alternativas[0]
    motivos: list[str] = []

    if any(a.rol != referencia.rol for a in alternativas[1:]):
        motivos.append("Las alternativas mezclan roles de inversor y deudor.")
    if any(a.moneda != referencia.moneda for a in alternativas[1:]):
        motivos.append("Las alternativas usan monedas contractuales diferentes.")
    if any(a.sistema != referencia.sistema for a in alternativas[1:]):
        motivos.append("Las alternativas usan sistemas de amortización diferentes.")
    if any(a.convencion_dias != referencia.convencion_dias for a in alternativas[1:]):
        motivos.append("Las alternativas usan convenciones de días diferentes.")
    if any(a.modalidad_tasa != referencia.modalidad_tasa for a in alternativas[1:]):
        motivos.append("Las alternativas usan modalidades de tasa diferentes.")

    return not motivos, tuple(motivos)
