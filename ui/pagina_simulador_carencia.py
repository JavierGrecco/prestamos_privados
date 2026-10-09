"""Simulador visual de préstamos con carencia inicial; no persiste datos."""
from __future__ import annotations

import csv
from io import StringIO
from datetime import date
from decimal import Decimal

import streamlit as st

from dominio import (
    ConvencionDias, ErrorValidacion, ModalidadTasa, SistemaAmortizacion,
    TratamientoCarencia, simular_carencia,
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


def _pct(valor: Decimal | None) -> str:
    return "No disponible" if valor is None else f"{valor * Decimal('100'):.2f}%"


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
        buffer, fieldnames=campos, delimiter=";", lineterminator="\\n"
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
    return ("\\ufeff" + buffer.getvalue()).encode("utf-8")


def _csv_calendario(resultado) -> bytes:
    """Exporta el calendario de cuotas de un único escenario."""
    buffer = StringIO(newline="")
    campos = [
        "numero_cuota", "fecha_vencimiento", "capital_inicial",
        "interes_periodo", "amortizacion_capital", "cuota_base",
        "interes_carencia_agregado", "importe_total", "saldo_capital",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\\n"
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
    return ("\\ufeff" + buffer.getvalue()).encode("utf-8")


def render() -> None:
    st.title("Simulador de carencia inicial")
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
        st.caption(
            "La comparación integral usa períodos mensuales. Las convenciones de "
            "días reales se incorporarán cuando las soporte también la amortización "
            "posterior, para no mezclar fórmulas."
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
        "convencion": ConvencionDias.MENSUAL,
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
