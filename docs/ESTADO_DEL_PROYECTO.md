# Estado del proyecto y rumbo

**Última referencia:** 8 de octubre de 2026

Este documento existe para que alguien que recién entra al repositorio pueda
entender rápidamente dónde estamos, qué ya está resuelto y qué sigue.

## En una frase

Préstamos Privados ya no es solo un motor de cálculo: tiene una vertical
operativa completa sobre Streamlit, trazabilidad y un Motor de Pagos V3 preparado
para adopción controlada. La siguiente evolución es convertir esa base sólida en
un producto que una persona pueda entender y usar sin saber de finanzas.

## Estado ejecutivo

**8 de octubre de 2026**

| Área | Estado | Situación |
|---|---|---|
| M1–M6 | ✅ | Vertical de producto integrada y validada |
| N1–N3 | ✅ | Identidad, sesión y capacidades/roles preparados |
| L1.2 | ✅ | Paquete reproducible de decisión de canary integrado |
| J17.1 | ✅ | Fachada única de preview integrada |
| J17.2 | ✅ | Renderer desacoplado de servicios de aplicación |
| L1.1 | 🚧 | Bloque técnico principal: canary real sobre base operativa autorizada |
| M7 | ✅ | Comparador de decisiones financieras integrado y validado |
| N4 | 📌 | Próxima evolución de identidad real cuando el despliegue multiusuario lo requiera |

### Prioridad inmediata

Primero: mantener `main` verde y conservar una integración por PR con CI.

Segundo: ejecutar L1.1 solo sobre una base controlada y con evidencia humana.

Tercero: seguir reduciendo la superficie Legacy sin cambiar reglas financieras;
el repositorio ya proporciona los controles, pero no inventa ni automatiza esa
autorización.

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

La protección administrativa de `main` sigue pendiente porque requiere una
configuración de GitHub que no está expuesta por la integración utilizada por
este proyecto.

### J17 — Preview

J17.1 y J17.2 ya redujeron la superficie de transición: la UI consume una
fachada única y el renderer recibe resultados ya calculados. Legacy continúa
disponible mientras L1.1 aporta la evidencia necesaria para el cut-over.

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

### M6 — Reportes y exportaciones ✅

Ahora existe una salida reutilizable de la situación financiera con una misma
fecha de corte y los mismos supuestos para posición, planificación, rendimiento
y escenarios.

La persona puede obtener un informe humano en Markdown y formatos estructurados
JSON/CSV sin modificar la base.

La documentación detallada está en docs/M6_REPORTES_PERSONALES.md.

### L1.2 — Paquete reproducible para decisión de canary ✅

El repositorio ahora puede construir una evidencia única con base, backup
verificable, readiness V3, hash/tamaño del backup, operador y motivo de revisión.

Esto no activa V3 y no reemplaza la aprobación humana ni la ejecución controlada
sobre una base operativa autorizada.

La documentación detallada está en docs/L1_2_PAQUETE_CANARY.md.

### L — Cut-over V3 sigue siendo un frente técnico paralelo

M1–M6 construyen la experiencia de producto sobre un core todavía en adopción
controlada. Legacy sigue siendo la autoridad efectiva hasta completar la
evidencia y el canary real definidos en el runbook.

### N1 — Identidad y autorización ✅

La aplicación separa el operador declarado, la persona seleccionada y la política
de acceso. En entornos configurados, la allowlist limita las personas
consultables y el entrypoint verifica la autorización antes de renderizar
pantallas personales.

El modo local queda explícitamente identificado como **sin autenticación real**.

La documentación detallada está en docs/N1_IDENTIDAD_AUTORIZACION.md.

### N2 — Identidad de sesión ✅

La aplicación ahora consume una abstracción `IdentidadSesion` separada del
operador declarado y de la persona seleccionada. El proveedor local deja claro
que no existe autenticación real, mientras el contexto de seguridad queda
preparado para recibir una identidad autenticada de un proveedor externo.

La documentación detallada está en docs/N2_IDENTIDAD_SESION.md.

### N3 — Autorización por capacidades y roles ✅

La aplicación ahora aplica permisos centralizados por rol sobre las superficies
transversales. La identidad y el permiso quedan separados: autenticarse no
implica tener todas las capacidades.

El modo local mantiene compatibilidad con `LOCAL_ADMIN`, pero sigue identificado
como sin autenticación real.

La documentación detallada está en docs/N3_CAPACIDADES_ROLES.md.

### N4 en adelante — Seguridad e identidad para multiusuario

El siguiente frente de producto/operación es separar definitivamente la
identidad autenticada de la persona consultada y del operador declarado. La
selección de una persona no debe equivaler a permiso para ver o modificar sus
datos.


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

### J17.1 — Fachada única de preview ✅

La pantalla de registro ya no importa directamente `ServicioPagosConSimulacion`.
Consume `ServicioPreviewPago`, que centraliza la selección entre la simulación
histórica y el preview canónico V3.

Esto es una consolidación de API y no un retiro de Legacy.

La documentación detallada está en docs/J17_PREVIEW_FACADE.md.


### J17.2 — Renderer desacoplado ✅

El renderer V3 recibe un `PreviewPagoV3` ya calculado y dejó de conocer
`ServicioPreviewPagoV3`. La selección LEGACY/SOMBRA/V3 queda en
`ServicioPreviewPago`.

Esto es una mejora de arquitectura, no un cambio de reglas financieras ni un
cut-over del motor.


### M7 — Comparador de decisiones financieras ✅

La aplicación incorpora una pantalla **Comparar** para contrastar dos o más
operaciones registradas con la misma fecha de corte, horizonte y supuesto de
inflación.

M7 muestra capital, flujo real, flujo futuro, valor real futuro y rendimiento
histórico cuando existe evidencia suficiente. También advierte cuando las
alternativas no son homogéneas por rol, moneda o reglas relevantes.

La primera versión compara operaciones registradas. Las simuladas quedan como
extensión futura sobre la misma estructura.

La documentación detallada está en docs/M7_COMPARADOR_DECISIONES.md.
