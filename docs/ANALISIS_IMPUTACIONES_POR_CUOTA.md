# Análisis de imputaciones por cuota en pagos Legacy

**Estado:** diagnóstico y caracterización. No define ni cambia una regla financiera.
**Seguimiento:** [issue #332 — Conciliar imputaciones por cuota con saldos aplicados](https://github.com/JavierGrecco/prestamos_privados/issues/332).
**Objetivo:** identificar qué significa hoy la referencia de cuota, qué partes del sistema la leen y qué se debe decidir antes de una corrección.

## 1. Hecho caracterizado

El [PR #333](https://github.com/JavierGrecco/prestamos_privados/pull/333) añadió una prueba reproducible: un pago deja una cuota parcial; el siguiente cubre ese arrastre y la cuota objetivo. Los saldos de la cuota previa se actualizan, pero las imputaciones del segundo pago quedan vinculadas a la cuota objetivo.

La suma de las imputaciones puede coincidir con el importe total del pago sin que sus referencias describan todas las cuotas cuyos saldos cambiaron. Son dos comprobaciones diferentes:

- **Cuadre global:** la suma de los conceptos imputados coincide con el monto del pago.
- **Trazabilidad por cuota:** cada importe queda atribuido a la cuota y al concepto correctos.

La prueba documenta el comportamiento actual; no confirma por sí sola cuál debe ser la política contractual o contable deseada.

## 2. Inventario de lectores y controles

| Componente | Qué hace con las imputaciones | Alcance o límite |
|---|---|---|
| `aplicacion/servicios/registro_pago_legacy.py` | Prepara la actualización de cuotas anteriores y la cuota objetivo; envía las imputaciones al repositorio con la referencia usada hoy por Legacy. | Actualiza saldos y registra imputaciones dentro de la misma operación, pero no divide la evidencia persistida por cada cuota anterior afectada. |
| `infraestructura/repositorios/pagos.py` — `PagoRepo.registrar` | Guarda `cuota_id`, concepto y monto. Comprueba que la suma de imputaciones coincida con el monto del pago. | Protege el cuadre total, no verifica la atribución por cuota. |
| `infraestructura/consultas/historial_pagos.py` | Devuelve las filas de imputación para reconstruir el detalle auditable, incluyendo `cuota_id`. | Presenta la referencia persistida; no reconstruye qué saldo de cuota consumió cada concepto. |
| `ui/pagina_pagos.py` | Muestra la referencia en la tabla de imputaciones bajo «Cuota registrada». Resuelve `numero_cuota` mediante el read model del historial. | Si existe número muestra `N.º n`; si `cuota_id` es nulo muestra «Sin cuota específica»; si existe el ID pero ya no se puede resolver la cuota, conserva «Referencia histórica #id». La legibilidad del dato está cubierta; esto no corrige la atribución financiera. |
| `infraestructura/consultas/pagos_v3.py` — `obtener_pago_v3` | Carga las referencias de cuota y verifica el total de imputaciones, el ledger, la correlación y la integridad del plan persistido. | La reconciliación del read model es global; no contrasta cada fila persistida contra la cuota afectada por cada aplicación del plan. |
| `infraestructura/consultas/comparador_sombra_pago_v3.py` | Convierte `cuota_id` a número de cuota y compara las imputaciones Legacy con las aplicaciones del plan V3 por cuota, concepto e importe. | Es el control existente que puede hacer visible una divergencia de atribución. SOMBRA la registra como observación y no invalida el pago efectivo Legacy. |
| `infraestructura/consultas/detalle_financiero_prestamo.py` | Calcula la trayectoria agregada del capital a partir de pagos válidos y sus imputaciones de capital. | La consulta no utiliza `cuota_id`; puede presentar el capital agregado aunque la referencia por cuota no sea correcta. |
| `aplicacion/servicios/exportaciones.py` — `amortizacion_csv` | Exporta la tabla de amortización y sus saldos por cuota. | No exporta las imputaciones de cada pago ni sirve como control de atribución pago-a-cuota. |
| `tests/test_registrar_pago_caracterizacion.py` | Caracteriza el caso de arrastre que salda la cuota previa mientras las imputaciones persisten asociadas a la cuota objetivo. | Protege el comportamiento observado, no declara que sea el comportamiento financiero deseado. |
| `tests/test_pagos_v3_read_model.py` | Comprueba que el read model detecte imputaciones cuyo total no cuadra. | Las pruebas actuales no demuestran una validación de cuota por cuota. |

## 3. Estado de la presentación de referencias en la UI

La observación histórica que indicaba que la pantalla mostraba siempre el ID interno ya no describe el código actual:

- `infraestructura/consultas/historial_pagos.py` hace un `LEFT JOIN` con `cuotas` y devuelve tanto `cuota_id` persistido como `numero_cuota` resoluble.
- `ui/pagina_pagos.py` usa `_etiqueta_cuota_registrada()`: presenta `N.º n` si el número está disponible; `Sin cuota específica` si `cuota_id` es nulo; y `Referencia histórica #id` cuando el ID existe pero ya no hay una fila de cuota que permita resolver el número.
- `tests/test_historial_pagos.py` verifica estos tres comportamientos y evita que un ID interno resoluble sea presentado como si fuera el número de vencimiento.

Por lo tanto, **la claridad visual de la referencia está corregida y probada**. Sigue pendiente determinar si la referencia persistida corresponde a la cuota cuyo saldo realmente consumió cada importe. No confundir el arreglo de presentación con la conciliación financiera de #332.

## 4. Qué aporta el control SOMBRA

El comparador `ComparadorSombraPagoSQLite` ya arma dos representaciones:

1. Las imputaciones Legacy que están guardadas en SQLite, traduciendo el ID a número de cuota cuando la referencia existe.
2. Las aplicaciones del plan V3, que conservan la cuota de cada obligación afectada.

Si ambas listas no coinciden, puede registrar una divergencia de imputaciones. La prueba de integración añadida en esta etapa comprueba ese camino con un arrastre real y verifica que la operación Legacy siga siendo efectiva.

Esto no significa que el plan V3 deba convertirse automáticamente en la regla correcta. La observación permite comparar dos comportamientos, no decide por sí sola cuál corresponde al contrato.

## 5. Decisiones que faltan antes de corregir

- **Semántica de `cuota_id`:** confirmar si cada fila debe identificar la cuota exacta cuyo saldo consume ese importe o si el modelo actual representa otra cosa.
- **Distribución del arrastre:** definir cómo se divide mora, interés y capital entre varias cuotas anteriores y la cuota objetivo.
- **Interés extra:** acordar cómo atribuir el interés extra calculado sobre capital vencido; no debe repartirse por intuición durante un refactor.
- **Historia:** establecer qué hacer con los pagos existentes y cómo mostrar referencias que ya quedaron guardadas. No reescribir hechos históricos automáticamente.
- **Informes y usuario:** decidir cómo representar referencias no disponibles y evitar que un ID interno se confunda con el número de cuota.

## 6. Criterio para dar el issue por resuelto

La solución futura debe demostrar por separado que:

1. el total de imputaciones coincide con el pago;
2. la suma aplicada por concepto y cuota coincide con el cambio esperado en los saldos;
3. los lectores de historial, auditoría, SOMBRA, detalle financiero y exportaciones conservan una interpretación coherente;
4. las fallas revierten pago, cuotas, ledger y auditoría como una sola operación;
5. los registros históricos conservan su significado y no se migran sin una estrategia explícita.

Hasta que la regla sea decidida, se mantiene la conducta productiva Legacy y no se habilita V3 por este trabajo.