# Estado de modularización y trabajo pendiente

**Corte:** 15 de octubre de 2026 (hora Argentina).
**Referencia integrada:** PR #348 y su CI post-merge están completos: 1.274 pruebas por versión de Python 3.11–3.14, CodeQL y auditoría aprobados. La base registra 295 archivos sin errores, 1.637 importaciones, 306 cruces, 70 hallazgos (24 pendientes, 7 excepciones y 39 dependencias de composición de borde) y cero ciclos. **Candidato PR #349, validado en su commit de código:** 1.279 pruebas por versión, CodeQL y auditoría aprobados; inventario de 299 archivos, 1.652 importaciones, 308 cruces, 71 hallazgos (24 pendientes, 7 excepciones y 40 dependencias de composición) y cero ciclos. Tras esta actualización documental, el HEAD final deberá repetir la matriz antes del merge.
**Seguimiento:** [#267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267) · [#293 — Inventario automático](https://github.com/JavierGrecco/prestamos_privados/issues/293) · [#223 — MVP local](https://github.com/JavierGrecco/prestamos_privados/issues/223).

> Este documento distingue estructura del código, dependencias pendientes y aceptación del producto. El número de archivos o de pull requests no es un porcentaje de modularización.

## 1. Dimensión actual del código

En el snapshot de referencia del PR #340, el árbol contiene 582 archivos, incluidos 450 archivos Python, 119 archivos Markdown y 175 archivos de pruebas. El auditor cubre 274 archivos Python de producción en las cinco capas acordadas; no cuenta los tests como módulos de producción.

| Capa | Archivos Python en la base de referencia |
|---|---:|
| Dominio | 30 |
| Aplicación | 99 |
| Infraestructura | 104 |
| UI | 31 |
| Scripts operativos | 13 |
| Total en capas auditadas | 277 |

Estos valores describen el volumen revisado antes de añadir el auditor. No indican cuántos archivos están mal modularizados: un módulo puede estar bien separado o conservar acoplamientos. El comando reproducible para actualizar el inventario es:

```bash
python scripts/auditar_fronteras_modulares.py . --format markdown --max-hallazgos 0
```

El mismo análisis ofrece JSON para automatización y se ejecuta en CI. Sus resultados separan infracciones de límites, dependencias temporales documentadas y fábricas de composición usadas en el borde de la UI.

### Medición de referencia y seguimiento

La línea base del PR #335 detectó **1.545 importaciones**, de las que **288 cruzaban entre capas**, con **83 observaciones en 26 archivos**: 49 pendientes de migración, 7 excepciones temporales y 27 usos informativos de composición.

Tras el PR #336, la misma auditoría marcó 81 observaciones y 46 pendientes. El PR #338 extrajo `IdentidadSesion` a un módulo neutral, y la auditoría confirmó **0 ciclos de importación**.

En la corrida del PR #339, la auditoría cubre **270 archivos Python** sin errores y detecta **1.547 importaciones**, 288 cruces entre capas y **79 observaciones en 26 archivos**: **42 pendientes de migración**, 7 excepciones documentadas y 30 usos de composición de borde. La regla `CONSTRUYE-REPOSITORIO` bajó de 21 a **19**, y `UI-ACCESO-INFRA-DIRECTO` de 20 a **18**. El detector sigue mostrando **0 ciclos de importación**.

En la corrida de CI del PR #340, con la separación de métricas principales, se auditaron **274 archivos Python**, sin errores, con **1.557 importaciones** y 290 cruces entre capas. El inventario informó **75 observaciones en 26 archivos**: **37 pendientes de migración**, 7 excepciones documentadas y 31 dependencias de composición de borde. Detectó **0 ciclos de importación**. La matriz aprobó 1.233 pruebas por cada versión de Python 3.11–3.14; CodeQL y auditoría de dependencias también finalizaron correctamente.

En la corrida de CI del PR #341, que extrae la selección de préstamos para escenarios de la UI, se auditan **277 archivos Python**, sin errores, con **1.566 importaciones** y 292 cruces entre capas. El inventario informa **73 observaciones en 26 archivos**: **34 pendientes de migración**, 7 excepciones documentadas y 32 usos de composición de borde. Sigue detectando **0 ciclos de importación**. La matriz aprobó **1.238 pruebas en cada versión de Python 3.11, 3.12, 3.13 y 3.14**; CodeQL y auditoría de dependencias finalizaron correctamente. Frente al PR #340, las observaciones bajan de 75 a 73 y las pendientes de 37 a 34.

La migración de dos pantallas resuelve cuatro observaciones pendientes del inventario: import/construcción de repositorio en la página principal y en el formulario de alta. Es una reducción de deuda medible, no una afirmación de que esas pantallas estén aceptadas funcionalmente. Los conteos representan referencias, no defectos confirmados ni módulos distintos.

## 2. Qué ya está modularizado

- El dominio concentra reglas financieras reutilizables: amortización, interés, mora, política de imputación, escenarios, rendimiento y planes de pago.
- Aplicación ya cuenta con puertos tipados, comandos de registro, consultas de solo lectura y servicios separados para las superficies financieras principales.
- Infraestructura concentra repositorios SQLite, consultas SQL y fábricas de composición para personas, préstamos, pagos, detalle financiero, reportes y otros módulos.
- La escritura Legacy de pagos ya delega parte de su trabajo en colaboradores específicos para distribución a inversores, recálculo de adelantos RAI/RNI, cuotas anteriores y cuota objetivo. El manejador conserva la unidad transaccional.
- La estructura de pagos tiene pruebas de caracterización, idempotencia, concurrencia y rollback; existen guardas AST para límites concretos, además de CI multiversión y controles de seguridad.
- El PR #334 añadió una prueba de SOMBRA sobre arrastre entre cuotas y mejoró la lectura humana de las referencias persistidas. No cambió reglas financieras.

## 3. Frentes que siguen abiertos

| Frente | Qué falta | Seguimiento |
|---|---|---|
| Inventario y guardas de arquitectura | Auditor AST integrado en CI. El PR #338 resolvió el ciclo de identidad y el PR #339 mantiene el recuento en cero; una prueba evita regresiones. Queda pendiente convertir límites migrados y estables en bloqueos estrictos, de forma gradual. | [#293](https://github.com/JavierGrecco/prestamos_privados/issues/293) |
| Pagos y composición | Retirar gradualmente dependencias concretas que todavía se ubican en servicios de aplicación, manteniendo un solo punto de composición y la transacción completa. | [#270](https://github.com/JavierGrecco/prestamos_privados/issues/270) |
| Alta de préstamo y unidad de trabajo | Verificar el uso de puertos y conservar una transacción indivisible entre alta, cuotas, participaciones, ledger y auditoría. | [#301](https://github.com/JavierGrecco/prestamos_privados/issues/301) |
| Entrada de UI | Esta entrega migra `ui/app.py` a `crear_servicio_personas` y elimina la doble consulta dentro de un render. Quedan otros accesos directos de UI señalados por el inventario y la frontera separada de arranque/migraciones. | [#302](https://github.com/JavierGrecco/prestamos_privados/issues/302) |
| Pago por cuota y evidencia histórica | Definir la semántica de atribución de mora/interés/capital cuando un pago cubre cuotas anteriores, y decidir el tratamiento histórico antes de corregir. | [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) |
| Cierre de arquitectura | Demostrar APIs públicas pequeñas, ausencia de ciclos relevantes, dependencias permitidas, excepciones documentadas y compatibilidad de consumidores. | [#267](https://github.com/JavierGrecco/prestamos_privados/issues/267) |

El inventario hace medibles las dependencias; las extracciones siguen siendo trabajo manual deliberado. Los PR #335–#338 pasaron CI completo; la UI raíz usa composición pública y el ciclo de identidad quedó resuelto. El PR #339 migra las consultas de personas de la página principal y del formulario de alta de préstamo. El PR #340 separó la lectura y el cálculo de métricas principales; el PR #341 trasladó el selector de préstamos para escenarios a una consulta de aplicación y una fábrica de composición. La última auditoría registra 34 pendientes y mantiene cero ciclos. Los siguientes pasos se eligen del detalle del inventario, no del número histórico de PRs.

## 4. Cuánto falta para terminar la modularización

No convierto el conteo de observaciones en un porcentaje: mide referencias y construcciones, no módulos completos. La auditoría del PR #341 registra 73 observaciones concentradas en 26 archivos, de las cuales 34 son pendientes de migración; son referencias/construcciones, no módulos distintos. También informa 7 excepciones documentadas, 32 usos de composición de borde y cero ciclos. El detector informa cero ciclos. El plan técnico se organiza en **seis frentes controlables**: inventario/guardas, UI y composición, pagos, alta de préstamos, semántica de trazabilidad financiera y aceptación global.

Como planificación provisional, reservar **8–15 jornadas de ingeniería** para cerrar los límites prioritarios, revisar consumidores, robustecer las guardas y consolidar documentación. La estimación tiene confianza media-baja: algunas observaciones se resolverán en conjunto y otras requerirán migrar consumidores uno por uno; el trabajo de pagos debe preservar resultados y rollback. No incluye cerrar todo el MVP local ni efectuar el cut-over de V3.

Una frontera se considerará cerrada solo cuando tenga contrato público, adaptador en el borde permitido, pruebas de caracterización/rollback cuando corresponda y una guarda contra regresiones. No es necesario convertir el proyecto en microservicios.

## 5. ¿Cuántas herramientas o utilidades quedan por implementar?

El MVP local no tiene una lista aislada de utilidades faltantes; tiene **siete paquetes de cierre funcional** definidos en `ROADMAP_MVP_LOCAL.md` (fases 0–6). Varias pantallas, simuladores, exportaciones y controles ya existen. El trabajo restante se concentra en conectar, reconciliar, aceptar y endurecer esas capacidades:

1. Aprobar reglas de contrato, calendario, mora y carencia.
2. Integrar el mismo calendario aprobado entre simulación, alta, pagos y reportes.
3. Terminar la conexión y aceptación del autocrédito/reposición: hechos, valuaciones, referencia USD y rendimiento objetivo sin doble contabilización.
4. Validar de punta a punta el préstamo privado desde la UI.
5. Validar de punta a punta el plan propio y conciliar posiciones e informes.
6. Completar operación segura local: instalación, backup/restauración, actualizaciones, concurrencia y controles de seguridad/gobierno.
7. Registrar aceptación final por una persona distinta del implementador y cerrar los defectos críticos.

El roadmap estima 21–34 jornadas para estos siete paquetes de MVP al corte del 12 de octubre; hay que revisar esa estimación después del inventario y de la aceptación manual. Eso no significa que falten siete programas nuevos: gran parte del código está integrado y aún requiere validación y conexión real.

## 6. Criterios de salida

- El auditor cubre las capas acordadas, se ejecuta en CI y ofrece salida legible y JSON reproducible, incluidos los componentes de importación cíclica.
- Las excepciones temporales tienen motivo, responsable de seguimiento y siguiente paso; no se ocultan.
- La UI no construye repositorios financieros ni ejecuta SQL.
- Los servicios de aplicación dependen de puertos/casos de uso y las fábricas concretas permanecen en la frontera de composición.
- No hay ciclos de negocio sin decisión documentada.
- Los pagos conservan atomicidad, exactitud decimal, idempotencia, ledger, auditoría y compatibilidad histórica.
- La documentación muestra lo que está integrado y lo que sigue en curso; el MVP solo se declara terminado tras la aceptación funcional y operativa.


## Frontera de métricas principales

La pantalla principal conserva la llamada histórica a `calcular_metricas(db, persona_id)`, pero `ui/metricas.py` queda como fachada de compatibilidad y formato. La lectura de participaciones, préstamos, cuotas y tasa se concentra en `infraestructura/consultas/metricas_principales.py`; el cálculo y sus textos explicativos viven en `aplicacion/consultas/metricas_principales.py`; el servicio recibe una fuente de datos por contrato y la fábrica concreta está en `infraestructura/composicion/metricas_principales.py`.

La extracción no redefine la fórmula del efecto real ni la forma histórica de elegir la tasa. La conversión de TEA a TEM todavía utiliza `float` y queda señalada como deuda técnica separada: corregir precisión numérica requiere pruebas financieras específicas y no se mezcla con el cambio de arquitectura. Las nuevas pruebas cubren los casos básicos de cálculo, la inyección de la fuente y las fronteras entre aplicación, UI e infraestructura.

**Nota sobre métricas del inventario:** PR #348 dejó integrada una base de **295 archivos sin errores**, **1.637 importaciones**, **306 cruces** y **70 hallazgos en 26 archivos** (24 pendientes, 7 excepciones y 39 usos de composición), con cero ciclos. El candidato de código PR #349 registra **299 archivos sin errores**, **1.652 importaciones**, **308 cruces** y **71 hallazgos en 26 archivos** (24 pendientes, 7 excepciones y 40 usos de composición), también sin ciclos. Ese candidato pasó 1.279 pruebas por Python 3.11–3.14, CodeQL y auditoría. Estos conteos miden referencias de arquitectura, no módulos distintos ni un porcentaje automático.

## Referencias

- [Arquitectura modular objetivo](ARQUITECTURA_MODULAR_OBJETIVO.md)
- [Inventario de imputaciones por cuota](ANALISIS_IMPUTACIONES_POR_CUOTA.md)
- [Roadmap operativo del MVP local](ROADMAP_MVP_LOCAL.md)
- [Estado del proyecto](ESTADO_DEL_PROYECTO.md)
- [Registro de cambios](REGISTRO_DE_CAMBIOS.md)

## Selector de escenarios — siguiente frontera en migración

La pantalla `ui/pagina_analisis.py` ahora consulta los préstamos mediante la fábrica `crear_consulta_prestamos_para_escenarios`. La regla de selección se trasladó a aplicación; SQLite y los repositorios concretos quedaron detrás de `infraestructura/consultas` y `infraestructura/composicion`. Se mantiene el comportamiento: incluir préstamos `ACTIVO` o `EN_MORA` de los que la persona sea deudora o inversora activa, mostrar cada préstamo una sola vez y ordenarlos por fecha de inicio más reciente. Se agregaron pruebas de selección y una guarda que impide reintroducir repositorios directos en la pantalla.

La medición ya quedó confirmada por el CI del PR #341: 277 archivos auditados, 1.566 importaciones, 292 cruces entre capas, 73 observaciones (34 pendientes de migración, 7 excepciones documentadas y 32 usos de composición de borde), y cero ciclos. Las 1.238 pruebas por versión de Python 3.11–3.14, CodeQL y auditoría de dependencias aprobaron.


## Pantalla de préstamos: nombres de garantes

Se retiró de `ui/pagina_prestamos.py` la construcción directa de `PersonaRepo` para resolver los nombres que se muestran en la sección de garantías. La consulta ahora utiliza `crear_servicio_personas(db).listar()` y una prueba de arquitectura evita que esa dependencia concreta vuelva a la pantalla.

Este paso acotado quedó integrado mediante el PR #342 después de aprobar la matriz completa de CI. Los repositorios de préstamos, participaciones y pagos siguen presentes en otras partes de la pantalla y requieren migraciones separadas. La medición confirmada posterior a este cambio es de 277 archivos auditados, 1.567 importaciones, 293 cruces entre capas, 73 hallazgos (33 pendientes, 7 excepciones documentadas y 33 dependencias de composición de borde) y cero ciclos.


## Listado de préstamos: lectura detrás de una consulta — PR #343 integrado

La siguiente extracción mueve a una consulta de aplicación la selección de préstamos de una persona y la localización de su próxima cuota pendiente. El contrato está en `aplicacion/consultas/listado_prestamos.py`; el adaptador que utiliza los repositorios actuales vive en `infraestructura/consultas/listado_prestamos.py`, y el armado concreto queda en `infraestructura/composicion/listado_prestamos.py`. La UI mantiene la forma de datos que consume la tarjeta visual, pero deja de decidir filtros, roles, duplicados y próxima cuota.

Se conserva el comportamiento existente: filtros Activos/Finalizados/Cancelados/Refinanciados/Todos; deudor antes que inversor; participación solo cuando está activa; ningún préstamo duplicado si la persona ocupa ambos roles; e identificación de la primera cuota `PENDIENTE` de la versión activa. No se cambiaron escrituras, reglas de pago, garantías ni fórmulas financieras. La matriz de CI del PR #343 fue aprobada.

La medición del CI del PR #343 confirmó **280 archivos Python auditados**, 1.578 importaciones, 296 cruces entre capas y 72 hallazgos en 26 archivos: 31 pendientes de migración, 7 excepciones documentadas y 34 dependencias de composición de borde. Se detectaron cero ciclos y pasaron **1.244 pruebas en cada versión de Python 3.11, 3.12, 3.13 y 3.14**, junto con CodeQL y auditoría de dependencias.


## Ficha básica del préstamo: lecturas detrás de composición — CI aprobado en PR #344

La nueva extracción reúne la lectura que usa la vista de detalle: datos básicos del préstamo, tasa anual de la versión activa y pagos válidos. El contrato tipado vive en `aplicacion/consultas/ficha_prestamo.py`; el adaptador SQLite está en `infraestructura/consultas/ficha_prestamo.py`, y el ensamblado en `infraestructura/composicion/ficha_prestamo.py`.

`ui/pagina_prestamos.py` ya no importa `PrestamoRepo` ni `PagoRepo`, ni ejecuta SQL directo para leer la tasa. La tarjeta conserva sus métricas, el filtro de pagos `VALIDA`, la etiqueta de tipo de pago y el orden cronológico que devuelve el repositorio. No se alteran las operaciones de pago, los cálculos de interés, las garantías ni las reglas de estado. La matriz CI del candidato de PR #344 quedó aprobada: 1.249 pruebas por versión de Python 3.11–3.14, CodeQL y auditoría de dependencias correctos. El inventario registra 283 archivos, 1.589 importaciones, 298 cruces entre capas, 69 hallazgos en 26 archivos (27 pendientes, 7 excepciones y 35 dependencias de composición de borde) y cero ciclos. La regla financiera y las operaciones de escritura siguen fuera de este cambio.


## Pantalla heredada de inicio: consulta de persona por servicio — PR #345 integrada

`ui/ss.py` todavía tenía una construcción directa de `PersonaRepo` para recuperar el nombre de la persona y saludar al usuario. La lectura ahora utiliza `crear_servicio_personas(db).obtener(persona_id)`, igual que la pantalla principal vigente. Se conserva el mensaje cuando la persona no existe y no se cambia el cálculo de métricas, sus fórmulas ni su presentación.

Se agrega una guarda AST a las pruebas de arquitectura para impedir que vuelva la dependencia directa. Esta pantalla heredada no figura entre las importaciones del punto de entrada vigente `ui/app.py`; la migración mantiene el archivo compatible sin asumir que eliminarlo sea seguro. PR #345 aprobó 1.250 pruebas por versión de Python 3.11–3.14, CodeQL, auditoría de dependencias e inventario modular.


## Simulador: lectura de planes y versiones guardadas detrás de consulta — PR #346 integrada

La selección y la lectura de versiones guardadas se separan de `ui/pagina_simulador_carencia.py`. El nuevo contrato de consulta en `aplicacion/consultas/planes_reposicion_guardados.py` devuelve metadatos tipados, comprueba la integridad de la versión y valida que el contenido decodificado del snapshot sea un objeto. El adaptador y la fábrica están en infraestructura.

Las lecturas de planes y versiones quedan integradas mediante PR #346. La consulta verifica el hash antes de exponer el JSON; no recalcula escenarios ni reescribe snapshots. La coordinación de las escrituras para crear un plan o guardar otra versión pasa al caso de uso documentado a continuación.


## Simulador: creación de plan y nueva versión mediante caso de uso — PR #347 integrada

El flujo `Guardar este análisis` deja de decidir y ejecutar desde la UI las llamadas a `crear_plan_con_snapshot` y `guardar_nueva_version`. Un nuevo puerto tipado y `ServicioGuardarAnalisisReposicion` resuelven la intención explícita de crear un plan o agregar una versión; el adaptador SQLite utiliza los mismos métodos del repositorio actual.

La persistencia conserva la validación final, la transacción que crea el plan junto con su primera versión, la protección contra agregar versiones a planes cerrados, los hashes y la inmutabilidad del historial. El caso de uso no cambia el snapshot ni recalcula valores financieros. PR #347 está integrada; su HEAD y la corrida post-merge aprobaron 1.269 pruebas por versión de Python 3.11–3.14, CodeQL y auditoría de dependencias. El inventario actualizado marca 291 archivos, 1.622 importaciones, 304 cruces, 69 hallazgos (24 pendientes, 7 excepciones y 38 usos de composición) y cero ciclos. El registro de aportes se está extrayendo en un paso separado.


## Simulador: registro de aportes de reposición detrás de un caso de uso — PR #348 integrada

La UI deja de llamar directamente a `repo.registrar_aporte` y utiliza `crear_servicio_registrar_aporte_reposicion(db)`. El contrato, servicio de aplicación, adaptador SQLite y fábrica delimitan el caso de uso sin duplicar las reglas de persistencia.

El cálculo del equivalente USD, el control de plan interno activo, el rechazo de fechas futuras, la validación de importes y cotizaciones, la obligación de identificar al operador, la creación del snapshot y su hash permanecen en `PlanesReposicionRepo.registrar_aporte`. La consulta de aportes y los movimientos/valuaciones de inversión siguen sin modificarse. PR #348 quedó integrada; su HEAD y la corrida post-merge aprobaron 1.274 pruebas por Python 3.11–3.14, CodeQL y auditoría. El inventario registra 295 archivos, 1.637 importaciones, 306 cruces, 70 hallazgos (24 pendientes, 7 excepciones y 39 usos de composición) y cero ciclos.


## Simulador: registro de flujos de inversión detrás de un caso de uso — PR #349 en revisión

La UI deja de llamar directamente a `repo.registrar_flujo_inversion` y utiliza `crear_servicio_registrar_flujo_inversion(db)`. El nuevo puerto, servicio, adaptador SQLite y fábrica delimitan el registro de movimientos declarados sin mezclarlo con los aportes de reposición.

La persistencia existente continúa validando la fecha, el tipo de flujo, la moneda, el importe, la cotización, la naturaleza de la fuente, el operador y el estado/tipo de plan. También conserva la conversión a USD de referencia, la transacción y la huella de integridad. Las lecturas del historial, el registro de valuaciones de inversión y el cálculo de XIRR no se modifican. El commit de código de PR #349 pasó 1.279 pruebas por versión en Python 3.11–3.14, CodeQL y auditoría; el inventario registra 299 archivos, 1.652 importaciones, 308 cruces, 71 hallazgos (24 pendientes, 7 excepciones y 40 usos de composición), sin ciclos. Al actualizar esta documentación, se debe volver a validar el HEAD completo antes de integrar.
