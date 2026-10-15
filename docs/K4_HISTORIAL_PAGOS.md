# K4 — Historial financiero y detalle auditable de pagos

K4 expone en la UI la evidencia que ya persiste el core financiero.

## Historial

La pantalla lista los últimos pagos de la persona y permite abrir un detalle individual.
El listado tiene un límite configurable para evitar cargar una cantidad ilimitada de registros en Streamlit.

## Detalle

Un pago puede mostrar:
- identidad, monto, fechas, tipo y motor;
- monto aplicado a capital, intereses ahorrados y cuotas restantes;
- imputaciones por cuota, concepto y origen;

La columna de imputaciones muestra la cuota registrada mediante su número de vencimiento cuando la cuota referenciada sigue disponible. Si no existe esa fila histórica, la UI mantiene visible la referencia guardada en vez de inventar un número. La referencia es el dato persistido: no reconstruye por sí sola qué cuota consumió cada importe en un pago con arrastre. Ese caso está documentado en [el análisis de imputaciones por cuota](ANALISIS_IMPUTACIONES_POR_CUOTA.md) y sigue abierto en el [issue #332](https://github.com/JavierGrecco/prestamos_privados/issues/332).
- devengamientos asociados cuando existen referencias;
- plan V3 persistido y su hash;
- movimientos del ledger y correlación;
- eventos de auditoría;
- observaciones SOMBRA asociadas.

## Principio

K4 es de solo lectura. No recalcula el pago ni modifica la base. El objetivo es que una operación financiera pueda reconstruirse desde la aplicación utilizando los hechos ya persistidos.

## Transición

Los pagos Legacy y V3 pueden aparecer juntos. El campo motor_version permite distinguir el origen.
Las observaciones SOMBRA se muestran como evidencia adicional y no sustituyen al resultado efectivo del pago.