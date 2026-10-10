# Diseño de correcciones auditables para planes de reposición

**Estado:** especificación de implementación; todavía no habilita correcciones en producción.  
**Ámbito:** aportes de reposición, flujos de inversión y valuaciones declaradas de un plan interno.

## Objetivo

Permitir corregir un dato registrado por error sin reescribir el historial financiero. Una corrección debe explicar qué dato reemplaza, por qué se corrige y quién/cuándo la registró. El historial original debe seguir disponible para auditoría y para reconstruir informes anteriores.

## Decisiones obligatorias

1. **No editar ni borrar hechos confirmados.** Las filas originales de aportes, movimientos y valuaciones permanecen inmutables.
2. **Corregir mediante un asiento compensatorio o una referencia de corrección.** La implementación elegirá el mecanismo compatible con el esquema actual, pero debe conservar vínculo explícito al registro original y al registro correctivo.
3. **Motivo obligatorio.** No se aceptan motivos vacíos ni genéricos que no expliquen el error.
4. **Trazabilidad del actor y del tiempo.** Registrar usuario de acceso cuando exista identidad autenticada, timestamp UTC y correlación de operación. No inferir que el nombre de una persona financiera es el actor autenticado.
5. **Integridad verificable.** Preservar el hash del registro original y calcular el hash de la corrección con serialización determinista y valores Decimal; no introducir float.
6. **Una corrección efectiva por versión del original.** Reintentos idempotentes no deben duplicar el ajuste. Una segunda corrección debe referenciar explícitamente la corrección anterior o seguir una cadena auditable.
7. **Atomicidad.** Validación, registro correctivo, auditoría y actualización de proyecciones/materializaciones ocurren en una sola transacción. Ante un fallo, no queda una corrección parcial.
8. **No reescribir informes históricos.** Un informe generado antes de la corrección debe poder reconstruirse con el estado histórico correspondiente. Los informes actuales muestran el dato original, la corrección y el efecto neto, sin ocultar la trazabilidad.
9. **Separación entre hechos y estimaciones.** Corregir una valuación declarada no la convierte en precio externo verificado ni en ganancia realizada.
10. **Autorización.** Corregir exige la capacidad operativa apropiada; la consulta del historial puede permanecer disponible en modo lectura según la política de permisos.

## Recorrido de usuario

1. Abrir un plan y localizar el aporte, movimiento o valuación.
2. Elegir **Corregir registro**; la interfaz muestra el registro original en modo lectura.
3. Ingresar el dato correcto y un motivo claro.
4. Revisar una comparación antes/después y el efecto sobre posición, rendimiento y exportaciones.
5. Confirmar; la operación queda registrada como nueva evidencia, sin alterar el original.
6. Consultar el historial de correcciones y exportarlo.

La UI debe distinguir visualmente **original**, **corregido**, **anulado por corrección** y **vigente**. No debe describir una anulación contable como si el registro nunca hubiera existido.

## Reglas financieras

- Una corrección de aporte debe actualizar el total efectivo de capital repuesto una sola vez.
- Una corrección de movimiento debe preservar fecha, moneda, importe, naturaleza y costos corregidos, además del valor anterior.
- Una corrección de valuación debe recalcular métricas derivadas, pero no crear por sí sola una ganancia realizada.
- La XIRR y los informes deben usar el conjunto efectivo de flujos según la cadena de correcciones, sin duplicar el original y el reemplazo.
- Las proyecciones guardadas no se alteran retroactivamente. Si la corrección cambia la base del análisis, se genera una nueva versión del plan/análisis y se conserva la anterior.
- No se mezclan correcciones del plan interno con pagos o saldos de préstamos Legacy/V3.

## Pruebas de aceptación requeridas

- Motivo ausente, dato inválido, referencia inexistente y corrección de tipo incompatible son rechazados sin cambios persistidos.
- El original permanece idéntico y su hash no cambia.
- La corrección conserva actor, timestamp UTC, motivo, vínculo al original y hash propio.
- Repetir la misma solicitud no duplica importes ni eventos.
- Fallas inyectadas en cada etapa producen rollback completo.
- Dos correcciones concurrentes del mismo registro no se aplican silenciosamente sobre una versión obsoleta.
- Totales de aportes, flujos netos, valuaciones, rendimiento y XIRR reflejan exactamente una versión efectiva.
- Los informes Markdown, JSON y CSV explican la corrección y conservan la trazabilidad sin interpretar fórmulas de hoja de cálculo como contenido confiable.
- Una base histórica puede actualizarse con backup verificado y sin modificar hechos financieros previos.
- Tests en Python 3.11–3.14, CodeQL, auditoría de dependencias y pruebas de UI relevantes quedan verdes.

## Orden de implementación

1. Inspeccionar los repositorios y triggers actuales de aportes, movimientos y valuaciones; definir el contrato de persistencia concreto antes de modificar el esquema.
2. Implementar modelo/servicio de corrección y migración compatible, con invariantes e idempotencia.
3. Añadir pruebas unitarias, de transacción, concurrencia y migración histórica.
4. Conectar la UI y la vista de historial.
5. Extender exportaciones y reportes con el estado corregido y su trazabilidad.
6. Ejecutar matriz de CI y documentar cualquier aceptación manual pendiente.

## Fuera de alcance

Este diseño no aprueba la modificación de contratos de préstamos, no decide divergencias económicas Legacy/V3 y no convierte cotizaciones o valuaciones ingresadas manualmente en evidencia externa verificada. Esas decisiones requieren sus propios criterios y validaciones.
