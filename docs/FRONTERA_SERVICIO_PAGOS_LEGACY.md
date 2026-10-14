# Frontera actual de ServicioPagos (Legacy)

**Estado:** diagnóstico previo a una futura modularización de la escritura. Este documento no cambia el comportamiento del sistema.  
**Seguimiento:** [Issue #267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267).  
**Prioridad:** mantener la aplicación local estable y no cambiar las reglas financieras mientras se separan responsabilidades.

## 1. Qué vemos hoy

`aplicacion/servicios/pagos.py` todavía concentra muchas tareas distintas en `ServicioPagos`. El constructor recibe la base de datos y crea directamente repositorios de préstamos, pagos, participaciones, ledger, auditoría, recálculos y políticas de pago.

En el mismo servicio conviven:

- validación de la solicitud y elección de la política vigente por fecha de valor;
- obtención de la deuda y cálculo de la imputación;
- actualización de cuotas y tratamiento de pagos parciales;
- adelantos RAI/RNI y recálculo de cuotas futuras;
- registro de pagos, imputaciones, distribución a inversores, ledger y auditoría.

Las consultas de resumen de impacto e historial de decisiones ya se extrajeron a `aplicacion/consultas/impacto_pagos.py` mediante el [PR #306](https://github.com/JavierGrecco/prestamos_privados/pull/306). La escritura continúa en `ServicioPagos`: **esa es la siguiente frontera, no una tarea que deba resolverse moviendo archivos sin más.**

## 2. La garantía que no puede perderse

Un pago no puede quedar guardado a medias. La operación debe conservar una unidad de trabajo coherente para el pago, sus imputaciones, la actualización de cuotas, el posible adelanto, la distribución entre inversores, el ledger y la auditoría.

En la implementación actual, el flujo usa una transacción principal y algunos repositorios o métodos auxiliares tienen sus propios bloques transaccionales. Antes de mover esas llamadas a adaptadores hay que caracterizar cómo se comporta el anidamiento de transacciones y probar que cualquier fallo tardío deja el estado anterior intacto.

Además, la misma solicitud debe seguir siendo idempotente: un reintento con la misma clave y el mismo contenido devuelve el pago original; una clave reutilizada con contenido distinto se rechaza.

## 3. Pruebas actuales que deben seguir pasando

Estas pruebas describen comportamientos reales del camino Legacy y deben permanecer como regresiones obligatorias:

| Prueba | Qué protege |
|---|---|
| `tests/test_registrar_pago_caracterizacion.py` | Pago exacto, pago parcial, orden de mora/interés/capital, interés extra, complemento, adelantos RAI/RNI y distribución/auditoría. |
| `test_error_durante_ledger_revierte_pago_y_cambios_de_cuotas` | Si falla el ledger, se revierte el pago y las cuotas quedan como estaban. |
| `test_fallo_despues_de_escribir_auditoria_revierte_toda_la_operacion` | Si falla después de insertar la auditoría, también se revierten pago, cuotas, ledger y auditoría. |
| `test_fallo_despues_de_recalculo_rai_o_rni_revierte_cronograma_y_evidencias` | Si falla después de un adelanto RAI o RNI, vuelven atrás el cronograma futuro, pagos, recálculos, ledger y auditoría. |
| `test_fallo_despues_de_distribuir_a_inversores_revierte_toda_la_operacion` | Si falla después de insertar los movimientos de distribución, se revierten cuotas, pago, ledger, recálculos y auditoría. |
| `tests/test_idempotencia_pago_legacy.py` | Reintentos, rechazo de claves con contenido distinto, concurrencia entre dos conexiones y separación entre fecha real y fecha de valor. |
| `tests/test_repositorios_pagos.py` | Reglas de persistencia de pagos, imputaciones, ledger y auditoría. |

La cobertura actual prueba fallos durante el ledger, después de escribir auditoría, después de los recálculos RAI/RNI y justo después de escribir movimientos de distribución a inversores. Es una base de partida, no una prueba de que todas las etapas soporten una extracción arquitectónica. Aún deben añadirse fallos después de actualizaciones parciales de cuotas y verificaciones de atomicidad específicas de la integración con inversores, sin reemplazar las regresiones existentes.

## 4. Orden recomendado para modularizar la escritura

1. **Cerrar la caracterización.** Dejar por escrito el estado anterior y posterior esperado de pagos, cuotas, imputaciones, ledger, auditoría, distribuciones y recálculos. Añadir inyección de fallos después de cada etapa crítica.
2. **Definir contratos pequeños.** La aplicación debe declarar qué necesita leer y qué operaciones debe ejecutar. Los contratos no exponen conexiones, SQL ni modelos privados de SQLite.
3. **Mover la persistencia, no las reglas.** Un adaptador SQLite y una unidad de trabajo implementan los contratos. La política de imputación, los cálculos y las decisiones sobre RAI/RNI permanecen en su autoridad actual.
4. **Conservar una sola transacción efectiva.** Todos los cambios que pertenecen a un pago deben confirmarse juntos o revertirse juntos. No se permiten transacciones independientes por cada repositorio.
5. **Validar de nuevo.** Ejecutar las pruebas de caracterización, fallos, idempotencia, concurrencia y cuadre del ledger; después, toda la suite de CI en Python 3.11–3.14 y los controles de seguridad.

La transición debe ser incremental: primero se reemplaza una dependencia por vez, mientras la API pública existente continúa funcionando. No se habilita V3 ni se cambia la autoridad Legacy por hacer esta refactorización.

## 5. Cuándo se podrá considerar completa esta etapa

La frontera de escritura no se acepta solo porque `ServicioPagos` deje de importar repositorios concretos. Para considerarla terminada, el equipo deberá demostrar que:

- la aplicación no conoce SQLite ni SQL;
- el pago y todas sus evidencias económicas permanecen atómicos;
- los reintentos siguen siendo seguros incluso con dos conexiones;
- los resultados de Legacy mantienen la caracterización aprobada;
- los métodos públicos continúan funcionando durante la migración;
- las reglas arquitectónicas quedan protegidas por pruebas automáticas.

Este documento fija el camino de trabajo; no declara que la escritura Legacy ya esté desacoplada ni que el motor V3 esté autorizado para reemplazarla.
