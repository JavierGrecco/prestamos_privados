# Fechas real y valor de los pagos

El registro de pagos distingue ahora entre:

- Fecha real: día en que el dinero fue recibido.
- Fecha valor: día en que el pago toma efecto contable/financiero.

Por compatibilidad, la fecha valor se inicializa igual a la fecha real y el
operador puede modificarla.

El comando de aplicación conserva ambas fechas y el motor V3 recibe
explícitamente fecha_valor.

La pantalla y el servicio mantienen la separación; la UI no inventa una
fecha financiera distinta de la ingresada por el operador.
