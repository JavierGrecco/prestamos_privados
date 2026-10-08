# K6 — Detalle financiero profundo del préstamo

K6 agrega una vista de solo lectura sobre la situación financiera de un préstamo.

## Amortización

La UI muestra la versión activa del cronograma y sus importes persistidos: capital inicial, interés, capital, cuota, saldo y capital pendiente.

Las marcas de cuota permiten distinguir pagos parciales, mora y cuotas creadas por recálculos.

## Evolución del capital

La trayectoria real se construye a partir de las aplicaciones de CAPITAL de pagos válidos y utiliza directamente el componente puro de trayectoria de capital del dominio.

No se recalculan pagos históricos.

## Devengamientos

La pantalla muestra los eventos persistidos con período, concepto, origen, tasa, días y versión del motor.

## RAI/RNI

Cada recálculo histórico muestra capital antes/después, cuotas antes/después e intereses antes/después, además del ahorro resultante.

Esto permite distinguir el cronograma actual de su historia de decisiones.

## Límites

K6 es de solo lectura. No cambia cronogramas ni permite editar recálculos.

La trayectoria representa reducciones de capital observadas en pagos válidos; no sustituye un estado contable completo ni una valuación de patrimonio.