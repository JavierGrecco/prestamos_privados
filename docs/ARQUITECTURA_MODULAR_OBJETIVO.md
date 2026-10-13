# Arquitectura modular por capacidades de negocio

**Estado:** objetivo arquitectónico acordado para orientar la evolución; la migración del código todavía está pendiente.  
**Seguimiento:** [Issue #267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267).  
**Prioridad:** mejorar mantenibilidad sin poner en riesgo el cierre del MVP local (#223).

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
- `aplicacion/servicios/fabrica_registro_pago_v3.py` conoce `BaseDatos` y el repositorio SQLite concreto. La composición de dependencias debe vivir en el punto de arranque/ensamblado de la aplicación, separado de los casos de uso.
- `ui/pagina_registrar_pago.py` importa directamente `BaseDatos`, excepciones de infraestructura y repositorios, además de servicios de aplicación. Hay que reducir ese acceso directo y hacer que la pantalla utilice casos de uso y consultas publicados.
- Los contratos de observación SOMBRA (`DivergenciaMotorPagoV3` y `EjecucionSombraMotorPagoV3`) también estaban definidos en el puente concreto y eran importados por los repositorios; el PR de contratos los traslada a `aplicacion.puertos.sombra_pago_v3`.
- El registro V3 está distribuido en varias fachadas (`registro_pago_v3.py`, `registro_pago_v3_completo.py`, `registro_pago_v3_completo_adelantos.py`, `registro_pago_v3_devengamientos.py`) y una fábrica que elige entre ellas. La arquitectura actual ya advierte que no deben eliminarse sin comparar Legacy/V3, caracterizar su comportamiento y definir la API canónica.

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
