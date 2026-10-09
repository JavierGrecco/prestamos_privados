"""Simulador visual de préstamos con carencia inicial; no persiste datos."""
from __future__ import annotations

import csv
from io import StringIO
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

import streamlit as st
from dateutil.relativedelta import relativedelta

from dominio import (
    ConvencionDias, ErrorValidacion, ModalidadTasa, SistemaAmortizacion,
    TratamientoCarencia, simular_carencia, simular_unidad_usd,
    CotizacionUnidad,
)


ETIQUETAS = {
    TratamientoCarencia.SIN_INTERES.value: "Sin interés durante la carencia",
    TratamientoCarencia.PAGAR_INTERES_DURANTE_CARENCIA.value: "Pagar intereses durante la carencia",
    TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value: "Diferir interés simple a la primera cuota",
    TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value: "Distribuir interés simple entre cuotas",
    TratamientoCarencia.CAPITALIZAR_AL_FIN.value: "Capitalizar al final (solo análisis)",
}

EXPLICACIONES = {
    TratamientoCarencia.SIN_INTERES.value: (
        "No se cobra interés compensatorio durante la carencia. El capital no "
        "aumenta; el interés de referencia se muestra como costo que el prestamista "
        "decide no cobrar, pero no forma parte de la deuda."
    ),
    TratamientoCarencia.PAGAR_INTERES_DURANTE_CARENCIA.value: (
        "Se pagan los intereses de cada período durante la carencia. El capital "
        "queda sin amortizar y el interés pagado no se acumula."
    ),
    TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value: (
        "No hay pagos durante la carencia. El interés simple se suma por separado "
        "a la primera cuota regular, sin pasar a formar parte del capital."
    ),
    TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value: (
        "El interés simple acumulado se reparte entre las cuotas posteriores. "
        "Ese componente no genera nuevos intereses."
    ),
    TratamientoCarencia.CAPITALIZAR_AL_FIN.value: (
        "El interés acumulado se suma al capital al terminar la carencia y luego "
        "genera intereses. Es solo un escenario comparativo; requiere revisión "
        "contractual/legal antes de cualquier uso real."
    ),
}


def _pesos(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    entero, centavos = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if valor < 0 else ''}$ {entero},{centavos}"


def _decimal_local(valor: Decimal, decimales: int = 2) -> str:
    """Formatea Decimal con separadores argentinos sin cambiar su valor."""
    signo = "-" if valor < 0 else ""
    entero, fraccion = f"{abs(valor):,.{decimales}f}".split(".")
    return f"{signo}{entero.replace(',', '.')},{fraccion}"


def _usd(valor: Decimal | None) -> str:
    return "No disponible" if valor is None else f"USD {_decimal_local(valor, 2)}"


def _pct(valor: Decimal | None) -> str:
    return "No disponible" if valor is None else f"{_decimal_local(valor * Decimal('100'), 2)}%"


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def _csv_comparacion(resultados: dict[str, object]) -> bytes:
    """Exporta supuestos y resultado de cada alternativa en formato neutral."""
    buffer = StringIO(newline="")
    campos = [
        "tratamiento", "fecha_desembolso", "meses_carencia",
        "fecha_fin_carencia", "fecha_primer_vencimiento",
        "capital_original", "tasa_anual", "modalidad_tasa",
        "sistema_amortizacion", "convencion_dias",
        "interes_referencia_carencia", "interes_pagado_durante_carencia",
        "interes_diferido_simple", "interes_no_cobrado",
        "interes_capitalizado_solo_analisis", "capital_amortizable",
        "primera_cuota", "total_pagado_deudor", "costo_total_intereses_deudor",
        "rendimiento_anualizado_prestamista", "solo_analisis", "advertencias",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    for clave, resultado in resultados.items():
        escritor.writerow({
            "tratamiento": ETIQUETAS[clave],
            "fecha_desembolso": resultado.fecha_desembolso.isoformat(),
            "meses_carencia": resultado.meses_carencia,
            "fecha_fin_carencia": resultado.fecha_fin_carencia.isoformat(),
            "fecha_primer_vencimiento": resultado.fecha_primer_vencimiento.isoformat(),
            "capital_original": str(resultado.capital_original),
            "tasa_anual": str(resultado.tasa_anual),
            "modalidad_tasa": resultado.modalidad_tasa.value,
            "sistema_amortizacion": resultado.sistema.value,
            "convencion_dias": resultado.convencion.value,
            "interes_referencia_carencia": str(resultado.interes_simple_referencia_carencia),
            "interes_pagado_durante_carencia": str(resultado.interes_carencia_pagado_durante),
            "interes_diferido_simple": str(resultado.interes_carencia_diferido),
            "interes_no_cobrado": str(resultado.interes_carencia_no_cobrado),
            "interes_capitalizado_solo_analisis": str(resultado.interes_carencia_capitalizado),
            "capital_amortizable": str(resultado.capital_amortizable_inicio),
            "primera_cuota": str(resultado.cuotas[0].importe_total),
            "total_pagado_deudor": str(resultado.total_pagado_deudor),
            "costo_total_intereses_deudor": str(resultado.costo_total_intereses_deudor),
            "rendimiento_anualizado_prestamista": (
                "" if resultado.rendimiento_anualizado_prestamista is None
                else str(resultado.rendimiento_anualizado_prestamista)
            ),
            "solo_analisis": str(resultado.solo_analisis).lower(),
            "advertencias": " | ".join(resultado.advertencias),
        })
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _csv_calendario(resultado) -> bytes:
    """Exporta el calendario de cuotas de un único escenario."""
    buffer = StringIO(newline="")
    campos = [
        "numero_cuota", "fecha_vencimiento", "capital_inicial",
        "interes_periodo", "amortizacion_capital", "cuota_base",
        "interes_carencia_agregado", "importe_total", "saldo_capital",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    for cuota in resultado.cuotas:
        escritor.writerow({
            "numero_cuota": cuota.numero,
            "fecha_vencimiento": cuota.vencimiento.isoformat(),
            "capital_inicial": str(cuota.capital_inicial),
            "interes_periodo": str(cuota.interes_periodo),
            "amortizacion_capital": str(cuota.amortizacion_capital),
            "cuota_base": str(cuota.cuota_base),
            "interes_carencia_agregado": str(cuota.interes_carencia_agregado),
            "importe_total": str(cuota.importe_total),
            "saldo_capital": str(cuota.saldo_capital),
        })
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")




def _csv_unidad_usd(resultado) -> bytes:
    """Exporta la cuota en USD y su equivalente ARS, si se calculó."""
    buffer = StringIO(newline="")
    campos = [
        "numero_cuota",
        "fecha_vencimiento",
        "capital_inicial_usd",
        "interes_periodo_usd",
        "amortizacion_capital_usd",
        "cuota_base_usd",
        "interes_carencia_usd",
        "importe_total_usd",
        "saldo_capital_usd",
        "cotizacion_inicial_fecha",
        "cotizacion_inicial_ars_por_usd",
        "cotizacion_inicial_naturaleza",
        "cotizacion_inicial_fuente",
        "cotizacion_inicial_lado",
        "naturaleza_cotizacion",
        "fecha_cotizacion",
        "ars_por_usd",
        "fuente_cotizacion",
        "lado_cotizacion",
        "equivalente_ars",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    for cuota in resultado.cuotas:
        cotizacion = cuota.cotizacion
        escritor.writerow({
            "numero_cuota": cuota.numero,
            "fecha_vencimiento": cuota.fecha_vencimiento.isoformat(),
            "capital_inicial_usd": str(cuota.capital_inicial_usd),
            "interes_periodo_usd": str(cuota.interes_periodo_usd),
            "amortizacion_capital_usd": str(cuota.amortizacion_capital_usd),
            "cuota_base_usd": str(cuota.cuota_base_usd),
            "interes_carencia_usd": str(cuota.interes_carencia_usd),
            "importe_total_usd": str(cuota.importe_total_usd),
            "saldo_capital_usd": str(cuota.saldo_capital_usd),
            "cotizacion_inicial_fecha": resultado.cotizacion_inicial.fecha_cotizacion.isoformat(),
            "cotizacion_inicial_ars_por_usd": str(resultado.cotizacion_inicial.ars_por_usd),
            "cotizacion_inicial_naturaleza": resultado.cotizacion_inicial.naturaleza,
            "cotizacion_inicial_fuente": resultado.cotizacion_inicial.fuente,
            "cotizacion_inicial_lado": resultado.cotizacion_inicial.lado,
            "naturaleza_cotizacion": "" if cotizacion is None else cotizacion.naturaleza,
            "fecha_cotizacion": "" if cotizacion is None else cotizacion.fecha_cotizacion.isoformat(),
            "ars_por_usd": "" if cotizacion is None else str(cotizacion.ars_por_usd),
            "fuente_cotizacion": "" if cotizacion is None else cotizacion.fuente,
            "lado_cotizacion": "" if cotizacion is None else cotizacion.lado,
            "equivalente_ars": "" if cuota.equivalente_ars is None else str(cuota.equivalente_ars),
        })
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _render_unidad_usd() -> None:
    """Pantalla analítica para recuperar capital medido en unidades USD."""
    st.subheader("Plan de reposición en USD")
    st.info(
        "Este modo mide el capital y las cuotas en unidades USD de referencia. "
        "No crea una obligación legal en dólares, no registra pagos y no garantiza "
        "que el precio del auto evolucione igual que el tipo de cambio."
    )
    st.caption(
        "La cotización inicial fija las unidades USD del plan. Para ver equivalentes "
        "ARS futuros, definí explícitamente una trayectoria proyectada por cuota. "
        "Sin esa hipótesis, el sistema muestra USD y deja el total ARS como no calculado."
    )

    col1, col2 = st.columns(2)
    with col1:
        capital_ars = st.number_input(
            "Capital utilizado para la compra (ARS)",
            min_value=1000.0, max_value=1_000_000_000_000.0,
            value=1_000_000.0, step=10_000.0, format="%.2f",
            key="sim_usd_capital_ars",
        )
        fecha_desembolso = st.date_input(
            "Fecha de desembolso / compra",
            value=date.today(), key="sim_usd_fecha_desembolso",
        )
        tasa_usd_pct = st.number_input(
            "Rendimiento objetivo anual en USD (%)",
            min_value=0.01, max_value=100.0, value=4.0, step=0.25,
            format="%.4f", key="sim_usd_tasa_anual",
            help=(
                "El 4% inicial es solo un ejemplo. Reemplazalo por un rendimiento "
                "neto que puedas fundamentar a partir de la inversión alternativa "
                "que elegiste. No es una predicción ni un rendimiento garantizado."
            ),
        )
        benchmark_usd = st.text_input(
            "Inversión alternativa de referencia",
            value="",
            placeholder="Ej.: instrumento o cartera USD que querés tomar como benchmark",
            key="sim_usd_benchmark_inversion",
            help=(
                "Identificá qué inversión habría mantenido ese capital. La tasa se "
                "ingresa por separado; el sistema no consulta rendimientos de mercado."
            ),
        )
        st.caption(
            "Para cumplir el objetivo completo, este escenario requiere una tasa "
            "positiva: capital + conservación de referencia USD + rendimiento objetivo."
        )
        modalidad = st.selectbox(
            "Modalidad de tasa en USD",
            options=["TEA", "TNA"],
            format_func=lambda x: (
                "TNA en USD — nominal anual" if x == "TNA"
                else "TEA en USD — efectiva anual"
            ),
            key="sim_usd_modalidad_tasa",
        )
    with col2:
        tc_inicial = st.number_input(
            "Cotización inicial (ARS por USD)",
            min_value=0.000001, max_value=1_000_000_000.0,
            value=1000.0, step=10.0, format="%.6f",
            key="sim_usd_tc_inicial",
        )
        fecha_tc = st.date_input(
            "Fecha de la cotización inicial",
            value=date.today(), key="sim_usd_fecha_tc",
        )
        fuente_tc = st.text_input(
            "Fuente / instrumento de cotización",
            value="",
            placeholder="Ej.: Dólar MEP — especificar instrumento y fuente",
            key="sim_usd_fuente_tc",
            help="No hay consulta de cotización en vivo. Identificá el origen del dato que ingresás.",
        )
        cotizacion_verificada = st.checkbox(
            "Verifiqué este valor en la fuente indicada",
            value=False,
            key="sim_usd_cotizacion_verificada",
        )
        lado_tc = st.selectbox(
            "Lado de la cotización",
            options=["VENDEDOR", "COMPRADOR"],
            format_func=lambda x: (
                "Vendedor — referencia para adquirir USD" if x == "VENDEDOR"
                else "Comprador — referencia de compra de USD al usuario"
            ),
            key="sim_usd_lado_tc",
        )

    col3, col4 = st.columns(2)
    with col3:
        meses_carencia = st.number_input(
            "Meses completos sin cuotas regulares",
            min_value=0, max_value=120, value=12, step=1,
            key="sim_usd_meses_carencia",
        )
        plazo = st.number_input(
            "Cuotas después de la carencia",
            min_value=1, max_value=240, value=24, step=1,
            key="sim_usd_plazo",
        )
    with col4:
        sistema_texto = st.selectbox(
            "Sistema de amortización",
            options=["FRANCES", "ALEMAN"],
            format_func=lambda x: (
                "Francés — cuota base constante" if x == "FRANCES"
                else "Alemán — capital constante"
            ),
            key="sim_usd_sistema",
        )
        convencion_texto = st.selectbox(
            "Convención temporal",
            options=["MENSUAL", "ACTUAL_365", "ACTUAL_360", "ACTUAL_ACTUAL", "TREINTA_360"],
            format_func=lambda x: {
                "MENSUAL": "Mensual",
                "ACTUAL_365": "Días reales / 365",
                "ACTUAL_360": "Días reales / 360",
                "ACTUAL_ACTUAL": "Días reales / año bisiesto",
                "TREINTA_360": "30E/360 Eurobond",
            }[x],
            key="sim_usd_convencion",
        )

    tratamiento_texto = st.selectbox(
        "Tratamiento del interés durante la carencia",
        options=[
            TratamientoCarencia.SIN_INTERES.value,
            TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value,
            TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value,
        ],
        format_func=lambda x: {
            TratamientoCarencia.SIN_INTERES.value: "Sin interés durante la carencia",
            TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value: "Diferir interés simple a la primera cuota",
            TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value: "Distribuir interés simple entre cuotas",
        }[x],
        key="sim_usd_tratamiento",
    )
    usar_proyeccion = st.checkbox(
        "Calcular equivalentes ARS con una trayectoria PROYECTADA de cotización",
        value=False,
        key="sim_usd_usar_proyeccion",
    )
    variacion_pct = Decimal("0")
    if usar_proyeccion:
        variacion_input = st.number_input(
            "Variación mensual proyectada del tipo de cambio (%)",
            min_value=-99.0, max_value=100.0, value=3.0, step=0.5,
            format="%.2f", key="sim_usd_variacion_mensual",
            help=(
                "Se aplica de forma compuesta mes a mes a partir de la cotización "
                "inicial. Es un supuesto editable, no un pronóstico ni una cotización real."
            ),
        )
        variacion_pct = Decimal(str(variacion_input))
        st.warning(
            "Los equivalentes ARS de la tabla son escenarios proyectados, no "
            "cotizaciones observadas. El cronograma en USD no cambia al modificar "
            "esta hipótesis."
        )

    if not fuente_tc.strip():
        st.warning(
            "Ingresá la fuente y el instrumento de la cotización inicial. "
            "No se consulta una cotización de mercado automáticamente."
        )
        return
    if not benchmark_usd.strip():
        st.warning(
            "Indicá qué inversión alternativa querés imitar. La tasa positiva debe "
            "representar el rendimiento objetivo de ese benchmark, no una ganancia "
            "elegida sin referencia."
        )
        return
    if tasa_usd_pct <= 0:
        st.error(
            "La reposición con rendimiento objetivo requiere una tasa anual positiva en USD."
        )
        return

    sistema = (
        SistemaAmortizacion.FRANCES
        if sistema_texto == "FRANCES"
        else SistemaAmortizacion.ALEMAN
    )
    convencion = {
        "MENSUAL": ConvencionDias.MENSUAL,
        "ACTUAL_365": ConvencionDias.ACTUAL_365,
        "ACTUAL_360": ConvencionDias.ACTUAL_360,
        "ACTUAL_ACTUAL": ConvencionDias.ACTUAL_ACTUAL,
        "TREINTA_360": ConvencionDias.TREINTA_360,
    }[convencion_texto]
    tratamiento = TratamientoCarencia(tratamiento_texto)
    try:
        cotizacion_inicial = CotizacionUnidad(
            fecha_cotizacion=fecha_tc,
            ars_por_usd=Decimal(str(tc_inicial)),
            fuente=fuente_tc.strip(),
            lado=lado_tc,
            naturaleza="OBSERVADA" if cotizacion_verificada else "SUPUESTO",
            referencia=(
                "Cotización ingresada por el usuario y marcada como verificada"
                if cotizacion_verificada
                else "Supuesto inicial ingresado por el usuario; no verificado en mercado"
            ),
        )
        argumentos = {
            "capital_desembolso_ars": Decimal(str(capital_ars)),
            "cotizacion_inicial": cotizacion_inicial,
            "tasa_anual_usd": Decimal(str(tasa_usd_pct)) / Decimal("100"),
            "modalidad_tasa": ModalidadTasa(modalidad),
            "convencion_dias": convencion,
            "sistema": sistema,
            "fecha_desembolso": fecha_desembolso,
            "meses_carencia": int(meses_carencia),
            "plazo_amortizacion_meses": int(plazo),
            "tratamiento_carencia": tratamiento,
        }
        resultado_base = simular_unidad_usd(**argumentos)
        cotizaciones = None
        if usar_proyeccion:
            factor_mensual = Decimal("1") + variacion_pct / Decimal("100")
            if factor_mensual <= 0:
                raise ErrorValidacion(
                    "La variación mensual produce una cotización no positiva"
                )
            cotizaciones = {}
            with localcontext() as contexto:
                contexto.prec = 32
                for cuota in resultado_base.cuotas:
                    meses_desde_cotizacion = (
                        (cuota.fecha_vencimiento.year - fecha_tc.year) * 12
                        + cuota.fecha_vencimiento.month - fecha_tc.month
                    )
                    factor = contexto.power(
                        factor_mensual, Decimal(max(0, meses_desde_cotizacion))
                    )
                    tasa_proyectada = (
                        cotizacion_inicial.ars_por_usd * factor
                    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    cotizaciones[cuota.fecha_vencimiento] = CotizacionUnidad(
                        fecha_cotizacion=cuota.fecha_vencimiento,
                        ars_por_usd=tasa_proyectada,
                        fuente=f"PROYECCIÓN mensual desde {fuente_tc.strip()}",
                        lado=lado_tc,
                        naturaleza="PROYECTADA",
                        referencia=(
                            f"Supuesto de variación mensual {variacion_pct}% "
                            f"desde {fecha_tc.isoformat()}; no es dato de mercado"
                        ),
                    )
        resultado = (
            simular_unidad_usd(
                **argumentos,
                cotizaciones_por_vencimiento=cotizaciones,
            )
            if cotizaciones is not None
            else resultado_base
        )
    except (ErrorValidacion, ValueError, ArithmeticError, OverflowError) as exc:
        st.error(str(exc))
        return

    st.subheader("Resultado del plan en unidades USD")
    st.caption(
        f"Fin de carencia: {_fecha(resultado.fecha_fin_carencia)}. "
        f"Primera cuota: {_fecha(resultado.fecha_primer_vencimiento)}. "
        f"Capital inicial: {_pesos(resultado.capital_desembolso_ars)} convertido a "
        f"{_usd(resultado.capital_inicial_usd)} usando "
        f"{_decimal_local(resultado.cotizacion_inicial.ars_por_usd, 6)} ARS/USD. "
        f"Fuente: {resultado.cotizacion_inicial.fuente}; lado: {resultado.cotizacion_inicial.lado}. "
        f"Naturaleza de la referencia inicial: {resultado.cotizacion_inicial.naturaleza}."
    )
    costo_rendimiento_objetivo_usd = (
        resultado.total_programado_usd - resultado.capital_inicial_usd
    )
    st.caption(
        f"Benchmark elegido: {benchmark_usd.strip()}. "
        f"Tasa objetivo: {_pct(resultado.tasa_anual_usd)} "
        f"({resultado.modalidad_tasa.value} en USD)."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capital a reponer (USD)", _usd(resultado.capital_inicial_usd))
    m2.metric(
        "Costo / rendimiento objetivo total (USD)",
        _usd(costo_rendimiento_objetivo_usd),
        help=(
            "Es el interés/costo financiero que se suma al capital en el escenario. "
            "En un préstamo entre partes distintas puede ser costo del deudor y "
            "rendimiento bruto del prestamista; en un autopréstamo es interno."
        ),
    )
    m3.metric("Total programado a recuperar (USD)", _usd(resultado.total_programado_usd))
    m4.metric("Rendimiento anualizado (XIRR USD)", _pct(resultado.rendimiento_anualizado_usd))
    m1, m2 = st.columns(2)
    m1.metric(
        "Total equivalente ARS",
        _pesos(resultado.total_equivalente_ars)
        if resultado.total_equivalente_ars is not None
        else "No calculado",
    )
    m2.metric(
        "Primera cuota equivalente ARS",
        _pesos(resultado.cuotas[0].equivalente_ars),
    )
    st.caption(
        "El interés y las cuotas se calculan en USD de referencia. La conversión ARS "
        "solo valúa cada cuota según el escenario seleccionado; no cambia la obligación, "
        "no compra dólares y no constituye una cobertura de mercado. El rendimiento "
        "objetivo es configurable y no garantizado; en el autopréstamo es costo de "
        "oportunidad interno, no ganancia externa consolidada."
    )
    if resultado.cotizacion_inicial.naturaleza == "SUPUESTO":
        st.warning(
            "La cotización inicial es un supuesto no verificado. Comprobá la fuente, "
            "el instrumento, el lado de cotización y la fecha antes de interpretar el resultado."
        )
    for aviso in resultado.advertencias:
        st.warning(aviso)

    tabla = []
    for cuota in resultado.cuotas:
        cotizacion = cuota.cotizacion
        tabla.append({
            "Cuota": cuota.numero,
            "Vencimiento": _fecha(cuota.fecha_vencimiento),
            "Capital inicial (USD)": _usd(cuota.capital_inicial_usd),
            "Interés período (USD)": _usd(cuota.interes_periodo_usd),
            "Capital amortizado (USD)": _usd(cuota.amortizacion_capital_usd),
            "Interés carencia (USD)": _usd(cuota.interes_carencia_usd),
            "Cuota total (USD)": _usd(cuota.importe_total_usd),
            "Cotización ARS/USD": (
                _decimal_local(cotizacion.ars_por_usd, 6) if cotizacion is not None else "No calculada"
            ),
            "Naturaleza": cotizacion.naturaleza if cotizacion is not None else "Sin conversión",
            "Equivalente ARS": _pesos(cuota.equivalente_ars),
            "Saldo capital (USD)": _usd(cuota.saldo_capital_usd),
        })
    st.dataframe(tabla, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar calendario USD y equivalentes por cuota (CSV)",
        data=_csv_unidad_usd(resultado),
        file_name="simulacion-unidad-usd.csv",
        mime="text/csv",
        key="sim_usd_descarga_csv",
    )
    st.caption(
        "Para un pago real, la cotización utilizada debe registrarse en la fecha "
        "aplicable a ese pago, junto con el importe y la moneda efectivamente recibidos. "
        "Esta pantalla todavía no registra operaciones."
    )


def render() -> None:
    st.title("Simulador de carencia inicial")
    unidad = st.radio(
        "Unidad del plan",
        options=["ARS nominal", "USD de referencia — solo análisis"],
        horizontal=True,
        key="sim_carencia_unidad",
        help=(
            "ARS nominal conserva el simulador habitual. El modo USD permite "
            "medir la reposición de capital en unidades USD, sin crear un contrato."
        ),
    )
    if unidad == "USD de referencia — solo análisis":
        _render_unidad_usd()
        return
    st.caption(
        "Compará cuándo empiezan los pagos, cómo se trata el interés y cuánto "
        "terminaría pagando cada parte antes de confirmar un préstamo."
    )
    st.info(
        "Simulación sin persistencia: no crea préstamos, no guarda condiciones "
        "contractuales y no modifica la base de datos."
    )
    st.warning(
        "La capitalización se muestra únicamente como escenario de análisis; "
        "no supone que esa cláusula sea válida para un contrato concreto."
    )

    with st.expander("Entender los tratamientos de intereses"):
        for clave, etiqueta in ETIQUETAS.items():
            st.markdown(f"**{etiqueta}**")
            st.write(EXPLICACIONES[clave])

    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input(
            "Capital a prestar (ARS)", min_value=1000.0,
            max_value=1_000_000_000_000.0, value=1_000_000.0,
            step=10_000.0, format="%.2f", key="sim_carencia_capital",
        )
        fecha_desembolso = st.date_input(
            "Fecha de desembolso", value=date.today(), key="sim_carencia_fecha",
        )
        tasa_pct = st.number_input(
            "Tasa anual (%)", min_value=0.0, max_value=1000.0,
            value=36.0, step=0.5, format="%.4f", key="sim_carencia_tasa",
        )
        modalidad = st.selectbox(
            "Modalidad de tasa", options=["TNA", "TEA"],
            format_func=lambda x: "TNA — nominal anual" if x == "TNA" else "TEA — efectiva anual",
            key="sim_carencia_modalidad",
        )
    with col2:
        meses = st.number_input(
            "Meses completos sin cuotas regulares", min_value=0, max_value=120,
            value=12, step=1, key="sim_carencia_meses",
        )
        plazo = st.number_input(
            "Cantidad de cuotas después de la carencia", min_value=1, max_value=240,
            value=24, step=1, key="sim_carencia_plazo",
        )
        sistema_texto = st.selectbox(
            "Sistema de amortización", options=["FRANCES", "ALEMAN"],
            format_func=lambda x: (
                "Francés — cuota base constante" if x == "FRANCES"
                else "Alemán — amortización de capital constante"
            ),
            key="sim_carencia_sistema",
        )
        convencion_clave = st.selectbox(
            "Cómo se cuenta el tiempo",
            options=[
                "MENSUAL",
                "ACTUAL_365",
                "ACTUAL_360",
                "ACTUAL_ACTUAL",
                "TREINTA_360",
            ],
            format_func=lambda x: {
                "MENSUAL": "Mensual",
                "ACTUAL_365": "Días reales / 365",
                "ACTUAL_360": "Días reales / 360",
                "ACTUAL_ACTUAL": "Días reales / año bisiesto",
                "TREINTA_360": "30E/360 Eurobond",
            }[x],
            key="sim_carencia_convencion",
        )
        st.caption(
            "ACTUAL/365, ACTUAL/360 y ACTUAL/ACTUAL usan las fechas reales. "
            "30E/360 cuenta meses de 30 días; si el vencimiento final es el último "
            "día de febrero, se conserva ese día. Esto es una simulación, no un contrato."
        )

    sistema = (
        SistemaAmortizacion.FRANCES
        if sistema_texto == "FRANCES"
        else SistemaAmortizacion.ALEMAN
    )
    argumentos = {
        "capital": Decimal(str(capital)),
        "tasa_anual": Decimal(str(tasa_pct)) / Decimal("100"),
        "modalidad": ModalidadTasa(modalidad),
        "convencion": {
            "MENSUAL": ConvencionDias.MENSUAL,
            "ACTUAL_365": ConvencionDias.ACTUAL_365,
            "ACTUAL_360": ConvencionDias.ACTUAL_360,
            "ACTUAL_ACTUAL": ConvencionDias.ACTUAL_ACTUAL,
            "TREINTA_360": ConvencionDias.TREINTA_360,
        }[convencion_clave],
        "fecha_desembolso": fecha_desembolso,
        "meses_carencia": int(meses),
        "plazo_amortizacion_meses": int(plazo),
        "sistema": sistema,
    }
    tratamientos_disponibles = tuple(
        tratamiento for tratamiento in TratamientoCarencia
        if not (
            modalidad == "TEA"
            and tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN
        )
    )
    if modalidad == "TEA":
        st.warning(
            "La capitalización no se incluye en la comparación TEA: el cálculo "
            "necesita una regla explícita de capitalización compatible con una "
            "tasa efectiva anual. Los otros cuatro tratamientos se calculan "
            "sobre los supuestos mostrados."
        )
    try:
        resultados = {
            tratamiento.value: simular_carencia(
                **argumentos,
                tratamiento=tratamiento,
                permitir_capitalizacion_solo_analisis=(
                    tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN
                ),
            )
            for tratamiento in tratamientos_disponibles
        }
    except (ErrorValidacion, ValueError) as exc:
        st.error(str(exc))
        return

    referencia = next(iter(resultados.values()))
    st.subheader("Comparación de alternativas")
    st.caption(
        f"Fin de carencia: {_fecha(referencia.fecha_fin_carencia)}. "
        f"Primer vencimiento regular: {_fecha(referencia.fecha_primer_vencimiento)}. "
        "El primer vencimiento regular es un mes después de terminar la carencia."
    )
    filas = []
    for clave, r in resultados.items():
        filas.append({
            "Tratamiento": ETIQUETAS[clave],
            "Interés de referencia": _pesos(r.interes_simple_referencia_carencia),
            "Cobrado durante carencia": _pesos(r.interes_carencia_pagado_durante),
            "Diferido simple": _pesos(r.interes_carencia_diferido),
            "No cobrado": _pesos(r.interes_carencia_no_cobrado),
            "Capitalizado*": _pesos(r.interes_carencia_capitalizado),
            "Primera cuota": _pesos(r.cuotas[0].importe_total),
            "Total pagado": _pesos(r.total_pagado_deudor),
            "Costo total de intereses": _pesos(r.costo_total_intereses_deudor),
            "Rendimiento anualizado prestamista": _pct(r.rendimiento_anualizado_prestamista),
        })
    st.dataframe(filas, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar comparación (CSV)",
        data=_csv_comparacion(resultados),
        file_name="simulacion-carencia-comparacion.csv",
        mime="text/csv",
        key="sim_carencia_descarga_comparacion",
    )
    st.caption(
        "* La capitalización solo se compara, no se ofrece como modalidad operativa. "
        "El rendimiento anualizado se calcula con las fechas de los flujos (XIRR), "
        "por lo que puede diferir de la tasa nominal o efectiva declarada."
    )

    clave = st.selectbox(
        "Ver calendario detallado", options=list(resultados),
        format_func=lambda x: ETIQUETAS[x], key="sim_carencia_detalle",
    )
    r = resultados[clave]
    st.subheader("Detalle del escenario")
    st.write(EXPLICACIONES[clave])
    m1, m2, m3 = st.columns(3)
    m1.metric("Total pagado por el deudor", _pesos(r.total_pagado_deudor))
    m2.metric("Costo total de intereses", _pesos(r.costo_total_intereses_deudor))
    m3.metric("Rendimiento anualizado del prestamista", _pct(r.rendimiento_anualizado_prestamista))
    m1, m2, m3 = st.columns(3)
    m1.metric("Capital a amortizar", _pesos(r.capital_amortizable_inicio))
    m2.metric("Interés simple de carencia", _pesos(r.interes_simple_referencia_carencia))
    m3.metric("Interés diferido sin capitalizar", _pesos(r.interes_carencia_diferido))
    for aviso in r.advertencias:
        st.warning(aviso)

    calendario = [
        {
            "Cuota": q.numero,
            "Vencimiento": _fecha(q.vencimiento),
            "Capital inicial": _pesos(q.capital_inicial),
            "Interés del período": _pesos(q.interes_periodo),
            "Amortización de capital": _pesos(q.amortizacion_capital),
            "Interés de carencia agregado": _pesos(q.interes_carencia_agregado),
            "Pago total": _pesos(q.importe_total),
            "Saldo de capital": _pesos(q.saldo_capital),
        }
        for q in r.cuotas
    ]
    st.dataframe(calendario, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar este calendario (CSV)",
        data=_csv_calendario(r),
        file_name=f"simulacion-carencia-{clave.lower()}.csv",
        mime="text/csv",
        key="sim_carencia_descarga_calendario",
    )
