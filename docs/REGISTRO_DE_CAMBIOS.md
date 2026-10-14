# Registro de cambios y continuidad

## Contratos y unidad de trabajo para garantías personales — 14 de octubre de 2026

- Se define `aplicacion/puertos/garantias_prestamo.py` con contratos para garantías, personas, préstamos, auditoría y unidad de trabajo, más el error público `GarantiaActivaDuplicada`.
- `ServicioGarantiasPrestamo` recibe los colaboradores por constructor y deja de importar `BaseDatos`, `sqlite3`, `ErrorTransaccion` y repositorios concretos.
- Se añade `UnidadTrabajoGarantiasSQLite` para mantener rollback y traducir únicamente el conflicto de unicidad de garantía activa a un error público; los demás errores técnicos siguen escalándose.
- Se añade `infraestructura/composicion/garantias_prestamo.py` y se migra la pantalla de préstamos y las pruebas de integración al factory.
- Se agregan guardas arquitectónicas y pruebas del adaptador para duplicado, errores técnicos y propagación de validaciones.
- Se preservan reglas de préstamo/garante, motivo de finalización, historial y auditoría atómica. No se cambian cuotas, pagos, ledger, esquema ni el motor financiero.

## Puertos para ServicioPersonas — 14 de octubre de 2026

- Se define `aplicacion/puertos/personas.py` con contratos para personas/roles, préstamos, participaciones y garantías, además de la lectura mínima que necesitan las exportaciones.
- `ServicioPersonas` recibe sus cuatro colaboradores por constructor y deja de importar `BaseDatos` y repositorios concretos.
- Se añade `infraestructura/composicion/personas.py`; la pantalla de personas y las pruebas de integración consumen la fábrica pública.
- `ServicioExportaciones` recibe la consulta de personas por contrato, y su composición la conecta con el servicio del dominio de personas.
- Se agregan guardas arquitectónicas y pruebas puras para proteger el rechazo del rol histórico ADMIN y la baja de GARANTE mientras existen garantías activas.
- Se preservan los filtros, el orden de relaciones por préstamo/rol y las exportaciones CSV de solo lectura; no se cambian esquemas ni reglas de estados.

## Planificador tipado para pagos V3 SOMBRA — 14 de octubre de 2026

- Se incorpora `ConsultaEstadoPagoSombraV3` en `aplicacion/puertos/sombra_pago_v3.py`, limitado a recuperar el estado auditable del préstamo.
- La implementación pasa a `aplicacion/servicios/planificador_sombra_pago_v3.py` como `PlanificadorSombraPagoV3`; recibe una consulta por contrato y calcula únicamente desde el snapshot.
- `aplicacion/servicios/sombra_pago_v3_sqlite.py` queda como alias temporal de compatibilidad, sin lógica propia ni dependencias de SQLite.
- La composición y las pruebas de integración usan la clase nueva. Se agregan pruebas puras de una sola lectura, snapshot del préstamo correcto y múltiples planificaciones sin relectura, más guardas de arquitectura.
- El cambio no altera la política de waterfall, idempotencia, la escritura Legacy, la observabilidad ni la persistencia de divergencias. V3 SOMBRA continúa siendo no efectiva y no bloqueante.

## Contratos de usuarios locales y unidad de trabajo — 14 de octubre de 2026

- Se crea `aplicacion/puertos/usuarios_locales.py` con el DTO seguro `UsuarioApp`, los protocolos para repositorios de cuenta, lectura de personas, auditoría y unidad de trabajo, y el error público `NombreUsuarioDuplicado`.
- `ServicioUsuariosLocales` recibe sus cuatro colaboradores por constructor; deja de importar `BaseDatos`, `sqlite3`, `ErrorTransaccion` y repositorios concretos.
- `UsuarioAppRepo` reexporta el DTO público para conservar la ruta de importación histórica y traduce la restricción de unicidad del username a un error de aplicación.
- `UnidadTrabajoUsuariosLocalesSQLite` concentra rollback y traducción de errores; una operación de cuenta y su auditoría siguen dentro de la misma transacción.
- `infraestructura/composicion/usuarios_locales.py` ensambla servicio y consulta de personas. Las pantallas de acceso/administración, los helpers E2E y el comando de recuperación offline usan esa fábrica.
- La UI de administración deja de importar `PersonaRepo` directamente para listar personas vinculables.
- Se agregan guardas arquitectónicas y una prueba básica del servicio con colaborador falso; la suite existente sigue cubriendo bloqueo de login, último ADMIN, revocación de sesiones y auditoría sin secretos.

## Contratos y composición para usuarios locales — 14 de octubre de 2026

- Se crea `aplicacion/puertos/usuarios_locales.py` con el DTO seguro `UsuarioApp`, protocolos para cuentas/personas/auditoría/unidad de trabajo y un error público de username duplicado.
- `ServicioUsuariosLocales` recibe sus colaboradores por constructor; deja de importar `BaseDatos`, `sqlite3` y repositorios concretos.
- La unidad de trabajo SQLite mantiene el rollback y la traducción de errores funcionales conocidos; el repositorio traduce solo la restricción de username duplicado.
- Se mantiene una ruta de importación compatible para `UsuarioApp` desde infraestructura, sin duplicar el modelo ni exponer hashes.
- La autenticación, la administración de usuarios, el helper E2E y la recuperación offline usan la fábrica de composición; la pantalla de usuarios obtiene personas vinculables mediante una consulta pública.
- Se añaden pruebas de arquitectura y de lecturas con colaboradores falsos, conservando pruebas de integración para bloqueo, último administrador, revocación de sesiones y auditoría sin secretos.

## Puerto de lectura para el reporte de reposición e inversión — 14 de octubre de 2026

- Se crea `aplicacion/puertos/reporte_inversion_reposicion.py` con protocolos tipados para plan, versión, aportes, flujos, valuaciones, resumen y las operaciones de lectura que necesita el informe.
- Se añade `infraestructura/consultas/reporte_inversion_reposicion.py`, que conserva el repositorio actual como fuente de verdad y limita el conteo SQL a tres categorías permitidas.
- `ServicioReporteInversionReposicion` recibe el lector por constructor y deja de importar `BaseDatos`, `PlanesReposicionRepo` o modelos de persistencia.
- Se añade composición local; la pantalla `pagina_simulador_carencia.py` y las pruebas de integración consumen la fábrica pública. La UI deja de construir el servicio de reporte con una conexión SQLite.
- Se agregan guardas arquitectónicas y prueba del rechazo de un plan inexistente sin SQLite.
- Se preservan verificación de hashes, límites de registros, rechazo de exportaciones parciales, XIRR, signos, formatos y neutralización de fórmulas CSV. No se escriben datos ni cambian cálculos.

## Puerto público para lectura auditable y One Shot V3 — 14 de octubre de 2026

- Se crea `aplicacion/puertos/pago_v3_auditable.py` con los DTO de pago, imputaciones, ledger, auditoría y conciliación, más el protocolo `ConsultaPagoV3Auditable`.
- `infraestructura/consultas/pagos_v3.py` importa y reexporta los DTO públicos, conservando las rutas de importación existentes, y añade un adaptador SQLite fino que reutiliza la consulta auditable actual.
- `PagoOneShotV3Query` recibe el lector por constructor. La proyección deja de importar `infraestructura.consultas.pagos_v3` y no repite conciliaciones ni lectura SQL.
- Se añade una fábrica local para ensamblar la consulta y pruebas con un lector falso, además de una guarda arquitectónica contra imports directos de infraestructura.
- Se preservan las cantidades One Shot, la detección de prepago, los intereses ahorrados y el estado de conciliación. El cambio es de estructura y de tipos, no de reglas ni de escritura.

## Puerto de identidad para reportes — 14 de octubre de 2026

- Se crea `aplicacion/puertos/reportes_persona.py` con el DTO `PersonaReporteLectura` y el protocolo `ConsultaPersonaParaReporte`.
- Se añade `infraestructura/consultas/reportes_persona.py` para traducir el registro de persona al contrato mínimo del reporte.
- `ServicioReportesPersona` recibe el lector por constructor y deja de importar `BaseDatos` o construir `PersonaRepo`.
- La composición local ensambla el nuevo lector junto a los read models de posición, planificación, rendimiento y escenarios.
- Se añade una guarda arquitectónica y una prueba de validación de persona sin SQLite.
- Se conserva el nombre visible y se mantienen formatos JSON, CSV y Markdown, fecha de corte común, supuestos y operaciones de solo lectura.

## Contrato de lectura para el comparador M7 — 14 de octubre de 2026

- Se crea `aplicacion/puertos/comparador_decisiones_financieras.py` con DTOs tipados para préstamos, participaciones y tasa activa, además del protocolo `ConsultaDatosComparadorDecisiones`.
- `infraestructura/consultas/comparador_decisiones_financieras.py` concentra el acceso a `PersonaRepo`, `PrestamoRepo` y `ParticipacionRepo`; la capa de aplicación no recibe objetos de persistencia.
- `ComparadorDecisionesFinancierasQuery` recibe por constructor el lector tipado y el análisis financiero compartido. Deja de importar infraestructura y construir repositorios.
- La fábrica del comparador conecta ambos puertos con adaptadores SQLite; las pruebas y la UI continúan usando el punto público de composición.
- Se añade una guarda arquitectónica y una prueba para listar alternativas sin SQLite.
- Se conservan filtros de visibilidad, etiquetas/roles, orden, condiciones registradas, límites de selección, flujos, XIRR, homogeneidad y valoración real. No cambia el esquema ni se escriben hechos financieros.

## Puerto de lectura para Mi espacio — 14 de octubre de 2026

- Se crea `aplicacion/puertos/vista_humana_persona.py` con contratos tipados para persona, roles, préstamos y participaciones que necesita la vista.
- Se añade `infraestructura/consultas/vista_humana_persona.py` para acceder a `PersonaRepo`, `PrestamoRepo` y `ParticipacionRepo`, y devolver DTOs públicos.
- `VistaHumanaPersonaQuery` recibe las lecturas por constructor; deja de importar `BaseDatos` o repositorios concretos.
- La composición local monta el lector de Mi espacio junto al análisis financiero y el detalle financiero de préstamo.
- Se añade una guarda arquitectónica y una prueba sin SQLite para una persona que todavía no tiene operaciones.
- Se preservan roles, visibilidad, orden de posiciones, próximos movimientos, actividad reciente, advertencias e importes. No cambia la lógica financiera ni se escriben datos.

## Contrato de lectura para planificación financiera — 13 de octubre de 2026

- `PlanificacionFinancieraPersonaQuery` recibe `ConsultaExistenciaPersonaFinanciera` y `AnalisisFinancieroQuery` por constructor; deja de crear `PersonaRepo` o aceptar una conexión SQLite.
- `ServicioPlanificacionFinancieraPersona` recibe la consulta ya compuesta.
- La fábrica `crear_servicio_planificacion_financiera_persona` conecta los contratos con los adaptadores SQLite en infraestructura.
- Se añaden pruebas del plan con colaboradores falsos, sin base de datos, y una guarda arquitectónica que impide reintroducir repositorios/SQLite en la consulta.
- Se conservan horizonte, fecha de corte, agrupación mensual, reserva sugerida y mes más exigente. No cambian cálculos, importes `Decimal`, proyecciones ni hechos persistidos.

## Puerto de lectura para el análisis financiero — 13 de octubre de 2026

- Se crea `aplicacion/puertos/analisis_financiero.py` con DTOs tipados para préstamos, participaciones, pagos, cobros, cuotas y tasa activa, además del protocolo `ConsultaAnalisisFinanciero`.
- Las consultas SQL y los accesos a `PrestamoRepo` / `ParticipacionRepo` pasan a `infraestructura/consultas/analisis_financiero.py`; el adaptador entrega datos tipados, no filas SQLite a la capa de aplicación.
- `AnalisisFinancieroQuery` queda dedicado a validar entradas y construir flujos, saldos, advertencias, XIRR y escenarios sin importar infraestructura ni ejecutar SQL.
- `infraestructura/composicion/analisis_financiero.py` conecta la consulta con SQLite y compone los servicios de análisis, planificación, escenarios y rendimiento.
- Se migran el dashboard, la posición financiera, Mi espacio, planificación, escenarios, rendimiento, reportes y el comparador M7 para recibir las consultas por el punto de composición. El comparador también recibe el análisis por constructor; deja de instanciarlo con la conexión SQLite.
- Se agregan guardas arquitectónicas y una prueba del análisis con un doble sin base de datos.
- Se mantienen las consultas en solo lectura y se conservan fórmulas, políticas, redondeo `Decimal`, filtros, orden y clasificación de flujos. No se modifica el esquema, no se escriben hechos financieros ni se habilita V3.
- La integración queda condicionada a la matriz completa de CI y a la revisión del PR asociado al issue #288.

## Puerto de lectura para el historial auditable de pagos — 13 de octubre de 2026

- Se crea `aplicacion/puertos/historial_pagos.py` con los DTO públicos `PagoAuditable` y `EvidenciaPagoAuditable`, y el protocolo `ConsultaHistorialPagos`.
- El SQL del historial y el ensamblado de imputaciones, devengamientos, ledger, auditoría, observaciones SOMBRA y plan se trasladan a `infraestructura/consultas/historial_pagos.py`.
- `aplicacion/consultas/historial_pagos.py` queda como fachada de aplicación que recibe el lector por constructor; no conoce SQLite ni contiene SQL.
- Se agrega `infraestructura/composicion/historial_pagos.py`; la pantalla de pagos y las pruebas usan `crear_historial_pagos_query`.
- Una prueba arquitectónica protege la separación entre aplicación e infraestructura y verifica que la pantalla use la fábrica.
- Se conservan validaciones, filtros por persona/préstamo, orden descendente por fecha/ID, límite de resultados y contenido de la evidencia. No se modifica ningún dato ni regla financiera.

## Contrato para la posición financiera personal — 13 de octubre de 2026

- Se crea `aplicacion/puertos/persona_financiera.py` para la consulta mínima de existencia de una persona y su adaptador SQLite correspondiente.
- `PosicionFinancieraPersonaQuery` deja de crear `PersonaRepo` y de recibir una conexión; recibe el lector de persona y el análisis ya compuesto.
- Se agrega `infraestructura/composicion/posicion_financiera.py`; `Mi espacio` y los tests de caracterización usan la fábrica pública, no construyen el servicio con `BaseDatos`.
- Se añaden guardas para impedir la vuelta de imports SQLite a la consulta de posición y la construcción directa del servicio desde la UI.
- Se migra `ServicioReportesPersona` para recibir la posición por constructor y se agrega `infraestructura/composicion/reportes_persona.py`; la pantalla y su test construyen el coordinador desde la fábrica. Esto evita que Reportes use la antigua firma con una conexión y mantiene el cálculo de posición compartido.
- Se preservan los agregados en `Decimal`, el cálculo de flujos reales/futuros, las ventanas mensuales, los acumulados y la semántica de saldo neto. No se modifican reglas financieras.
- Límite pendiente explícito: `AnalisisFinancieroQuery` mantiene su propia implementación SQL y composición interna. Su extracción se evaluará por separado con contratos de flujos y pruebas de caracterización.
- Se actualiza el encabezado y estado de `ARQUITECTURA_MODULAR_OBJETIVO.md` para indicar que la migración está en marcha, pero aún no está completada ni aceptada.

## Puerto tipado para el detalle financiero del préstamo — 13 de octubre de 2026

- Se crea `aplicacion/puertos/detalle_financiero_prestamo.py` con DTOs tipados para préstamo, cuotas, devengamientos, recalculos e imputaciones de capital, y con el protocolo `ConsultaDetalleFinancieroPrestamo`.
- El SQL que vivía en `aplicacion/consultas/detalle_financiero_prestamo.py` se traslada a `infraestructura/consultas/detalle_financiero_prestamo.py`. El read model de aplicación recibe lecturas por contrato y ya no importa `PrestamoRepo` ni consulta directamente la base.
- Se añade `infraestructura/composicion/detalle_financiero.py`; la pantalla de detalle y las exportaciones consumen la fábrica local. Se actualizan las pruebas de caracterización que cubren Decimal, fallback contractual, recalculos y trayectoria de capital.
- Se agrega una guarda arquitectónica que impide que la consulta vuelva a importar infraestructura o ejecutar SQL directo.
- Se migran también `Mi espacio` y las pruebas de la vista humana al punto `infraestructura/composicion/vista_humana_persona.py`, que inyecta el adaptador de detalle. La primera corrida reveló seis fallos por consumidores que seguían usando el constructor anterior; quedan cubiertos por la nueva composición y una guarda para evitar la regresión.
- No se recalculan hechos históricos ni se realizan escrituras. Se mantienen el orden de cuotas/devengamientos/recalculos, la agregación de imputaciones de capital por pago, la regla de fallback contractual para saldos pendientes y la construcción existente de la trayectoria.

## Contrato público de consulta de auditoría — 13 de octubre de 2026

- Se crea `aplicacion/puertos/auditoria.py` con `ConsultaAuditoria` y `EntradaAuditoria` como contrato/modelo público de lectura.
- `infraestructura/repositorios/modelos.py` conserva `EntradaAuditoria` como reexportación compatible; el repositorio lo importa directamente desde el puerto.
- `ServicioAuditoria` recibe una consulta por constructor y no crea repositorios concretos. Se conserva la validación de correlación vacía y la propagación de filtros/limitación.
- Se crean `infraestructura/composicion/auditoria.py` y `infraestructura/composicion/exportaciones.py`; las pantallas de auditoría, personas y detalle financiero, junto con las pruebas de integración, usan las fábricas. `ServicioExportaciones` recibe el caso de uso de auditoría por constructor, en lugar de recrearlo con `BaseDatos`. Una guarda arquitectónica impide que una pantalla vuelva a construir exportaciones directamente.
- Se agrega una guarda de arquitectura que impide que el servicio vuelva a importar infraestructura, más una prueba unitaria sin SQLite para la validación de correlación.
- No se modifica la escritura, inmutabilidad, esquema, orden ni contenido de los eventos de auditoría.

## Verificación de backup inyectada en el paquete canary — 13 de octubre de 2026

- `ServicioPaqueteCanaryV3` recibe `OperacionesBackup` por constructor y deja de importar `verificar_backup` ni el DTO concreto `ResultadoBackup` desde infraestructura.
- Se normaliza el contrato reusable en `aplicacion/puertos/operaciones_backup.py`, compartido por `ServicioOperacionUI` y el paquete canary.
- `infraestructura/composicion/motor_pago.py` inyecta `OperacionesBackupSQLite` al construir el paquete de decisión; el chequeo de integridad, hash y manifiesto sigue ejecutándose mediante la implementación verificada existente.
- Se agrega una guarda arquitectónica que impide volver a importar infraestructura desde el servicio del paquete canary. La condición de aptitud sigue siendo integridad del backup más readiness canary listo; no se cambia el formato de evidencia.

## Composición de pagos organizada por responsabilidades — 13 de octubre de 2026

- Se reduce `infraestructura/composicion/pagos.py` a una fachada pública que reexporta las fábricas existentes, para preservar los imports de la UI y las CLI.
- Se separan los ensamblados en cuatro módulos: `preview_pagos.py` (Legacy/V3 previews), `motor_pago.py` (preflight, configuración y canary), `registro_pago.py` (coordinación de registro UI) y `operaciones.py` (métricas SOMBRA, integridad y backup).
- La configuración compartida del preflight se mantiene: el registro UI crea una sola instancia y la inyecta tanto en la configuración persistente como en el caso de uso coordinador.
- Se ajusta la prueba de canary que parcheaba una función interna para apuntar al nuevo módulo de responsabilidad y se agrega una prueba que fija la compatibilidad de la fachada y los módulos cohesionados.
- No se mueven fórmulas financieras, persistencia, transacciones, auditoría ni idempotencia; solo cambia la ubicación del ensamblado.

## Puerto de backup e integridad para Operación UI — 13 de octubre de 2026

- Se agrega `aplicacion/puertos/operacion_ui.py` con el contrato `OperacionesBackup` y protocolos de resultado para integridad, backup y restore.
- `ServicioOperacionUI` deja de importar `infraestructura.backup`; recibe la ruta de la base activa, el preflight, la consulta de métricas y las operaciones de backup por constructor.
- Se crea `infraestructura/adaptadores/operaciones_backup.py` como adaptador fino que delega a las rutinas SQLite verificadas. La composición local lo inyecta desde `crear_servicio_operacion_ui`.
- Se conservan la confirmación explícita para crear backups, el directorio operativo permitido, la verificación de manifiesto/hash, los chequeos quick/integrity/foreign-key y el restore drill sobre una ruta temporal aislada.
- Se añade una guarda arquitectónica que impide que el servicio de aplicación vuelva a importar infraestructura/SQLite. Los tests existentes de backup, integridad, listado y restore drill siguen cubriendo el flujo real.

## Fábricas SQLite V3/SOMBRA en la raíz de composición — 13 de octubre de 2026

- Se crea `infraestructura/composicion/registradores_pago.py` para ensamblar registradores V3 y el puente SOMBRA con repositorios concretos de SQLite.
- Se eliminan `aplicacion/servicios/fabrica_registro_pago_v3.py` y `aplicacion/servicios/fabrica_sombra_pago_v3_sqlite.py`; sus APIs internas pasan a la composición de infraestructura.
- Se elimina `crear_sombra_pago_v3_sqlite` del módulo del servicio/adaptador. Ahora la composición instancia `SombraPagoV3SQLite` con `RepositorioRegistroPagoSQLiteV3`, sin una fábrica que importe infraestructura desde aplicación.
- Se actualizan la composición principal y las pruebas de registro con devengamientos, RAI/RNI, distribución a inversores y SOMBRA para usar el nuevo módulo.
- Las firmas de las fábricas se mantienen en la API interna de composición. No se cambia cómo se calcula, confirma o audita un pago; se conservan el uso de la misma base, el gate Legacy/SOMBRA/V3, el fingerprint de idempotencia y el repositorio transaccional existente.

## Puerto transaccional para configuración del Motor de Pagos — 13 de octubre de 2026

- Se crea `aplicacion/puertos/configuracion_motor_pago.py` con el DTO público del estado, el modo efectivo y los contratos de persistencia/gate.
- `ServicioConfiguracionMotorPago` ya no construye `ConfiguracionMotorPagoRepo`, `AuditoriaRepo` ni administra una conexión. Valida usuario, motivo y modo, aplica el gate al solicitar V3 y delega el cambio al puerto.
- Se crea `infraestructura/adaptadores/configuracion_motor_pago.py`: el cambio optimista de revisión y su registro de auditoría quedan dentro de una transacción exterior compartida.
- La composición local arma el adaptador y comparte el mismo preflight con el registro/readiness cuando corresponde. Se mantiene el modo sin cambio como operación idempotente y no se audita una selección del modo ya vigente.
- Se agrega una prueba de fallo de auditoría que verifica rollback de modo y revisión, además de una guarda arquitectónica que impide importar infraestructura desde el caso de uso.
- No se modifica el mecanismo de bloqueo V3, los criterios del preflight ni la autoridad Legacy/SOMBRA/V3.

## Contrato de lectura para métricas SOMBRA V3 — 13 de octubre de 2026

- Se crea `aplicacion/puertos/metricas_sombra_v3.py` y se trasladan allí los DTO públicos `MetricasSombraV3` y `ConteoSombraV3`, junto con el protocolo de lectura.
- `infraestructura/consultas/metricas_sombra_v3.py` construye esos DTO públicos desde SQLite; conserva los símbolos importados en el módulo para no romper sus importadores existentes.
- `ServicioMetricasSombraV3` recibe una consulta por constructor y ya no crea `MetricasSombraV3Query` ni importa infraestructura.
- Se añade `crear_servicio_metricas_sombra_v3` al punto de composición; la pantalla Motor V3 y las pruebas utilizan esa fábrica.
- Se añade una regla arquitectónica para impedir que la capa de aplicación vuelva a importar adaptadores SQLite desde el servicio de métricas.
- La agregación, los filtros por préstamo/tipo, la validación de límites y los cálculos de tasas se mantienen sin cambios.

## Migración de consumidores de preflight/readiness — 13 de octubre de 2026

- Se migran la CLI de preflight, la CLI de readiness/canary, el paquete de decisión, la pantalla del Motor V3 y la pantalla Operación para construir sus dependencias a través de `infraestructura/composicion/pagos.py`.
- `ServicioReadinessCanaryV3` ahora recibe el preflight y el lector de configuración ya ensamblados; `ServicioPaqueteCanaryV3` recibe el evaluador readiness como colaborador. `ServicioOperacionUI` recibe preflight y métricas SOMBRA como lectores.
- La configuración persistente y el readiness comparten una evaluación de preflight dentro de cada ensamblado, evitando consultas duplicadas en la evaluación.
- Se conservan los seis criterios, umbrales y mensajes del gate. No se modifican la escritura de pagos, la decisión Legacy/SOMBRA/V3 ni la transacción de configuración.
- Se añade una guarda de arquitectura que impide que readiness vuelva a importar adaptadores de infraestructura.

## Puertos de lectura del preflight V3 — 13 de octubre de 2026

- Se crea `aplicacion/puertos/preflight_motor_pago_v3.py` con contratos para consultar versión de esquema, auditoría de integridad y métricas de SOMBRA.
- `PreflightMotorPagoV3` ya no importa `version_actual`, `auditar_integridad_v3` ni construye `ServicioMetricasSombraV3`; recibe esos tres lectores por constructor y conserva sus umbrales y criterios de aceptación/rechazo.
- `infraestructura/composicion/pagos.py` agrega `crear_preflight_motor_pago_v3`, donde se conectan las consultas reales de infraestructura con el preflight.
- La fábrica del registro comparte la misma instancia de preflight con `ServicioRegistroPagoUI` y `ServicioConfiguracionMotorPago`. Así el modo efectivo y el selector siguen usando el mismo gate para habilitar V3.
- Se actualizan las pruebas a la composición real y se agrega una guarda arquitectónica que impide volver a importar adaptadores desde el preflight.
- No cambian la versión mínima del esquema, el umbral de ejecuciones SOMBRA, la tolerancia a divergencias/errores ni la tasa mínima de coincidencia. No se agregan escrituras ni se alteran las transacciones de pago.

## Inyección de colaboradores para el registro de pagos UI — 13 de octubre de 2026

- `ServicioRegistroPagoUI` recibe configuración, preflight, ejecutor Legacy, fábrica del puente SOMBRA, lectores de préstamo/política y fábrica del registrador V3 por constructor.
- Se crea `aplicacion/puertos/registro_pago_ui.py` para contratos de colaboradores y el DTO `ResultadoRegistroPago`, manteniendo la importación histórica desde `aplicacion.servicios.pagos` como reexportación compatible.
- `infraestructura/composicion/pagos.py` agrega `crear_servicio_registro_pago_ui` y centraliza allí la construcción de dependencias SQLite; tanto la pantalla de registro de pago como la pantalla de estado del Motor V3 utilizan esta fábrica.
- Se actualizan las pruebas unitarias para usar colaboradores falsos sin SQLite y se agrega una guarda arquitectónica contra imports directos de infraestructura y fábricas concretas.
- La transacción crítica permanece en los casos de uso de registro ya existentes. No se modifica la autoridad del modo Legacy/SOMBRA/V3, las reglas financieras, el waterfall ni los contratos de idempotencia.
- El preflight y las fábricas de registro aún tienen sus propias dependencias internas de infraestructura; esta entrega mueve la composición fuera del coordinador UI, no completa por sí sola toda la migración.

## Puertos de lectura para el preview V3 — 13 de octubre de 2026

- Se añade `aplicacion/puertos/preview_pago_v3.py` con contratos para consultar la política vigente, estado de obligaciones, fechas de devengamiento y cuotas futuras necesarias para el adelanto.
- `ServicioPreviewPagoV3` recibe los lectores y la consulta de deuda por constructor; deja de guardar la conexión SQLite y no crea `PrestamoRepo`, `PoliticaPagoRepo` ni `RepositorioRegistroPagoSQLiteV3`.
- `infraestructura/composicion/pagos.py` arma los adaptadores reales para la versión local, y se agrega `crear_servicio_preview_pago_v3` para hacer explícita esa construcción en pruebas/integraciones.
- Las pruebas de caracterización mantienen los mismos escenarios de deuda, waterfall, excedente y comparación Legacy/V3. Se añade una regla estática para evitar que el preview vuelva a importar infraestructura.
- La consulta es de solo lectura: no cambia fórmulas, escrituras, transacciones, auditoría o idempotencia. La composición del registro de pagos sigue pendiente.

## Punto de composición para el preview de pagos — 13 de octubre de 2026

- Se crea `infraestructura/composicion/pagos.py`, que ensambla la fachada de preview con el repositorio de lectura, la simulación Legacy y el preview V3.
- `ServicioPreviewPago` pasa a recibir esos tres colaboradores por constructor; deja de importar `PrestamoRepo` y deja de conocer cómo se construyen los adaptadores.
- La pantalla de registro y las pruebas de caracterización usan `crear_servicio_preview_pago`, manteniendo el montaje SQLite explícito fuera de la fachada de aplicación.
- Se agrega una guarda arquitectónica para impedir la reintroducción de imports de infraestructura en esa fachada.
- El límite sigue siendo deliberadamente parcial: `ServicioPreviewPagoV3` y `ServicioRegistroPagoUI` todavía tienen composición/detalles de persistencia por extraer. No se alteran fórmulas financieras, ni escrituras, transacciones, auditoría o idempotencia.

## Puerto de lectura para la consulta de deuda — 13 de octubre de 2026

- Se agrega `aplicacion/puertos/consulta_prestamo_pago.py` con el contrato de lectura requerido por la consulta de deuda y el DTO público de resumen de préstamo.
- `ServicioDeudaProximoPago` ya no importa ni crea `PrestamoRepo`; recibe la dependencia por constructor.
- Los consumidores actuales (`ServicioPreviewPago`, `ServicioPreviewPagoV3` y `ServicioPagos`) inyectan explícitamente el repositorio SQLite ya disponible; se corrigió además la ruta de compatibilidad de `ServicioPagos` detectada por la primera ejecución de CI. El punto de composición sigue siendo transitorio y se migrará en un cambio posterior.
- Se agrega una prueba con repositorio falso, sin abrir base de datos, y una guarda estática para evitar que la consulta vuelva a importar infraestructura.
- La suite existente continúa cubriendo la integración real contra SQLite. No se modifican fórmulas financieras ni escrituras, transacciones, auditoría, idempotencia o selección Legacy/SOMBRA/V3.

## Consulta pública para identificar el préstamo en la pantalla de pagos — 13 de octubre de 2026

- La pantalla de registro dejó de importar `PrestamoRepo` y ahora consulta `ServicioPreviewPago.obtener_resumen_prestamo`.
- Se define el DTO inmutable `ResumenPrestamoParaPago`, que expone solamente identificador, número y destino. La UI no recibe el modelo de persistencia completo.
- Se agrega una guarda de arquitectura que impide que `ui/pagina_registrar_pago.py` importe repositorios directamente, además de pruebas del contrato y de la delegación.
- No cambia la ruta de escritura, las fórmulas financieras, la idempotencia, la transacción ni el modo Legacy/SOMBRA/V3.
- La composición SQLite y las dependencias directas de algunos servicios de aplicación siguen pendientes; este cambio cubre una fuga concreta, no todo el issue #270.

## Guardas arquitectónicas para contratos públicos — 13 de octubre de 2026

- Se fortalece `tests/test_arquitectura_capas.py` para resolver imports absolutos y relativos. Así se reducen los casos en que una dependencia prohibida podría quedar oculta detrás de un import relativo.
- Se agrega una regla verificable en CI: los módulos de `aplicacion/puertos/` no pueden importar servicios concretos, infraestructura, UI, Streamlit ni SQLite.
- Se mantiene una migración progresiva: todavía no se prohíbe toda dependencia directa de aplicación hacia infraestructura porque existen consumidores de pagos que deben refactorizarse con pruebas de compatibilidad y atomicidad.
- El cambio es preventivo y no modifica las reglas financieras, las políticas de pago, la escritura de datos ni el modo efectivo de Legacy/V3. La aceptación depende de la suite y de los controles de seguridad del PR.

## Arquitectura modular por capacidades de negocio — 13 de octubre de 2026

- Se documenta una arquitectura objetivo basada en módulos de negocio cohesionados, APIs públicas explícitas, dependencias sin ciclos y responsabilidad clara sobre los datos.
- Se distingue la modularidad del código de la decisión de desplegar procesos independientes. Para el MVP local se conserva una aplicación y una base SQLite, con límites lógicos de propiedad de datos y transacciones financieras protegidas.
- Se establece una migración incremental: inventario de dependencias, contratos públicos, verificaciones automáticas y extracción por áreas. No se autoriza una reescritura general ni cambios financieros implícitos.
- Se incorpora la primera protección automática en `tests/test_arquitectura_capas.py`: el dominio no puede importar aplicación, infraestructura, UI, Streamlit ni SQLite. La regla protege una frontera ya observada limpia; las comprobaciones de ciclos y APIs públicas se agregarán a medida que se inventaríen y reduzcan las dependencias actuales.
- Se vincula el trabajo al [issue #267](https://github.com/JavierGrecco/prestamos_privados/issues/267). La modularización debe apoyar y no sustituir el cierre prioritario del MVP local (#223).
- Documento rector: [Arquitectura modular por capacidades de negocio](ARQUITECTURA_MODULAR_OBJETIVO.md). Esta es la decisión y hoja de implementación inicial; el código todavía debe migrarse por etapas.

## Contratos de pagos y persistencia sin dependencia de servicios concretos — 13 de octubre de 2026

- Se trasladan `EstadoRegistroPagoV3`, `IdempotenciaPagoV3` y el protocolo de repositorio a `aplicacion/puertos/registro_pago_v3.py`.
- Se trasladan los resultados y DTO de observabilidad SOMBRA a `aplicacion/puertos/sombra_pago_v3.py`.
- Los servicios antiguos importan y reexportan los mismos tipos para conservar compatibilidad, mientras los adaptadores SQLite dependen del contrato estable y no de implementaciones de servicio.
- La prueba `tests/test_arquitectura_capas.py` se amplía para impedir que la infraestructura importe `aplicacion.servicios`.
- El cambio es estructural: no modifica fórmulas, política de pago ni el orden transaccional. Debe validarse con la suite completa antes de integrar.

## Prevención de HTML dinámico — 13 de octubre de 2026

- Se amplía el contrato estático de la UI para detectar datos de texto no confiables insertados en f-strings, concatenaciones con `+` y llamadas directas a `.format()`, siempre que el marcado HTML literal sea reconocible.
- Se incorporan regresiones para confirmar que los casos inseguros se detectan y que el uso explícito de `escape()` evita falsos positivos en los ejemplos cubiertos.
- La auditoría de HTML documenta la cobertura nueva y mantiene visibles sus límites: el análisis no sustituye una revisión de seguridad y no cubre de forma completa plantillas formateadas de manera indirecta.
- El cambio se propone en el [PR #266](https://github.com/JavierGrecco/prestamos_privados/pull/266). Solo amplía pruebas preventivas y documentación; no cambia el HTML de ejecución ni las reglas financieras.

## Coherencia de producto, evaluación y roadmap — corte verificado de main

- Se consolida `docs/PRODUCTO.md` como descripción del propósito, perfiles, funciones actuales y límites del producto, incluyendo préstamos privados y autocrédito/reposición con referencia USD y rendimiento objetivo.
- `docs/ESTADO_DEL_PROYECTO.md` distingue capacidades integradas, bloqueos y aceptación pendiente; ya no presenta la evaluación como si main estuviera en el commit funcional anterior.
- `docs/ROADMAP_MVP_LOCAL.md` se mantiene como la única hoja de ruta operativa, con fases, dependencias y criterios de salida; `docs/ROADMAP.md` conserva la evolución técnica histórica.
- `docs/EVALUACION_EJECUTIVA_MVP_2026-10-12.md` mantiene nota 7,0/10, avance funcional 65–70%, preparación operativa 55–60% y estimación de 21–34 jornadas, explícitamente como estimaciones de ingeniería.
- El PR #264 se integró en `main` como commit `8fd2c30f77f913c96148f8767c89074f251439e4`. El CI posterior al merge pasó **1.061 pruebas en cada una de Python 3.11–3.14**, CodeQL y auditoría de dependencias. [Pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38338273679) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38338273668).
- Esta entrega no cambia cálculos ni habilita carencia/V3: explicita qué está integrado en código y qué aún requiere aprobación contractual o aceptación manual.
- Los PRs históricos #240–#245 se cerraron como supersedidos por la consolidación #260 tras verificar que sus archivos relevantes se conservaron en el cambio integrado; sus ramas y commits quedan disponibles para trazabilidad.
- El issue [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) sigue siendo el seguimiento coordinador del cierre local.

## Evaluación ejecutiva y comparación profesional — 12 de octubre de 2026

- Se incorpora `docs/EVALUACION_EJECUTIVA_MVP_2026-10-12.md` como evaluación versionada con calificación técnica, completitud funcional estimada, preparación para uso real, porcentajes por área y comparación con plataformas de servicing.
- La evaluación conserva la estimación vigente de 21–34 jornadas para el MVP local (más 2–4 jornadas si la comparación contra precio de contado es obligatoria para el primer piloto).
- Los puntajes se declaran explícitamente como estimaciones técnicas, separadas de CI y aceptación manual.
- Se enlaza el documento desde el estado ejecutivo y el roadmap canónico para que la evaluación no dependa del chat.


## Correcciones auditables para planes internos — PR #260 / esquema v026

- Agrega la tabla append-only `correcciones_auditables`, con tipo e ID del registro, hash del original, snapshot propuesto/hash, motivo, identidad autenticada, marca UTC, clave idempotente y cadena opcional de propuestas anteriores.
- El servicio comprueba permisos en la capa de aplicación; vuelve a leer y verificar el snapshot original; prohíbe floats en el snapshot; valida fechas, importes, monedas, cotizaciones y equivalentes USD; serializa de forma determinista.
- Usa `BEGIN IMMEDIATE` para serializar propuestas. La misma solicitud con la misma clave es idempotente; una solicitud diferente no puede reutilizarla.
- Agrega interfaz de historial/comparación y formulario guiado para proponer correcciones de aportes, flujos de inversión y valuaciones, con motivo obligatorio y comparación de antes/después.
- **No aplica las propuestas a los hechos originales** ni modifica posiciones, XIRR o informes. Aplicar una corrección efectiva requiere una fase separada con reglas de reconstrucción/auditoría, preservación de informes históricos y pruebas contra doble contabilización.
- El PR #260 quedó integrado en `main` en el commit `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52`. Ese commit pasó **1.061 pruebas en cada una de Python 3.11, 3.12, 3.13 y 3.14**, además de CodeQL y auditoría de dependencias. Evidencia en `main`: [tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38333090358) y [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38333090329).
- La aceptación visual/manual y la prueba sobre una copia restaurada de una base histórica siguen pendientes.

## Entrega consolidada integrada en `main` — 12 de octubre de 2026

La entrega se integró mediante el [PR #258](https://github.com/JavierGrecco/prestamos_privados/pull/258) en el commit `b0d96de99611e6daab0a8b268e221347b97eb018`. Consolida el trabajo de los PRs #246–#257 para evitar que las mejoras queden dispersas en ramas sin integrar. Las ramas y commits originales se conservan para trazabilidad.

- **Pagos y SQLite:** reintentos idempotentes, separación de fecha real y fecha valor, transacción con reserva de escritura, y rollback obligatorio si falla una operación anidada.
- **Límites financieros:** valida importes `Decimal` finitos y en centavos exactos; rechaza tasas negativas/no finitas y cotizaciones inválidas en el alta; no admite participantes inactivos.
- **Precisión:** conversión TEA mensual mediante `Decimal`, sin una conversión intermedia a `float`.
- **Migraciones:** rechaza historiales incompletos o inconsistentes antes de modificar el esquema; serializa el inicio de migraciones concurrentes para que dos arranques no apliquen la misma versión dos veces; agrega pruebas de preservación de una operación histórica real.
- **Atomicidad:** cubre con fallos inducidos el alta de préstamos y el registro de pagos.
- **Seguridad HTML:** amplía el contrato estático para detectar aliases de campos de texto usados en plantillas HTML.
- **Convención temporal:** `dominio/convenciones_fechas.py` centraliza el cálculo de fracciones por fechas y factores TNA/TEA para que el devengamiento por período y el calendario explícito compartan semántica. La ruta mensual regular conserva su compatibilidad; la API rechaza `datetime` en lugar de fecha civil. No se recalculan préstamos históricos.
- **Protección contractual del calendario:** la alta Legacy todavía genera cuotas con el motor mensual y no aplica al cronograma persistido la convención temporal seleccionada. Para evitar guardar condiciones que el cálculo no respeta, la UI y el servicio de aplicación solo permiten crear préstamos reales con convención `MENSUAL`; ACTUAL/365, ACTUAL/360 y 30E/360 quedan como comparaciones hasta integrar y validar la misma regla en alta, pagos e informes.
- **Convención 30/360:** la UI identifica la regla como `30E/360 ISDA (ajuste de fin de mes)`, explica la excepción del vencimiento final en febrero y advierte que no es intercambiable con Eurobond Basis. La corrección del rótulo no altera importes por sí sola.
- **Escenarios USD:** las cotizaciones de simulación requieren `Decimal` finito, positivo y fechado; se normalizan metadatos y se rechazan referencias/marcas inválidas sin cambiar cotizaciones existentes ni tratarlas automáticamente como observadas.

La matriz combinada pasó **1.014 pruebas** en cada versión de Python 3.11, 3.12, 3.13 y 3.14 tanto en el HEAD consolidado previo al merge como en el commit integrado en `main`. CodeQL y auditoría de dependencias también pasaron después de la integración. La aceptación visual/local sigue siendo una actividad separada y pendiente.


Este documento ayuda a entender el proyecto sin tener que reconstruir la historia leyendo todos los commits. Resume los cambios relevantes, cómo se validan y qué queda pendiente.

**Última actualización:** 12 de octubre de 2026 (hora Argentina); `main` verificado en `d83f08ab99d23764d3ee5f3dd5db5853c93fc310`. El último commit funcional consolidado citado es `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52`; los commits posteriores al corte funcional actualizan la documentación.

Para ver el estado actual de cada frente, consultar también el [Estado del proyecto](ESTADO_DEL_PROYECTO.md), el [Roadmap](ROADMAP.md) y los issues enlazados. El issue o PR es la referencia viva para su trabajo específico.

La hoja de ruta para finalizar la experiencia local está centralizada en [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md), con fases, dependencias y criterios de aceptación. El seguimiento coordinador es [issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223).

## Trazabilidad de las mejoras integradas por el PR #258

### Idempotencia de pagos, concurrencia y versionado contractual — origen PR #247, integrado

Se reserva el turno de escritura de SQLite antes de leer la última versión de un snapshot. La lectura del máximo, el armado del JSON canónico/hash y el INSERT ocurren en una misma transacción. Esto evita que dos conexiones independientes intenten asignar el mismo número de versión. Una regresión abre dos conexiones al mismo archivo e intenta guardar dos snapshots simultáneos; comprueba las versiones 1 y 2, los identificadores distintos y los hashes verificables.

**Validación consolidada:** el PR #258 pasó 1.014 pruebas en Python 3.11–3.14 y controles de seguridad en su HEAD previo al merge. Evidencia: [suite consolidada](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38329537575) y [controles de seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38329537653). El commit integrado `b0d96de99611e6daab0a8b268e221347b97eb018` volvió a pasar 1.014 pruebas por versión, CodeQL y auditoría: [tests en main](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38329891855), [seguridad en main](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38329891858).

**Límite:** es una mejora de persistencia, no activa préstamos reales con carencia. No cambia cuotas, tasas, intereses, pagos ni saldos históricos. La carencia todavía requiere integración contractual y E2E de cuotas, pagos parciales, adelantos, mora e informes antes de habilitarse.

La misma rama amplía la protección transaccional del registro Legacy: la lectura de deuda ocurre después de `BEGIN IMMEDIATE`, y la ruta de la UI ya no pierde la clave/huella de idempotencia que crea para el intento. El repositorio persiste esos dos campos en las columnas de la migración v009; un reintento idéntico devuelve el pago ya registrado y un payload diferente con la misma clave se rechaza. Se agregaron pruebas de repetición y con dos conexiones SQLite independientes enviando simultáneamente el mismo intento. El contrato Legacy de pago y el motor de sombras mantienen su separación; la carencia no queda habilitada por estos cambios.

También se corrige una omisión del adaptador Legacy: antes conservaba `fecha_real`, pero descartaba la `fecha_valor` que el formulario ya permitía seleccionar. Ahora ambas fechas se guardan por separado; la fecha valor determina la deuda/mora calculada, la versión de política de pago vigente y la fecha efectiva del recálculo RAI/RNI, mientras que `fecha_real` identifica el movimiento efectivo de caja y los asientos contables. Se agregaron regresiones que verifican la política elegida, las dos fechas persistidas y el rechazo explícito de `datetime` donde el contrato requiere una fecha civil sin hora.

### Ampliación de la barrera de HTML dinámico — origen PR #246, integrado

El control estático detecta campos de texto extraídos y pasados por alias locales simples hasta una plantilla HTML, y añade una regresión para que importes, porcentajes e íconos calculados no se clasifiquen como texto crudo. Esta ampliación forma parte del HEAD consolidado del PR #258, validado con 1.014 pruebas por versión en Python 3.11–3.14, CodeQL y auditoría de dependencias.

**Límite:** la comprobación es preventiva, no un sanitizador universal. El issue #158 permanece abierto para ampliar la prevención y completar la aceptación E2E; los PRs de origen #246–#257 quedan sustituidos por la entrega consolidada, con sus ramas y commits preservados.

## Novedades del 10 de octubre de 2026

### Proyección original integrada al reporte de inversión — PR #237

El informe por plan incorpora la proyección guardada de la versión activa junto a supuestos y hechos declarados. En Markdown agrega una lectura humana del benchmark, la tasa y los valores comparados; JSON preserva el snapshot completo (incluidos sensibilidad y calendario); CSV diferencia filas de supuestos y proyecciones con etiquetas que advierten que no son resultados realizados. Los datos históricos que carezcan de campos opcionales se siguen exportando sin inventar valores. Los nombres de benchmark se escapan para que texto aportado por el usuario no altere el formato Markdown.

La mejora permite contrastar el resultado proyectado con aportes, rescates, distribuciones, costos externos y valuaciones registrados, sin sumar automáticamente estos valores a la posición personal ni modificar préstamos/pagos Legacy/V3. El PR #237 pasó la matriz de tests Python 3.11–3.14, CodeQL y la auditoría de dependencias antes de integrarse. No hay conciliación automática con brokers ni validación externa de las valuaciones.

### Descarga directa del informe desde la UI — PR #238

La pantalla de planes internos muestra tres descargas: Markdown para lectura humana, JSON con el snapshot completo y CSV para análisis. El informe incluye la última proyección guardada y los movimientos/valuaciones declarados del plan. Para evitar comparar una proyección histórica con hechos posteriores, las descargas se ofrecen cuando se selecciona la versión vigente; al mirar una versión antigua, la UI explica por qué no se habilita la exportación. La función es de solo lectura y no requiere permisos para operar el plan.

La prueba E2E verifica que los tres controles aparecen al consultar un plan interno. El PR #238 pasó tests Python 3.11–3.14, CodeQL y auditoría de dependencias antes de integrarse. La validación manual en navegador y entorno local sigue pendiente; un test de UI no sustituye esa aceptación.


### Roadmap profesional para la entrega local

Se creó una hoja de ruta operativa con lenguaje de producto, estado de cada frente, dependencias entre fases, alcance explícito del MVP, criterios de salida y forma de trabajo para cada PR. La prioridad es cerrar préstamos privados y autocrédito/reposición desde la UI local; nube y conexión automática a mercados permanecen fuera del camino crítico. El plan queda coordinado por el issue #223.

### Guardar y consultar análisis de reposición USD — PR #225

El simulador permite guardar un análisis desde la UI local y volver a consultarlo. La migración v022 agrega la tabla de snapshots con creación registrada y bloqueos de actualización/eliminación; el repositorio serializa importes con `Decimal`, conserva supuestos y resultados en JSON determinista y calcula un SHA-256 para comprobar integridad. La UI permite seleccionar análisis guardados, consultar el calendario y revisar supuestos/sensibilidad. La acción de guardar exige capacidad `OPERAR`.

La entrega es deliberadamente un **snapshot inmutable de análisis**: no es aún un plan editable ni registra contrato, desembolso o pagos. La siguiente tarea de la fase 2 es agrupar versiones bajo una identidad de plan con ciclo de vida, manteniendo separadas las obligaciones reales y el rendimiento hipotético. CI de PR #225 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Planes de reposición con identidad y versiones — PR #227

Se agrega la migración v023 con una entidad de plan y su historial de versiones. Los snapshots v022 existentes se convierten en planes con versión inicial, vinculados al registro de origen para conservar continuidad. La UI permite crear un plan, guardar una nueva versión consecutiva, consultar versiones anteriores y cerrar el plan sin borrar el historial. Tanto los planes como sus versiones están protegidos por triggers; cada versión contiene su SHA-256 y los valores financieros se serializan sin `float`.

La entrega conserva un límite deliberado: el plan es una herramienta de planificación financiera, no un préstamo legal ni un registro de desembolsos, aportes, cobros o ganancias realizadas. El siguiente paso es la aceptación manual y el seguimiento de cuánto capital se repuso, cómo se conserva poder de compra y cómo se compara el rendimiento realizado con el objetivo, sin contabilizar proyecciones como resultados reales. PR #227 validado en Python 3.11–3.14 y con controles de seguridad aprobados.

### Registro de aportes y avance de reposición — PR #229

La migración v024 incorpora un libro de aportes asociado a un plan interno activo. Cada registro conserva fecha, importe ARS, cotización declarada, naturaleza (observada o supuesto), fuente/referencia, equivalente USD de referencia, autor y SHA-256. Los aportes no se editan ni se borran; el modelo de correcciones debe conservar la traza y queda para una etapa posterior.

La UI permite registrar aportes desde el plan, consultar el historial y comparar el equivalente USD de referencia acumulado contra las cuotas programadas ya vencidas de la versión seleccionada. La comparación no revalúa aportes anteriores al tipo de cambio de hoy ni prueba que se hayan comprado dólares. Tampoco registra pagos de préstamos o rendimiento de inversiones: el equivalente USD es una referencia, no un resultado realizado. Se validan importes/cotizaciones positivos, precisión, fuente para cotizaciones observadas y rechazo de fechas futuras. CI de PR #229 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Flujos de inversión, valuaciones y rendimiento reportado — PR #232

La migración v025 agrega libros inmutables separados para movimientos y valuaciones de inversión. Los movimientos distinguen aportes a la inversión, rescates, distribuciones y costos/impuestos pagados fuera de la cartera. Cada fila guarda fecha, moneda, importe original, cotización declarada para convertir ARS/USD, fuente/referencia, autor y SHA-256. Las valuaciones mantienen snapshots históricos y permiten registrar un valor cero si la cartera queda totalmente deteriorada.

La UI muestra aportes a inversión, cobros/rescates, costos externos, última valuación y resultado total en USD de referencia. Calcula XIRR anualizada solo cuando hay un aporte a inversión, existe una valuación igual o posterior al último movimiento y el solver encuentra un resultado. El solver netea flujos de una misma fecha, usa bisección acotada y no publica una tasa única si los flujos netos alternan de signo más de una vez, porque podrían admitir soluciones múltiples. En esos casos, la UI explica la ambigüedad en lugar de reportar una tasa potencialmente engañosa; en otros casos sin raíz numérica fiable, indica qué falta o por qué no pudo calcularse. El valor de mercado final de los activos abiertos es una valuación no realizada, no una ganancia cobrada. Para evitar doble conteo, los costos externos se deben registrar solo si se pagaron fuera de la cartera y no están descontados de la valuación ingresada.

Todos los flujos/valuaciones son datos declarados por el usuario: no hay descarga ni conciliación automática con broker, cotizaciones o comprobantes. Esto no modifica pagos contractuales Legacy/V3. CI de PR #232 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Informe exportable de reposición e inversión por plan

Se agrega una exportación de solo lectura desde el plan interno, con Markdown legible, JSON estructurado y CSV de movimientos. El informe reúne por separado aportes destinados a reposición, movimientos de inversión, valuaciones históricas, resultado/XIRR reportados y metadatos de integridad del plan. No agrega esos importes al reporte personal M2/M5 porque todavía no existe conciliación de titularidad/consolidación que descarte doble conteo.

El servicio valida el hash de la última versión del plan, verifica los hashes de los registros exportados y se niega a generar un archivo que omita silenciosamente historiales mayores al límite admitido. Los datos permanecen declarados por el usuario, la valuación abierta sigue marcada como no realizada y el equivalente USD de montos ARS es solo referencia. La exportación no crea auditoría ni muta préstamos o pagos.


### Hardening de exportaciones de reposición/inversión

El informe Markdown presenta los importes con agrupación y decimal locales, incluye notas de trazabilidad y explicita qué tipos de flujo son salidas negativas y cuáles entradas positivas para XIRR. En CSV, los campos de texto libre que comienzan con caracteres interpretables como fórmulas de planilla se neutralizan; los importes canónicos permanecen numéricos y se agrega la columna `direccion_xirr`. Las pruebas verifican que el esquema CSV sea consistente y que las referencias potencialmente activas se exporten como texto.


### Importación de índice histórico de retorno total — etapa B inicial de issue #204

El modo USD permite descargar una plantilla CSV e importar observaciones fechadas de un índice de retorno total con nivel, moneda, tipo de índice (bruto/neto), fuente y referencia por fila. Se exige UTF-8, separador punto y coma, valores `Decimal`, fechas ISO estrictamente crecientes, moneda homogénea, tipo de índice homogéneo, fuente declarada y al menos 30 días entre la primera y la última observación. Se limita el archivo a 2 MB y 5.000 filas.

El resumen muestra retorno acumulado, CAGR observado con base 365 días, caída máxima desde un pico histórico y el mayor hueco de fechas de toda la serie, con inicio y fin de ese hueco. La serie permanece en sesión y puede inspeccionarse junto con sus referencias. Solo si el índice está clasificado como `BRUTO_TOTAL_RETURN`, la moneda es USD, el nombre/clase coincide con el benchmark seleccionado, el rendimiento anualizado está dentro del rango admitido, hay **al menos 365 días de historia y 12 observaciones**, y ningún intervalo entre observaciones supera **45 días**, la UI habilita una casilla explícita para usar el CAGR pasado como **hipótesis de rendimiento bruto base**; después se aplican los costos, el impuesto estimado y el margen de escenarios. Las series cortas o con huecos mayores siguen disponibles para análisis y backtest si las fechas operativas están cubiertas, pero no se permite usar ese CAGR como tasa base. La exportación de sensibilidad incluye también el mayor hueco y sus fechas para auditoría. Una serie `NETO_TOTAL_RETURN` se puede analizar, pero no se puede reutilizar como rendimiento bruto para evitar doble descuento de costos/impuestos. El CAGR nunca se aplica automáticamente ni se presenta como pronóstico.

Si se importa un índice total-return ya calculado, la aplicación conserva la clasificación y la metodología declaradas por el proveedor, pero no verifica de forma independiente su autenticidad. No descarga datos de mercado y no implementa todavía un modelo específico de bonos, cupón corrido, rendimiento al vencimiento ni acciones corporativas.

### Derivar índice total-return desde precio no ajustado + distribuciones — etapa B

Se añade una segunda vía de carga con plantilla CSV: fecha, precio de cierre **no ajustado**, distribución en efectivo por unidad, moneda, clasificación bruto/neto, fuente y referencia. El precio debe declararse como `PRECIO_NO_AJUSTADO`; la importación rechaza otras bases para evitar sumar una distribución a un precio que ya podría incorporarla. La primera observación debe tener distribución cero porque no existe un intervalo previo dentro de la serie para reinvertirla.

Para cada intervalo calcula `TRI_t = TRI_(t-1) × (P_t + D_t) / P_(t-1)`, normalizando la serie a 100. La distribución declarada se reinvierte al cierre de su fecha. Se mantiene `Decimal`, el orden estricto de fechas, la moneda única, la clasificación homogénea bruto/neto, la fuente y referencias. Los precios y distribuciones originales permanecen en la sesión y se muestran junto al índice derivado; el método de construcción viaja también en el CSV de sensibilidad y en el CSV del backtest.

Esta fórmula es una aproximación de retorno total con distribuciones por unidad, no un feed verificado ni una liquidación fiscal. El usuario debe confirmar que los precios realmente son no ajustados y que las distribuciones corresponden a esas fechas/unidades; no se corrigen splits, fusiones, cambios de unidad, retenciones particulares ni los flujos de bonos/YTM. El modo neto necesita distribuciones netas consistentes con esa metodología. Sin esas comprobaciones, el resultado no debe usarse como rentabilidad realizada de un activo real.

Se suma una descarga de trazabilidad que combina en cada fila el precio no ajustado, la distribución declarada, los metadatos originales y el nivel total-return derivado. Exporta la fórmula normalizada y conserva fuente/referencia; los textos libres reciben protección contra inyección de fórmulas en hojas de cálculo. El CSV se rechaza si las fechas de las entradas y del índice no coinciden fila por fila.

### Backtest histórico del capital y las cuotas — extensión de etapa B de issue #204

Sobre la serie histórica importada, el simulador permite contrastar el valor que habría alcanzado el capital original mantenido en el índice contra el valor final de las cuotas reinvertidas en sus fechas programadas. El backtest usa niveles observados iguales o anteriores a cada fecha, informa el desfase en días y rechaza cierres obsoletos (más de 45 días), fechas fuera de la cobertura o una serie que no esté expresada en USD. Calcula la valoración final de ambos caminos, su brecha, el rendimiento anualizado observado del capital y la XIRR de la cartera acumulada cuando existe una solución.

El backtest conserva el tipo del índice (`BRUTO_TOTAL_RETURN` o `NETO_TOTAL_RETURN`) y descarga un CSV con fechas valoradas, fuentes/referencias, desfases, montos finales, brecha y XIRR. No aplica una segunda deducción de costos/impuestos a los niveles observados. No cambia el plan ni guarda contratos/cuotas en base de datos; si el historial no cubre todo el calendario, muestra la causa y no extrapola.

### Benchmark neto y sensibilidad conservador/base/alto — etapa A de issue #204

El simulador USD distingue el rendimiento bruto de la inversión alternativa y calcula una tasa neta ilustrativa descontando costos anuales estimados e impuesto configurado sobre el rendimiento positivo posterior a costos. Se añade clase de activo, etiqueta del benchmark y margen editable que crea escenarios conservador/base/alto. La tabla compara el valor final contrafactual del capital inicial contra las mismas cuotas reinvertidas; el calendario, las cuotas contractuales y la unidad USD del plan no varían al cambiar un escenario. Se puede exportar la sensibilidad a CSV con los supuestos incluidos.

Los costos se modelan como proporción anual simple del capital y el impuesto como porcentaje estimado de la ganancia positiva; no es una liquidación fiscal ni modela en esta etapa todos los flujos de cada instrumento. Las tasas son hipótesis manuales, no retornos reales recuperados de mercado. La etapa B — importar series históricas fechadas con fuente, metodología y tratamiento de distribuciones — sigue pendiente; el código no inventa cotizaciones ni rendimientos históricos.

### Importación y plantilla CSV de cotizaciones por cuota

El modo de cotización individual ahora ofrece una plantilla CSV descargable e importación de tasas por vencimiento. El formato documenta el separador punto y coma (compatible con coma decimal), incluye número de cuota y fecha ISO, y permite fuente, lado, naturaleza y referencia. La importación comprueba columnas, fechas contra el calendario actual, duplicados, cotizaciones finitas/positivas y fuente antes de cargar la tabla. Las filas sin cotización pueden quedar vacías; una fila parcialmente completada se rechaza. Si cambia el calendario del plan, se eliminan las cotizaciones previas para no asociar un valor antiguo a una cuota distinta.

El CSV de resultados expone también la referencia de la cotización. Los campos libres de fuente/referencia reciben protección frente a fórmulas al abrir los CSV en aplicaciones de hojas de cálculo. No se persisten las cotizaciones: pertenecen al escenario de simulación actual.

### Cotizaciones individuales por vencimiento en modo USD — issue #202

El simulador incorpora un método explícito para ingresar una cotización independiente en cada cuota. La tabla presenta cuota y vencimiento calculados como campos bloqueados, con valores editables para ARS/USD, fuente/instrumento, lado comprador/vendedor, naturaleza (observada, proyectada o supuesto) y referencia opcional. Las cotizaciones quedan vacías por defecto: el tipo de cambio inicial no se copia silenciosamente a pagos futuros.

Cada valor se valida como `Decimal`, requiere fuente cuando se carga una tasa y se asocia a la fecha exacta del vencimiento. Las cuotas sin datos quedan sin equivalente ARS; el total ARS solo está disponible cuando todas las cotizaciones están completas. La tabla y el CSV distinguen cotización, fuente, lado, naturaleza y equivalente por cuota. Las cuotas y métricas USD no cambian cuando cambia la ruta ARS.

Se amplían las regresiones unitarias y E2E. El simulador sigue siendo analítico y no consulta tipos de cambio en vivo ni guarda operaciones.

### Precisión decimal en el simulador ARS/USD

Las entradas financieras del simulador de carencia dejan de depender de widgets numéricos que entregan `float`. Capital, tasas, cotización inicial ARS/USD y variación cambiaria proyectada se ingresan como texto validado y se convierten directamente a `Decimal`. Se aceptan formatos argentinos como `1.000.000,50` y `36,5000`, además del formato decimal canónico cuando no resulta ambiguo. Se rechazan valores vacíos, no finitos, separadores inconsistentes, importes fuera de rango y precisión mayor a la permitida. Los meses y plazos continúan como enteros.

Se amplía la regresión unitaria para formatos válidos/invalidos y la prueba E2E para recorrer ambos modos del simulador y confirmar que las entradas conservan su representación textual. La simulación sigue siendo analítica: no persiste préstamos ni pagos.

La UI no consulta cotizaciones en vivo ni valida externamente el benchmark ingresado; esos datos siguen siendo supuestos declarados por el usuario.

## Novedades del 9 de octubre de 2026

### Contraste de colores y legibilidad — UX D4

Las tres paletas incorporan una prueba automatizada de contraste WCAG AA para texto normal (mínimo 4.5:1), cubriendo combinaciones semánticas de superficies, botones, enlaces y estados de éxito, alerta, error y neutral. Se ajustaron tonos insuficientes en botones primarios, textos secundarios y estados de las paletas clara, intermedia y oscura. El tema oscuro sigue siendo el predeterminado.

La comprobación automática no sustituye la inspección visual manual en navegador, en distintos tamaños de ventana y con navegación por teclado. Esos controles de aceptación de D4 siguen pendientes y se deben registrar solo después de ejecutarlos realmente.


### Aislamiento de transacciones explícitas de pagos V3 — issue #159

Se detectó que el repositorio de pagos V3 usa `BEGIN IMMEDIATE` y `COMMIT/ROLLBACK` en llamadas separadas. El bloqueo individual al obtener la conexión no mantenía el `RLock` durante todo el ciclo, dejando una brecha frente a dos servicios que compartieran una misma instancia de `BaseDatos`. Se añadió `bloqueo_transaccion_explicita()` y el adaptador V3 lo mantiene desde `begin` hasta el cierre de la unidad de trabajo. El estado del contexto se guarda por hilo para evitar mezclar repositorios concurrentes.

Se añade una regresión donde dos servicios intentan registrar pagos con la misma revisión sobre una sola instancia compartida: la segunda transacción debe esperar al commit de la primera y luego rechazar la revisión obsoleta sin duplicar el pago. Este refuerzo no habilita un despliegue multiusuario ni reemplaza pruebas con dos sesiones reales de Streamlit. Issue #159 permanece abierto hasta cubrir ese nivel E2E y la operación bajo contención.


### Frontera de HTML confiable más estricta — issue #158

Se eliminó la fábrica pública que permitía etiquetar un string arbitrario como fragmento HTML confiable. El constructor ahora requiere un token interno; las pantallas quedan cubiertas por una prueba estática que impide importar o invocar el mecanismo de construcción. Los badges siguen disponibles: escapan el texto y validan la variante CSS. Las notas inline también escapan el texto y las celdas de estado se construyen combinando exclusivamente fragmentos tipados; el consumidor heredado de la pantalla de préstamos fue migrado a esa API. Se agregaron regresiones para el rechazo de construcción directa.

Esta entrega reduce la posibilidad de que una pantalla futura convierta por accidente una nota, un nombre o una referencia en HTML ejecutable. No cierra el issue #158: sigue pendiente ampliar el análisis estático de interpolaciones, revisar aliases/atributos y validar los flujos E2E de las superficies de HTML. La suite, CodeQL y la auditoría de dependencias deben pasar en CI antes de integrar.

### Rendimiento objetivo como requisito central del autopréstamo — issue #202

El usuario aclaró que la meta no es solo recuperar capital o conservar su valor de referencia: el plan debe recuperar capital, conservar poder de compra y sumar un rendimiento positivo como si el dinero hubiera permanecido invertido. La UI del modo USD requiere ahora un benchmark identificable y una tasa anual USD positiva, usa TEA como opción inicial y muestra el costo/rendimiento objetivo total junto con XIRR. El 0% queda como comparación analítica, no como el escenario principal. En un autopréstamo se reporta como costo de oportunidad/rendimiento interno, no como ganancia externa consolidada. La cotización proyectada continúa siendo un supuesto y el modo no crea contratos ni pagos. La tasa y la etiqueta del benchmark se cargan manualmente; el [issue #204](https://github.com/JavierGrecco/prestamos_privados/issues/204) sigue el trabajo para comparar contra una inversión identificable con costos, reinversión y datos históricos cuando estén disponibles.

### UI del plan interno en unidad USD — PR #200

El [issue #199](https://github.com/JavierGrecco/prestamos_privados/issues/199) continúa el [simulador USD de dominio integrado en PR #198](https://github.com/JavierGrecco/prestamos_privados/pull/198). El modo ARS nominal permanece como predeterminado. El modo USD convierte el capital inicial con una cotización fechada y muestra capital, cuotas, intereses y saldos en USD; la equivalencia ARS es opcional y usa una trayectoria proyectada cuota por cuota. Sin esa hipótesis, el total ARS queda sin calcular. La pantalla continúa siendo analítica, no registra operaciones y no presenta USD como contrato legal habilitado. La suite de CI debe validar el E2E de ambos modos antes de integrar.


### Rendimiento objetivo como requisito central del autopréstamo — issue #202

El usuario aclaró que la meta no es solo recuperar capital o conservar su valor de referencia: el plan debe recuperar capital, conservar poder de compra y sumar un rendimiento positivo como si el dinero hubiera permanecido invertido. La UI del modo USD requiere ahora un benchmark identificable y una tasa anual USD positiva, usa TEA como opción inicial y muestra el costo/rendimiento objetivo total junto con XIRR. El 0% queda como comparación analítica, no como el escenario principal. En un autopréstamo se reporta como costo de oportunidad/rendimiento interno, no como ganancia externa consolidada. La cotización proyectada continúa siendo un supuesto y el modo no crea contratos ni pagos.

### Comparación de valor final frente al benchmark — issue #206

El simulador calcula dos valores al último vencimiento: cuánto habría valido el capital original si siguiera invertido con el benchmark, y cuánto valdrían las cuotas recuperadas si cada una se reinvirtiera desde su fecha de vencimiento hasta ese mismo final. La diferencia muestra si el plan completo queda por debajo o por encima de la alternativa, manteniendo todo en USD de referencia. La comparación es una hipótesis de reinversión con una tasa manual; no representa aún el retorno histórico de un instrumento específico ni incluye sus costos/impuestos.

### Rendimiento reinvertido durante la carencia — issue #204

La simulación USD separa ahora dos conceptos: el crecimiento contrafactual del capital si permaneciera invertido durante la carencia (con reinversión del rendimiento por período) y el interés simple contractual que el escenario incluye en sus cuotas. En el modo de autopréstamo, el valor futuro del benchmark se convierte en la base interna a reponer; ese crecimiento no se guarda como cláusula legal ni como interés contractual. En el modo de préstamo entre personas, la tasa contractual USD queda separada de la tasa del benchmark; la diferencia respecto del benchmark se muestra como brecha informativa, sin sumarla automáticamente a la deuda. Las pruebas cubren TEA compuesta frente a interés simple diferido y la UI mantiene separadas ambas rutas.

### Autopréstamo y cobertura cambiaria — diseño documentado (issue #194)

Se documenta el caso de uso de compra al contado con reposición del capital, distinguiendo objetivo nominal, conservación en una unidad USD y ganancia. El documento separa el plan interno de reposición del préstamo real entre personas, exige registrar una cotización base y una referencia por cada pago, y propone gatillos como alertas de presupuesto, no como cambios automáticos de contrato. Incluye alternativas ARS nominal, USD, USD referenciado y UVA/CER, más referencias normativas oficiales vigentes consultadas el 09/10/2026. La implementación y la habilitación de condiciones contractuales sensibles siguen pendientes.


### Amortización por fechas explícitas — integrada por PR #190

El [issue #189](https://github.com/JavierGrecco/prestamos_privados/issues/189) registró la brecha entre la convención guardada y el generador mensual que utiliza el alta. El [PR #190](https://github.com/JavierGrecco/prestamos_privados/pull/190) integró una API aditiva para calendarios explícitos. Mantiene igualdad exacta con el motor legado cuando el calendario MENSUAL coincide y calcula factores por fechas para ACTUAL/365, ACTUAL/360, ACTUAL/ACTUAL y 30E/360 ISDA, con excepción del vencimiento final en febrero. La ruta usa TNA proporcional y TEA compuesta con Decimal y cubre amortización francesa y alemana. El servicio de alta todavía no utiliza esta API.

Este cambio aún no modifica el servicio de alta, no recalcula préstamos históricos y no hace operativa la carencia. La suite completa y la revisión de seguridad del HEAD final deben pasar antes de proponer la integración.

### Integración de convenciones temporales en el simulador de carencia — PR #191

El [issue #186](https://github.com/JavierGrecco/prestamos_privados/issues/186) continúa con el [PR #191](https://github.com/JavierGrecco/prestamos_privados/pull/191). El simulador utiliza ahora la misma API de amortización por fechas que el dominio para las cuotas posteriores, y el cálculo de interés simple durante la carencia reutiliza los factores temporales TNA/TEA. La UI permite elegir MENSUAL, ACTUAL/365, ACTUAL/360, ACTUAL/ACTUAL y 30E/360 ISDA.

Es una mejora de análisis, no una operación real: el alta actual no se modifica, los préstamos existentes no se recalculan y ningún interés diferido se convierte automáticamente en capital. La matriz de CI y la revisión de seguridad del PR #191 están en curso.

### Carencia inicial y primera cuota diferida — simulador integrado; operación real pendiente

El [issue #186](https://github.com/JavierGrecco/prestamos_privados/issues/186)
define el alcance financiero y legal del caso. El [PR #187](https://github.com/JavierGrecco/prestamos_privados/pull/187)
agrega cálculo simple de devengamiento, simulación comparativa y una pantalla
accesible desde **Análisis e informes → Simular carencia**.

La pantalla compara interés no cobrado, pago de intereses durante la carencia,
interés simple diferido a la primera cuota, distribución del interés simple sin
capitalización y capitalización solo como análisis. Muestra fechas, cuotas,
total del deudor, componentes de interés y rendimiento anualizado del prestamista
a partir de flujos fechados. No crea ni modifica préstamos.

**Límites explícitos:** el cálculo integral usa convención mensual porque el
generador regular de amortización aún no soporta de manera homogénea todas las
convenciones de días reales. Capitalización con TEA queda deshabilitada hasta
definir una semántica contractual consistente. La persistencia de contratos con
carencia, imputación de pagos, mora y validación E2E operativa siguen pendientes.
El PR continúa en borrador mientras se corrige y confirma CI del simulador.

Consulta el [diseño financiero de carencia inicial](DISENO_CARENCIA_INICIAL.md)
para la decisión de producto, ejemplos, riesgos y etapas siguientes.



### D0 — Plan de evolución UX e identidad polifuncional (integrada)

El [PR #180](https://github.com/JavierGrecco/prestamos_privados/pull/180) integró el [plan de evolución](PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md) y su enlace en el índice documental. La issue coordinadora es [#173](https://github.com/JavierGrecco/prestamos_privados/issues/173). Las entregas D1–D6 cuentan con issues, alcance y criterios de aceptación. El PR pasó CI para Python 3.11–3.14, auditoría de dependencias y CodeQL.

### D1 — Arranque recuperable y selección explícita de persona (integrada)

El [PR #181](https://github.com/JavierGrecco/prestamos_privados/pull/181) resolvió la primera barrera de uso con una base sin personas:
- conserva el tema oscuro como predeterminado, conforme a la preferencia de producto;
- deja de seleccionar automáticamente a Javier o a la primera persona disponible;
- permite ir a Personas desde el estado vacío solo cuando la cuenta tiene capacidad de operar;
- presenta una orientación cuando falta seleccionar persona y una pantalla requiere ese contexto;
- agrega pruebas AppTest para inicio sin persona, selección explícita y permisos de LECTURA.

El PR pasó CI para Python 3.11–3.14, CodeQL y auditoría de dependencias. La issue [#174](https://github.com/JavierGrecco/prestamos_privados/issues/174) quedó cerrada.

### D2 — Personas polifuncionales, vínculo de cuenta y garantías (integrada)

El [PR #182](https://github.com/JavierGrecco/prestamos_privados/pull/182) se integró por squash en el commit `4fdbc67`; el issue [#175](https://github.com/JavierGrecco/prestamos_privados/issues/175) quedó cerrado.

- La migración v019 agrega el vínculo opcional entre una cuenta local y una persona financiera. Las cuentas históricas siguen sin vincular hasta que una persona administradora lo decide; la vinculación no concede capacidades.
- La migración v020 agrega garantías relacionadas con un préstamo, con alcance, tope opcional, estado y motivo/fecha de cierre.
- Las personas pueden acumular roles financieros `DEUDOR`, `INVERSOR` y `GARANTE`; el rol financiero `ADMIN` queda como legado y no concede privilegios de acceso.
- Las garantías se auditan y mantienen fuera de los cálculos de deuda, intereses, mora, pagos y ledger.
- `Mi espacio` consulta la persona vinculada a la cuenta y no toma una persona arbitraria del selector global.

**Validación real:** [tests en Python 3.11–3.14](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37885777659) y [CodeQL + auditoría de dependencias](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37885777657) finalizaron correctamente antes de integrar.

### D3 — Catálogo único y navegación agrupada por permisos (integrada)

El [PR #183](https://github.com/JavierGrecco/prestamos_privados/pull/183) integró D3 y cerró el issue [#176](https://github.com/JavierGrecco/prestamos_privados/issues/176). El commit de integración es [e788fde](https://github.com/JavierGrecco/prestamos_privados/commit/e788fdeffea028754aafe7d9e854ac9bbc7819f4).

- `ui/navegacion.py` define el catálogo central con grupo, capacidad, contexto y nivel de cada pantalla.
- La navegación ya no es una fila horizontal interminable: se agrupa en el sidebar y destaca la ruta activa.
- Detalle financiero se abre desde el préstamo, no como acceso global.
- Administrar el sistema y cambiar el modo efectivo de Motor V3 son capacidades distintas.
- La auditoría global queda reservada a ADMIN por defecto.
- Los tests de Python 3.11–3.14, CodeQL y auditoría de dependencias pasaron sobre la rama antes de integrar.
- D4 continúa siendo responsable de la inspección visual completa y el ajuste fino de CSS.

### D4 — Rediseño visual de prioridad oscura (integrada por PR #184)

El [PR #184](https://github.com/JavierGrecco/prestamos_privados/pull/184) se
integró por squash en `776ce15`. Conserva oscuro como tema predeterminado,
hace coherentes los widgets nativos con el tema elegido, ordena la navegación y
recupera el selector de tema en la configuración inicial y el login. Incluye
regresiones para temas, cuenta existente y bootstrap del primer ADMIN.

**Validación automatizada:** tests Python 3.11–3.14, CodeQL y auditoría de
dependencias pasaron antes de la integración. **Pendiente:** revisión visual
manual de dark, tamaños de ventana, teclado y widgets en un navegador real.

### D5 — Instalación local reproducible (implementación integrada por PR #185; validación manual pendiente)

**Issue:** [#178](https://github.com/JavierGrecco/prestamos_privados/issues/178)  
**PR de implementación:** [#185](https://github.com/JavierGrecco/prestamos_privados/pull/185)

Se agregan dos ayudantes multiplataforma: `scripts/preparar_entorno.py`
prepara `.venv` e instala los manifiestos declarados sin tocar SQLite;
`scripts/iniciar_local.py` exige el intérprete virtual de este checkout, una
ruta explícita de base y una inspección del schema antes de lanzar Streamlit.
Una base nueva se inicializa; una base existente con migraciones pendientes no
se actualiza sin una autorización explícita y un backup verificado.

La guía `docs/INSTALACION_LOCAL.md` separa PowerShell, CMD y macOS/Linux, explica
la diferencia entre cuenta de acceso y persona financiera y detalla qué hacer
si aparece el asistente de ADMIN en una base donde se esperaba una cuenta.

**Validación automatizada:** la revisión de código pasó tests en Python
3.11–3.14 ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991491)),
CodeQL y auditoría de dependencias
([seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991509)),
y el smoke de instalación ejecutó el preparador y las regresiones en Ubuntu,
Windows y macOS ([smoke](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991644)).
La suite, CodeQL, auditoría y smoke multiplataforma también finalizaron correctamente sobre el HEAD documental `ee5403a`; ese commit no altera código ejecutable. **Pendiente manual:** inspección de UI,
primer acceso y reinicio en un navegador/entorno real. El lock exacto de
dependencias también queda como mejora separada porque los manifiestos usan
rangos de versiones.

## Novedades del 8 de octubre de 2026

### En desarrollo — rama `feature/usuarios-locales-admin`

- **Cuentas locales de acceso (v017):** ya integradas y verificadas. La aplicación tiene cuentas separadas de las personas del negocio, inicio de sesión con hash scrypt, bootstrap de ADMIN, roles `ADMIN/OPERADOR/LECTURA`, administración auditada, bloqueo temporal por intentos fallidos y recuperación offline de ADMIN. Pasaron los tests en Python 3.11–3.14, auditoría de dependencias y CodeQL.
- **Revocación de sesiones locales (v018, PR en preparación):** agrega una revisión por cuenta para invalidar sesiones existentes después de cambiar contraseña, rol o estado. El esquema no modifica préstamos, pagos ni movimientos financieros; la prueba de actualización v017→v018 conserva las cuentas existentes.
- **Fuera de alcance actual:** registro público, verificación de correo, recuperación por email y proveedor OIDC/SSO permanecen pendientes de N4. La ejecución local no debe exponerse a Internet.

### Cambios integrados

- **J18.2 — Política de pago trazable:** cada pago conserva la versión de política aplicada; la migración v016 asocia los pagos históricos cuando existe evidencia suficiente. La documentación se sincronizó en el [PR #153](https://github.com/JavierGrecco/prestamos_privados/pull/153).
- **Seguridad de CI:** el permiso para publicar resultados de CodeQL quedó limitado a ese job y la auditoría de dependencias incluye el manifiesto de desarrollo. Ver [PR #154](https://github.com/JavierGrecco/prestamos_privados/pull/154).
- **Criterios financieros y migraciones:** el proyecto distingue las divergencias identificadas de una equivalencia financiera demostrada; también aclara que la prueba H4 actual cubre v009 → v010, no toda la historia hasta v016. Ver [PR #155](https://github.com/JavierGrecco/prestamos_privados/pull/155).
- **Dependencias:** la instalación de ejecución se separó de las herramientas de pruebas y se alinearon los manifiestos e instrucciones. Ver [PR #161](https://github.com/JavierGrecco/prestamos_privados/pull/161).
- **Seguridad de la interfaz:** los componentes compartidos escapan tablas, notas, badges y estados vacíos, con regresiones contra texto malicioso. Ver [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162).
- **Segunda capa de seguridad:** se escaparon identificadores visibles del préstamo y se agregó una prueba para el historial de decisiones. Ver [PR #164](https://github.com/JavierGrecco/prestamos_privados/pull/164).
- **Renderer heredado:** también se protegió `ui/ss.py`, una pantalla antigua que no está conectada al punto de entrada actual, y se agregó una regresión específica. Ver [PR #165](https://github.com/JavierGrecco/prestamos_privados/pull/165).
- **Control automático de HTML:** se agregó una prueba estática que revisa llamadas a `render_html()` y a `st.markdown(..., unsafe_allow_html=True)` para detectar campos de texto sensibles insertados sin escape. También se escapó el número de préstamo en el encabezado de pagos. Ver [PR #167](https://github.com/JavierGrecco/prestamos_privados/pull/167).
- **Migraciones explícitas:** la inspección de schema dejó de crear el historial al consultar la versión; la UI inicializa bases vacías, pero bloquea upgrades silenciosos sobre bases existentes. `python -m scripts.migrar_base` ofrece modo de inspección y, al actualizar, exige generar un backup verificado antes de ejecutar los cambios. El issue [#160](https://github.com/JavierGrecco/prestamos_privados/issues/160) sigue abierto para hardening de recuperación y casos históricos sin versión.
- **Concurrencia SQLite:** `BaseDatos` ahora protege la transacción exterior con `threading.RLock` y serializa los accesos SQL sobre una instancia compartida; se añade una prueba que fuerza una falla concurrente y verifica que el rollback de una operación no borre el cambio de otra. La validación E2E de pagos y dos sesiones sigue pendiente en [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159); detalles en [Concurrencia de SQLite](CONCURRENCIA_SQLITE.md).

Los cuatro PR pasaron los tests en Python 3.11–3.14, auditoría de dependencias y CodeQL antes de integrarse.

### Seguridad de interfaz: varias tandas integradas, auditoría completa pendiente

Los [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162), [#164](https://github.com/JavierGrecco/prestamos_privados/pull/164), [#165](https://github.com/JavierGrecco/prestamos_privados/pull/165) y [#167](https://github.com/JavierGrecco/prestamos_privados/pull/167) ya están integrados. Las mejoras incluyen:

- Las tablas escapan encabezados y celdas de texto por defecto.
- Los mensajes contextuales y los estados vacíos escapan los textos que muestran.
- Los tipos visuales de notas y badges se limitan a valores conocidos.
- Varias pantallas escapan nombres, notas, referencias y datos históricos antes de insertarlos en HTML.
- Se agregaron pruebas para etiquetas, atributos y texto malicioso.
- Se incorporó una comprobación estática para campos sensibles conocidos; ayuda a detectar regresiones, pero no entiende todos los aliases ni todas las formas posibles de construir HTML.

**Esto no cierra todavía la auditoría de la interfaz.** La función que renderiza plantillas HTML conserva su propósito y no sanea automáticamente todo el HTML que recibe. La revisión manual y la cobertura actual están descritas en [Auditoría de HTML en la interfaz](AUDITORIA_HTML_UI.md). La prevención automática inicial ya existe en `tests/test_ui_html_escape_contract.py`, pero su lista de campos es deliberadamente acotada. Sigue pendiente ampliar la detección y completar la validación de extremo a extremo. El issue [#158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158) permanecerá abierto hasta cumplir esos puntos.

## Pendientes prioritarios

1. **Elegir y documentar la regla financiera de salida:** resolver las diferencias de interés post-vencimiento y la distribución interés/capital después de pagos parciales. [Issue #145](https://github.com/JavierGrecco/prestamos_privados/issues/145).
2. **Ejecutar un canary controlado:** solo sobre una base autorizada, con backup verificable, readiness, revisión humana y rollback preparado. No activar V3 automáticamente. [Issue #74](https://github.com/JavierGrecco/prestamos_privados/issues/74).
3. **Completar la auditoría de HTML dinámico:** seguir desde los componentes compartidos al resto de las pantallas y cubrir cada límite de confianza. [Issue #158](https://github.com/JavierGrecco/prestamos_privados/issues/158).
4. **Aislar las sesiones de SQLite:** probar la aplicación con dos sesiones simultáneas y evitar que compartan una misma transacción. [Issue #159](https://github.com/JavierGrecco/prestamos_privados/issues/159).
5. **Controlar las actualizaciones de la base:** separar la migración de bases existentes del arranque normal de la UI. [Issue #160](https://github.com/JavierGrecco/prestamos_privados/issues/160).
6. **Ampliar las pruebas de migraciones:** comprobar actualizaciones representativas hasta v016 sin reescribir hechos económicos. [Issue #156](https://github.com/JavierGrecco/prestamos_privados/issues/156).
7. **Proteger la rama principal:** configurar PR obligatorio y checks requeridos en GitHub. [Issue #157](https://github.com/JavierGrecco/prestamos_privados/issues/157).
8. **Preparar la autenticación real:** integrar un proveedor de identidad si se habilita un despliegue multiusuario. [Issue #137](https://github.com/JavierGrecco/prestamos_privados/issues/137).

## Cómo mantenemos este registro

Cada tanda de trabajo debe explicar, en lenguaje cotidiano:

- qué problema encontramos y a quién puede afectar;
- qué cambió realmente;
- qué pruebas o verificaciones lo respaldan;
- qué no se cambió y por qué;
- qué falta, quién o qué lo bloquea y cuál es el criterio para darlo por terminado.

Un PR abierto no se registra como integrado. Un check pendiente no se describe como verde. Una decisión financiera u operativa que requiere autorización humana no se da por resuelta mediante código o documentación.
