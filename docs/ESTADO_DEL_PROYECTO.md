# Estado del proyecto y rumbo

**Última referencia:** 8 de octubre de 2026

Este documento existe para que alguien que recién entra al repositorio pueda
entender rápidamente dónde estamos, qué ya está resuelto y qué sigue.

## En una frase

Préstamos Privados ya no es solo un motor de cálculo: tiene una vertical
operativa completa sobre Streamlit, trazabilidad y un Motor de Pagos V3 preparado
para adopción controlada. La siguiente evolución es convertir esa base sólida en
un producto que una persona pueda entender y usar sin saber de finanzas.

## Qué está terminado

### Núcleo financiero

- reglas financieras separadas en dominio/;
- planes de pago y amortización;
- pagos completos y parciales;
- mora;
- adelantos RAI/RNI;
- devengamientos;
- distribución entre inversores;
- ledger y auditoría;
- Decimal para dinero;
- pruebas de propiedades y regresiones.

### Motor V3

- integración real con SQLite;
- SOMBRA;
- preflight;
- feature flag;
- modo persistente LEGACY/SOMBRA/V3;
- idempotencia;
- control de concurrencia;
- rollback operativo entre operaciones;
- observabilidad y evidencia histórica;
- canary E2E persistente;
- documentación y runbook.

### Aplicación

- alta de préstamos;
- registro y preview de pagos;
- detalle financiero;
- análisis financiero;
- personas y roles;
- ciclo de vida de préstamos;
- auditoría global e inmutable;
- backups y restore drill;
- exportaciones;
- aceptación end-to-end de la aplicación.

## Qué estamos construyendo ahora

### M1 — Mi espacio ✅

La primera capa de producto orientada directamente a la persona.

La idea es simple: una persona debería poder entrar y entender rápidamente:

**qué tiene, qué tiene pendiente y qué viene después.**

La nueva superficie:

- adapta el contenido al rol de deudor, inversor o ambos;
- separa información real de información estimada;
- usa lenguaje cotidiano;
- explica términos básicos;
- permite profundizar solo cuando hace falta;
- no duplica las reglas financieras ni escribe en SQLite.

La regla permanente está en docs/PRINCIPIOS_UX.md.

## Qué sigue después de M1

### L — Cut-over V3

Es la prioridad técnica de estabilización:

1. ejecutar el precheck sobre una base operativa real;
2. conservar evidencia;
3. ejecutar canary controlado;
4. validar resultados;
5. usar Legacy como rollback entre operaciones;
6. retirar fachadas solo cuando exista evidencia suficiente.

La protección administrativa de main sigue pendiente porque requiere una
configuración de GitHub que no está expuesta por la integración utilizada por
este proyecto.

### J17 — Preview

El issue #99 sigue abierto para converger el preview histórico y el V3 hacia
una única autoridad. No debe resolverse eliminando Legacy a ciegas.

### M2 — Posición financiera consolidada ✅

Mi espacio ahora resume la posición de capital conocida dentro de la aplicación:
capital invertido, capital de deuda pendiente, posición neta de capital,
movimientos reales y proyecciones futuras separadas.

No se presenta como patrimonio total y no incorpora activos externos que el
sistema no conozca.

La documentación detallada está en docs/M2_POSICION_FINANCIERA.md.

### M3 — Planificación financiera ✅

Ahora existe una pantalla **Planificar** que proyecta cobros y pagos futuros
conocidos, muestra el neto mensual, el acumulado y una reserva de referencia
para el peor déficit acumulado.

No es un presupuesto personal: no incorpora sueldo, gastos, ahorros ni activos
externos que la aplicación no conozca.

La documentación detallada está en docs/M3_PLANIFICACION_FINANCIERA.md.

### M4 — Escenarios ✅

Ahora existe una pantalla **Escenarios** para comparar los mismos flujos futuros
bajo diferentes supuestos de inflación y devaluación.

El contrato nominal no cambia. Los escenarios solo cambian la forma de leer el
valor económico de los flujos. La referencia USD se muestra solo cuando existe
un tipo de cambio válido.

La documentación detallada está en docs/M4_ESCENARIOS_PLANIFICACION.md.

### M5 — Rendimiento explicado ✅

La pantalla **Rendimiento** usa las métricas históricas existentes y agrega
contexto: significado para inversor/deudor, cantidad de movimientos, período,
supuesto de inflación y disponibilidad de XIRR/USD.

La aplicación no completa una tasa con proyecciones cuando faltan hechos reales.

La documentación detallada está en docs/M5_RENDIMIENTO_EXPLICADO.md.

### M6 en adelante — Producto financiero

Una vez estable la adopción:

- patrimonio completo;
- planificación financiera;
- escenarios y poder adquisitivo;
- XIRR/NPV ampliados;
- reportes más completos.

## Cómo orientarse en el código

| Necesidad | Dónde mirar |
| --- | --- |
| Regla financiera | dominio/ |
| Caso de uso / transacción | aplicacion/ |
| Persistencia | infraestructura/ |
| Pantalla | ui/ |
| Regresión | tests/ |
| Decisión o procedimiento | docs/ |

Regla práctica:

> Si una pantalla necesita inventar una fórmula financiera, probablemente la
> lógica está en el lugar equivocado.

La UI presenta. El dominio decide. La aplicación orquesta. La infraestructura
persiste.

## Cómo trabajar de forma segura

Antes de cambiar una regla financiera:

1. encontrar y entender el comportamiento actual;
2. agregar o revisar una regresión;
3. implementar el cambio en la capa correcta;
4. comparar resultados;
5. ejecutar CI;
6. documentar el motivo del cambio.

No se elimina una pieza Legacy solo porque haya una alternativa más nueva. Se
retira cuando dejan de existir consumidores y la evidencia demuestra que la
nueva ruta es suficiente.

## Principio de producto

La precisión financiera y la claridad humana no compiten.

El proyecto debe mantener la complejidad necesaria para que los cálculos sean
correctos, pero mostrarla de forma gradual:

**primero comprender → después decidir → después profundizar.**