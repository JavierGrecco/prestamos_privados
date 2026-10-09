"""Componente de simulación de reposición de capital en unidades USD.

La unidad USD es una referencia económica del escenario. El componente no
crea contratos ni registra operaciones cambiarias/pagos reales.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

import streamlit as st
from dateutil.relativedelta import relativedelta

from dominio import (
    CotizacionUnidad,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    TratamientoCarencia,
    ConvencionDias,
    simular_unidad_usd,
)


TRATAMIENTOS = (
    TratamientoCarencia.SIN_INTERES,
    TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA,
    TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
)
ETIQUETAS_TRATAMIENTO = {
    TratamientoCarencia.SIN_INTERES: "Sin interés durante la carencia",
    TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA: (
        "Interés simple diferido a la primera cuota"
    ),
    TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO: (
        "Interés simple distribuido entre las cuotas"
    ),
}


def _decimal_entrada(valor: str, nombre: str) -> Decimal:
    texto = valor.strip().replace(" ", "")
    if not texto:
        raise ErrorValidacion(f"Completá {nombre}.")
    if "," in texto and "." in texto:
        # Convención local: punto para miles y coma decimal.
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation as exc:
        raise ErrorValidacion(f"{nombre} debe ser un número válido.") from exc
    if not numero.is_finite():
        raise ErrorValidacion(f"{nombre} debe ser un número finito.")
    return numero


def _dinero(valor: Decimal | None, unidad: str) -> str:
    if valor is None:
        return "Incompleto"
    entero, centavos = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    signo = "-" if valor < 0 else ""
    return f"{signo}{unidad} {entero},{centavos}"


def _porcentaje(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    return f"{(valor * Decimal('100')):.2f}%"


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def _registro_a_fecha(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if hasattr(valor, "to_pydatetime"):
        return valor.to_pydatetime().date()
    raise ErrorValidacion("Cada cotización debe estar asociada a una fecha válida.")


def _exportar_csv(resultado) -> bytes:
    salida = StringIO(newline="")
    campos = [
        "cuota", "fecha_vencimiento", "capital_inicial_usd",
        "interes_periodo_usd", "amortizacion_capital_usd",
        "interes_carencia_usd", "importe_total_usd",
        "cotizacion_ars_por_usd", "fuente_cotizacion", "lado_cotizacion",
        "naturaleza_cotizacion", "equivalente_ars", "saldo_capital_usd",
    ]
    escritor = csv.DictWriter(
        salida, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    for cuota in resultado.cuotas:
        cot = cuota.cotizacion
        escritor.writerow({
            "cuota": cuota.numero,
            "fecha_vencimiento": cuota.fecha_vencimiento.isoformat(),
            "capital_inicial_usd": str(cuota.capital_inicial_usd),
            "interes_periodo_usd": str(cuota.interes_periodo_usd),
            "amortizacion_capital_usd": str(cuota.amortizacion_capital_usd),
            "interes_carencia_usd": str(cuota.interes_carencia_usd),
            "importe_total_usd": str(cuota.importe_total_usd),
            "cotizacion_ars_por_usd": "" if cot is None else str(cot.ars_por_usd),
            "fuente_cotizacion": "" if cot is None else cot.fuente,
            "lado_cotizacion": "" if cot is None else cot.lado,
            "naturaleza_cotizacion": "" if cot is None else cot.naturaleza,
            "equivalente_ars": (
                "" if cuota.equivalente_ars is None else str(cuota.equivalente_ars)
            ),
            "saldo_capital_usd": str(cuota.saldo_capital_usd),
        })
    return ("\ufeff" + salida.getvalue()).encode("utf-8")


def render(
    *,
    capital_desembolso_ars: Decimal,
    fecha_desembolso: date,
    meses_carencia: int,
    plazo_amortizacion_meses: int,
    sistema: SistemaAmortizacion,
    convencion: ConvencionDias,
) -> None:
    st.divider()
    st.header("Reposición del capital con rendimiento objetivo en USD")
    st.caption(
        "Este escenario parte del capital en pesos utilizado para el auto, lo "
        "convierte a unidades USD en la fecha de origen y estima la recuperación "
        "del capital más un rendimiento objetivo en esa unidad."
    )
    st.info(
        "Objetivo completo: reponer el capital, conservar su referencia de valor "
        "en USD y sumar un rendimiento por el tiempo transcurrido. Elegí la tasa "
        "según una inversión alternativa concreta; el sistema no predice el dólar "
        "ni garantiza el rendimiento."
    )
    with st.expander("Por qué el autopréstamo también tiene un costo", expanded=True):
        st.write(
            "En un autopréstamo, la tasa representa el costo de oportunidad del "
            "dinero que retiraste de tus inversiones. El plan calcula cuánto "
            "deberías reponer y qué rendimiento objetivo querés atribuirle a ese "
            "capital. Es una métrica interna para disciplinar el ahorro: no es un "
            "ingreso externo ni una ganancia consolidada del hogar."
        )

    with st.form("sim_usd_formulario", clear_on_submit=False):
        st.subheader("Capital y rendimiento objetivo")
        a, b = st.columns(2)
        with a:
            capital_origen = st.text_input(
                "Capital utilizado (ARS)",
                value=f"{capital_desembolso_ars:.2f}",
                key="sim_usd_capital_ars",
                help="Importe efectivamente destinado a la compra del vehículo.",
            )
            tc_inicial_texto = st.text_input(
                "Cotización inicial (ARS por USD)",
                value="",
                key="sim_usd_tc_inicial",
                placeholder="Ingresá la cotización de la fecha de origen",
            )
            fecha_tc_inicial = st.date_input(
                "Fecha de la cotización inicial",
                value=fecha_desembolso,
                max_value=fecha_desembolso,
                key="sim_usd_fecha_tc_inicial",
            )
            fuente_tc_inicial = st.text_input(
                "Fuente / instrumento de la cotización inicial",
                value="",
                key="sim_usd_fuente_tc_inicial",
                placeholder="Ej.: bono/instrumento, proveedor o serie",
            )
            referencia_tc_inicial = st.text_input(
                "Referencia o evidencia (opcional)",
                value="",
                key="sim_usd_referencia_tc_inicial",
            )
        with b:
            tasa_usd_texto = st.text_input(
                "Rendimiento objetivo anual en USD (%)",
                value="",
                key="sim_usd_tasa_objetivo",
                placeholder="Ingresá la tasa del benchmark elegido",
                help=(
                    "Debe representar la alternativa que comparás con retirar el "
                    "capital. No es la tasa argentina en pesos ni una predicción."
                ),
            )
            modalidad_texto = st.selectbox(
                "Modalidad de la tasa en USD",
                options=["TEA", "TNA"],
                format_func=lambda x: (
                    "TEA — rendimiento efectivo anual"
                    if x == "TEA" else "TNA — tasa nominal anual"
                ),
                key="sim_usd_modalidad",
            )
            lado_tc_inicial = st.selectbox(
                "Lado de la cotización inicial",
                options=["VENDEDOR", "COMPRADOR", "OTRO"],
                format_func=lambda x: {
                    "VENDEDOR": "Vendedor (costo de comprar USD)",
                    "COMPRADOR": "Comprador",
                    "OTRO": "Otro / definido manualmente",
                }[x],
                key="sim_usd_lado_tc_inicial",
            )
            naturaleza_inicial = st.selectbox(
                "Tipo de dato inicial",
                options=["OBSERVADA", "PROYECTADA"],
                key="sim_usd_naturaleza_inicial",
            )
            tratamiento_texto = st.selectbox(
                "Tratamiento del interés durante la carencia",
                options=[t.value for t in TRATAMIENTOS],
                format_func=lambda x: ETIQUETAS_TRATAMIENTO[TratamientoCarencia(x)],
                key="sim_usd_tratamiento",
            )
        enviar = st.form_submit_button(
            "Calcular plan USD y sus equivalentes en pesos",
            type="primary",
        )

    # En Streamlit la sección se recalcula cuando se confirma el formulario,
    # evitando ejecutar el simulador ante cada tecla editada.
    if not enviar:
        st.caption(
            f"El escenario reutiliza el calendario mostrado arriba: desembolso "
            f"{_fecha(fecha_desembolso)}, carencia de {meses_carencia} meses y "
            f"{plazo_amortizacion_meses} cuotas posteriores."
        )
        return

    try:
        capital_ars = _decimal_entrada(capital_origen, "el capital en ARS")
        cotizacion_inicial_valor = _decimal_entrada(
            tc_inicial_texto, "la cotización inicial ARS/USD"
        )
        tasa_usd_pct = _decimal_entrada(
            tasa_usd_texto, "el rendimiento objetivo anual en USD"
        )
        if capital_ars <= 0:
            raise ErrorValidacion("El capital en ARS debe ser mayor a cero.")
        if cotizacion_inicial_valor <= 0:
            raise ErrorValidacion("La cotización inicial debe ser mayor a cero.")
        if tasa_usd_pct <= 0:
            raise ErrorValidacion(
                "Para este escenario de recuperación más ganancia, la tasa objetivo "
                "USD debe ser positiva. Usá otro escenario si querés comparar 0%."
            )
        if not fuente_tc_inicial.strip():
            raise ErrorValidacion(
                "Completá la fuente/instrumento de la cotización inicial."
            )
        if fecha_tc_inicial > fecha_desembolso:
            raise ErrorValidacion(
                "La cotización inicial no puede ser posterior al desembolso."
            )

        cotizacion_inicial = CotizacionUnidad(
            fecha_cotizacion=fecha_tc_inicial,
            ars_por_usd=cotizacion_inicial_valor,
            fuente=fuente_tc_inicial.strip(),
            lado=lado_tc_inicial,
            naturaleza=naturaleza_inicial,
            referencia=referencia_tc_inicial.strip() or None,
        )
        tasa_usd = tasa_usd_pct / Decimal("100")
        argumentos = {
            "capital_desembolso_ars": capital_ars,
            "cotizacion_inicial": cotizacion_inicial,
            "tasa_anual_usd": tasa_usd,
            "modalidad_tasa": ModalidadTasa(modalidad_texto),
            "convencion_dias": convencion,
            "sistema": sistema,
            "fecha_desembolso": fecha_desembolso,
            "meses_carencia": meses_carencia,
            "plazo_amortizacion_meses": plazo_amortizacion_meses,
            "tratamiento_carencia": TratamientoCarencia(tratamiento_texto),
        }
        base = simular_unidad_usd(**argumentos)
    except (ErrorValidacion, ValueError, InvalidOperation) as exc:
        st.error(str(exc))
        return

    st.subheader("Calendario de conversión por fecha")
    st.caption(
        "La cuota y el saldo se calculan en USD. Cada cotización de la tabla solo "
        "convierte esa cuota a pesos para compararla con un presupuesto; no "
        "recalcula las unidades USD ni convierte este escenario en contrato."
    )
    registros = [
        {
            "fecha_vencimiento": cuota.fecha_vencimiento,
            "ars_por_usd": None,
            "fuente": "",
            "lado": "VENDEDOR",
            "naturaleza": "PROYECTADA",
        }
        for cuota in base.cuotas
    ]
    with st.expander(
        "Cargar una cotización ARS/USD para cada vencimiento",
        expanded=True,
    ):
        editados = st.data_editor(
            registros,
            key="sim_usd_cotizaciones_por_fecha",
            hide_index=True,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "fecha_vencimiento": st.column_config.DateColumn(
                    "Vencimiento", disabled=True, format="DD/MM/YYYY"
                ),
                "ars_por_usd": st.column_config.NumberColumn(
                    "ARS por USD", min_value=0.0001, step=1.0, format="%.4f"
                ),
                "fuente": st.column_config.TextColumn("Fuente / instrumento"),
                "lado": st.column_config.SelectboxColumn(
                    "Lado", options=["VENDEDOR", "COMPRADOR", "OTRO"]
                ),
                "naturaleza": st.column_config.SelectboxColumn(
                    "Dato", options=["OBSERVADA", "PROYECTADA"]
                ),
            },
        )

    if hasattr(editados, "to_dict"):
        filas_editadas = editados.to_dict(orient="records")
    else:
        filas_editadas = list(editados)
    cotizaciones: dict[date, CotizacionUnidad] = {}
    try:
        for fila in filas_editadas:
            valor_tc = fila.get("ars_por_usd")
            if valor_tc is None or str(valor_tc).strip().lower() in {"", "nan", "none", "<na>"}:
                continue
            fecha_tc = _registro_a_fecha(fila.get("fecha_vencimiento"))
            fuente = str(fila.get("fuente") or "").strip()
            if not fuente:
                raise ErrorValidacion(
                    f"Completá la fuente de cotización de la cuota con vencimiento "
                    f"{_fecha(fecha_tc)}."
                )
            cotizaciones[fecha_tc] = CotizacionUnidad(
                fecha_cotizacion=fecha_tc,
                ars_por_usd=Decimal(str(valor_tc)),
                fuente=fuente,
                lado=str(fila.get("lado") or "VENDEDOR"),
                naturaleza=str(fila.get("naturaleza") or "PROYECTADA"),
            )
        resultado = simular_unidad_usd(
            **argumentos,
            cotizaciones_por_vencimiento=cotizaciones,
        )
    except (ErrorValidacion, ValueError, InvalidOperation) as exc:
        st.error(str(exc))
        return

    st.subheader("Resultado: recuperar capital + rendimiento objetivo")
    costo_rendimiento_usd = resultado.total_programado_usd - resultado.capital_inicial_usd
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capital inicial de referencia", _dinero(resultado.capital_inicial_usd, "USD"))
    m2.metric("Costo / rendimiento objetivo total", _dinero(costo_rendimiento_usd, "USD"))
    m3.metric("Total programado", _dinero(resultado.total_programado_usd, "USD"))
    m4.metric("Rendimiento anualizado (XIRR USD)", _porcentaje(resultado.rendimiento_anualizado_usd))

    m1, m2 = st.columns(2)
    m1.metric(
        "Total equivalente en ARS",
        _dinero(resultado.total_equivalente_ars, "ARS"),
    )
    primer_equiv = resultado.cuotas[0].equivalente_ars if resultado.cuotas else None
    m2.metric("Primera cuota equivalente", _dinero(primer_equiv, "ARS"))

    if resultado.total_equivalente_ars is None:
        st.warning(
            "Faltan cotizaciones para uno o más vencimientos. Se muestran solo "
            "los equivalentes calculables; el total en ARS permanece incompleto."
        )
    st.warning(
        "La tasa USD es un rendimiento objetivo elegido para comparar una "
        "alternativa de inversión. No representa una rentabilidad garantizada. "
        "En un autopréstamo, el costo/rendimiento es interno y no una ganancia "
        "externa consolidada del hogar."
    )
    for aviso in resultado.advertencias:
        st.caption(aviso)

    tabla = [
        {
            "Cuota": c.numero,
            "Vencimiento": _fecha(c.fecha_vencimiento),
            "Capital inicial (USD)": _dinero(c.capital_inicial_usd, "USD"),
            "Interés período (USD)": _dinero(c.interes_periodo_usd, "USD"),
            "Amortización capital (USD)": _dinero(c.amortizacion_capital_usd, "USD"),
            "Interés carencia (USD)": _dinero(c.interes_carencia_usd, "USD"),
            "Total cuota (USD)": _dinero(c.importe_total_usd, "USD"),
            "Cotización ARS/USD": (
                "Sin cargar" if c.cotizacion is None
                else f"{c.cotizacion.ars_por_usd:.4f}"
            ),
            "Fuente": "" if c.cotizacion is None else c.cotizacion.fuente,
            "Equivalente (ARS)": _dinero(c.equivalente_ars, "ARS"),
            "Saldo capital (USD)": _dinero(c.saldo_capital_usd, "USD"),
        }
        for c in resultado.cuotas
    ]
    st.dataframe(tabla, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar plan USD y equivalentes ARS (CSV)",
        data=_exportar_csv(resultado),
        file_name="plan-reposicion-usd-escenario.csv",
        mime="text/csv",
        key="sim_usd_descargar_csv",
    )
