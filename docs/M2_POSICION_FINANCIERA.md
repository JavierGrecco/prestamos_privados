# M2 — Posición financiera por persona

## Propósito

M2 amplía **Mi espacio** con una posición financiera consolidada dentro de
Préstamos Privados.

El sistema no conoce todo el patrimonio de una persona. Por eso no presenta
esta cifra como patrimonio total.

## Qué significa cada dato

**Capital invertido**
Capital de inversiones activas que la persona tiene registrado en el sistema.

**Capital pendiente de deuda**
Capital que todavía figura pendiente en préstamos activos de la persona.

**Posición neta de capital**
Capital invertido menos capital pendiente de deuda. Es una medida de exposición
de capital dentro de los préstamos registrados.

**Cobros reales registrados**
Dinero de inversiones que ya figura como cobrado.

**Pagos reales registrados**
Dinero de préstamos que ya figura como pagado.

**Cobros futuros estimados**
Cuotas futuras proyectadas de inversiones activas. No son garantía de cobro.

**Pagos futuros estimados**
Cuotas futuras proyectadas de préstamos activos. No son un saldo disponible ni
una deuda adicional inventada.

## Evolución histórica

Se muestran hasta 12 meses de movimientos reales agrupados por mes.

El acumulado es un acumulado de caja de los movimientos registrados:

`entradas reales - salidas reales`

No representa patrimonio y no intenta reconstruir activos externos.

## Decisiones de diseño

- no se agregan activos externos que la aplicación no conozca;
- no se suman inversión y deuda bajo una etiqueta ambigua;
- no se transforma una proyección en un hecho real;
- no se crean nuevas reglas financieras;
- se reutiliza `AnalisisFinancieroQuery` como fuente financiera;
- la capa M2 es de solo lectura.

## Fuente de código

- `aplicacion/consultas/posicion_financiera_persona.py` — read model y servicio;
- `ui/pagina_mi_espacio.py` — presentación;
- `tests/test_posicion_financiera_persona.py` — reglas de consolidación;
- `tests/test_ui_e2e.py` — aceptación de la pantalla.

## Próxima evolución

M3 puede usar esta base para planificación financiera: mostrar qué podría
suceder bajo distintos escenarios, siempre separando hechos reales de
estimaciones.