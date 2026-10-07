# Motor de Pagos V3 — G1: devengamientos explícitos

G1 agrega una pieza que faltaba para que el interés nacido por el paso del
tiempo pueda auditarse como hecho financiero y no como un número recalculado
silenciosamente al momento del pago.

## Persistencia

La migración v010 crea `devengamientos` como registro append-only con:

- préstamo y cuota de referencia;
- concepto;
- monto;
- período [fecha_desde, fecha_hasta);
- origen y referencia;
- base;
- tasa anual, modalidad y convención;
- días y fracción anual;
- huella única;
- versión del motor y timestamp técnico.

Los triggers impiden UPDATE/DELETE. Una corrección debe representarse mediante
un nuevo evento compensatorio.

No se crea FK a `cuota_id` deliberadamente: el proyecto actual permite
recalcular/recrear cuotas futuras, y el historial de un devengamiento no debe
quedar borrado por una reestructuración.

## Política pura

`generar_interes_capital_pendiente` calcula solamente interés adicional sobre
capital efectivamente pendiente en el snapshot. El período empieza en el
vencimiento o en el último corte persistido, lo que evita duplicar el mismo
período.

Esta etapa NO decide automáticamente:

- tasa de mora;
- base de mora;
- penalidades;
- capitalización de intereses;
- interés contractual francés ya incluido en el cronograma.

Esas son reglas de negocio del crédito y deben venir de una política explícita.

## Próxima integración

G2 debe leer los devengamientos persistidos, generar solo el período faltante
hasta `fecha_valor`, incorporarlos al `calcular_plan_pago` y persistirlos dentro
de la misma transacción del pago. La prueba clave será demostrar que un mismo
período nunca se cobra dos veces.
