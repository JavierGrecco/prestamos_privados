# M7 — Comparador de decisiones financieras

## Propósito

M7 reúne en una sola pantalla información financiera que ya existe en la
aplicación para ayudar a comparar dos o más operaciones registradas.

No reemplaza el análisis financiero, no crea nuevas reglas y no decide por la
persona.

## Qué compara

Para cada alternativa muestra, usando la misma fecha de corte y horizonte:

- capital de referencia;
- flujo real acumulado;
- flujo futuro proyectado;
- valor real de los flujos futuros;
- rendimiento o costo anualizado cuando existe XIRR;
- resultado anualizado ajustado por inflación;
- condiciones relevantes del préstamo.

Las cifras salen de los cashflows existentes de AnalisisFinancieroQuery y el
XIRR se calcula con la función del dominio ya usada por M5.

## Homogeneidad

La pantalla permite comparar aunque las operaciones no sean idénticas, pero
advierte cuando cambian reglas que modifican la interpretación:

- rol de la persona;
- moneda contractual;
- sistema de amortización;
- convención de días;
- modalidad de tasa.

Una tasa, un capital o un plazo diferentes no vuelven inválida una comparación:
son justamente variables que puede resultar útil contrastar.

## Hechos, proyecciones y supuestos

- **Flujo real:** movimiento que ya ocurrió.
- **Flujo futuro:** proyección contractual dentro del horizonte elegido.
- **Valor real futuro:** proyección expresada a precios de hoy según la inflación elegida.
- **Rendimiento:** métrica histórica basada en flujos reales.
- **Supuesto:** hipótesis utilizada para expresar valor futuro y rendimiento real.

Nunca se presenta una proyección como hecho.

## Primera versión

M7.1 compara operaciones registradas por la persona y permite seleccionar entre
dos y seis alternativas.

Las alternativas simuladas quedan para una extensión posterior sobre la misma
estructura, sin mezclar hipótesis con operaciones persistidas.

## Arquitectura

- aplicacion/consultas/comparador_decisiones_financieras.py — read model M7;
- ui/pagina_comparador.py — presentación;
- dominio/xirr.py — cálculo XIRR existente;
- dominio/licuacion.py — cálculo de valor real existente;
- aplicacion/consultas/analisis_financiero.py — fuente de cashflows;
- tests/test_comparador_decisiones_financieras.py — reglas M7;
- tests/test_ui_e2e.py — aceptación de la pantalla.

## Límite

M7 organiza información para decidir. No recomienda comprar, prestar, invertir,
refinanciar ni tomar deuda.
