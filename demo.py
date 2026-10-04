"""
Demo ejecutable del motor financiero.

Ejecutar: python demo.py

Este archivo muestra cómo se usa el motor desde afuera. Cuando
construyamos la UI, va a llamar a las mismas funciones.
"""
from datetime import date
from decimal import Decimal

from dominio import (
    generar_tabla, imputar_pago, calcular_mora, xirr,
    comparar_plazos, escenarios_predefinidos_argentina,
    comparar_escenarios, calcular_tasa_real, proyectar_licuacion,
    SistemaAmortizacion, ModalidadTasa, ConceptoImputacion,
)


def formatear_pesos(v: Decimal) -> str:
    """Da formato $ 1.234.567,89 a un Decimal."""
    entero, decimales = f"{v:.2f}".split(".")
    return f"$ {int(entero):,}".replace(",", ".") + f",{decimales}"


def main():
    print("=" * 78)
    print("MOTOR FINANCIERO — DEMO")
    print("=" * 78)

    # ------------------------------------------------------------
    # 1. Tabla de amortización
    # ------------------------------------------------------------
    capital = Decimal("20000000")
    tasa = Decimal("0.30")
    meses = 36
    inicio = date(2026, 1, 1)

    print(f"\nPréstamo: {formatear_pesos(capital)} a {float(tasa)*100}% TNA, "
          f"{meses} meses")

    tabla = generar_tabla(
        capital=capital,
        tasa_anual=tasa,
        modalidad=ModalidadTasa.TNA,
        meses=meses,
        fecha_inicio=inicio,
        sistema=SistemaAmortizacion.FRANCES,
    )

    print(f"\n--- Primeras 3 cuotas ---")
    for f in tabla[:3]:
        print(f"  Cuota {f['numero']:>2} | {f['vencimiento']} | "
              f"Cuota {formatear_pesos(f['cuota']):>16} | "
              f"Interés {formatear_pesos(f['interes']):>14} | "
              f"Capital {formatear_pesos(f['capital']):>14} | "
              f"Saldo {formatear_pesos(f['saldo']):>16}")

    total_intereses = sum(f["interes"] for f in tabla)
    total_pagado = sum(f["cuota"] for f in tabla)
    print(f"\n  Total intereses: {formatear_pesos(total_intereses)}")
    print(f"  Total pagado:    {formatear_pesos(total_pagado)}")

    # ------------------------------------------------------------
    # 2. Comparación de plazos
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("COMPARACIÓN DE PLAZOS")
    print("=" * 78)

    resultados = comparar_plazos(
        capital=capital,
        tasa_anual=tasa,
        modalidad=ModalidadTasa.TNA,
        plazos=[6, 12, 24, 36, 48, 60, 73],
        fecha_inicio=inicio,
    )

    print(f"\n{'Plazo':>7} {'Cuota prom.':>16} {'Interés total':>18} "
          f"{'Total pagado':>18}")
    print("-" * 62)
    for r in resultados:
        print(f"{r['meses']:>5} m {formatear_pesos(r['cuota_promedio']):>16} "
              f"{formatear_pesos(r['total_intereses']):>18} "
              f"{formatear_pesos(r['total_pagado']):>18}")

    # ------------------------------------------------------------
    # 3. Pago parcial
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("PAGO PARCIAL")
    print("=" * 78)

    cuota1 = tabla[0]
    deudas = {
        ConceptoImputacion.INTERES: cuota1["interes"],
        ConceptoImputacion.CAPITAL: cuota1["capital"],
    }
    aplicado, excedente = imputar_pago(Decimal("300000"), deudas)
    print(f"\n  Pago recibido: {formatear_pesos(Decimal('300000'))}")
    print(f"  Interés cubierto: {formatear_pesos(aplicado[ConceptoImputacion.INTERES])}")
    print(f"  Capital cubierto: {formatear_pesos(aplicado[ConceptoImputacion.CAPITAL])}")
    print(f"  Interés pendiente: "
          f"{formatear_pesos(cuota1['interes'] - aplicado[ConceptoImputacion.INTERES])}")

    # ------------------------------------------------------------
    # 4. Mora por atraso
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("MORA POR ATRASO")
    print("=" * 78)

    mora = calcular_mora(
        monto_vencido=Decimal("500000"),
        tasa_mora_anual=Decimal("0.50"),
        fecha_vencimiento=date(2026, 2, 1),
        fecha_calculo=date(2026, 2, 20),
    )
    print(f"\n  19 días de atraso sobre $500.000 al 50% anual: "
          f"{formatear_pesos(mora)}")

    # ------------------------------------------------------------
    # 5. Escenarios macroeconómicos
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("ESCENARIOS MACROECONÓMICOS")
    print("=" * 78)

    escenarios = escenarios_predefinidos_argentina()
    resultados_esc = comparar_escenarios(
        capital=capital,
        tasa_anual=tasa,
        modalidad=ModalidadTasa.TNA,
        meses=meses,
        fecha_inicio=inicio,
        escenarios=escenarios,
        tc_inicial=Decimal("1500"),
    )

    print(f"\n{'Escenario':<12} {'Infl.':>7} {'Deval.':>7} "
          f"{'Cuota final real':>18} {'Cuota final USD':>16} {'Pérdida':>10}")
    print("-" * 78)
    for r in resultados_esc:
        print(f"{r.escenario.nombre:<12} "
              f"{float(r.escenario.inflacion_mensual)*100:>6.1f}% "
              f"{float(r.escenario.devaluacion_mensual)*100:>6.1f}% "
              f"{formatear_pesos(r.cuota_final_real):>18} "
              f"USD {float(r.cuota_final_usd):>10,.2f} "
              f"{float(r.perdida_poder_compra_pct):>9.1f}%")

    # ------------------------------------------------------------
    # 6. Licuación
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("LICUACIÓN DE LA CUOTA")
    print("=" * 78)

    proyeccion = proyectar_licuacion(
        cuota_nominal=tabla[0]["cuota"],
        inflacion_mensual=Decimal("0.05"),
        meses=36,
    )
    print(f"\n  Cuota inicial: {formatear_pesos(proyeccion[0]['cuota_nominal'])}")
    print(f"  Cuota al mes 12 (en pesos de hoy): "
          f"{formatear_pesos(proyeccion[11]['cuota_real'])}")
    print(f"  Cuota al mes 36 (en pesos de hoy): "
          f"{formatear_pesos(proyeccion[35]['cuota_real'])}")
    print(f"  Licuación al mes 36: "
          f"{float(proyeccion[35]['licuacion_acumulada'])*100:.1f}%")

    tasa_real = calcular_tasa_real(Decimal("0.30"), Decimal("0.80"))
    print(f"\n  Tasa real con inflación del 80% anual: "
          f"{float(tasa_real)*100:.2f}%")

    # ------------------------------------------------------------
    # 7. XIRR
    # ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("XIRR DE UN INVERSOR")
    print("=" * 78)

    flujos = [
        (date(2026, 1, 1), Decimal("-10000000")),
        (date(2026, 7, 1), Decimal("2000000")),
        (date(2027, 1, 1), Decimal("3000000")),
        (date(2027, 7, 1), Decimal("7000000")),
    ]
    r = xirr(flujos)
    print(f"\n  Rendimiento anualizado: {float(r)*100:.2f}%")

    print("\n" + "=" * 78)
    print("Fin del demo.")
    print("=" * 78)


if __name__ == "__main__":
    main()