"""Simulador visual de préstamos con carencia inicial; no persiste datos."""
from __future__ import annotations

import csv
from io import StringIO
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import streamlit as st
from dateutil.relativedelta import relativedelta

from dominio import (
    ConvencionDias, ErrorValidacion, ModalidadTasa, SistemaAmortizacion,
    TratamientoCarencia, simular_carencia, simular_unidad_usd,
    CotizacionUnidad, calcular_tasa_neta_benchmark_usd,
    comparar_escenarios_benchmark, ObservacionIndiceRetornoTotal,
    resumir_serie_indice_retorno_total,
    comparar_flujos_con_indice_historico,
    ObservacionPrecioDistribucion,
    derivar_indice_retorno_total_desde_precios,
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


def _parsear_decimal_es(
    texto: str,
    *,
    etiqueta: str,
    minimo: Decimal,
    maximo: Decimal,
    decimales_maximos: int,
) -> Decimal:
    """Valida entradas decimales sin pasar por float.

    Acepta coma decimal (1.000.000,50), enteros con agrupación argentina
    (1.000.000) y decimales canónicos (1000000.50). Para evitar ambigüedad,
    un punto seguido por tres cifras en un número distinto de cero se
    interpreta como separador de miles; si se desea decimal, usar coma.
    """
    original = (texto or "").strip().replace(" ", "").replace("\u00a0", "")
    if not original:
        raise ErrorValidacion(f"Ingresá {etiqueta}.")

    signo = ""
    cuerpo = original
    if cuerpo.startswith(("-", "+")):
        signo = "-" if cuerpo[0] == "-" else ""
        cuerpo = cuerpo[1:]
    if not cuerpo:
        raise ErrorValidacion(f"{etiqueta.capitalize()} no es un número válido.")

    if "," in cuerpo:
        if cuerpo.count(",") != 1:
            raise ErrorValidacion(f"{etiqueta.capitalize()} tiene separadores inválidos.")
        entero, fraccion = cuerpo.split(",", 1)
        if not entero or not fraccion.isdigit():
            raise ErrorValidacion(f"{etiqueta.capitalize()} no es un número válido.")
        if "." in entero:
            grupos = entero.split(".")
            if (
                not grupos[0].isdigit()
                or not 1 <= len(grupos[0]) <= 3
                or any(not grupo.isdigit() or len(grupo) != 3 for grupo in grupos[1:])
            ):
                raise ErrorValidacion(
                    f"{etiqueta.capitalize()} tiene un agrupamiento de miles inválido."
                )
            entero = "".join(grupos)
        elif not entero.isdigit():
            raise ErrorValidacion(f"{etiqueta.capitalize()} no es un número válido.")
        normalizado = signo + entero + "." + fraccion
    elif "." in cuerpo:
        grupos = cuerpo.split(".")
        if grupos[0] == "0" and len(grupos) > 1 and all(g.isdigit() for g in grupos[1:]):
            # Permite precisión subunitaria, por ejemplo 0.000001 ARS/USD.
            normalizado = signo + "0." + "".join(grupos[1:])
        else:
            parece_miles = (
                len(grupos) > 1
                and 1 <= len(grupos[0]) <= 3
                and grupos[0].isdigit()
                and grupos[0] != "0"
                and all(g.isdigit() and len(g) == 3 for g in grupos[1:])
            )
            if parece_miles:
                normalizado = signo + "".join(grupos)
            elif (
                len(grupos) == 2
                and grupos[0].isdigit()
                and grupos[1].isdigit()
            ):
                normalizado = signo + grupos[0] + "." + grupos[1]
            else:
                raise ErrorValidacion(
                    f"{etiqueta.capitalize()} no es válido; revisá los separadores."
                )
    else:
        if not cuerpo.isdigit():
            raise ErrorValidacion(f"{etiqueta.capitalize()} no es un número válido.")
        normalizado = signo + cuerpo

    try:
        valor = Decimal(normalizado)
    except (InvalidOperation, ValueError) as exc:
        raise ErrorValidacion(f"{etiqueta.capitalize()} no es un número válido.") from exc

    if not valor.is_finite():
        raise ErrorValidacion(f"{etiqueta.capitalize()} debe ser un número finito.")
    if valor < minimo or valor > maximo:
        raise ErrorValidacion(
            f"{etiqueta.capitalize()} debe estar entre {minimo} y {maximo}."
        )
    decimales = max(0, -valor.as_tuple().exponent)
    if decimales > decimales_maximos:
        raise ErrorValidacion(
            f"{etiqueta.capitalize()} admite como máximo {decimales_maximos} decimales."
        )
    return valor


COLUMNAS_CSV_INDICE_RETORNO_TOTAL = (
    "fecha",
    "indice_retorno_total",
    "moneda",
    "tipo_indice",
    "fuente",
    "referencia",
)


def _csv_plantilla_indice_retorno_total() -> bytes:
    """Plantilla CSV de índice total-return; punto y coma admite coma decimal."""
    buffer = StringIO(newline="")
    escritor = csv.DictWriter(
        buffer,
        fieldnames=COLUMNAS_CSV_INDICE_RETORNO_TOTAL,
        delimiter=";",
        lineterminator="\n",
    )
    escritor.writeheader()
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _leer_csv_indice_retorno_total(contenido: bytes):
    """Lee una serie total-return con fecha, nivel, moneda, fuente y referencia."""
    if not isinstance(contenido, bytes) or not contenido:
        raise ErrorValidacion("El archivo de la serie histórica está vacío.")
    if len(contenido) > 2_000_000:
        raise ErrorValidacion("El archivo de la serie histórica supera 2 MB.")

    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ErrorValidacion(
            "El CSV de la serie debe estar codificado en UTF-8. Descargá la plantilla."
        ) from exc

    lector = csv.DictReader(StringIO(texto), delimiter=";")
    if not lector.fieldnames:
        raise ErrorValidacion("El CSV de la serie no contiene encabezados.")
    encabezados = [str(nombre or "").strip() for nombre in lector.fieldnames]
    if len(encabezados) != len(set(encabezados)):
        raise ErrorValidacion("El CSV de la serie contiene encabezados duplicados.")
    faltantes = set(COLUMNAS_CSV_INDICE_RETORNO_TOTAL) - set(encabezados)
    if faltantes:
        raise ErrorValidacion(
            "Faltan columnas del índice total-return: "
            + ", ".join(sorted(faltantes))
            + ". Usá la plantilla con separador punto y coma (;)."
        )
    lector.fieldnames = encabezados

    observaciones = []
    for numero_linea, registro in enumerate(lector, start=2):
        if numero_linea > 5001:
            raise ErrorValidacion("La serie puede contener como máximo 5.000 filas.")
        if None in registro:
            raise ErrorValidacion(
                f"Fila {numero_linea}: hay más campos que columnas; revisá el separador ';'."
            )
        valores = {
            str(clave): str(valor or "").strip()
            for clave, valor in registro.items()
            if clave is not None
        }
        if not any(valores.values()):
            continue

        fecha_texto = valores.get("fecha", "")
        try:
            fecha_observacion = date.fromisoformat(fecha_texto)
        except ValueError as exc:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe usar formato AAAA-MM-DD."
            ) from exc
        if fecha_observacion.isoformat() != fecha_texto:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe usar formato AAAA-MM-DD."
            )

        nivel = _parsear_decimal_es(
            valores.get("indice_retorno_total", ""),
            etiqueta=f"el nivel del índice de la fila {numero_linea}",
            minimo=Decimal("0.00000001"),
            maximo=Decimal("1000000000000"),
            decimales_maximos=10,
        )
        observaciones.append(
            ObservacionIndiceRetornoTotal(
                fecha=fecha_observacion,
                nivel_indice=nivel,
                moneda=valores.get("moneda", ""),
                fuente=valores.get("fuente", ""),
                tipo_indice=valores.get("tipo_indice", ""),
                referencia=valores.get("referencia", "") or None,
            )
        )

    if not observaciones:
        raise ErrorValidacion("El CSV no contiene observaciones históricas.")
    return resumir_serie_indice_retorno_total(tuple(observaciones)), tuple(observaciones)


COLUMNAS_CSV_PRECIO_DISTRIBUCION = (
    "fecha",
    "precio_no_ajustado",
    "distribucion_por_unidad",
    "moneda",
    "tipo_indice",
    "base_precio",
    "fuente",
    "referencia",
)


def _csv_plantilla_precio_distribucion() -> bytes:
    """Plantilla de precios no ajustados y distribuciones en efectivo por unidad."""
    buffer = StringIO(newline="")
    escritor = csv.DictWriter(
        buffer,
        fieldnames=COLUMNAS_CSV_PRECIO_DISTRIBUCION,
        delimiter=";",
        lineterminator="\n",
    )
    escritor.writeheader()
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _leer_csv_precio_distribucion(contenido: bytes):
    """Importa inputs de precio no ajustado/distribución y deriva el TRI normalizado."""
    if not isinstance(contenido, bytes) or not contenido:
        raise ErrorValidacion("El archivo de precios/distribuciones está vacío.")
    if len(contenido) > 2_000_000:
        raise ErrorValidacion("El archivo de precios/distribuciones supera 2 MB.")

    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ErrorValidacion(
            "El CSV de precios/distribuciones debe estar en UTF-8."
        ) from exc

    lector = csv.DictReader(StringIO(texto), delimiter=";")
    if not lector.fieldnames:
        raise ErrorValidacion("El CSV de precios/distribuciones no contiene encabezados.")
    encabezados = [str(nombre or "").strip() for nombre in lector.fieldnames]
    if len(encabezados) != len(set(encabezados)):
        raise ErrorValidacion("El CSV de precios/distribuciones tiene encabezados duplicados.")
    faltantes = set(COLUMNAS_CSV_PRECIO_DISTRIBUCION) - set(encabezados)
    if faltantes:
        raise ErrorValidacion(
            "Faltan columnas en precios/distribuciones: "
            + ", ".join(sorted(faltantes))
            + ". Descargá la plantilla con separador punto y coma (;)."
        )
    lector.fieldnames = encabezados

    observaciones = []
    for numero_linea, registro in enumerate(lector, start=2):
        if numero_linea > 5001:
            raise ErrorValidacion(
                "La serie de precios/distribuciones puede tener como máximo 5.000 filas."
            )
        if None in registro:
            raise ErrorValidacion(
                f"Fila {numero_linea}: hay más valores que columnas; revisá el separador ';'."
            )
        valores = {
            str(clave): str(valor or "").strip()
            for clave, valor in registro.items()
            if clave is not None
        }
        if not any(valores.values()):
            continue

        fecha_texto = valores.get("fecha", "")
        try:
            fecha_observacion = date.fromisoformat(fecha_texto)
        except ValueError as exc:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe usar formato AAAA-MM-DD."
            ) from exc
        if fecha_observacion.isoformat() != fecha_texto:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe usar formato AAAA-MM-DD."
            )

        try:
            precio = _parsear_decimal_es(
                valores.get("precio_no_ajustado", ""),
                etiqueta=f"el precio no ajustado de la fila {numero_linea}",
                minimo=Decimal("0.00000001"),
                maximo=Decimal("1000000000000"),
                decimales_maximos=10,
            )
            distribucion = _parsear_decimal_es(
                valores.get("distribucion_por_unidad", ""),
                etiqueta=f"la distribución de la fila {numero_linea}",
                minimo=Decimal("0"),
                maximo=Decimal("1000000000000"),
                decimales_maximos=10,
            )
            observacion = ObservacionPrecioDistribucion(
                fecha=fecha_observacion,
                precio_no_ajustado=precio,
                distribucion_por_unidad=distribucion,
                moneda=valores.get("moneda", ""),
                tipo_indice=valores.get("tipo_indice", ""),
                base_precio=valores.get("base_precio", ""),
                fuente=valores.get("fuente", ""),
                referencia=valores.get("referencia", "") or None,
            )
        except ErrorValidacion as exc:
            raise ErrorValidacion(f"Fila {numero_linea}: {exc}") from exc
        observaciones.append(observacion)

    if not observaciones:
        raise ErrorValidacion("El CSV no contiene observaciones de precio/distribución.")
    precios_validados = tuple(observaciones)
    indice_derivado = derivar_indice_retorno_total_desde_precios(precios_validados)
    return (
        resumir_serie_indice_retorno_total(indice_derivado),
        indice_derivado,
        precios_validados,
    )


def _csv_trazabilidad_precios_distribuciones(
    precios,
    indice_derivado,
    *,
    benchmark: str,
    clase: str,
) -> bytes:
    """Exporta las entradas originales y el nivel total-return calculado por fila."""
    precios_validados = tuple(precios)
    indice_validado = tuple(indice_derivado)
    if not precios_validados or len(precios_validados) != len(indice_validado):
        raise ErrorValidacion(
            "La trazabilidad requiere la misma cantidad de precios y niveles derivados."
        )
    if any(
        precio.fecha != indice.fecha
        for precio, indice in zip(precios_validados, indice_validado)
    ):
        raise ErrorValidacion(
            "Las fechas de precios y del índice derivado deben coincidir fila por fila."
        )

    buffer = StringIO(newline="")
    campos = [
        "benchmark",
        "clase_activo",
        "fecha",
        "precio_no_ajustado",
        "distribucion_por_unidad",
        "moneda",
        "tipo_indice",
        "base_precio",
        "fuente_original",
        "referencia_original",
        "nivel_indice_total_return_derivado",
        "metodo",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    formula = (
        "TRI_t = TRI_(t-1) * (P_t + D_t) / P_(t-1); "
        "TRI inicial = 100; distribución reinvertida al cierre de su fecha"
    )
    for precio, indice in zip(precios_validados, indice_validado):
        escritor.writerow(
            {
                "benchmark": _texto_csv_seguro(benchmark),
                "clase_activo": _texto_csv_seguro(clase),
                "fecha": precio.fecha.isoformat(),
                "precio_no_ajustado": str(precio.precio_no_ajustado),
                "distribucion_por_unidad": str(precio.distribucion_por_unidad),
                "moneda": precio.moneda,
                "tipo_indice": precio.tipo_indice,
                "base_precio": precio.base_precio,
                "fuente_original": _texto_csv_seguro(precio.fuente),
                "referencia_original": _texto_csv_seguro(precio.referencia),
                "nivel_indice_total_return_derivado": str(indice.nivel_indice),
                "metodo": formula,
            }
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


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




def _csv_escenarios_benchmark(
    resultados,
    *,
    benchmark: str,
    clase: str,
    tasas_brutas_pct: dict[str, Decimal],
    costos_pct: Decimal,
    impuesto_pct: Decimal,
    origen_tasa_base: str = "SUPUESTO_MANUAL",
    resumen_historico=None,
    cagr_historico_usado: bool = False,
    metodo_serie: str = "INDICE_TOTAL_RETURN_IMPORTADO",
) -> bytes:
    """Exporta los escenarios de sensibilidad y sus supuestos declarados."""
    buffer = StringIO(newline="")
    campos = [
        "benchmark",
        "clase_activo",
        "escenario",
        "rendimiento_bruto_pct",
        "costos_anuales_pct",
        "impuesto_estimado_sobre_rendimiento_pct",
        "rendimiento_neto_pct",
        "valor_capital_original_final_usd",
        "valor_cuotas_reinvertidas_final_usd",
        "brecha_final_usd",
        "origen_tasa_base",
        "historia_fecha_inicio",
        "historia_fecha_fin",
        "historia_moneda",
        "historia_tipo_indice",
        "historia_metodo_serie",
        "historia_observaciones",
        "cagr_historico_anualizado_pct",
        "cagr_historico_usado_como_base",
        "naturaleza",
    ]
    escritor = csv.DictWriter(
        buffer,
        fieldnames=campos,
        delimiter=";",
        lineterminator="\n",
    )
    escritor.writeheader()
    for resultado in resultados:
        escritor.writerow(
            {
                "benchmark": _texto_csv_seguro(benchmark),
                "clase_activo": _texto_csv_seguro(clase),
                "escenario": resultado.nombre,
                "rendimiento_bruto_pct": str(tasas_brutas_pct[resultado.nombre]),
                "costos_anuales_pct": str(costos_pct),
                "impuesto_estimado_sobre_rendimiento_pct": str(impuesto_pct),
                "rendimiento_neto_pct": str(resultado.tasa_anual_neta_usd * Decimal("100")),
                "valor_capital_original_final_usd": str(
                    resultado.valor_capital_original_final_usd
                ),
                "valor_cuotas_reinvertidas_final_usd": str(
                    resultado.valor_cuotas_reinvertidas_final_usd
                ),
                "brecha_final_usd": str(resultado.brecha_final_usd),
                "origen_tasa_base": _texto_csv_seguro(origen_tasa_base),
                "historia_fecha_inicio": (
                    resumen_historico.fecha_inicio.isoformat()
                    if resumen_historico is not None else ""
                ),
                "historia_fecha_fin": (
                    resumen_historico.fecha_fin.isoformat()
                    if resumen_historico is not None else ""
                ),
                "historia_moneda": (
                    resumen_historico.moneda if resumen_historico is not None else ""
                ),
                "historia_tipo_indice": (
                    resumen_historico.tipo_indice
                    if resumen_historico is not None else ""
                ),
                "historia_metodo_serie": (
                    _texto_csv_seguro(metodo_serie)
                    if resumen_historico is not None else ""
                ),
                "historia_observaciones": (
                    str(resumen_historico.cantidad_observaciones)
                    if resumen_historico is not None else ""
                ),
                "cagr_historico_anualizado_pct": (
                    str(resumen_historico.rendimiento_anualizado * Decimal("100"))
                    if resumen_historico is not None else ""
                ),
                "cagr_historico_usado_como_base": str(cagr_historico_usado).lower(),
                "naturaleza": (
                    "SENSIBILIDAD_CON_CAGR_HISTORICO"
                    if cagr_historico_usado
                    else "SENSIBILIDAD_SUPUESTO_MANUAL"
                ),
            }
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _csv_backtest_indice_historico(
    resultado_backtest,
    *,
    benchmark: str,
    clase: str,
    observaciones,
    metodo_serie: str = "INDICE_TOTAL_RETURN_IMPORTADO",
) -> bytes:
    """Exporta el backtest junto con la procedencia de la serie utilizada."""
    buffer = StringIO(newline="")
    campos = [
        "benchmark",
        "clase_activo",
        "moneda_serie",
        "tipo_indice",
        "fuentes_serie",
        "referencias_serie",
        "cantidad_observaciones",
        "fecha_inicio_operacion",
        "fecha_fin_operacion",
        "fecha_observacion_inicio",
        "fecha_observacion_fin",
        "desfase_inicio_dias",
        "desfase_fin_dias",
        "capital_inicial_usd",
        "cantidad_flujos",
        "valor_final_capital_original_usd",
        "valor_final_cuotas_reinvertidas_usd",
        "brecha_final_usd",
        "rendimiento_anualizado_capital_original",
        "xirr_cartera_reinvertida",
        "metodo_serie",
        "metodologia",
    ]
    escritor = csv.DictWriter(
        buffer, fieldnames=campos, delimiter=";", lineterminator="\n"
    )
    escritor.writeheader()
    fuentes = " | ".join(sorted({observacion.fuente for observacion in observaciones}))
    referencias = " | ".join(
        sorted(
            {
                observacion.referencia
                for observacion in observaciones
                if observacion.referencia
            }
        )
    )
    escritor.writerow(
        {
            "benchmark": _texto_csv_seguro(benchmark),
            "clase_activo": _texto_csv_seguro(clase),
            "moneda_serie": resultado_backtest.moneda,
            "tipo_indice": resultado_backtest.tipo_indice,
            "fuentes_serie": _texto_csv_seguro(fuentes),
            "referencias_serie": _texto_csv_seguro(referencias),
            "cantidad_observaciones": resultado_backtest.cantidad_observaciones,
            "fecha_inicio_operacion": resultado_backtest.fecha_inicio_operacion.isoformat(),
            "fecha_fin_operacion": resultado_backtest.fecha_fin_operacion.isoformat(),
            "fecha_observacion_inicio": resultado_backtest.fecha_observacion_inicio.isoformat(),
            "fecha_observacion_fin": resultado_backtest.fecha_observacion_fin.isoformat(),
            "desfase_inicio_dias": resultado_backtest.dias_desfase_inicio,
            "desfase_fin_dias": resultado_backtest.dias_desfase_fin,
            "capital_inicial_usd": str(resultado_backtest.capital_inicial_usd),
            "cantidad_flujos": resultado_backtest.cantidad_flujos,
            "valor_final_capital_original_usd": str(
                resultado_backtest.valor_final_capital_original
            ),
            "valor_final_cuotas_reinvertidas_usd": str(
                resultado_backtest.valor_final_cuotas_reinvertidas
            ),
            "brecha_final_usd": str(resultado_backtest.brecha_final),
            "rendimiento_anualizado_capital_original": str(
                resultado_backtest.rendimiento_anualizado_capital_original
            ),
            "xirr_cartera_reinvertida": (
                ""
                if resultado_backtest.xirr_cartera_reinvertida is None
                else str(resultado_backtest.xirr_cartera_reinvertida)
            ),
            "metodo_serie": _texto_csv_seguro(metodo_serie),
            "metodologia": (
                "BACKTEST_HISTORICO; nivel igual o anterior a cada fecha; "
                "desfase máximo validado; no se extrapolan cotizaciones"
            ),
        }
    )
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
        "cotizacion_inicial_referencia",
        "tasa_contrato_anual_usd",
        "modalidad_contrato",
        "tasa_benchmark_anual_usd",
        "modalidad_benchmark",
        "modo_reposicion_interna",
        "capital_objetivo_fin_carencia_usd",
        "rendimiento_benchmark_carencia_usd",
        "interes_debido_carencia_usd",
        "brecha_rendimiento_benchmark_carencia_usd",
        "valor_original_invertido_fin_plazo_usd",
        "valor_cuotas_reinvertidas_fin_plazo_usd",
        "brecha_valor_final_benchmark_usd",
        "naturaleza_cotizacion",
        "fecha_cotizacion",
        "ars_por_usd",
        "fuente_cotizacion",
        "lado_cotizacion",
        "referencia_cotizacion",
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
            "cotizacion_inicial_fuente": _texto_csv_seguro(resultado.cotizacion_inicial.fuente),
            "cotizacion_inicial_lado": resultado.cotizacion_inicial.lado,
            "cotizacion_inicial_referencia": _texto_csv_seguro(resultado.cotizacion_inicial.referencia),
            "tasa_contrato_anual_usd": str(resultado.tasa_anual_usd),
            "modalidad_contrato": resultado.modalidad_tasa.value,
            "tasa_benchmark_anual_usd": str(resultado.tasa_benchmark_usd),
            "modalidad_benchmark": resultado.modalidad_benchmark.value,
            "modo_reposicion_interna": str(resultado.modo_reposicion_interna).lower(),
            "capital_objetivo_fin_carencia_usd": str(resultado.capital_objetivo_fin_carencia_usd),
            "rendimiento_benchmark_carencia_usd": str(resultado.rendimiento_benchmark_carencia_usd),
            "interes_debido_carencia_usd": str(resultado.interes_debido_carencia_usd),
            "brecha_rendimiento_benchmark_carencia_usd": str(resultado.brecha_rendimiento_benchmark_carencia_usd),
            "valor_original_invertido_fin_plazo_usd": str(resultado.valor_original_invertido_fin_plazo_usd),
            "valor_cuotas_reinvertidas_fin_plazo_usd": str(resultado.valor_cuotas_reinvertidas_fin_plazo_usd),
            "brecha_valor_final_benchmark_usd": str(resultado.brecha_valor_final_benchmark_usd),
            "naturaleza_cotizacion": "" if cotizacion is None else cotizacion.naturaleza,
            "fecha_cotizacion": "" if cotizacion is None else cotizacion.fecha_cotizacion.isoformat(),
            "ars_por_usd": "" if cotizacion is None else str(cotizacion.ars_por_usd),
            "fuente_cotizacion": "" if cotizacion is None else _texto_csv_seguro(cotizacion.fuente),
            "lado_cotizacion": "" if cotizacion is None else cotizacion.lado,
            "referencia_cotizacion": "" if cotizacion is None else _texto_csv_seguro(cotizacion.referencia),
            "equivalente_ars": "" if cuota.equivalente_ars is None else str(cuota.equivalente_ars),
        })
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _cotizaciones_desde_editor(filas, cuotas) -> dict[date, CotizacionUnidad]:
    """Valida cotizaciones editadas por cuota y devuelve un mapa por vencimiento.

    Las filas sin cotización, fuente ni referencia se consideran vacías. Si una
    fila está parcialmente completada, se rechaza para evitar ocultar errores
    al calcular equivalentes ARS.
    """
    if hasattr(filas, "to_dict"):
        filas = filas.to_dict(orient="records")
    if len(filas) != len(cuotas):
        raise ErrorValidacion(
            "La tabla de cotizaciones debe conservar una fila por cada vencimiento."
        )

    resultado: dict[date, CotizacionUnidad] = {}
    for cuota, fila in zip(cuotas, filas):
        texto_tasa = str(fila.get("ars_por_usd") or "").strip()
        fuente = str(fila.get("fuente") or "").strip()
        referencia = str(fila.get("referencia") or "").strip()
        if not texto_tasa and not fuente and not referencia:
            continue
        if not texto_tasa:
            raise ErrorValidacion(
                f"Cuota {cuota.numero}: ingresá la cotización ARS/USD o vaciá la fila."
            )
        if not fuente:
            raise ErrorValidacion(
                f"Cuota {cuota.numero}: indicá la fuente/instrumento de la cotización."
            )

        ars_por_usd = _parsear_decimal_es(
            texto_tasa,
            etiqueta=f"la cotización de la cuota {cuota.numero}",
            minimo=Decimal("0.000001"),
            maximo=Decimal("1000000000"),
            decimales_maximos=6,
        )
        lado = str(fila.get("lado") or "").strip().upper()
        naturaleza = str(fila.get("naturaleza") or "").strip().upper()
        if lado not in {"VENDEDOR", "COMPRADOR"}:
            raise ErrorValidacion(
                f"Cuota {cuota.numero}: el lado debe ser VENDEDOR o COMPRADOR."
            )
        cotizacion = CotizacionUnidad(
            fecha_cotizacion=cuota.fecha_vencimiento,
            ars_por_usd=ars_por_usd,
            fuente=fuente,
            lado=lado,
            naturaleza=naturaleza,
            referencia=referencia or None,
        )
        resultado[cuota.fecha_vencimiento] = cotizacion

    return resultado


COLUMNAS_CSV_COTIZACIONES = (
    "numero_cuota",
    "fecha_vencimiento",
    "ars_por_usd",
    "fuente",
    "lado",
    "naturaleza",
    "referencia",
)


def _csv_plantilla_cotizaciones(resultado_base, lado_default: str) -> bytes:
    """Crea una plantilla con punto y coma para admitir comas decimales."""
    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=COLUMNAS_CSV_COTIZACIONES,
        delimiter=";",
        lineterminator="\n",
    )
    writer.writeheader()
    for cuota in resultado_base.cuotas:
        writer.writerow(
            {
                "numero_cuota": cuota.numero,
                "fecha_vencimiento": cuota.fecha_vencimiento.isoformat(),
                "ars_por_usd": "",
                "fuente": "",
                "lado": lado_default,
                "naturaleza": "SUPUESTO",
                "referencia": "",
            }
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _leer_csv_cotizaciones(
    contenido: bytes,
    resultado_base,
    *,
    lado_default: str,
) -> list[dict[str, object]]:
    """Carga cotizaciones desde CSV sin usar float ni asociarlas por posición.

    El separador es punto y coma, lo que permite tasas con formato regional
    como 1.250,500000. Se verifica la cuota y el vencimiento de cada fila.
    """
    if not isinstance(contenido, bytes) or not contenido:
        raise ErrorValidacion("El archivo CSV de cotizaciones está vacío.")
    if len(contenido) > 1_000_000:
        raise ErrorValidacion("El archivo CSV supera el tamaño permitido de 1 MB.")

    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ErrorValidacion(
            "El CSV debe estar codificado en UTF-8. Descargá la plantilla y completala."
        ) from exc

    lector = csv.DictReader(StringIO(texto), delimiter=";")
    if not lector.fieldnames:
        raise ErrorValidacion("El CSV no contiene encabezados.")
    encabezados = [str(nombre or "").strip() for nombre in lector.fieldnames]
    if len(encabezados) != len(set(encabezados)):
        raise ErrorValidacion("El CSV contiene encabezados duplicados.")
    faltantes = set(COLUMNAS_CSV_COTIZACIONES) - set(encabezados)
    if faltantes:
        raise ErrorValidacion(
            "El CSV no tiene las columnas requeridas: "
            + ", ".join(sorted(faltantes))
            + ". Usá la plantilla con separador punto y coma (;)."
        )
    lector.fieldnames = encabezados

    cuotas = tuple(resultado_base.cuotas)
    cuotas_por_numero = {int(cuota.numero): cuota for cuota in cuotas}
    fila_por_numero = {int(cuota.numero): indice for indice, cuota in enumerate(cuotas)}
    filas = _filas_cotizaciones_editables(resultado_base, lado_default)
    numeros_vistos: set[int] = set()
    cantidad_filas = 0

    for numero_linea, registro in enumerate(lector, start=2):
        if None in registro:
            raise ErrorValidacion(
                f"Fila {numero_linea}: hay más campos que columnas; verificá el separador ';'."
            )
        valores = {
            str(clave): str(valor or "").strip()
            for clave, valor in registro.items()
            if clave is not None
        }
        if not any(valores.values()):
            continue
        cantidad_filas += 1

        numero_texto = valores.get("numero_cuota", "")
        fecha_texto = valores.get("fecha_vencimiento", "")
        if not numero_texto.isdigit() or not fecha_texto:
            raise ErrorValidacion(
                f"Fila {numero_linea}: el número de cuota y el vencimiento son obligatorios."
            )
        numero = int(numero_texto)
        if numero not in cuotas_por_numero:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la cuota {numero} no existe en el plan actual."
            )
        if numero in numeros_vistos:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la cuota {numero} está repetida en el CSV."
            )
        numeros_vistos.add(numero)

        try:
            vencimiento = date.fromisoformat(fecha_texto)
        except ValueError as exc:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe tener formato AAAA-MM-DD."
            ) from exc
        if vencimiento.isoformat() != fecha_texto:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fecha debe tener formato AAAA-MM-DD."
            )
        cuota = cuotas_por_numero[numero]
        if vencimiento != cuota.fecha_vencimiento:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la cuota {numero} vence el "
                f"{cuota.fecha_vencimiento.isoformat()}, no el {fecha_texto}."
            )

        texto_tasa = valores.get("ars_por_usd", "")
        fuente = valores.get("fuente", "")
        referencia = valores.get("referencia", "")
        if not texto_tasa and not fuente and not referencia:
            continue
        if not texto_tasa:
            raise ErrorValidacion(
                f"Fila {numero_linea}: ingresá la cotización ARS/USD o vaciá los campos de esa fila."
            )
        if not fuente:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la fuente/instrumento es obligatoria."
            )

        ars_por_usd = _parsear_decimal_es(
            texto_tasa,
            etiqueta=f"la cotización de la cuota {numero}",
            minimo=Decimal("0.000001"),
            maximo=Decimal("1000000000"),
            decimales_maximos=6,
        )
        lado = valores.get("lado", "").upper()
        naturaleza = valores.get("naturaleza", "").upper()
        if lado not in {"VENDEDOR", "COMPRADOR"}:
            raise ErrorValidacion(
                f"Fila {numero_linea}: el lado debe ser VENDEDOR o COMPRADOR."
            )
        if naturaleza not in {"OBSERVADA", "PROYECTADA", "SUPUESTO"}:
            raise ErrorValidacion(
                f"Fila {numero_linea}: la naturaleza debe ser OBSERVADA, PROYECTADA o SUPUESTO."
            )

        CotizacionUnidad(
            fecha_cotizacion=vencimiento,
            ars_por_usd=ars_por_usd,
            fuente=fuente,
            lado=lado,
            naturaleza=naturaleza,
            referencia=referencia or None,
        )
        indice = fila_por_numero[numero]
        filas[indice].update(
            {
                "ars_por_usd": texto_tasa,
                "fuente": fuente,
                "lado": lado,
                "naturaleza": naturaleza,
                "referencia": referencia,
            }
        )

    if cantidad_filas == 0:
        raise ErrorValidacion("El CSV no contiene filas de cuotas para importar.")
    return filas


def _texto_csv_seguro(valor: str | None) -> str:
    """Mitiga la inyección de fórmulas al abrir CSV exportados en hojas de cálculo."""
    texto = str(valor or "")
    contenido = texto.lstrip(" \t\r\n")
    if contenido.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + texto
    return texto


def _filas_cotizaciones_editables(resultado_base, lado_default: str) -> list[dict[str, object]]:
    """Prepara una fila editable por vencimiento; la cotización queda vacía a propósito."""
    return [
        {
            "numero_cuota": cuota.numero,
            "fecha_vencimiento": cuota.fecha_vencimiento.isoformat(),
            "ars_por_usd": "",
            "fuente": "",
            "lado": lado_default,
            "naturaleza": "SUPUESTO",
            "referencia": "",
        }
        for cuota in resultado_base.cuotas
    ]


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

    tipo_plan = st.radio(
        "Qué querés medir",
        options=[
            "Autopréstamo / reposición interna",
            "Préstamo entre personas",
        ],
        horizontal=True,
        key="sim_usd_tipo_plan",
        help=(
            "En el plan interno se reinvierte el rendimiento objetivo durante la carencia "
            "y se incorpora al monto que se busca reponer. En un préstamo entre personas, "
            "el interés de carencia se trata por separado."
        ),
    )
    modo_reposicion_interna = tipo_plan == "Autopréstamo / reposición interna"
    if modo_reposicion_interna:
        st.info(
            "Plan interno: el capital se proyecta hasta el final de la carencia como si "
            "hubiera seguido invertido al rendimiento objetivo. Ese crecimiento forma "
            "la base interna que se busca reponer; no se registra como cláusula legal "
            "de capitalización ni crea una deuda frente a uno mismo."
        )

    col1, col2 = st.columns(2)
    with col1:
        capital_ars_texto = st.text_input(
            "Capital utilizado para la compra (ARS)",
            value="1.000.000,00",
            help="Hasta 2 decimales. Podés escribir 1.000.000,50 o 1000000,50.",
            key="sim_usd_capital_ars",
        )
        fecha_desembolso = st.date_input(
            "Fecha de desembolso / compra",
            value=date.today(), key="sim_usd_fecha_desembolso",
        )
        tasa_usd_pct_texto = st.text_input(
            "Rendimiento anual BRUTO estimado del benchmark en USD (%)",
            value="4,0000",
            help=(
                "Supuesto manual antes de costos e impuestos, con hasta 4 decimales. "
                "No es una tasa de mercado verificada ni un rendimiento garantizado."
            ),
            key="sim_usd_tasa_anual",
        )
        benchmark_usd = st.text_input(
            "Benchmark / inversión alternativa de referencia",
            value="",
            placeholder="Ej.: cartera USD, bono o instrumento que vas a analizar",
            key="sim_usd_benchmark_inversion",
            help=(
                "Nombre descriptivo. El simulador no busca ni verifica datos externos "
                "del instrumento o sus rendimientos."
            ),
        )
        clase_benchmark = st.selectbox(
            "Clase de activo del benchmark",
            options=[
                "Cartera / ETF",
                "Bonos / renta fija",
                "Cuenta remunerada / depósito",
                "Instrumento privado",
                "Otro / hipótesis propia",
            ],
            key="sim_usd_benchmark_clase",
        )
        col_costos, col_impuesto, col_margen = st.columns(3)
        with col_costos:
            costos_benchmark_pct_texto = st.text_input(
                "Costos anuales estimados (%)",
                value="0,0000",
                key="sim_usd_benchmark_costos_pct",
                help=(
                    "Proporción anual estimada del capital para gastos de administración "
                    "u operación. Se resta al rendimiento bruto."
                ),
            )
        with col_impuesto:
            impuesto_benchmark_pct_texto = st.text_input(
                "Impuesto estimado sobre ganancia (%)",
                value="0,0000",
                key="sim_usd_benchmark_impuesto_pct",
                help=(
                    "Supuesto aplicado solo al rendimiento positivo luego de costos. "
                    "No es una liquidación fiscal ni una recomendación tributaria."
                ),
            )
        with col_margen:
            margen_escenarios_pct_texto = st.text_input(
                "Margen por escenario (puntos porcentuales)",
                value="2,0000",
                key="sim_usd_benchmark_margen_escenarios_pct",
                help=(
                    "Conservador = rendimiento bruto base − margen; alto = base + margen. "
                    "Son sensibilidades editables, no pronósticos."
                ),
            )
        if modo_reposicion_interna:
            st.caption(
                "En el autopréstamo, el rendimiento neto base debe ser positivo para "
                "reconstruir el capital, conservar poder de compra en USD y sumar una "
                "ganancia/costo de oportunidad objetivo."
            )
        else:
            st.caption(
                "El benchmark externo puede tener rendimiento negativo. Se comparará "
                "contra la tasa contractual por separado; la tasa del préstamo no puede "
                "ser negativa y no se modifica al cambiar escenarios del benchmark."
            )
        modalidad_benchmark_texto = st.selectbox(
            "Modalidad del rendimiento de la inversión alternativa",
            options=["TEA", "TNA"],
            format_func=lambda x: (
                "TNA en USD — nominal anual" if x == "TNA"
                else "TEA en USD — efectiva anual"
            ),
            key="sim_usd_modalidad_tasa",
        )
        if modo_reposicion_interna:
            # La tasa efectiva se convierte a Decimal después de validar el texto.
            tasa_contractual_pct_texto = tasa_usd_pct_texto
            modalidad_contractual_texto = modalidad_benchmark_texto
        else:
            tasa_contractual_pct_texto = st.text_input(
                "Tasa anual del préstamo en USD (%)",
                value="4,0000",
                help=(
                    "Hasta 4 decimales. Tasa acordada entre las personas; puede "
                    "diferir del benchmark. El 4% inicial es ilustrativo, no una "
                    "recomendación ni una tasa de mercado."
                ),
                key="sim_usd_tasa_contractual",
            )
            modalidad_contractual_texto = st.selectbox(
                "Modalidad de la tasa contractual",
                options=["TEA", "TNA"],
                format_func=lambda x: (
                    "TEA contractual en USD" if x == "TEA"
                    else "TNA contractual en USD"
                ),
                key="sim_usd_modalidad_contractual",
            )
    with col2:
        tc_inicial_texto = st.text_input(
            "Cotización inicial (ARS por USD)",
            value="1.000,000000",
            help="Hasta 6 decimales. Usá coma decimal o formato canónico; la cotización debe ser positiva.",
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

    resumen_benchmark_historico = None
    observaciones_benchmark_historico = ()
    contexto_serie_benchmark = (benchmark_usd.strip(), clase_benchmark)

    with st.expander("Serie histórica del benchmark (opcional)", expanded=False):
        st.caption(
            "Podés importar un índice de retorno total ya calculado por su proveedor o "
            "derivarlo de precios de cierre no ajustados más distribuciones en efectivo. "
            "No uses precios ajustados junto con dividendos/cupones: contarías la misma "
            "distribución dos veces. No se consulta mercado en vivo."
        )
        metodo_importacion_historica = st.selectbox(
            "Formato de la serie histórica",
            options=[
                "Índice total-return ya calculado",
                "Precio no ajustado + distribuciones por unidad",
            ],
            key="sim_usd_metodo_importacion_serie",
            help=(
                "El índice derivado reinvierte cada distribución al cierre de su fecha. "
                "La etiqueta bruto/neto debe coincidir con el tratamiento del dividendo/"
                "cupón indicado por la fuente; no es una liquidación fiscal."
            ),
        )
        st.download_button(
            "Descargar plantilla de serie histórica CSV",
            data=_csv_plantilla_indice_retorno_total(),
            file_name="plantilla-indice-retorno-total.csv",
            mime="text/csv",
            key="sim_usd_plantilla_serie_historica",
        )
        if metodo_importacion_historica == "Precio no ajustado + distribuciones por unidad":
            st.download_button(
                "Descargar plantilla de precios + distribuciones CSV",
                data=_csv_plantilla_precio_distribucion(),
                file_name="plantilla-precios-distribuciones.csv",
                mime="text/csv",
                key="sim_usd_plantilla_precios_distribuciones",
            )
        archivo_serie = st.file_uploader(
            "Importar índice histórico de retorno total",
            type=["csv"],
            key="sim_usd_archivo_serie_historica",
            help=(
                "UTF-8, separador punto y coma (;), fechas AAAA-MM-DD y al menos "
                "30 días entre la primera y última observación."
            ),
        )
        if st.button(
            "Analizar serie histórica",
            key="sim_usd_analizar_serie_historica",
        ):
            if archivo_serie is None:
                st.warning("Elegí el CSV de la serie antes de analizarlo.")
            elif not benchmark_usd.strip():
                st.warning("Identificá el benchmark antes de asociarle una serie histórica.")
            else:
                # Una carga nueva que falla no debe dejar activa, sin aviso, una
                # serie anterior como si fuera el archivo recién seleccionado.
                st.session_state.pop("sim_usd_serie_benchmark_historica", None)
                st.session_state.pop("sim_usd_contexto_serie_benchmark", None)
                st.session_state.pop("sim_usd_metodo_serie_benchmark", None)
                st.session_state.pop("sim_usd_observaciones_precio_benchmark", None)
                st.session_state["sim_usd_usar_cagr_historico"] = False
                try:
                    if metodo_importacion_historica == "Precio no ajustado + distribuciones por unidad":
                        (
                            resumen_importado,
                            observaciones_importadas,
                            observaciones_precio_importadas,
                        ) = _leer_csv_precio_distribucion(archivo_serie.getvalue())
                        metodo_serie_importada = (
                            "PRECIO_NO_AJUSTADO_DISTRIBUCIONES_REINVERTIDAS_AL_CIERRE"
                        )
                    else:
                        resumen_importado, observaciones_importadas = (
                            _leer_csv_indice_retorno_total(archivo_serie.getvalue())
                        )
                        observaciones_precio_importadas = ()
                        metodo_serie_importada = "INDICE_TOTAL_RETURN_IMPORTADO"
                except (ErrorValidacion, ValueError, ArithmeticError) as exc:
                    st.error(str(exc))
                else:
                    st.session_state["sim_usd_serie_benchmark_historica"] = (
                        observaciones_importadas
                    )
                    st.session_state["sim_usd_contexto_serie_benchmark"] = (
                        benchmark_usd.strip(),
                        clase_benchmark,
                    )
                    st.session_state["sim_usd_metodo_serie_benchmark"] = (
                        metodo_serie_importada
                    )
                    st.session_state["sim_usd_observaciones_precio_benchmark"] = (
                        observaciones_precio_importadas
                    )
                    st.session_state["sim_usd_usar_cagr_historico"] = False
                    st.success(
                        f"Serie validada: {resumen_importado.cantidad_observaciones} "
                        f"observaciones, {resumen_importado.dias_transcurridos} días, "
                        f"moneda {resumen_importado.moneda}."
                    )

        if st.button(
            "Quitar serie histórica cargada",
            key="sim_usd_quitar_serie_historica",
            disabled=not bool(
                st.session_state.get("sim_usd_serie_benchmark_historica")
            ),
        ):
            st.session_state.pop("sim_usd_serie_benchmark_historica", None)
            st.session_state.pop("sim_usd_contexto_serie_benchmark", None)
            st.session_state.pop("sim_usd_metodo_serie_benchmark", None)
            st.session_state.pop("sim_usd_observaciones_precio_benchmark", None)
            st.session_state["sim_usd_usar_cagr_historico"] = False

        observaciones_benchmark_historico = tuple(
            st.session_state.get("sim_usd_serie_benchmark_historica", ())
        )
        observaciones_precio_benchmark_historico = tuple(
            st.session_state.get("sim_usd_observaciones_precio_benchmark", ())
        )
        contexto_guardado = st.session_state.get(
            "sim_usd_contexto_serie_benchmark", ("", "")
        )
        if observaciones_benchmark_historico:
            try:
                resumen_benchmark_historico = (
                    resumir_serie_indice_retorno_total(
                        observaciones_benchmark_historico
                    )
                )
            except ErrorValidacion as exc:
                st.error(
                    f"La serie guardada ya no es válida: {exc}. Quitala e importala otra vez."
                )
                resumen_benchmark_historico = None

        if resumen_benchmark_historico is not None:
            metodo_serie_guardado = st.session_state.get(
                "sim_usd_metodo_serie_benchmark", "INDICE_TOTAL_RETURN_IMPORTADO"
            )
            etiqueta_metodo_serie = (
                "Índice total-return importado del proveedor"
                if metodo_serie_guardado == "INDICE_TOTAL_RETURN_IMPORTADO"
                else "Índice total-return derivado de precio no ajustado + distribuciones reinvertidas"
            )
            st.caption(
                f"Serie cargada para: {contexto_guardado[0]} "
                f"({contexto_guardado[1]}). Método: {etiqueta_metodo_serie}. "
                "El CAGR es retrospectivo, no una predicción."
            )
            metricas_hist = st.columns(3)
            metricas_hist[0].metric(
                "Retorno acumulado histórico",
                _pct(resumen_benchmark_historico.rendimiento_acumulado),
            )
            metricas_hist[1].metric(
                "CAGR histórico anualizado",
                _pct(resumen_benchmark_historico.rendimiento_anualizado),
            )
            metricas_hist[2].metric(
                "Caída máxima observada",
                _pct(resumen_benchmark_historico.caida_maxima),
            )
            tabla_serie_historica = [
                {
                    "Fecha": observacion.fecha.isoformat(),
                    "Nivel índice total-return": _decimal_local(
                        observacion.nivel_indice, 10
                    ),
                    "Moneda": observacion.moneda,
                    "Tipo de índice": observacion.tipo_indice,
                    "Fuente": observacion.fuente,
                    "Referencia": observacion.referencia or "",
                }
                for observacion in observaciones_benchmark_historico
            ]
            st.dataframe(
                tabla_serie_historica,
                hide_index=True,
                use_container_width=True,
                height=260,
            )
            if observaciones_precio_benchmark_historico:
                st.caption(
                    "Datos de entrada usados para derivar el índice: precios de cierre "
                    "no ajustados y distribuciones por unidad. Revisá las fuentes y "
                    "referencias originales; la aplicación no verifica al proveedor."
                )
                tabla_precios_historicos = [
                    {
                        "Fecha": observacion.fecha.isoformat(),
                        "Precio no ajustado": _decimal_local(
                            observacion.precio_no_ajustado, 10
                        ),
                        "Distribución por unidad": _decimal_local(
                            observacion.distribucion_por_unidad, 10
                        ),
                        "Moneda": observacion.moneda,
                        "Tipo de índice declarado": observacion.tipo_indice,
                        "Base de precio": observacion.base_precio,
                        "Fuente": observacion.fuente,
                        "Referencia": observacion.referencia or "",
                    }
                    for observacion in observaciones_precio_benchmark_historico
                ]
                st.dataframe(
                    tabla_precios_historicos,
                    hide_index=True,
                    use_container_width=True,
                    height=260,
                )
        else:
            st.caption(
                "Todavía no hay una serie validada en esta sesión. La tasa manual "
                "del benchmark sigue disponible."
            )

        identidad_serie_coincide = (
            resumen_benchmark_historico is not None
            and contexto_guardado == contexto_serie_benchmark
        )
        tasa_historica_utilizable = (
            identidad_serie_coincide
            and resumen_benchmark_historico is not None
            and resumen_benchmark_historico.moneda == "USD"
            and resumen_benchmark_historico.tipo_indice == "BRUTO_TOTAL_RETURN"
            and Decimal("-1") < resumen_benchmark_historico.rendimiento_anualizado
            <= Decimal("1")
        )
        if (
            not tasa_historica_utilizable
            and st.session_state.get("sim_usd_usar_cagr_historico", False)
        ):
            st.session_state["sim_usd_usar_cagr_historico"] = False
        usar_cagr_historico = st.checkbox(
            "Usar CAGR histórico como rendimiento bruto base (solo hipótesis)",
            value=False,
            key="sim_usd_usar_cagr_historico",
            disabled=not tasa_historica_utilizable,
            help=(
                "Solo para un índice BRUTO_TOTAL_RETURN expresado en USD. Al activarlo, "
                "el CAGR observado se usa como tasa bruta base; después se aplican costos/"
                "impuesto y márgenes. Un índice NETO no se vuelve a cargar como bruto. "
                "No implica que el futuro vaya a repetir el pasado."
            ),
        )
        if resumen_benchmark_historico is not None and not identidad_serie_coincide:
            st.warning(
                "La serie pertenece a otro nombre/clase de benchmark. No se aplicará "
                "al plan actual hasta que cargues una serie asociada a esta selección."
            )
        elif (
            resumen_benchmark_historico is not None
            and resumen_benchmark_historico.moneda != "USD"
        ):
            st.warning(
                "La serie histórica está expresada en "
                f"{resumen_benchmark_historico.moneda}; no se convierte automáticamente "
                "a USD ni se puede usar directamente como tasa base del plan en USD."
            )
        elif (
            resumen_benchmark_historico is not None
            and resumen_benchmark_historico.tipo_indice != "BRUTO_TOTAL_RETURN"
        ):
            st.warning(
                "La serie está clasificada como NETO_TOTAL_RETURN. Se muestran sus "
                "estadísticas históricas, pero no se aplicará como rendimiento bruto "
                "para evitar volver a descontar costos/impuestos."
            )
        elif (
            resumen_benchmark_historico is not None
            and not tasa_historica_utilizable
            and resumen_benchmark_historico.moneda == "USD"
        ):
            st.warning(
                "El CAGR histórico está fuera del rango admitido para la tasa base "
                "(-100% a 100%). Se muestran sus estadísticas, pero no se aplicará al plan."
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

    if modo_reposicion_interna:
        # El crecimiento de benchmark ya se incorpora a la base objetivo; no se
        # agrega un interés contractual de carencia en paralelo.
        tratamiento_texto = TratamientoCarencia.SIN_INTERES.value
        st.caption(
            "En este modo no se suma interés simple por carencia: el rendimiento del "
            "benchmark se reinvierte y queda incluido en el objetivo interno."
        )
    else:
        tratamiento_texto = st.selectbox(
            "Tratamiento del interés durante la carencia",
            options=[
                TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value,
                TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value,
                TratamientoCarencia.SIN_INTERES.value,
            ],
            format_func=lambda x: {
                TratamientoCarencia.SIN_INTERES.value: "Sin interés durante la carencia",
                TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA.value: "Diferir interés simple a la primera cuota",
                TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO.value: "Distribuir interés simple entre cuotas",
            }[x],
            key="sim_usd_tratamiento",
        )
    metodo_equivalencia = st.selectbox(
        "Cómo calcular el equivalente ARS de cada cuota",
        options=[
            "Sin conversión ARS",
            "Proyección mensual (escenario)",
            "Cotización individual por cuota",
        ],
        key="sim_usd_metodo_equivalencia",
        help=(
            "Podés dejar el plan solo en USD, usar una proyección mensual editable "
            "o ingresar una cotización independiente para cada vencimiento. La "
            "cotización inicial nunca se reutiliza silenciosamente para cuotas futuras."
        ),
    )
    usar_proyeccion = metodo_equivalencia == "Proyección mensual (escenario)"
    usar_cotizaciones_manuales = (
        metodo_equivalencia == "Cotización individual por cuota"
    )
    variacion_pct_texto = "0,00"
    if usar_proyeccion:
        variacion_pct_texto = st.text_input(
            "Variación mensual proyectada del tipo de cambio (%)",
            value="3,00",
            help=(
                "Hasta 2 decimales. Se aplica de forma compuesta mes a mes desde la "
                "cotización inicial. Es un supuesto editable, no una cotización real."
            ),
            key="sim_usd_variacion_mensual",
        )
        st.warning(
            "Los equivalentes ARS de la tabla son escenarios proyectados, no "
            "cotizaciones observadas. El cronograma en USD no cambia al modificar "
            "esta hipótesis."
        )
    elif usar_cotizaciones_manuales:
        st.info(
            "Ingresá una cotización, fuente/instrumento y lado para cada vencimiento "
            "que quieras valuar. Las filas vacías quedan sin equivalente ARS; el "
            "total ARS se mostrará solo cuando todas las cuotas tengan cotización."
        )

    try:
        capital_ars = _parsear_decimal_es(
            capital_ars_texto,
            etiqueta="el capital en ARS",
            minimo=Decimal("1000"),
            maximo=Decimal("1000000000000"),
            decimales_maximos=2,
        )
        if usar_cagr_historico:
            if (
                resumen_benchmark_historico is None
                or not tasa_historica_utilizable
            ):
                raise ErrorValidacion(
                    "No hay un CAGR histórico USD válido asociado al benchmark actual."
                )
            tasa_usd_bruta_pct = (
                resumen_benchmark_historico.rendimiento_anualizado
                * Decimal("100")
            )
            fuente_tasa_base = "CAGR_HISTORICO_TOTAL_RETURN"
        else:
            tasa_usd_bruta_pct = _parsear_decimal_es(
                tasa_usd_pct_texto,
                etiqueta="el rendimiento anual bruto del benchmark",
                minimo=Decimal("-99.9999"),
                maximo=Decimal("100"),
                decimales_maximos=4,
            )
            fuente_tasa_base = "SUPUESTO_MANUAL"
        costos_benchmark_pct = _parsear_decimal_es(
            costos_benchmark_pct_texto,
            etiqueta="los costos anuales del benchmark",
            minimo=Decimal("0"),
            maximo=Decimal("100"),
            decimales_maximos=4,
        )
        impuesto_benchmark_pct = _parsear_decimal_es(
            impuesto_benchmark_pct_texto,
            etiqueta="el impuesto estimado del benchmark",
            minimo=Decimal("0"),
            maximo=Decimal("100"),
            decimales_maximos=4,
        )
        margen_escenarios_pct = _parsear_decimal_es(
            margen_escenarios_pct_texto,
            etiqueta="el margen de escenarios",
            minimo=Decimal("0"),
            maximo=Decimal("100"),
            decimales_maximos=4,
        )
        tasas_brutas_escenarios_pct = {
            "Conservador": tasa_usd_bruta_pct - margen_escenarios_pct,
            "Base": tasa_usd_bruta_pct,
            "Alto": tasa_usd_bruta_pct + margen_escenarios_pct,
        }
        if tasas_brutas_escenarios_pct["Alto"] > Decimal("100"):
            raise ErrorValidacion(
                "El escenario alto no puede superar el 100% bruto anual en esta "
                "versión. Reducí el margen o el rendimiento base."
            )
        tasas_benchmark_netas = {
            nombre: calcular_tasa_neta_benchmark_usd(
                tasa_bruta_anual=tasa_bruta_pct / Decimal("100"),
                costos_anuales=costos_benchmark_pct / Decimal("100"),
                impuesto_sobre_rendimiento_positivo=(
                    impuesto_benchmark_pct / Decimal("100")
                ),
            )
            for nombre, tasa_bruta_pct in tasas_brutas_escenarios_pct.items()
        }
        if any(tasa <= Decimal("-1") for tasa in tasas_benchmark_netas.values()):
            raise ErrorValidacion(
                "Algún escenario neto llega a −100% o menos; reducí costos/margen "
                "o ajustá el rendimiento bruto para mantener una valuación definida."
            )
        # El plan usa la tasa neta base; las otras dos quedan como sensibilidad.
        tasa_usd_pct = tasas_benchmark_netas["Base"] * Decimal("100")
        tc_inicial = _parsear_decimal_es(
            tc_inicial_texto,
            etiqueta="la cotización inicial ARS/USD",
            minimo=Decimal("0.000001"),
            maximo=Decimal("1000000000"),
            decimales_maximos=6,
        )
        if modo_reposicion_interna:
            tasa_contractual_pct = tasa_usd_pct
        else:
            tasa_contractual_pct = _parsear_decimal_es(
                tasa_contractual_pct_texto,
                etiqueta="la tasa contractual USD",
                minimo=Decimal("0"),
                maximo=Decimal("100"),
                decimales_maximos=4,
            )
        variacion_pct = (
            _parsear_decimal_es(
                variacion_pct_texto,
                etiqueta="la variación mensual proyectada",
                minimo=Decimal("-99"),
                maximo=Decimal("100"),
                decimales_maximos=2,
            )
            if usar_proyeccion
            else Decimal("0")
        )
    except ErrorValidacion as exc:
        st.error(str(exc))
        return

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
    if modo_reposicion_interna and tasa_usd_pct <= 0:
        st.error(
            "El autopréstamo requiere un rendimiento neto base positivo en USD. "
            "Ajustá rendimiento bruto, costos, impuesto o margen de escenarios."
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
            "capital_desembolso_ars": capital_ars,
            "cotizacion_inicial": cotizacion_inicial,
            "tasa_anual_usd": tasa_contractual_pct / Decimal("100"),
            "modalidad_tasa": ModalidadTasa(modalidad_contractual_texto),
            "tasa_benchmark_usd": tasa_usd_pct / Decimal("100"),
            "modalidad_benchmark": ModalidadTasa(modalidad_benchmark_texto),
            "convencion_dias": convencion,
            "sistema": sistema,
            "fecha_desembolso": fecha_desembolso,
            "meses_carencia": int(meses_carencia),
            "plazo_amortizacion_meses": int(plazo),
            "tratamiento_carencia": tratamiento,
            "modo_reposicion_interna": modo_reposicion_interna,
        }
        resultado_base = simular_unidad_usd(**argumentos)
        cotizaciones: dict[date, CotizacionUnidad] | None = None
        if usar_cotizaciones_manuales:
            st.subheader("Cotizaciones ARS/USD por cuota")
            st.caption(
                "La fecha de cada fila es el vencimiento calculado del plan y no se "
                "puede editar. Dejá la cotización vacía cuando no tengas un dato "
                "verificado o un supuesto explícito para esa cuota."
            )
            firma_calendario = tuple(
                (cuota.numero, cuota.fecha_vencimiento.isoformat())
                for cuota in resultado_base.cuotas
            )
            if (
                st.session_state.get("sim_usd_firma_calendario_cotizaciones")
                != firma_calendario
            ):
                # El modelo base vive en una clave de sesión independiente. No
                # se escribe en la clave del widget: Streamlit reserva allí el
                # DataEditorState de solo lectura y no el contenido tabular.
                st.session_state["sim_usd_firma_calendario_cotizaciones"] = (
                    firma_calendario
                )
                st.session_state["sim_usd_filas_cotizaciones_base"] = (
                    _filas_cotizaciones_editables(
                        resultado_base,
                        lado_default=lado_tc,
                    )
                )
                st.session_state["sim_usd_revision_editor_cotizaciones"] = (
                    int(st.session_state.get("sim_usd_revision_editor_cotizaciones", 0))
                    + 1
                )

            st.download_button(
                "Descargar plantilla CSV de cotizaciones",
                data=_csv_plantilla_cotizaciones(
                    resultado_base,
                    lado_default=lado_tc,
                ),
                file_name="plantilla-cotizaciones-ars-usd.csv",
                mime="text/csv",
                key="sim_usd_plantilla_cotizaciones",
                help=(
                    "Una fila por vencimiento. Conservá las columnas de cuota y "
                    "fecha; completá cotización, fuente, lado y naturaleza."
                ),
            )
            archivo_cotizaciones = st.file_uploader(
                "Importar cotizaciones desde CSV",
                type=["csv"],
                key="sim_usd_archivo_cotizaciones_csv",
                help=(
                    "Usá la plantilla descargada. El archivo debe ser UTF-8 y "
                    "usar punto y coma como separador para admitir comas decimales."
                ),
            )
            if st.button(
                "Aplicar CSV a la tabla",
                key="sim_usd_aplicar_cotizaciones_csv",
            ):
                if archivo_cotizaciones is None:
                    st.warning("Elegí un archivo CSV antes de importarlo.")
                else:
                    try:
                        filas_importadas = _leer_csv_cotizaciones(
                            archivo_cotizaciones.getvalue(),
                            resultado_base,
                            lado_default=lado_tc,
                        )
                    except ErrorValidacion as exc:
                        st.error(str(exc))
                    else:
                        st.session_state["sim_usd_filas_cotizaciones_base"] = (
                            filas_importadas
                        )
                        st.session_state["sim_usd_revision_editor_cotizaciones"] = (
                            int(st.session_state.get("sim_usd_revision_editor_cotizaciones", 0))
                            + 1
                        )
                        cantidad_importada = sum(
                            bool(str(fila.get("ars_por_usd") or "").strip())
                            for fila in filas_importadas
                        )
                        if cantidad_importada:
                            st.success(
                                f"Se cargaron {cantidad_importada} cotizaciones. "
                                "Revisá la tabla antes de interpretar el resultado."
                            )
                        else:
                            st.info(
                                "El CSV se validó, pero no contiene cotizaciones "
                                "completas; los equivalentes ARS siguen sin calcular."
                            )

            filas_iniciales = st.session_state.get(
                "sim_usd_filas_cotizaciones_base",
                _filas_cotizaciones_editables(
                    resultado_base,
                    lado_default=lado_tc,
                ),
            )
            revision_editor = int(
                st.session_state.get("sim_usd_revision_editor_cotizaciones", 1)
            )
            filas_editadas = st.data_editor(
                filas_iniciales,
                key=f"sim_usd_cotizaciones_por_cuota_r{revision_editor}",
                num_rows="fixed",
                hide_index=True,
                use_container_width=True,
                disabled=["numero_cuota", "fecha_vencimiento"],
                column_config={
                    "numero_cuota": st.column_config.NumberColumn(
                        "Cuota", format="%d"
                    ),
                    "fecha_vencimiento": st.column_config.TextColumn(
                        "Vencimiento"
                    ),
                    "ars_por_usd": st.column_config.TextColumn(
                        "ARS por USD",
                        help="Hasta 6 decimales; por ejemplo 1.250,500000.",
                    ),
                    "fuente": st.column_config.TextColumn(
                        "Fuente / instrumento",
                        help="Ej.: MEP, entidad o fuente que estás usando.",
                    ),
                    "lado": st.column_config.SelectboxColumn(
                        "Lado",
                        options=["VENDEDOR", "COMPRADOR"],
                        required=True,
                    ),
                    "naturaleza": st.column_config.SelectboxColumn(
                        "Naturaleza",
                        options=["OBSERVADA", "PROYECTADA", "SUPUESTO"],
                        required=True,
                    ),
                    "referencia": st.column_config.TextColumn(
                        "Referencia / evidencia",
                        help="Opcional: URL, identificación del instrumento o nota.",
                    ),
                },
            )
            # Mantener la tabla materializada fuera del estado interno del
            # widget permite alternar métodos de valuación y volver sin perder
            # lo editado. Las importaciones reinician la clave del editor.
            if hasattr(filas_editadas, "to_dict"):
                filas_materializadas = filas_editadas.to_dict(orient="records")
            else:
                filas_materializadas = [dict(fila) for fila in filas_editadas]
            st.session_state["sim_usd_filas_cotizaciones_base"] = (
                filas_materializadas
            )
            cotizaciones = _cotizaciones_desde_editor(
                filas_materializadas,
                resultado_base.cuotas,
            )
            if not cotizaciones:
                st.warning(
                    "Todavía no hay cotizaciones por cuota. El cronograma USD se "
                    "calcula, pero no se muestra un total ARS estimado."
                )
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
    origen_tasa_base_texto = (
        "CAGR histórico de índice total-return (observado; usado como hipótesis)"
        if fuente_tasa_base == "CAGR_HISTORICO_TOTAL_RETURN"
        else "supuesto manual del usuario"
    )
    st.caption(
        f"Benchmark elegido: {benchmark_usd.strip()} ({clase_benchmark}). "
        f"Origen de la tasa bruta base: {origen_tasa_base_texto}. "
        f"Rendimiento bruto base: {_pct(tasa_usd_bruta_pct / Decimal('100'))}; "
        f"rendimiento neto base estimado: {_pct(resultado.tasa_benchmark_usd)} "
        f"({resultado.modalidad_benchmark.value} en USD). "
        f"Tasa contractual usada en las cuotas: {_pct(resultado.tasa_anual_usd)} "
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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Capital objetivo al fin de carencia (USD)",
        _usd(resultado.capital_objetivo_fin_carencia_usd),
    )
    m2.metric(
        "Rendimiento benchmark durante carencia (USD)",
        _usd(resultado.rendimiento_benchmark_carencia_usd),
        help=(
            "Valor contrafactual del capital si el rendimiento del benchmark se "
            "reinvierte cada período durante la carencia."
        ),
    )
    m3.metric(
        "Interés de carencia separado (USD)",
        _usd(resultado.interes_debido_carencia_usd),
        help=(
            "En el plan interno es cero porque el rendimiento de la carencia ya "
            "forma parte de la base objetivo; en un préstamo externo corresponde "
            "al interés simple diferido seleccionado."
        ),
    )
    m4.metric(
        "Brecha frente al benchmark (USD)",
        _usd(resultado.brecha_rendimiento_benchmark_carencia_usd),
        help=(
            "Diferencia entre el rendimiento contrafactual de la carencia y el "
            "interés que el escenario externo incluye por separado."
        ),
    )
    if modo_reposicion_interna:
        st.info(
            "El crecimiento del benchmark durante la carencia está incluido en la "
            "base interna a reponer. No es una cláusula contractual ni una ganancia "
            "externa consolidada del hogar."
        )
    elif resultado.brecha_rendimiento_benchmark_carencia_usd != Decimal("0.00"):
        st.warning(
            "El interés de carencia del escenario contractual no coincide con el "
            "rendimiento del benchmark durante el mismo período. La diferencia se "
            "muestra para comparar; no se agrega automáticamente a la deuda."
        )
    resultados_sensibilidad = comparar_escenarios_benchmark(
        capital_inicial_usd=resultado.capital_inicial_usd,
        fecha_desembolso=fecha_desembolso,
        flujos_cuotas=tuple(
            (cuota.fecha_vencimiento, cuota.importe_total_usd)
            for cuota in resultado.cuotas
        ),
        escenarios=tasas_benchmark_netas,
        modalidad_benchmark=resultado.modalidad_benchmark,
        convencion_dias=convencion,
    )
    st.subheader("Sensibilidad del benchmark")
    st.caption(
        "Se usa exactamente el mismo capital, calendario e importe de cada cuota; "
        "solo cambia la tasa neta de reinversión alternativa. Los tres escenarios "
        "son supuestos editables y no pronósticos ni datos de mercado."
    )
    filas_sensibilidad = []
    for escenario in resultados_sensibilidad:
        filas_sensibilidad.append(
            {
                "Escenario": escenario.nombre,
                "Rendimiento bruto anual (%)": _decimal_local(
                    tasas_brutas_escenarios_pct[escenario.nombre], 4
                ),
                "Costos anuales (%)": _decimal_local(costos_benchmark_pct, 4),
                "Impuesto estimado (%)": _decimal_local(impuesto_benchmark_pct, 4),
                "Rendimiento neto estimado (%)": _decimal_local(
                    escenario.tasa_anual_neta_usd * Decimal("100"), 4
                ),
                "Capital original al final (USD)": _usd(
                    escenario.valor_capital_original_final_usd
                ),
                "Cuotas reinvertidas al final (USD)": _usd(
                    escenario.valor_cuotas_reinvertidas_final_usd
                ),
                "Brecha final (USD)": _usd(escenario.brecha_final_usd),
            }
        )
    st.dataframe(filas_sensibilidad, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar sensibilidad de benchmark (CSV)",
        data=_csv_escenarios_benchmark(
            resultados_sensibilidad,
            benchmark=benchmark_usd.strip(),
            clase=clase_benchmark,
            tasas_brutas_pct=tasas_brutas_escenarios_pct,
            costos_pct=costos_benchmark_pct,
            impuesto_pct=impuesto_benchmark_pct,
            origen_tasa_base=fuente_tasa_base,
            resumen_historico=resumen_benchmark_historico,
            cagr_historico_usado=usar_cagr_historico,
            metodo_serie=st.session_state.get(
                "sim_usd_metodo_serie_benchmark",
                "INDICE_TOTAL_RETURN_IMPORTADO",
            ),
        ),
        file_name="sensibilidad-benchmark-usd.csv",
        mime="text/csv",
        key="sim_usd_descarga_escenarios_csv",
    )
    st.caption(
        "Modelo simplificado: los costos se restan como proporción anual del capital "
        "y el impuesto configurado se aplica solo sobre el rendimiento positivo después "
        "de costos. Ajustá el supuesto a tu situación; no constituye una liquidación fiscal."
    )

    with st.expander("Backtest histórico del capital y las cuotas (opcional)", expanded=False):
        st.caption(
            "Usa las observaciones históricas de la serie importada para valorar el "
            "capital inicial y reinvertir cada cuota en su fecha programada. Solo se "
            "calcula si la serie cubre todo el calendario; no se extrapola más allá "
            "del historial. Las tasas de nivel se toman del cierre igual o anterior "
            "a cada fecha, con un desfase máximo de 45 días."
        )
        if not observaciones_benchmark_historico or resumen_benchmark_historico is None:
            st.info("Importá primero una serie histórica validada para habilitar el backtest.")
        elif not identidad_serie_coincide:
            st.warning(
                "La serie cargada no corresponde al nombre y la clase de benchmark actuales."
            )
        elif resumen_benchmark_historico.moneda != "USD":
            st.warning(
                "El backtest del plan se expresa en USD. La serie cargada está en "
                f"{resumen_benchmark_historico.moneda} y no se convierte automáticamente."
            )
        else:
            try:
                resultado_backtest = comparar_flujos_con_indice_historico(
                    capital_inicial_usd=resultado.capital_inicial_usd,
                    fecha_desembolso=fecha_desembolso,
                    flujos_cuotas=tuple(
                        (cuota.fecha_vencimiento, cuota.importe_total_usd)
                        for cuota in resultado.cuotas
                    ),
                    observaciones=observaciones_benchmark_historico,
                )
            except ErrorValidacion as exc:
                st.info(
                    "No se puede calcular un backtest comparable con esta serie: "
                    f"{exc} Importá un historial que cubra la compra y todos los "
                    "vencimientos, sin huecos superiores a 45 días."
                )
            else:
                st.caption(
                    f"Período valorado: "
                    f"{resultado_backtest.fecha_inicio_operacion.isoformat()} a "
                    f"{resultado_backtest.fecha_fin_operacion.isoformat()}. "
                    f"Índice {resultado_backtest.tipo_indice}; "
                    f"{resultado_backtest.cantidad_observaciones} observaciones. "
                    "La valoración usa el nivel observado igual o anterior a cada fecha."
                )
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Capital original al cierre histórico (USD)",
                    _usd(resultado_backtest.valor_final_capital_original),
                    help=(
                        "Cuánto habría valido el capital inicial si permanecía invertido "
                        "en el índice entre las fechas valoradas."
                    ),
                )
                c2.metric(
                    "Cuotas reinvertidas al cierre histórico (USD)",
                    _usd(resultado_backtest.valor_final_cuotas_reinvertidas),
                    help=(
                        "Cada cuota se reinvierte en el índice en su fecha programada "
                        "y se valúa al cierre final del período."
                    ),
                )
                c3.metric(
                    "Brecha histórica de reinversión (USD)",
                    _usd(resultado_backtest.brecha_final),
                    help=(
                        "Valor de las cuotas reinvertidas menos el valor del capital "
                        "original mantenido invertido; no modifica el cronograma del plan."
                    ),
                )
                c4, c5 = st.columns(2)
                c4.metric(
                    "Retorno anualizado observado del capital",
                    _pct(resultado_backtest.rendimiento_anualizado_capital_original),
                )
                c5.metric(
                    "XIRR de la cartera con cuotas reinvertidas",
                    _pct(resultado_backtest.xirr_cartera_reinvertida),
                    help=(
                        "Tasa interna de retorno con fechas irregulares de las "
                        "aportaciones reinvertidas y la valuación final. Puede no "
                        "estar disponible si no existe una raíz XIRR válida."
                    ),
                )
                st.caption(
                    "El backtest utiliza el tipo de índice declarado. Si es BRUTO, "
                    "los valores no descuentan costos/impuestos; si es NETO, reflejan "
                    "la metodología neta reportada por la fuente. No se vuelven a "
                    "aplicar aquí los supuestos manuales de costos/impuestos."
                )
                st.download_button(
                    "Descargar backtest histórico (CSV)",
                    data=_csv_backtest_indice_historico(
                        resultado_backtest,
                        benchmark=benchmark_usd.strip(),
                        clase=clase_benchmark,
                        observaciones=observaciones_benchmark_historico,
                        metodo_serie=st.session_state.get(
                            "sim_usd_metodo_serie_benchmark",
                            "INDICE_TOTAL_RETURN_IMPORTADO",
                        ),
                    ),
                    file_name="backtest-historico-benchmark-usd.csv",
                    mime="text/csv",
                    key="sim_usd_descarga_backtest_historico_csv",
                )

    st.subheader("Comparación al vencimiento final")
    mf1, mf2, mf3 = st.columns(3)
    mf1.metric(
        "Valor del capital original si siguiera invertido (USD)",
        _usd(resultado.valor_original_invertido_fin_plazo_usd),
        help=(
            "Valor contrafactual del capital inicial llevado hasta el último "
            "vencimiento con la tasa benchmark y reinversión por período."
        ),
    )
    mf2.metric(
        "Valor final de cuotas reinvertidas (USD)",
        _usd(resultado.valor_cuotas_reinvertidas_fin_plazo_usd),
        help=(
            "Cada cuota se considera reinvertida en su fecha de vencimiento hasta "
            "la fecha final, usando el benchmark seleccionado."
        ),
    )
    mf3.metric(
        "Brecha final contra la inversión alternativa (USD)",
        _usd(resultado.brecha_valor_final_benchmark_usd),
        help=(
            "Valor de las cuotas reinvertidas menos el valor que habría alcanzado "
            "la inversión original. Negativa: el plan queda por debajo; positiva: "
            "supera el benchmark, bajo los supuestos elegidos."
        ),
    )
    if modo_reposicion_interna and abs(resultado.brecha_valor_final_benchmark_usd) <= Decimal("1.00"):
        st.success(
            "La reposición con reinversión queda alineada con el benchmark dentro "
            "de una tolerancia de USD 1,00; la pequeña diferencia puede venir del "
            "redondeo monetario de las cuotas."
        )
    elif modo_reposicion_interna:
        st.warning(
            "La reposición no coincide exactamente con el benchmark en el horizonte "
            "completo. Revisá la tasa, el calendario y los redondeos antes de usar "
            "el escenario como meta de ahorro."
        )
    else:
        st.caption(
            "En un préstamo entre personas, esta brecha mide la rentabilidad del "
            "flujo cobrado y reinvertido frente al benchmark elegido; no modifica "
            "las obligaciones del contrato."
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
            "Fuente de cotización": cotizacion.fuente if cotizacion is not None else "Sin conversión",
            "Lado de cotización": cotizacion.lado if cotizacion is not None else "—",
            "Naturaleza": cotizacion.naturaleza if cotizacion is not None else "Sin conversión",
            "Referencia": cotizacion.referencia if cotizacion is not None and cotizacion.referencia else "",
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
        capital_texto = st.text_input(
            "Capital a prestar (ARS)",
            value="1.000.000,00",
            help="Hasta 2 decimales. Podés escribir 1.000.000,50 o 1000000,50.",
            key="sim_carencia_capital",
        )
        fecha_desembolso = st.date_input(
            "Fecha de desembolso", value=date.today(), key="sim_carencia_fecha",
        )
        tasa_pct_texto = st.text_input(
            "Tasa anual (%)",
            value="36,0000",
            help="Entre 0 y 1.000, con hasta 4 decimales. Ejemplo: 36,5 o 36,5000.",
            key="sim_carencia_tasa",
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

    try:
        capital = _parsear_decimal_es(
            capital_texto,
            etiqueta="el capital",
            minimo=Decimal("1000"),
            maximo=Decimal("1000000000000"),
            decimales_maximos=2,
        )
        tasa_pct = _parsear_decimal_es(
            tasa_pct_texto,
            etiqueta="la tasa anual",
            minimo=Decimal("0"),
            maximo=Decimal("1000"),
            decimales_maximos=4,
        )
    except ErrorValidacion as exc:
        st.error(str(exc))
        return

    sistema = (
        SistemaAmortizacion.FRANCES
        if sistema_texto == "FRANCES"
        else SistemaAmortizacion.ALEMAN
    )
    argumentos = {
        "capital": capital,
        "tasa_anual": tasa_pct / Decimal("100"),
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
