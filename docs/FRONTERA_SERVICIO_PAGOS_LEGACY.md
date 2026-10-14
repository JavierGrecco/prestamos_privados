# Frontera actual de ServicioPagos (Legacy)

**Estado:** diagnóstico previo a una futura modularización de la escritura. Este documento no cambia el comportamiento del sistema.  
**Seguimiento:** [Issue #267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267).  
**Prioridad:** mantener la aplicación local estable y no cambiar las reglas financieras mientras se separan responsabilidades.

## 1. Qué vemos hoy

`ServicioPagos` conserva la fachada pública y delega la escritura a `ManejadorRegistroPagoLegacy`. La ruta UI, el preview Legacy, el puente SOMBRA y las pruebas de caracterización usan `infraestructura/composicion/servicio_pagos_legacy.py`; la fábrica construye los repositorios SQLite y los inyecta. `PagoRepo` concentra el SQL de idempotencia y los metadatos de adelanto. En paralelo, `ServicioPreviewPago` consume el contrato `SimuladorPagoLegacy` de `aplicacion/puertos/preview_pago.py`, en vez de tipar directamente `ServicioPagosConSimulacion`. El constructor `ServicioPagos(db)` se conserva únicamente como puente de compatibilidad; su uso directo dentro del repositorio queda en una prueba dedicada. Antes de eliminarlo se debe comprobar si hay consumidores externos y acordar una migración compatible.

La simulación de adelanto de solo lectura también se separó en `aplicacion/consultas/simulacion_adelanto_legacy.py`. La fachada mantiene `simular_adelanto()` y le entrega una función que conserva la resolución histórica de deuda y política. Esta extracción no mueve el registro efectivo del adelanto ni las escrituras RAI/RNI; solo separa las alternativas que se muestran antes de confirmar una operación.

La proyección de solo lectura del estado de cuotas con arrastre ya se separó en `aplicacion/consultas/estado_cuotas_con_arrastre.py`. `ServicioPagos.estado_cuotas_con_arrastre()` sigue disponible como API compatible y delega el armado de la respuesta a esta consulta. El contrato de lectura enumera también los campos de cuota que necesita esta proyección. La extracción mantiene los cálculos existentes; la prueba de caracterización protege los importes y el desglose sin consultar infraestructura desde la consulta.

La compatibilidad de políticas para bases antiguas también deja de resolverse mediante una captura de `sqlite3.OperationalError` en `ServicioPagos`: la fachada utiliza `PoliticaPagoRepo.obtener_vigente_con_id_o_canonica()`, que solo aplica la política canónica cuando falta la tabla versionada. La consulta matemática de deuda queda como colaborador compartido y no necesita conocer ese detalle de persistencia.

La preparación de cambios para las cuotas impagas anteriores a la cuota objetivo se separa en `aplicacion/servicios/preparacion_cuotas_anteriores_pago_legacy.py`. El colaborador aplica el orden de waterfall que recibe de la política y devuelve las actualizaciones previstas junto con los importes remanentes. No modifica las cuotas de entrada, no accede a SQLite y no abre transacciones. El manejador conserva el cálculo financiero principal y sigue siendo responsable de la escritura atómica.

La siguiente extracción, revisada en esta entrega, separa también la preparación del estado de la cuota objetivo y el armado de la lista de imputaciones en `aplicacion/servicios/preparacion_cuota_objetivo_pago_legacy.py`. El colaborador calcula el saldo posterior, el interés extra previsto y la lista que se enviará al repositorio, sin escribir ni abrir transacciones. El manejador sigue decidiendo cuándo registrar el pago y aplica todos los cambios dentro de la misma unidad de trabajo. Se conserva la semántica de imputaciones Legacy actual; no se introduce una nueva regla de asignación.

### Hallazgo de conciliación por cuota — issue #332

La prueba de caracterización `test_caracteriza_atribucion_de_imputaciones_con_arrastre_de_cuota_parcial` deja reproducido un punto que requiere decisión antes de cualquier corrección: cuando una cuota previa está en `PARCIAL`, el pago del período siguiente puede terminar sus saldos y actualizar también la cuota objetivo, mientras las filas de `imputaciones` del pago se vinculan a la cuota objetivo. El total de las imputaciones sí coincide con el importe registrado, pero la referencia por cuota no refleja necesariamente qué saldo fue reducido.

Esto describe el comportamiento actual; por sí solo no determina cuál debe ser la regla contractual o contable. El issue [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) rastrea el inventario de lectores de `imputaciones.cuota_id`, el efecto sobre informes/exportaciones y la decisión de atribución. No se cambia el comportamiento productivo ni se reescriben pagos históricos hasta concluir ese análisis.

El recálculo y la sustitución de cuotas futuras tras un adelanto se delegan ahora en `aplicacion/servicios/aplicador_adelanto_legacy.py`. El colaborador usa contratos de repositorio, no conoce SQLite y no abre una transacción propia. El manejador continúa invocándolo dentro de la unidad atómica que contiene el pago, la distribución, el ledger y la auditoría. La API interna de delegación se mantiene para preservar los puntos de extensión históricos.

El reparto proporcional a inversores se delega ahora en `aplicacion/servicios/distribucion_pago_legacy.py`. El colaborador recibe contratos de lectura de participaciones y escritura al ledger, no conoce tablas ni conexiones y no abre su propia transacción. La llamada continúa dentro de la unidad de trabajo de registro del manejador, de modo que una falla al distribuir revierte el pago completo.

El caso de uso de escritura extraído coordina parte de las responsabilidades que antes residían enteramente en la fachada. En esta transición siguen conviviendo:

- validación de la solicitud y elección de la política vigente por fecha de valor;
- obtención de la deuda y cálculo de la imputación; la preparación de cuotas anteriores se delega en `PreparadorCuotasAnterioresPagoLegacy` y la preparación de la cuota objetivo y sus imputaciones en `PreparadorCuotaObjetivoPagoLegacy`;
- actualización de cuotas y tratamiento de pagos parciales;
- coordinación del adelanto RAI/RNI (el recálculo de cuotas futuras ahora se delega en `AplicadorAdelantoLegacy`);
- registro de pagos e imputaciones, distribución a inversores (ahora delegada en `DistribuidorPagoLegacy`), ledger y auditoría.

Las consultas de resumen de impacto e historial de decisiones ya se extrajeron a `aplicacion/consultas/impacto_pagos.py` mediante el [PR #306](https://github.com/JavierGrecco/prestamos_privados/pull/306). El coordinador transaccional se extrae en el [PR #313](https://github.com/JavierGrecco/prestamos_privados/pull/313): el caso de uso queda detrás de contratos de aplicación, mientras la fachada conserva la API Legacy y los adaptadores concentran las operaciones SQL. El PR #315 mueve la composición de la ruta UI fuera del constructor; el PR #316 lleva también el preview Legacy y SOMBRA a esa misma fábrica. El PR #318 completa un pequeño paso de dependencia: el preview consulta un puerto de simulación en vez de importar la clase Legacy concreta. La caracterización funcional ya usa la fábrica oficial y la guarda arquitectónica no encontró construcciones directas en las rutas productivas del repositorio. Una prueba dedicada mantiene protegido el contrato `ServicioPagos(db)`. Antes de eliminar ese puente, queda por confirmar si algún consumidor externo depende de él.

### Contrato de composición que también se verifica

La prueba de composición debe comprobar no solo que los colaboradores sean del tipo esperado, sino que cada repositorio conserve la identidad exacta de la misma instancia de `BaseDatos` entregada a la fábrica. También debe verificar que el manejador reciba los mismos repositorios expuestos por la fachada. De ese modo, una futura modificación de la fábrica no podrá introducir inadvertidamente otra conexión o duplicar un colaborador detrás de la API pública.

Esta comprobación complementa —no sustituye— las pruebas de rollback, idempotencia y concurrencia. La garantía se acepta cuando la prueba de contrato y la matriz de CI están en verde.

## 2. La garantía que no puede perderse

Un pago no puede quedar guardado a medias. La operación debe conservar una unidad de trabajo coherente para el pago, sus imputaciones, la actualización de cuotas, el posible adelanto, la distribución entre inversores, el ledger y la auditoría.

La conciliación por cuota tiene ahora una caracterización explícita y queda abierta en [issue #332](https://github.com/JavierGrecco/prestamos_privados/issues/332): se verifica tanto el saldo total del pago como la diferencia entre la cuota que disminuye y la cuota a la que se vincula la imputación. No se da por resuelta hasta definir la regla deseada y sus efectos sobre informes e historia.

El [PR #314](https://github.com/JavierGrecco/prestamos_privados/pull/314) mueve la transacción inmediata exterior al manejador de aplicación. Este abre la unidad de trabajo antes de consultar la clave de idempotencia y vuelve a comprobarla dentro de la misma transacción antes de leer la deuda y registrar el pago. Los bloques de repositorios que ya existen se adhieren a esa unidad exterior; no deben confirmar por separado el pago, las cuotas, el recálculo, la distribución, el ledger o la auditoría. La fachada conserva la traducción de errores para la UI, pero ya no decide dónde empieza y termina la operación atómica.

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
| `test_fallo_despues_de_actualizar_cuota_revierte_todo_el_pago` | Si falla justo después de guardar el estado de la cuota, se revierten la cuota y todas las evidencias del pago. |
| `tests/test_idempotencia_pago_legacy.py` | Reintentos, rechazo de claves con contenido distinto, concurrencia entre dos conexiones y separación entre fecha real y fecha de valor. |
| `tests/test_repositorios_pagos.py` | Reglas de persistencia de pagos, imputaciones, ledger y auditoría. |

La cobertura actual prueba fallos después de la actualización de una cuota, entre dos actualizaciones consecutivas de cuotas, durante el ledger, después de escribir auditoría, después de los recálculos RAI/RNI y justo después de escribir movimientos de distribución a inversores. La prueba `test_fallo_en_segunda_actualizacion_de_cuotas_revierte_todo` deja constancia de que la primera cuota llegó a cambiar dentro de la transacción y verifica que el rollback restaure las cuotas, pagos, imputaciones, ledger, auditoría y recálculos al estado anterior. Las pruebas de idempotencia también cubren reintentos idénticos, conflictos de clave y concurrencia con dos conexiones. Siguen pendientes verificaciones adicionales de las fronteras entre repositorios, sin reemplazar las regresiones existentes.

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
