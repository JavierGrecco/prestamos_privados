# L1 — Inventario de consumidores Legacy y superficie de transición

## Objetivo

Identificar qué consumidores mantienen vivo el flujo Legacy y qué piezas V3 siguen siendo fachadas de transición. Este documento evita retirar módulos basándose solamente en búsquedas de nombres.

## API efectiva principal de la UI

| Consumidor | Uso actual | Clasificación | Retiro |
|---|---|---|---|
| `aplicacion.servicios.registro_pago_ui.ServicioRegistroPagoUI` | Punto único de registro efectivo; delega a Legacy, SOMBRA o V3 según el modo persistido | **Productivo / frontera estable** | Mantener |
| `aplicacion.servicios.pagos.ServicioPagos` | Registro Legacy efectivo cuando el modo persistido es `LEGACY` | **Productivo / rollback** | Mantener hasta cierre de cut-over |
| `aplicacion.servicios.pagos_simulacion.ServicioPagosConSimulacion` | Preview/simulación histórica desde la UI | **Productivo / transición** | Reemplazar con simulación canónica antes de retirar |
| `ui/pagina_registrar_pago.py` | Usa `ServicioPagosConSimulacion` para preview histórico y `ServicioRegistroPagoUI` para confirmación | **Productivo / UI** | Mantener mientras exista preview histórico |
| `aplicacion.servicios.__init__.py` | Mantiene alias público `ServicioPagos = ServicioPagosConSimulacion` por compatibilidad | **Compatibilidad** | Retirar solo después de inventario de imports externos |

## Superficie V3 transitoria

| Pieza | Rol | Decisión actual |
|---|---|---|
| `registro_pago_v3.py` | registro transaccional base | mantener como componente interno |
| `registro_pago_v3_devengamientos.py` | composición histórica de devengamientos | mantener temporalmente |
| `registro_pago_v3_completo.py` | registro + devengamientos + distribución | mantener temporalmente |
| `registro_pago_v3_completo_adelantos.py` | registro completo + RAI/RNI | candidato a caso de uso final V3 |
| `fabrica_registro_pago_v3.py` | composition root | mantener |
| `puente_motor_pago_v3.py` | frontera de selección/ejecución | mantener durante adopción |
| `ejecutor_sombra_pago_v3.py` / `sombra_pago_v3_sqlite.py` | ejecución SOMBRA | mantener mientras exista sombra |
| `simulacion_pagos_v3.py` | simulación V3 paralela | mantener hasta converger el preview |

## Evidencia y tests

`scripts/auditar_apis_pago.py` usa AST y es útil para inventariar imports sin ejecutar módulos. Su alcance es estático: no demuestra ausencia de referencias dinámicas, reflection, entrypoints externos o consumidores fuera del repositorio.

Por eso, antes de retirar una API deben verificarse además:

1. referencias de código productivo;
2. referencias de tests y fixtures;
3. imports públicos documentados;
4. scripts/entradas de operación;
5. consumidores externos conocidos;
6. existencia de una API de reemplazo con regresiones equivalentes.

## Regla para retirar Legacy

No retirar `ServicioPagos` ni `ServicioPagosConSimulacion` solamente porque V3 ya exista.

El retiro requiere:

- canary real satisfactorio;
- rollback probado;
- inventario de consumidores actualizado;
- simulación y registro convergentes cuando corresponda;
- equivalencia financiera aceptada;
- migración/compatibilidad documentada;
- CI completamente verde.

## Próxima convergencia recomendada

El objetivo de la siguiente etapa es que el preview de la UI deje de depender de una segunda implementación de planificación financiera. La migración debe comenzar con caracterización y comparación, no con eliminación directa.

## J17.2 — Frontera del renderer del preview

La UI ya no instancia ni importa `ServicioPreviewPagoV3` directamente.

`ServicioPreviewPago` resuelve el modo y devuelve el resultado de aplicación;
`ui/preview_pago_v3.py` se limita a presentar ese resultado.

Esto reduce el acoplamiento de la UI y mantiene la futura convergencia en una
frontera de aplicación estable.

La próxima decisión sigue siendo de adopción, no de eliminación: Legacy continúa
siendo necesario para rollback y comparación hasta cerrar L1.1 y la equivalencia
financiera.
