# K2 — Dashboard financiero

K2 convierte cálculos ya existentes del dominio en una vista financiera de solo lectura para la UI.

## Hechos reales

El cashflow real se construye a partir de:
- aportes registrados en participaciones;
- desembolsos contractuales registrados en préstamos;
- pagos válidos registrados en pagos;
- cobros a inversores observados en el ledger.

Los signos se normalizan desde la perspectiva de la persona:
- dinero que entra: positivo;
- dinero que sale: negativo.

## Proyecciones

Las cuotas futuras se muestran como **proyección contractual**. Se toma la cuota pendiente de la versión activa del préstamo y no se agregan supuestos de mora futura ni tipos de cambio inventados.

Para inversores, la proyección utiliza su porcentaje activo del préstamo.

## XIRR

La XIRR se calcula usando la función existente del dominio y solo con flujos históricos reales.

La XIRR USD se muestra únicamente cuando todos los flujos del rol tienen una conversión USD explícita. No se calcula una tasa sobre una muestra parcial.

## Poder de compra

La UI permite ingresar una inflación mensual de referencia.

Ese valor es un **supuesto del usuario**, no un dato automático de mercado. Se utiliza para convertir flujos futuros a una representación de poder de compra de hoy y para calcular rendimiento real anualizado.

## Escenarios

La sección de escenarios utiliza directamente los tipos EscenarioMacro, comparar_escenarios y los escenarios predefinidos existentes en el dominio.

Los escenarios no son predicciones. Son herramientas de stress testing y planificación.

## Límites

La posición de capital no equivale a patrimonio contable completo: no incluye dinero fuera de los préstamos, inmuebles, mercado de valores u otras posiciones externas.

Tampoco se interpreta una XIRR inexistente como cero. Cuando faltan flujos o signos suficientes, la UI muestra `—`.
