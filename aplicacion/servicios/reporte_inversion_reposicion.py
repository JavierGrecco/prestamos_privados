"""Exportación de hechos de un plan de reposición e inversión.

Este reporte es deliberadamente independiente de los reportes por persona:
un plan interno no es un préstamo contractual y sus movimientos no deben
sumarse automáticamente a la posición financiera personal.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dominio import ErrorValidacion
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PlanesReposicionRepo
from infraestructura.repositorios.modelos import (
    AporteReposicion,
    FlujoInversionReposicion,
    PlanReposicionPersistido,
    ResumenRendimientoInversion,
    ValoracionInversionReposicion,
)


_MAX_REGISTROS = 100
_ETIQUETAS_FLUJO = {
    "APORTE_INVERSION": "Aporte destinado a inversión",
    "RESCATE": "Rescate de inversión",
    "DISTRIBUCION": "Distribución cobrada",
    "COSTO_IMPUESTO_EXTERNO": "Costo/impuesto externo",
}

# Convención de signos aplicada por el cálculo de XIRR: el monto original se
# conserva positivo en el registro, y el tipo de movimiento determina su signo.
_DIRECCION_XIRR = {
    "APORTE_INVERSION": "SALIDA_NEGATIVA",
    "RESCATE": "ENTRADA_POSITIVA",
    "DISTRIBUCION": "ENTRADA_POSITIVA",
    "COSTO_IMPUESTO_EXTERNO": "SALIDA_NEGATIVA",
}
_DIRECCION_XIRR_HUMANA = {
    "SALIDA_NEGATIVA": "salida de dinero (flujo negativo)",
    "ENTRADA_POSITIVA": "entrada de dinero (flujo positivo)",
}


@dataclass(frozen=True, slots=True)
class ReporteInversionReposicion:
    """Fotografía de solo lectura de un plan y su historial declarado."""

    plan: PlanReposicionPersistido
    fecha_corte: date
    version_sha256: str
    aportes_reposicion: tuple[AporteReposicion, ...]
    flujos_inversion: tuple[FlujoInversionReposicion, ...]
    valuaciones: tuple[ValoracionInversionReposicion, ...]
    resumen: ResumenRendimientoInversion

    @property
    def total_aportes_reposicion_ars(self) -> Decimal:
        return sum(
            (aporte.monto_ars for aporte in self.aportes_reposicion),
            Decimal("0.00"),
        )

    @property
    def total_aportes_reposicion_usd_ref(self) -> Decimal:
        return sum(
            (aporte.equivalente_usd for aporte in self.aportes_reposicion),
            Decimal("0.00"),
        )


class ServicioReporteInversionReposicion:
    """Genera reportes legibles y exportables sin escribir en la base."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._repo = PlanesReposicionRepo(db)

    def obtener(self, plan_id: int) -> ReporteInversionReposicion:
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        plan = self._repo.obtener_plan(plan_id)
        if plan is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        if plan.tipo_plan != "REPOSICION_INTERNA":
            raise ErrorValidacion(
                "Este informe solo corresponde a planes internos de reposición"
            )
        if plan.ultima_version < 1:
            raise ErrorValidacion(
                "El plan no tiene una versión guardada e íntegra para informar"
            )

        version = self._repo.obtener_version(plan.id, plan.ultima_version)
        if version is None or not self._repo.verificar_version(version):
            raise ErrorValidacion(
                "No se puede exportar el plan porque falló la integridad de su última versión"
            )

        # No exportar silenciosamente un historial parcial. Si crece más allá
        # del límite de cálculo auditado, primero se debe ampliar el modelo.
        conteos = {
            "aportes de reposición": self._contar("aportes_reposicion", plan.id),
            "flujos de inversión": self._contar("flujos_inversion_reposicion", plan.id),
            "valuaciones": self._contar("valuaciones_inversion_reposicion", plan.id),
        }
        exceso = [nombre for nombre, cantidad in conteos.items() if cantidad > _MAX_REGISTROS]
        if exceso:
            detalle = ", ".join(exceso)
            raise ErrorValidacion(
                "No se exportó el informe completo porque el plan supera el límite "
                f"de {_MAX_REGISTROS} registros para: {detalle}. No se generó un CSV parcial."
            )

        aportes = self._repo.listar_aportes(plan.id, limite=_MAX_REGISTROS)
        aportes_completos = []
        for aporte in aportes:
            completo = self._repo.obtener_aporte(aporte.id)
            if completo is None or not self._repo.verificar_aporte(completo):
                raise ErrorValidacion(
                    f"No se puede exportar: falló la integridad del aporte #{aporte.id}"
                )
            aportes_completos.append(completo)

        flujos = tuple(self._repo.listar_flujos_inversion(plan.id, limite=_MAX_REGISTROS))
        valuaciones = tuple(
            self._repo.listar_valuaciones_inversion(plan.id, limite=_MAX_REGISTROS)
        )
        # El resumen también verifica los hashes de cada flujo y valuación y
        # aplica el criterio conservador de XIRR. No sustituirlo por un
        # cálculo distinto dentro de la capa de reportes.
        resumen = self._repo.resumen_rendimiento_inversion(plan.id)

        corte = date.today()
        return ReporteInversionReposicion(
            plan=plan,
            fecha_corte=corte,
            version_sha256=version.snapshot_sha256,
            aportes_reposicion=tuple(
                sorted(aportes_completos, key=lambda item: (item.fecha_aporte, item.id))
            ),
            flujos_inversion=tuple(flujos),
            valuaciones=tuple(
                sorted(valuaciones, key=lambda item: (item.fecha_valuacion, item.id))
            ),
            resumen=resumen,
        )

    def markdown(self, reporte: ReporteInversionReposicion) -> str:
        plan = reporte.plan
        resumen = reporte.resumen
        lineas = [
            "# Reporte del plan de reposición e inversión",
            "",
            f"**Plan:** {plan.nombre} (#{plan.id})",
            f"**Estado:** {plan.estado}",
            f"**Fecha de corte:** {reporte.fecha_corte.isoformat()}",
            f"**Desembolso/compra de referencia:** {plan.fecha_desembolso.isoformat()}",
            f"**Capital original:** {_decimal(plan.capital_original_ars)} ARS",
            f"**Versión del plan:** {plan.ultima_version}",
            f"**SHA-256 de la última versión:** {reporte.version_sha256}",
            "",
            "> Informe a nivel de plan interno, separado de la posición personal M2 y del rendimiento histórico M5 de préstamos. No sumar estas cifras a esos reportes sin una conciliación explícita que evite doble conteo.",
            "",
            "## Aportes destinados a reponer capital",
            "",
            f"- Aportes registrados: **{len(reporte.aportes_reposicion)}**",
            f"- Total aportado: **{_decimal(reporte.total_aportes_reposicion_ars)} ARS**",
            f"- Equivalente de referencia de esos aportes: **{_decimal(reporte.total_aportes_reposicion_usd_ref)} USD ref.**",
            "- Estos aportes registran dinero reservado/destinado a reposición; no son por sí mismos compra de dólares, aportes a una cartera, pago de cuota ni ganancia.",
            "",
            "## Inversión declarada y rendimiento reportado",
            "",
            f"- Aportes a inversión: **{_decimal(resumen.aportes_inversion_usd_ref)} USD ref.**",
            f"- Rescates y distribuciones: **{_decimal(resumen.cobros_y_rescates_usd_ref)} USD ref.**",
            f"- Costos externos: **{_decimal(resumen.costos_externos_usd_ref)} USD ref.**",
            f"- Última valuación del saldo que sigue invertido: **{_decimal_opcional(resumen.valor_mercado_final_usd_ref)} USD ref.**",
            f"- Resultado total reportado: **{_decimal_opcional(resumen.resultado_total_usd_ref)} USD ref.**",
            f"- XIRR anual reportada: **{_porcentaje_opcional(resumen.xirr_anual)}**",
            f"- Estado del cálculo XIRR: {resumen.mensaje_xirr}",
            "",
            "Una valuación del saldo abierto no es una ganancia realizada. El resultado total reportado combina rescates/distribuciones con la última valuación, y descuenta aportes y costos externos registrados.",
            "",
            "## Historial de aportes de reposición",
            "",
        ]
        if not reporte.aportes_reposicion:
            lineas.append("No hay aportes destinados a reposición registrados.")
        for item in reporte.aportes_reposicion:
            lineas.append(
                f"- {item.fecha_aporte.isoformat()} — ARS {_decimal(item.monto_ars)} "
                f"(USD ref. {_decimal(item.equivalente_usd)}; cotización {_decimal(item.cotizacion_ars_por_usd)}; "
                f"{item.naturaleza_cotizacion}; fuente {_texto(item.fuente_cotizacion)}; "
                f"ref. {_texto(item.referencia)}; nota {_texto(item.nota)}; SHA-256 {item.snapshot_sha256})."
            )

        lineas.extend(["", "## Historial de movimientos de inversión", ""])
        if not reporte.flujos_inversion:
            lineas.append("No hay movimientos de inversión registrados.")
        for item in reporte.flujos_inversion:
            lineas.append(
                f"- {item.fecha_flujo.isoformat()} — {_ETIQUETAS_FLUJO.get(item.tipo_flujo, item.tipo_flujo)}: "
                f"{item.moneda} {_decimal(item.monto_original)} "
                f"(dirección XIRR: {_DIRECCION_XIRR_HUMANA.get(_DIRECCION_XIRR.get(item.tipo_flujo, ''), 'no determinada')}; "
                f"USD ref. {_decimal(item.equivalente_usd)}; {_texto(item.naturaleza_cotizacion)}; "
                f"fuente {_texto(item.fuente_cotizacion)}; ref. {_texto(item.referencia)}; "
                f"nota {_texto(item.nota)}; SHA-256 {item.snapshot_sha256})."
            )

        lineas.extend(["", "## Historial de valuaciones", ""])
        if not reporte.valuaciones:
            lineas.append("No hay valuaciones registradas.")
        for item in reporte.valuaciones:
            lineas.append(
                f"- {item.fecha_valuacion.isoformat()} — saldo valuado: {item.moneda} "
                f"{_decimal(item.valor_original)} (USD ref. {_decimal(item.equivalente_usd)}; "
                f"{_texto(item.naturaleza_cotizacion)}; fuente {_texto(item.fuente_cotizacion)}; "
                f"ref. {_texto(item.referencia)}; nota {_texto(item.nota)}; "
                f"SHA-256 {item.snapshot_sha256})."
            )

        lineas.extend([
            "",
            "## Alcance y advertencias",
            "",
            "- Flujos, fuentes y valuaciones son declarados por la persona que carga el dato; no están conciliados automáticamente con un broker ni comprobados por una fuente de mercado.",
            "- El equivalente USD de importes en ARS es una referencia basada en la cotización guardada por fecha; no prueba tenencia ni compra efectiva de dólares.",
            "- Los costos externos deben incluirse solo si se pagaron fuera de la cartera y no están ya descontados de la valuación.",
            "- El informe es de solo lectura: no crea ni modifica contratos, cuotas, pagos, movimientos ni valores guardados.",
        ])
        return "\n".join(lineas)

    def json(self, reporte: ReporteInversionReposicion) -> str:
        return json.dumps(
            self._a_dict(reporte),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def csv_detalle(self, reporte: ReporteInversionReposicion) -> str:
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow([
            "seccion", "fecha", "tipo", "direccion_xirr", "moneda",
            "importe_original", "usd_referencia", "naturaleza", "fuente",
            "referencia", "nota", "registro_id", "sha256", "creado_por",
        ])
        writer.writerows(self._filas_csv(reporte))
        return buffer.getvalue()

    def _contar(self, tabla: str, plan_id: int) -> int:
        # Los nombres de tabla vienen de literales internos, no de entrada externa.
        fila = self._db.consultar_uno(
            f"SELECT COUNT(*) AS cantidad FROM {tabla} WHERE plan_id = ?",
            (plan_id,),
        )
        return int(fila["cantidad"])

    @staticmethod
    def _a_dict(reporte: ReporteInversionReposicion) -> dict:
        plan = reporte.plan
        resumen = reporte.resumen
        return {
            "tipo_reporte": "PLAN_INTERNO_REPOSICION_INVERSION",
            "fecha_corte": reporte.fecha_corte.isoformat(),
            "alcance": {
                "separado_de_posicion_personal": True,
                "usd_es_referencia": True,
                "valuacion_abierta_es_ganancia_realizada": False,
                "datos_declarados_sin_conciliacion_automatica": True,
            },
            "plan": {
                "id": plan.id,
                "nombre": plan.nombre,
                "tipo_plan": plan.tipo_plan,
                "estado": plan.estado,
                "fecha_desembolso": plan.fecha_desembolso.isoformat(),
                "capital_original_ars": str(plan.capital_original_ars),
                "version_actual": plan.ultima_version,
                "version_sha256": reporte.version_sha256,
            },
            "resumen": {
                "cantidad_aportes_reposicion": len(reporte.aportes_reposicion),
                "total_aportes_reposicion_ars": str(reporte.total_aportes_reposicion_ars),
                "total_aportes_reposicion_usd_ref": str(reporte.total_aportes_reposicion_usd_ref),
                "cantidad_flujos_inversion": resumen.cantidad_flujos,
                "cantidad_valuaciones": resumen.cantidad_valuaciones,
                "aportes_inversion_usd_ref": str(resumen.aportes_inversion_usd_ref),
                "cobros_y_rescates_usd_ref": str(resumen.cobros_y_rescates_usd_ref),
                "costos_externos_usd_ref": str(resumen.costos_externos_usd_ref),
                "valor_mercado_final_usd_ref": _str_opcional(resumen.valor_mercado_final_usd_ref),
                "resultado_total_usd_ref": _str_opcional(resumen.resultado_total_usd_ref),
                "xirr_anual": _str_opcional(resumen.xirr_anual),
                "mensaje_xirr": resumen.mensaje_xirr,
            },
            "aportes_reposicion": [
                {
                    "id": x.id,
                    "fecha": x.fecha_aporte.isoformat(),
                    "monto_ars": str(x.monto_ars),
                    "cotizacion_ars_por_usd": str(x.cotizacion_ars_por_usd),
                    "equivalente_usd_ref": str(x.equivalente_usd),
                    "naturaleza_cotizacion": x.naturaleza_cotizacion,
                    "fuente": x.fuente_cotizacion,
                    "referencia": x.referencia,
                    "nota": x.nota,
                    "sha256": x.snapshot_sha256,
                    "creado_por": x.creado_por,
                    "creado_en": x.creado_en,
                }
                for x in reporte.aportes_reposicion
            ],
            "flujos_inversion": [
                {
                    "id": x.id,
                    "fecha": x.fecha_flujo.isoformat(),
                    "tipo": x.tipo_flujo,
                    "direccion_xirr": _DIRECCION_XIRR.get(x.tipo_flujo),
                    "moneda": x.moneda,
                    "monto_original": str(x.monto_original),
                    "cotizacion_ars_por_usd": _str_opcional(x.cotizacion_ars_por_usd),
                    "equivalente_usd_ref": str(x.equivalente_usd),
                    "naturaleza_cotizacion": x.naturaleza_cotizacion,
                    "fuente": x.fuente_cotizacion,
                    "referencia": x.referencia,
                    "nota": x.nota,
                    "sha256": x.snapshot_sha256,
                    "creado_por": x.creado_por,
                    "creado_en": x.creado_en,
                }
                for x in reporte.flujos_inversion
            ],
            "valuaciones": [
                {
                    "id": x.id,
                    "fecha": x.fecha_valuacion.isoformat(),
                    "moneda": x.moneda,
                    "valor_original": str(x.valor_original),
                    "cotizacion_ars_por_usd": _str_opcional(x.cotizacion_ars_por_usd),
                    "equivalente_usd_ref": str(x.equivalente_usd),
                    "naturaleza_cotizacion": x.naturaleza_cotizacion,
                    "fuente": x.fuente_cotizacion,
                    "referencia": x.referencia,
                    "nota": x.nota,
                    "sha256": x.snapshot_sha256,
                    "creado_por": x.creado_por,
                    "creado_en": x.creado_en,
                }
                for x in reporte.valuaciones
            ],
        }

    @staticmethod
    def _filas_csv(reporte: ReporteInversionReposicion) -> list[list[str]]:
        resumen = reporte.resumen
        filas = [
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Capital original del plan", "",
             "ARS", str(reporte.plan.capital_original_ars), "", "Referencia del plan", "", "",
             "", "", reporte.version_sha256, reporte.plan.creado_por],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Total aportes destinados a reposición", "",
             "ARS", str(reporte.total_aportes_reposicion_ars), str(reporte.total_aportes_reposicion_usd_ref),
             "No es flujo de inversión", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Aportes a inversión", "",
             "USD ref.", str(resumen.aportes_inversion_usd_ref), str(resumen.aportes_inversion_usd_ref),
             "Flujos declarados", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Rescates y distribuciones", "",
             "USD ref.", str(resumen.cobros_y_rescates_usd_ref), str(resumen.cobros_y_rescates_usd_ref),
             "Cobros declarados", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Costos externos", "",
             "USD ref.", str(resumen.costos_externos_usd_ref), str(resumen.costos_externos_usd_ref),
             "Si no se reflejan ya en la valuación", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Última valuación", "",
             "USD ref.", _str_opcional(resumen.valor_mercado_final_usd_ref), _str_opcional(resumen.valor_mercado_final_usd_ref),
             "No es ganancia realizada", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "Resultado total reportado", "",
             "USD ref.", _str_opcional(resumen.resultado_total_usd_ref), _str_opcional(resumen.resultado_total_usd_ref),
             "No equivale necesariamente a ganancia realizada", "", "", "", "", "", ""],
            ["RESUMEN", reporte.fecha_corte.isoformat(), "XIRR anual reportada", "",
             "tasa", _str_opcional(resumen.xirr_anual), "", resumen.mensaje_xirr, "", "", "", "", "", ""],
        ]
        for x in reporte.aportes_reposicion:
            filas.append([
                "APORTE_REPOSICION", x.fecha_aporte.isoformat(), "Aporte destinado a reposición",
                "", "ARS", str(x.monto_ars), str(x.equivalente_usd), x.naturaleza_cotizacion,
                x.fuente_cotizacion or "", x.referencia or "", x.nota or "", str(x.id),
                x.snapshot_sha256, x.creado_por,
            ])
        for x in reporte.flujos_inversion:
            filas.append([
                "FLUJO_INVERSION", x.fecha_flujo.isoformat(),
                _ETIQUETAS_FLUJO.get(x.tipo_flujo, x.tipo_flujo),
                _DIRECCION_XIRR.get(x.tipo_flujo, ""), x.moneda,
                str(x.monto_original), str(x.equivalente_usd), x.naturaleza_cotizacion,
                x.fuente_cotizacion or "", x.referencia or "", x.nota or "", str(x.id),
                x.snapshot_sha256, x.creado_por,
            ])
        for x in reporte.valuaciones:
            filas.append([
                "VALUACION", x.fecha_valuacion.isoformat(), "Valor del saldo que sigue invertido",
                "", x.moneda, str(x.valor_original), str(x.equivalente_usd),
                "VALUACION_NO_REALIZADA", x.fuente_cotizacion or "", x.referencia or "",
                x.nota or "", str(x.id), x.snapshot_sha256, x.creado_por,
            ])
        # Neutralizar fórmulas de hoja de cálculo en campos textuales declarados
        # por el usuario (fuentes, referencias, notas y autor). Los importes se
        # conservan como números canónicos sin prefijos para permitir su análisis.
        columnas_texto = (2, 3, 7, 8, 9, 10, 13)
        for fila in filas:
            for indice in columnas_texto:
                fila[indice] = _texto_csv_seguro(fila[indice])
        return filas


def _texto_csv_seguro(valor: str | None) -> str:
    """Evita fórmulas de hoja de cálculo dentro de texto libre exportado a CSV."""
    texto = "" if valor is None else str(valor)
    sin_espacios = texto.lstrip(" \t\r\n")
    if texto and (texto[0] in "\t\r\n" or sin_espacios.startswith(("=", "+", "-", "@"))):
        return "'" + texto
    return texto

def _decimal(valor: Decimal) -> str:
    """Formato humano es-AR; JSON y CSV conservan el decimal canónico."""
    texto = format(abs(valor), "f")
    entero, separador, fraccion = texto.partition(".")
    entero_agrupado = f"{int(entero):,}".replace(",", ".")
    resultado = entero_agrupado + ("," + fraccion if separador else "")
    return ("-" if valor < 0 else "") + resultado


def _decimal_opcional(valor: Decimal | None) -> str:
    return "No disponible" if valor is None else _decimal(valor)


def _str_opcional(valor: Decimal | None) -> str | None:
    return None if valor is None else _decimal(valor)


def _porcentaje_opcional(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    porcentaje = (valor * Decimal("100")).quantize(Decimal("0.01"))
    return f"{_decimal(porcentaje)}%"


def _texto(valor: str | None) -> str:
    return (valor or "sin dato").replace("\n", " ").replace("\r", " ")
