# Estado del proyecto y rumbo

**Última actualización:** 10 de octubre de 2026. Las novedades, cambios validados y pendientes se reúnen en el [Registro de cambios](REGISTRO_DE_CAMBIOS.md).

Este documento existe para que alguien que recién entra al repositorio pueda
entender rápidamente dónde estamos, qué ya está resuelto y qué sigue.

## En una frase

Préstamos Privados ya no es solo un motor de cálculo: tiene una vertical
operativa completa sobre Streamlit, trazabilidad y un Motor de Pagos V3 preparado
para adopción controlada. La siguiente evolución es convertir esa base sólida en
un producto que una persona pueda entender y usar sin saber de finanzas.

## Estado ejecutivo

**10 de octubre de 2026**

| Área | Estado | Situación |
|---|---|---|
| M1–M7 | ✅ | Vertical de producto integrada y validada; la terminación del MVP local sigue pendiente de cerrar los recorridos contractuales y de autocrédito |
| N1–N3 | ✅ | Identidad, sesión y capacidades/roles preparados |
| L1.2 | ✅ | Paquete reproducible de decisión de canary integrado |
| J17.1 | ✅ | Fachada única de preview integrada |
| J17.2 | ✅ | Renderer desacoplado de servicios de aplicación |
| J17.3 | ✅ | Lectura de deuda compartida; Legacy ya no es necesario para esa consulta |
| J17.4 | ✅ | Matriz reproducible del preview; divergencias sensibles identificadas |
| J17.5 | 🚧 | Divergencias caracterizadas; falta decisión financiera y criterio formal de salida |
| J18 | ✅ | Política común de imputación versionada por préstamo |
| J18.1 | ✅ | SOMBRA consume la política vigente sin cambiar Legacy efectivo |
| J18.2 | ✅ | Cada pago conserva la versión exacta de política aplicada |
| L1.1 | 🚧 | Bloque técnico principal: canary real sobre base operativa autorizada |
| M7 | ✅ | Comparador de decisiones financieras integrado y validado |
| Simulador y planes de reposición ARS/USD | 🚧 | Benchmark bruto/neto, sensibilidad, índice total-return, backtest y exportaciones. PR #225 guarda análisis; PR #227 aporta identidad/versiones/cierre (v023); PR #229 añade aportes inmutables de reposición con fuente de cotización, equivalente USD de referencia y resumen de avance contra cuotas vencidas (v024). **No crea contrato ni pago, no prueba compra de USD ni calcula aún rendimiento de una inversión real.** No descarga mercado; pendiente aceptación manual y modelos específicos de bonos/YTM, retenciones y acciones corporativas |
| Cuentas locales / esquema v024 | ✅ / 🚧 | Cuentas locales, garantías y snapshots de carencia (v021) integrados. v022 guarda análisis, v023 los agrupa bajo planes versionados y v024 agrega aportes inmutables de reposición con trazabilidad. El alta de préstamo y los pagos todavía no forman un recorrido operativo completo con carencia |
| D2 — Personas polifuncionales y garantías | ✅ | [PR #182](https://github.com/JavierGrecco/prestamos_privados/pull/182) integrado; roles financieros acumulables, vínculo cuenta-persona opcional y garantía ligada al préstamo, sin efectos implícitos sobre deuda o pagos |
| D3 — Navegación por catálogo y capacidades | ✅ | PR #183 integrado; catálogo único, navegación agrupada, rutas contextuales y capacidades sensibles separadas; CI previo al merge en verde |
| D4 — Diseño visual oscuro | ✅ | PR #184 integrado; tema oscuro predeterminado y selector previo al login recuperado. La inspección visual manual del usuario sigue pendiente |
| D5 — Instalación local reproducible | 🚧 | Implementación y guía integradas por PR #185; tests Python 3.11–3.14, CodeQL, auditoría y smoke Ubuntu/Windows/macOS verdes; siguen pendientes primer acceso/reinicio manual y lock exacto de dependencias |
| N4 | 📌 | Registro público, recuperación por email y proveedor de identidad online siguen pendientes ([#137](https://github.com/JavierGrecco/prestamos_privados/issues/137)) |
| Seguridad de interfaz | 🚧 | Escape, regresiones y primera comprobación estática integrados por [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162), [#164](https://github.com/JavierGrecco/prestamos_privados/pull/164), [#165](https://github.com/JavierGrecco/prestamos_privados/pull/165) y [#167](https://github.com/JavierGrecco/prestamos_privados/pull/167); falta ampliar cobertura y validar E2E ([#158](https://github.com/JavierGrecco/prestamos_privados/issues/158)) |
| H4.2 — Migraciones históricas | 📌 | Ampliar las pruebas de actualización hasta v020, incluida la revocación de sesiones sin reescribir hechos financieros ([#156](https://github.com/JavierGrecco/prestamos_privados/issues/156)) |
| Protección de main | 🚧 | Falta configurar reglas de rama y checks obligatorios ([#157](https://github.com/JavierGrecco/prestamos_privados/issues/157)) |
| Concurrencia de UI/SQLite | 🚧 | `RLock` protege la transacción explícita de pagos V3 entre `BEGIN IMMEDIATE` y `COMMIT/ROLLBACK`; hay regresión con dos servicios sobre la misma instancia y revisión obsoleta. Falta E2E de dos sesiones reales de Streamlit y contención operativa ([#159](https://github.com/JavierGrecco/prestamos_privados/issues/159)) |
| Migraciones al iniciar | 🚧 | La UI inicializa bases vacías y bloquea upgrades silenciosos de bases existentes; hay CLI de inspección y backup verificado. Faltan pruebas ampliadas de recuperación ([#160](https://github.com/JavierGrecco/prestamos_privados/issues/160)) |

### Prioridad inmediata

La ruta de entrega prioritaria ya está centralizada en la [Hoja de ruta del MVP local](ROADMAP_MVP_LOCAL.md) y el [issue coordinador #223](https://github.com/JavierGrecco/prestamos_privados/issues/223). El orden actual es:

1. Cerrar las decisiones financieras del MVP, con ejemplos numéricos aprobados. Mantener Legacy como autoridad operativa mientras las diferencias con V3 sigan abiertas.
2. Conectar las condiciones contractuales y el calendario del préstamo; el snapshot inmutable de carencia ya existe como base técnica, pero no equivale a la operación completa.
3. Aceptar manualmente el plan y el registro de aportes v024. Luego modelar inversiones realizadas, rescates, costos/impuestos y valorización para medir poder de compra y rendimiento realizado frente al objetivo, separándolos de los escenarios del benchmark.
4. Completar ambos recorridos desde la UI, incluyendo pagos, posiciones, auditoría y reportes.
5. Asegurar instalación, migraciones, backups/restauración, seguridad y aceptación manual.

La protección de `main`, el hardening de sesiones y las diferencias Legacy/V3 siguen siendo tareas relevantes de confiabilidad. No habilitar el cut-over por calendario ni por tener CI verde; la salida financiera necesita evidencia y aprobación propia.

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

### D5 — Instalación reproducible 🚧

El trabajo activo concentra la preparación del entorno Python y el inicio local
con una ruta explícita de SQLite. El iniciador valida el `.venv` de la copia
actual, inicializa solo bases nuevas y se detiene ante migraciones pendientes
hasta recibir autorización y una ruta de backup verificado. La guía cubre
PowerShell, CMD, macOS y Linux; las plataformas que no se ejecuten manualmente
se declararán como no verificadas.


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

J17.1–J17.4 redujeron y midieron la superficie de transición: la UI consume una
fachada única, el renderer recibe resultados ya calculados y la lectura de deuda
es compartida. J17.5 caracterizó diferencias metodológicas sensibles, pero su
issue continúa abierto hasta registrar la decisión financiera de autoridad y
convertirla en criterios de aceptación verificables. La política J18 aporta
versionado y trazabilidad; no debe confundirse con una equivalencia Legacy/V3
que todavía no se demostró para todos los escenarios.

Legacy continúa disponible por transición, comparación y rollback; no se retira
solo por existir una implementación V3.

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


### J18 — Política unificada y trazable

La aplicación ya cuenta con una política de pagos común y versionada por préstamo. Legacy, V3 y SOMBRA utilizan el mismo concepto de política, evitando que una pantalla o una ruta técnica elija silenciosamente un waterfall distinto.

Como siguiente capa, v016 agrega `politica_pago_id` al pago. Así, una operación histórica puede indicar qué versión de política regía en su fecha valor, incluso si posteriormente el contrato cambia de metodología.

La regla de producto queda reforzada:

**el resultado financiero histórico no debe depender de la configuración actual del sistema para poder ser explicado.**


## 9 de octubre de 2026 — evolución de UX e identidad

- **D0 integrada:** el plan de UX e identidad polifuncional está en
  [PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md](PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md)
  y la documentación incluye la secuencia D1–D6.
- **D1 integrada:** el [PR #181](https://github.com/JavierGrecco/prestamos_privados/pull/181)
  mantiene dark como tema predeterminado, deja de seleccionar una persona
  arbitrariamente y guía al ADMIN a crear la primera persona desde una base vacía.
- **D2 en desarrollo:** rama `feat/personas-polifuncionales-d2`, issue [#175](https://github.com/JavierGrecco/prestamos_privados/issues/175).
  Prepara v019 de vínculo cuenta-persona opcional y v020 de garantías por préstamo,
  sin reescribir los hechos económicos. La validación final de D2 depende de las
  pruebas nuevas y del CI completo del PR.
