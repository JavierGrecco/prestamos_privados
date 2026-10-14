# Arquitectura modular por capacidades de negocio

**Estado:** implementación incremental en curso; ya hay límites y contratos aplicados en producción de código, pero la modularización todavía no está aceptada como completa.  
**Seguimiento:** [Issue #267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267).  
**Prioridad:** mejorar mantenibilidad sin poner en riesgo el cierre del MVP local (#223).

## Estado de implementación — 14 de octubre de 2026

La migración ya no está solamente planificada: hay cambios integrados en `main` y protegidos con CI. En las últimas entregas se han añadido puertos tipados y adaptadores SQLite para el análisis financiero, la planificación personal y la vista humana de Mi espacio. El comparador M7 también queda detrás de un contrato de lectura: sus cálculos continúan en aplicación y el acceso a personas, préstamos y participaciones se concentra en infraestructura. Los detalles y sus evidencias están en [el registro de cambios](REGISTRO_DE_CAMBIOS.md) y en el [seguimiento de arquitectura (#267)](https://github.com/JavierGrecco/prestamos_privados/issues/267).

**Esto no significa que la arquitectura ya esté terminada.** `ServicioPrestamos`, `ServicioPersonas` y `ServicioGarantiasPrestamo` están integrados con contratos públicos y composición. El catálogo de correcciones auditables y su escritura transaccional quedaron integrados en `main` mediante los [PR #304](https://github.com/JavierGrecco/prestamos_privados/pull/304) y [#305](https://github.com/JavierGrecco/prestamos_privados/pull/305). El [PR #306](https://github.com/JavierGrecco/prestamos_privados/pull/306) separó también las consultas de resumen e historial de decisiones de pago: `ServicioPagos` conserva su API pública, mientras esas proyecciones se calculan en una consulta de solo lectura mediante contratos. No se modificaron el registro transaccional, Legacy/SOMBRA/V3 ni sus reglas económicas. La siguiente frontera crítica es el flujo de escritura de `ServicioPagos`. El [diagnóstico de ServicioPagos Legacy](FRONTERA_SERVICIO_PAGOS_LEGACY.md) reúne las garantías caracterizadas. Los PR [#313](https://github.com/JavierGrecco/prestamos_privados/pull/313) y [#314](https://github.com/JavierGrecco/prestamos_privados/pull/314) extrajeron el coordinador de escritura Legacy, su unidad de trabajo e idempotencia. El PR #315 traslada el ensamblado de repositorios de la ruta UI a `infraestructura/composicion/servicio_pagos_legacy.py`; el constructor histórico `ServicioPagos(db)` permanece como puente explícito para consumidores antiguos. La migración completa requiere inventariar y mover esos consumidores restantes antes de eliminar el puente. El PR #316 unifica además la composición de los previews Legacy y del puente SOMBRA mediante la misma fábrica; no se construyen servicios de pago desde esos ensamblados. El constructor directo sigue siendo una ruta de compatibilidad temporal para consumidores restantes. Se añade una guarda AST en el PR #317 para detectar nuevas construcciones directas desde aplicación, UI, scripts o composición fuera de la fábrica oficial. El PR #317 también migró el detalle de préstamos (`ui/pagina_prestamos.py`) al ensamblado oficial después de que la guarda AST detectara ese último uso directo. La regla permanece estricta y cubre aplicación, UI, scripts y composición. La arquitectura general aún necesita más límites y pruebas: una suite verde valida lo probado, pero no certifica por sí sola el producto completo ni la ausencia total de errores financieros.

El plan sigue siendo migrar capacidad por capacidad, preservar resultados históricos, mantener Legacy como autoridad hasta una decisión explícita y no tocar la transacción de registro de pagos durante refactorizaciones que solo necesitan separar lecturas.


## 1. La decisión, en palabras simples

Préstamos Privados debe organizarse en **módulos de negocio con límites claros, contratos públicos pequeños y dependencias controladas**. Cada módulo resuelve una responsabilidad, mantiene su complejidad dentro de sus límites y ofrece servicios para que otras partes puedan utilizarla.

Para la entrega local actual, esos módulos compartirán un único proceso de aplicación y una base SQLite. Eso describe cómo se ejecuta y se instala el producto; **no significa que cada módulo sea otro monolito**. Cada módulo debe ser pequeño en responsabilidad, cohesivo y accesible mediante su API pública. Tampoco implica que todos los módulos puedan acceder libremente a todos los demás.

Conviene distinguir tres conceptos:

- **Modularidad:** cómo se separa, entiende, prueba y mantiene el código.
- **Despliegue:** cuántos programas o procesos se instalan y operan por separado.
- **Distribución:** cómo se comunican esos procesos, normalmente por red o mensajería.

Primero haremos firmes los límites lógicos. No añadiremos procesos separados, llamadas HTTP internas, una base por módulo ni un bus de eventos solo para que la arquitectura parezca distribuida. Esas decisiones se justifican cuando hay necesidades comprobables de despliegue independiente, escala, aislamiento o propiedad operativa.

## 2. Principios obligatorios

### 2.1. Dividir por responsabilidad de negocio, no por tipo de archivo

Cada módulo representa una capacidad reconocible —por ejemplo, préstamos, pagos o reposición de capital— y contiene o coordina las piezas necesarias para esa responsabilidad. No alcanza con repartir archivos entre carpetas llamadas `servicios`, `helpers` o `utils`.

Los límites se deciden mirando las reglas que cambian juntas, los datos que protege cada capacidad y el lenguaje que usa el negocio. Si dos áreas tienen reglas y ciclos de vida distintos, no deben fusionarse solo porque ambas usan dinero.

### 2.2. Una API pública por módulo

Cada módulo debe declarar qué operaciones ofrece, qué datos recibe, qué resultados devuelve y qué errores puede comunicar. Sus consumidores usan esa API; no importan implementaciones internas, llaman repositorios privados del otro módulo ni dependen de tablas ajenas.

Los contratos serán explícitos y tipados. No deben exponer conexiones SQLite, filas crudas de la base, objetos internos mutables ni detalles accidentales de implementación.

### 2.3. Dependencias permitidas, sin ciclos

Las dependencias entre módulos deben formar un grafo dirigido sin ciclos. Un módulo solo puede depender de contratos públicos que estén aprobados como parte de su diseño.

Si dos áreas se necesitan mutuamente, no se resolverá creando importaciones circulares. Se redefinirá el límite, se moverá la coordinación a un caso de uso apropiado o se introducirá un contrato que represente la necesidad real.

### 2.4. Cada dato tiene un responsable

Cada módulo define qué conceptos y tablas están bajo su responsabilidad, quién puede modificarlos y por qué operación. Que los módulos compartan el archivo SQLite no concede permiso para leer o escribir cualquier tabla directamente.

Las lecturas entre módulos se hacen por servicios o consultas publicados. Los informes pueden combinar lecturas y modelos de consulta, pero no se convierten en otra autoridad de cálculo o escritura.

No se exige una base física separada para cada módulo en el MVP local. La propiedad de datos es primero una regla de diseño y acceso. Separar bases es otra decisión, con costos y requisitos propios.

### 2.5. Una sola autoridad por regla financiera

Una regla importante —interés, calendario, mora, imputación, distribución, rendimiento o conversión monetaria— debe tener una implementación autorizada para cada política vigente. Simuladores, pantallas e informes consumen esa autoridad; no copian la fórmula.

Las diferencias entre Legacy y V3 se resuelven con caracterización, casos numéricos aprobados y evidencia. La reorganización modular no autoriza por sí misma el cut-over a V3 ni cambia préstamos históricos.

### 2.6. Las transacciones financieras siguen siendo atómicas

El registro de un pago puede necesitar guardar el pago, las imputaciones, la actualización de cuotas, el ledger y la auditoría. En la aplicación local, esas escrituras críticas deben conservar una unidad transaccional coherente en SQLite.

Los módulos pueden aportar operaciones de escritura propias coordinadas por el caso de uso de aplicación y la misma unidad de trabajo. No deben abrir y confirmar transacciones independientes que permitan dejar un pago registrado sin su evidencia asociada.

No se dividirá una operación crítica entre servicios remotos hasta diseñar y probar un protocolo explícito de consistencia, reintentos, idempotencia y recuperación.

### 2.7. Compartir solo los conceptos realmente comunes

Un núcleo compartido puede contener tipos transversales estables, como importes exactos, fechas civiles, identificadores y contratos básicos. Debe ser pequeño y no convertirse en una carpeta donde se acumulen reglas sin dueño.

Los conceptos de préstamo, pago, rendimiento y reposición pertenecen a sus respectivos contextos. Que dos módulos manejen valores monetarios no significa que deban compartir todo su modelo de negocio.

### 2.8. Verificar las reglas con herramientas, no solo con disciplina

Las reglas arquitectónicas importantes deben comprobarse en CI. `tests/test_arquitectura_capas.py` protege tres límites: el dominio no importa capas externas; la infraestructura no importa servicios concretos de aplicación; y los contratos de `aplicacion/puertos/` no dependen de servicios concretos, infraestructura, UI, Streamlit ni SQLite. La comprobación resuelve imports absolutos y relativos para reducir vías de evasión. Es una protección incremental: no prohíbe todavía toda dependencia directa de los servicios de aplicación hacia SQLite, porque el flujo de pagos tiene consumidores existentes que deben migrarse por etapas. La revisión humana sigue siendo necesaria; el análisis estático no detecta todos los imports dinámicos y todavía deben incorporarse controles de ciclos y de acceso a APIs públicas.

Los tests deben cubrir reglas de dominio, contratos entre módulos, persistencia, transacciones y recorridos de extremo a extremo. Mover archivos y obtener pruebas verdes no basta para aceptar una modularización si no se demostraron los límites y los comportamientos esperados.


### Hallazgos iniciales del código

Una primera inspección puntual del flujo de pagos confirma que hay que establecer y hacer cumplir esos límites. No es aún un inventario completo de todas las importaciones del repositorio.

- `infraestructura/repositorios/registro_pago_v3.py` necesitaba conocer `EstadoRegistroPagoV3` e `IdempotenciaPagoV3`, definidos dentro del servicio concreto. El PR de contratos los traslada a `aplicacion.puertos.registro_pago_v3`; el servicio conserva importaciones de reexportación para no romper consumidores existentes.
- Las fábricas que ensamblan la escritura V3 y el puente SOMBRA ya viven en `infraestructura/composicion/registradores_pago.py`, no en `aplicacion/servicios`. Allí se conectan los casos de uso de registro con `RepositorioRegistroPagoSQLiteV3`, las consultas comparadoras, los repositorios de observabilidad y el ejecutor Legacy, sin trasladar reglas financieras fuera de sus servicios actuales.
- `ui/pagina_registrar_pago.py` dejó de importar `PrestamoRepo` directamente para resolver el número y el destino del préstamo. La pantalla consume `ServicioPreviewPago.obtener_resumen_prestamo`, que devuelve el DTO público `ResumenPrestamoParaPago` y no expone el modelo de persistencia. Sigue conociendo `BaseDatos` y una excepción de infraestructura; la composición de dependencias y el tratamiento de errores todavía deben desacoplarse.
- `aplicacion/consultas/deuda_proximo_pago.py` depende del protocolo `RepositorioLecturaPrestamoPago` de `aplicacion/puertos/consulta_prestamo_pago.py`; ya no importa ni crea `PrestamoRepo` y se prueba con un colaborador falso, sin SQLite.
- `aplicacion/consultas/historial_pagos.py` queda como fachada sobre `ConsultaHistorialPagos`. Los DTO públicos están en `aplicacion/puertos/historial_pagos.py`, mientras `infraestructura/consultas/historial_pagos.py` conserva el SQL de solo lectura. La pantalla de pagos recibe la consulta desde `infraestructura/composicion/historial_pagos.py`; la extracción no cambia hechos persistidos ni cálculos financieros.
- `aplicacion/consultas/preview_pago.py` recibe sus tres colaboradores por constructor y no conoce repositorios concretos. La raíz `infraestructura/composicion/pagos.py` los ensambla para la instalación SQLite local; la UI y las pruebas de caracterización usan ese punto de composición.
- La posición financiera también se reutiliza desde Reportes mediante `infraestructura/composicion/reportes_persona.py`. `ServicioReportesPersona` recibe ese read model por constructor, y la pantalla de Reportes ya no construye el servicio directamente. La extracción de consultas SQL internas de planificación, rendimiento y escenarios queda pendiente por separado.
- `aplicacion/consultas/preview_pago_v3.py` recibe cuatro colaboradores de lectura mediante contratos públicos (`RepositorioLecturaPrestamoPago`, `RepositorioPoliticaPreviewV3`, `RepositorioEstadoPreviewPagoV3` y `ServicioDeudaProximoPago`). No importa adaptadores SQLite ni recibe una conexión; la composición local conecta esos contratos con los repositorios existentes.
- `aplicacion/servicios/registro_pago_ui.py` dejó de crear repositorios, configuración, preflight y fábricas Legacy/SOMBRA/V3. Recibe esas dependencias por constructor; `infraestructura/composicion/pagos.py` ofrece `crear_servicio_registro_pago_ui`, que delega el ensamblado V3/SOMBRA en `infraestructura/composicion/registradores_pago.py`. Quedan pendientes los límites internos de algunas fachadas de escritura, a migrar solo con pruebas de atomicidad e idempotencia.
- `aplicacion/servicios/preflight_motor_pago_v3.py` recibe tres lectores por contrato: versión de esquema, auditoría de integridad y métricas SOMBRA. No importa migraciones, consultas SQLite ni otros servicios para recuperar esos datos. `infraestructura/composicion/pagos.py` los ensambla y comparte el mismo preflight con registro y configuración, conservando todos los criterios para habilitar V3.
- `ServicioReadinessCanaryV3` recibe el preflight y la configuración por constructor; el paquete de decisión, la CLI de canary y las pantallas de Motor V3/Operación usan fábricas del punto de composición. `ServicioOperacionUI` también recibe su lectura de métricas y preflight sin construirlos internamente. Además, recibe `OperacionesBackup` por contrato y solo usa la ruta de la base activa; `infraestructura/adaptadores/operaciones_backup.py` conecta el puerto con `infraestructura.backup`. El servicio ya no importa funciones ni DTOs de ese módulo, y una guarda arquitectónica protege la frontera. `ServicioPaqueteCanaryV3` también recibe el mismo puerto de verificación y ya no importa el adaptador de backup; el contrato compartido vive en `aplicacion/puertos/operaciones_backup.py`.
- `ServicioConfiguracionMotorPago` ya recibe `PersistenciaConfiguracionMotorPago` y el gate preflight por contrato; no importa ni construye repositorios, auditoría ni transacciones. `infraestructura/adaptadores/configuracion_motor_pago.py` implementa el cambio de modo auditado en una misma transacción exterior, conserva la revisión optimista y usa los repositorios existentes con transacciones anidadas. Una prueba inyecta un fallo de auditoría y verifica que el modo y la revisión se revierten.
- `aplicacion/servicios/metricas_sombra_v3.py` ahora recibe una `ConsultaMetricasSombraV3` por contrato. `ConteoSombraV3` y `MetricasSombraV3` viven en `aplicacion/puertos/metricas_sombra_v3.py`; la consulta SQLite los importa desde ahí, sin que aplicación dependa de su implementación. La pantalla Motor V3 y las pruebas construyen la consulta a través de `crear_servicio_metricas_sombra_v3`.
- `aplicacion/servicios/auditoria.py` ahora depende del protocolo `ConsultaAuditoria` y del DTO público `EntradaAuditoria`, ambos en `aplicacion/puertos/auditoria.py`. La UI obtiene el servicio desde `infraestructura/composicion/auditoria.py`; se conserva una ruta de importación compatible de `EntradaAuditoria` desde `infraestructura.repositorios.modelos`. El servicio de consulta ya no construye `AuditoriaRepo` ni importa infraestructura. `ServicioExportaciones` recibe ese caso de uso por constructor y `infraestructura/composicion/exportaciones.py` ensambla ambos read models. Esto evita recrear el servicio con `BaseDatos` desde el caso de exportación de auditoría.
- `aplicacion/consultas/detalle_financiero_prestamo.py` ahora consume `ConsultaDetalleFinancieroPrestamo` y deja de importar `PrestamoRepo` o ejecutar SQL. Los DTO de lectura tipados viven en `aplicacion/puertos/detalle_financiero_prestamo.py`; el adaptador `infraestructura/consultas/detalle_financiero_prestamo.py` concentra los SELECT de préstamo, cuotas, devengamientos, recalculos e imputaciones de capital. `infraestructura/composicion/detalle_financiero.py` arma el adaptador para la UI y exportaciones. La capa de aplicación mantiene la validación, la conversión al read model público, la suma de importes y la trayectoria histórica de capital; no reconstruye ni modifica hechos persistidos.
- Los contratos de observación SOMBRA (`DivergenciaMotorPagoV3` y `EjecucionSombraMotorPagoV3`) también estaban definidos en el puente concreto y eran importados por los repositorios; el PR de contratos los traslada a `aplicacion.puertos.sombra_pago_v3`.
- El registro V3 está distribuido en varias fachadas (`registro_pago_v3.py`, `registro_pago_v3_completo.py`, `registro_pago_v3_completo_adelantos.py`, `registro_pago_v3_devengamientos.py`). La composición SQLite elige el registrador adecuado, pero las fachadas no se consolidan en esta entrega: primero deben compararse Legacy/V3 y caracterizarse sus invariantes de transacción, idempotencia, adelantos, devengamientos y distribución a inversores.
- `infraestructura/composicion/pagos.py` se mantiene como fachada pública compatible, pero ya no contiene todos los ensamblados. Se divide en `preview_pagos.py`, `motor_pago.py`, `registro_pago.py` y `operaciones.py`, cada uno con una responsabilidad cohesionada. Los consumidores actuales conservan sus imports; las funciones se implementan en el módulo de composición especializado.

Estos hallazgos describen objetivos de refactorización, no un juicio sobre la validez de los resultados financieros actuales. Se corregirán de manera incremental, después de identificar consumidores y cubrir las invariantes con pruebas. No se moverán tipos ni servicios críticos en bloque solo para que el árbol de carpetas parezca más limpio.

## 3. Mapa inicial de responsabilidades

Este mapa es el punto de partida para inspeccionar las dependencias reales. No significa que todos los módulos deban crearse o moverse de una vez.

| Módulo propuesto | Responsabilidad principal |
|---|---|
| **Préstamos** | Condiciones contractuales, alta, calendario permitido y ciclo de vida del préstamo. |
| **Pagos** | Vista previa, cálculo autorizado, registro, imputación, adelantos, devengamientos e idempotencia. |
| **Ledger y auditoría** | Movimientos financieros registrados, evidencia histórica e historial de decisiones. |
| **Personas y garantías** | Participantes, relaciones financieras, roles de una persona en una operación y garantías asociadas. |
| **Identidad y acceso** | Cuentas de acceso, sesiones, permisos y capacidades; una cuenta no es lo mismo que una persona financiera. |
| **Autocrédito e inversión** | Planes de reposición, versiones, aportes, flujos, valuaciones, referencias cambiarias, escenarios y rendimiento cuando haya evidencia suficiente. |
| **Consultas e informes** | Posición, comparaciones, reportes y exportaciones de datos ya definidos por las capacidades responsables. |
| **Plataforma local** | Arranque, configuración, SQLite, migraciones, backups, restauración y unidad de trabajo. |

Las reglas monetarias y temporales compartidas solo se centralizarán cuando tengan una semántica común demostrada. El objetivo no es forzar todas las áreas dentro de un modelo de datos universal.

## 4. Cómo se relacionan los módulos

El flujo normal será:

```text
Pantalla o futura API
        |
        v
Caso de uso de aplicación
        |
        +----> API pública de la capacidad
        |
        +----> Unidad de trabajo / transacción
        |
        +----> APIs de ledger y auditoría cuando corresponde
        |
        v
Resultado claro + registros consistentes
```

Una pantalla solicita una acción o consulta; no decide fórmulas ni persiste datos de negocio por su cuenta. El caso de uso coordina los módulos necesarios y devuelve un resultado entendible.

Se utilizarán llamadas internas síncronas como mecanismo predeterminado cuando la operación necesita un resultado inmediato. Los eventos se incorporarán cuando exista una necesidad real de comunicar un hecho a consumidores independientes, no como reemplazo automático de llamadas simples. Un bus de eventos dentro de una aplicación local agrega complejidad y no se incorpora por moda.

## 5. Estructura de código objetivo

La estructura exacta se decide después de inventariar archivos, importaciones y consumidores. Como guía, cada capacidad debería tener un punto de entrada reconocible y mantener cerca sus reglas, casos de uso, adaptadores y pruebas.

```text
aplicacion/
  modulos/
    prestamos/
      api.py              # operaciones públicas
      contratos.py        # entradas y resultados
      dominio/            # reglas propias del módulo
      adaptadores/         # persistencia y conexiones permitidas
      tests/               # pruebas de la capacidad
    pagos/
      api.py
      contratos.py
      dominio/
      adaptadores/
      tests/
    reposicion/
      api.py
      contratos.py
      dominio/
      adaptadores/
      tests/
  plataforma/
    sqlite/
    migraciones/
    backup/
ui/
  # Streamlit: presentación y captura de acciones
```

Este árbol es ilustrativo, no una instrucción para mover todo el repositorio de golpe. Podemos conservar temporalmente paquetes actuales y crear fachadas públicas sobre ellos. La reorganización física debe seguir al entendimiento de dependencias y producir una mejora verificable, no precederlo.

## 6. Cómo se aplicará sin poner en riesgo la operación

### Etapa 1 — Inventario y línea base

- Enumerar los módulos funcionales actuales, sus archivos, importaciones, servicios y consumidores.
- Identificar quién es responsable de cada tabla y qué operaciones cambian datos.
- Marcar dependencias circulares, accesos directos entre áreas y fachadas redundantes.
- Registrar las pruebas y los resultados financieros de referencia antes de cambiar estructura.

**Salida:** mapa actual y mapa objetivo revisados; lista de brechas priorizada por riesgo.

### Etapa 2 — Contratos y reglas automáticas

- Definir los puntos de entrada públicos y las dependencias permitidas.
- Agregar comprobaciones automáticas para evitar ciclos e importaciones internas prohibidas.
- Verificar que dominio no dependa de Streamlit o SQLite y que UI no duplique reglas financieras.
- Documentar los contratos con ejemplos de entradas, resultados, errores y efectos.

**Salida:** CI rechaza nuevas violaciones arquitectónicas relevantes.

### Etapa 3 — Extracción incremental de módulos

- Empezar por áreas donde el acoplamiento y el riesgo sean menores, como determinadas consultas, exportaciones e informes.
- Continuar con autocrédito/reposición cuando las reglas de propiedad y los contratos estén claros.
- Conservar adaptadores compatibles mientras existan consumidores legítimos.
- Eliminar duplicaciones solo después de demostrar que no contienen comportamientos diferentes necesarios.

**Salida:** cada área tiene una API reconocible y pruebas de contrato, sin cambios involuntarios en los resultados.

### Etapa 4 — Consolidación de préstamos y pagos

- Caracterizar Legacy y V3 con ejemplos financieros aprobados.
- Reducir fachadas mediante una secuencia explícita de sustitución y compatibilidad.
- Verificar atomicidad, reintentos, idempotencia, concurrencia, rollback y migraciones.
- Mantener la decisión de activar V3 separada de la refactorización.

**Salida:** API estable y evidencia suficiente para aceptar cada sustitución. Ninguna equivalencia se da por supuesta.

### Etapa 5 — Validación y mantenimiento

- Ejecutar la matriz de CI completa y los tests de arquitectura.
- Completar los recorridos del usuario, instalación, backup y restauración que correspondan al MVP.
- Actualizar arquitectura, índice, estado, registro de cambios y roadmap.
- Registrar deuda técnica restante en lugar de ocultarla bajo una etiqueta de “refactorización terminada”.

**Salida:** cambios aceptados por evidencia y documentación coherente con el código.

La modularización se hará en PRs pequeños. No se realizará una reescritura general ni se mezclará un traslado de archivos con un cambio de fórmula financiera.

## 7. Cuándo considerar módulos desplegables de forma independiente

Separar una capacidad en otro proceso o servicio solo se evaluará cuando exista una razón comprobable, por ejemplo:

- Necesidad de desplegar o escalar esa capacidad con independencia del resto.
- Un límite de seguridad, disponibilidad o recursos que requiera aislamiento.
- Integración con usuarios o sistemas externos que justifique una API estable.
- Equipos que realmente necesiten mantener y operar capacidades con ciclos de entrega distintos.

Antes de separar un servicio será necesario definir quién es dueño de sus datos, cómo versiona su API, qué sucede si no responde, cómo se propagan identificadores de correlación, cómo se manejan reintentos e idempotencia y cómo se recupera una operación parcial.

En una operación financiera que atraviesa servicios, no se debe prometer una única transacción ACID entre bases independientes. Habría que diseñar explícitamente la consistencia y, si corresponde, mecanismos como outbox, procesos de compensación y reconciliación. Esa complejidad no se introduce en el MVP local sin necesidad.

Si más adelante se justifica separar una capacidad, se hará de forma gradual mediante una interfaz de compatibilidad y una migración controlada. Un módulo con buenos límites puede convertirse en candidato a servicio; no todos necesitan hacerlo.

## 8. Criterios para considerar aceptada la modularidad

- [ ] Cada módulo tiene una responsabilidad y un responsable de datos claramente documentados.
- [ ] Cada módulo ofrece una API pública pequeña, tipada y probada.
- [ ] No existen ciclos entre módulos de negocio.
- [ ] Los módulos consumidores no importan detalles internos ajenos ni acceden directamente a sus tablas.
- [ ] UI no duplica reglas de dominio ni escribe registros financieros directamente.
- [ ] Las operaciones críticas conservan atomicidad, precisión, idempotencia y auditoría.
- [ ] CI verifica automáticamente las principales reglas de dependencia.
- [ ] Legacy/V3, reportes e historiales conservan comportamientos aprobados.
- [ ] La instalación local sigue siendo simple y reproducible.
- [ ] La documentación describe la arquitectura implementada, incluidos los límites y excepciones que sigan vigentes.

## 9. Qué queda fuera de esta decisión

Esta decisión no ordena migrar de inmediato a microservicios, cambiar de SQLite, introducir una API web, adoptar un bus de eventos, cambiar las reglas contractuales ni habilitar V3 o carencia. Esos asuntos tienen criterios y aprobaciones propios.

La modularidad debe facilitar la finalización del MVP local; no convertirse en una segunda reescritura interminable. Las prioridades y los criterios de aceptación del producto siguen definidos en el [roadmap del MVP local](ROADMAP_MVP_LOCAL.md).

## 10. Referencias de la industria

Estas referencias sustentan los principios adoptados:

- [Microsoft — Microservices Architecture Style](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices): límites de negocio, contratos, propiedad de datos y costos de una arquitectura distribuida.
- [Microsoft — Domain Analysis](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/domain-analysis): identificación iterativa de subdominios y contextos delimitados.
- [Spring Modulith — Verification](https://docs.spring.io/spring-modulith/reference/verification.html): comprobación automatizada de dependencias permitidas, ausencia de ciclos y acceso por interfaces públicas.
- [Martin Fowler — Microservice Prerequisites](https://martinfowler.com/bliki/MicroservicePrerequisites.html): las exigencias operativas adicionales de microservicios.
- [Martin Fowler — Microservice Trade-Offs](https://martinfowler.com/articles/microservice-trade-offs.html): beneficios y costos de límites independientes, gestión de datos y consistencia distribuida.
- [Apache Fineract — Key Design Principles](https://cwiki.apache.org/confluence/spaces/FINERACT/pages/61334200/Key+Design+Principles): referencia de una plataforma financiera que combina módulos funcionales, servicios, comandos, consultas y persistencia transaccional.

La decisión final debe seguir el contexto del producto. Estas referencias aportan principios y mecanismos de verificación, no una obligación de copiar su lenguaje de programación o infraestructura.
