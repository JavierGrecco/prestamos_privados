# Roadmap

## Estado actual

**Motor de Pagos V3:** avanzado, integrado con SQLite, con controles de
integridad y preparado para adopción controlada.

El flujo Legacy continúa siendo la autoridad efectiva mientras V3 se valida en
SOMBRA.

La suite se ejecuta en CI sobre Python 3.11, 3.12, 3.13 y 3.14.

## H — Hardening financiero

Bloque completado.

### H1. Comparación Legacy vs V3 ✅

Existe una proyección económica común y escenarios automatizados para comparar
resultados sin exigir igualdad de IDs o metadatos técnicos.

### H2. Atomicidad ante fallas ✅

Excepciones inyectadas después de etapas críticas demuestran rollback exacto del
estado de aplicación.

### H3. Concurrencia e idempotencia ✅

Dos conexiones SQLite permiten verificar serialización, revisión optimista y
reintentos idempotentes.

### H4. Datos existentes ✅

Una base construida hasta v009 puede evolucionar mediante migraciones nuevas sin
alterar sus hechos económicos existentes.

## V3-B — Propiedades matemáticas ✅

El núcleo puro tiene property-based testing sobre waterfall, conservación,
determinismo, TNA, TEA y Actual/365.

## I — Adopción controlada

### I1. Snapshot previo a Legacy ✅

SOMBRA captura explícitamente el estado antes de Legacy y V3 calcula sobre ese
snapshot.

### I2. SOMBRA real sobre SQLite ✅

Existe un adaptador SQLite real que mantiene Legacy efectivo y evita cualquier
persistencia V3 durante la sombra.

### I3. Observabilidad histórica ✅

Divergencias y errores SOMBRA se persisten como observaciones append-only.

### I4. Métricas ✅

Existe un read model de observabilidad por tipo, préstamo y fingerprint.

### I5. Universo de ejecuciones ✅

Cada ejecución SOMBRA puede quedar registrada como SIN_DIVERGENCIA,
DIVERGENCIA o ERROR_SOMBRA, permitiendo medir tasas sobre un denominador real.

### I6. Preflight objetivo ✅

El servicio de preflight evalúa schema, integridad, volumen de ejecuciones,
divergencias, errores y tasa de coincidencia.

No activa V3 por sí mismo.

### I7. Feature flag protegido por preflight ✅

La selección de V3 requiere un preflight explícitamente aprobado. La ausencia
de configuración mantiene Legacy.

El entrypoint productivo ya está conectado al selector/feature flag protegido por preflight.

### I8. Rollback operativo ✅

Drill reproducible de vuelta explícita a Legacy después de una activación controlada.

El rollback será una transición entre operaciones, no un fallback automático en
mitad de una transacción financiera.

### I9. Revisión operativa de evidencia SOMBRA ✅
- métricas agregadas por ejecuciones, divergencias, errores, préstamo y fingerprint;
- consulta de incidencias con filtros por tipo y préstamo;
- visualización en la UI para revisar divergencias y errores sin modificar hechos históricos;
- acceso de solo lectura para preparar una revisión humana antes del cut-over.

### I10. Informe reproducible de preflight ✅
- CLI para evaluar una base SQLite existente sin aplicar migraciones ni modificar datos;
- salida JSON con criterios y motivos de rechazo;
- códigos de salida distintos para aprobado, rechazo controlado y error operativo;
- pruebas de aceptación del comando.

### I11. Modo de motor persistente y auditable ✅
- configuración operacional persistente LEGACY, SOMBRA o V3;
- activación de V3 bloqueada por preflight;
- motivo obligatorio para cualquier cambio;
- control optimista de concurrencia;
- auditoría del cambio de modo;
- UI y registro de pagos comparten el mismo modo efectivo persistente;

### I12. Precheck operativo de canary ✅
- evaluación única de integridad, preflight, evidencia SOMBRA y modo persistido;
- salida JSON reproducible y códigos de salida operativos;
- exige permanecer en LEGACY o SOMBRA antes del canary;
- pruebas de aceptación sin mutaciones.

### I13. Readiness de canary visible en la UI ✅
- el CLI y Streamlit comparten el mismo servicio de readiness;
- la UI muestra integridad, preflight, evidencia SOMBRA y modo persistido;
- el estado listo/no listo es solo de lectura y no activa V3 por sí mismo;
- pruebas AppTest y de servicio.

### I14. Artefacto de evidencia de canary ✅
- el precheck puede persistir su JSON con timestamp UTC;
- escritura atómica para evitar archivos parciales;
- stdout y artefacto son idénticos;
- el informe puede conservarse como evidencia del estado de la base evaluada.

### I15. Preflight coherente y evidencia protegida ✅
- baseline único de schema V3 compartido por preflight, activación y readiness;
- regresión que impide que el CLI sea más permisivo que el gate efectivo;
- artefactos de evidencia no se sobrescriben por defecto;
- reemplazo de evidencia requiere `--force-output` explícito;
- errores operativos conservan ruta de base y timestamp en su salida.

## L1.1 — Preparación del canary real

### Runbook operativo ✅
`docs/CANARY_RUNBOOK_V3.md` define la secuencia reproducible para backup, health check, precheck con evidencia, revisión humana, activación explícita, primera operación canary, verificación y rollback entre operaciones.

### Inventario de consumidores Legacy ✅
`docs/LEGACY_CONSUMERS.md` identifica la superficie Legacy que todavía debe permanecer disponible y los criterios necesarios para retirar cada pieza sin romper consumidores reales.

## J — Consolidación

La adopción controlada ya cuenta con controles y evidencia de I1–I15. El objetivo de J es
reducir gradualmente la superficie transitoria y demostrar recuperabilidad
operativa sin cambiar el comportamiento financiero.

### J1. Consolidación de APIs y conceptos de PlanPago ✅

- distinguir explícitamente API Legacy y API V3;
- identificar consumidores antes de retirar fachadas;
- definir el resultado financiero canónico para V3;
- mantener compatibilidad de imports públicos durante la transición.

### J2. Observabilidad operativa y backups ✅

- health check con quick_check, integrity_check y foreign_key_check;
- backup SQLite autocontenido mediante la API online backup;
- manifiesto y SHA-256 verificables;
- restore sin sobrescritura;
- restore drill automatizado sobre el schema actual;
- CLI operativa y documentación del procedimiento.

J2 demuestra recuperabilidad de un artefacto SQLite, pero no equivale todavía a
un plan completo de continuidad de negocio: siguen pendientes almacenamiento
externo, pérdida del equipo, cifrado, replicación y objetivos RTO/RPO medidos.

### J3. Consolidación del monto distribuible ✅

Las rutas completas de registro V3 usan el mismo dato canónico del PlanPago
(`monto_pago_recibido`) para distribuir el cobro entre inversores, incluido el
excedente tratado como RAI/RNI.

Las fachadas todavía no se eliminan: el retiro de módulos sigue condicionado a
la evidencia de consumidores reales y una API de reemplazo.


## K — Integración y producto

La UI ya consume los principales componentes estabilizados del core. K1–K6 completan la primera vertical funcional: registrar, previsualizar, analizar, auditar y operar.

### K1. Integración funcional del Motor V3 en la UI ✅
- registro desde Streamlit mediante una frontera de aplicación única;
- modos Legacy, SOMBRA y V3 protegido por preflight;
- idempotencia y revisión optimista;
- RAI/RNI, devengamientos y distribución disponibles para la ruta V3.

### K2. Dashboard financiero funcional ✅
- cashflow real y proyectado;
- posición contractual como deudor e inversor;
- XIRR ARS y USD cuando la evidencia es completa;
- poder de compra y rendimiento real con supuestos explícitos;
- escenarios macroeconómicos.

### K3. Preview canónico de pagos V3 ✅
- PlanPago V3 sin persistencia;
- cuotas afectadas, imputaciones, devengamientos y excedente visibles;
- RAI/RNI explícitos;
- comparación contra preview histórico;
- revisión del snapshot usada como control optimista.

### K4. Historial financiero y detalle auditable ✅
- historial de pagos con límite configurable;
- plan V3 persistido y hash;
- imputaciones, devengamientos, ledger, auditoría y SOMBRA;
- acceso directo desde el préstamo.

### K5. Operación desde la UI ✅
- health check de la base activa;
- creación y verificación de backups locales;
- SHA-256 y manifest;
- restore drill temporal seguro;
- preflight y métricas SOMBRA consolidados;
- nunca se restaura sobre la base productiva desde esta pantalla.

### K6. Detalle financiero profundo del préstamo ✅
- amortización vigente;
- capital original, aplicado y pendiente;
- trayectoria real del capital;
- devengamientos persistidos;
- historial RAI/RNI;
- acceso directo desde el detalle del préstamo.

### K7. Aceptación end-to-end de la UI ✅
- arranque del entrypoint real mediante AppTest;
- base SQLite aislada configurable con `PRESTAMOS_DB_PATH`;
- fail-closed ante migraciones incompletas;
- navegación por Resumen, Préstamos, Motor V3, Análisis, Pagos y Operación;
- acceso al detalle financiero desde el préstamo;
- comprobación de las pestañas del detalle financiero;
- conservación del estado de navegación.

K7 queda validado por CI sobre Python 3.11–3.14.


### K8. Registro de pago end-to-end desde la UI ✅
- confirmación real desde Streamlit;
- ejecución SOMBRA con Legacy efectivo y V3 sombra;
- verificación de pago, imputaciones, cuota, ledger y auditoría;
- verificación de la ejecución SOMBRA;
- preview Legacy delegado al servicio, sin waterfall ni tasa hardcodeados en UI;
- idempotencia y control de errores permanecen en la capa de aplicación.

K8 queda validado por CI sobre Python 3.11–3.14.



### K9. Alta de préstamo end-to-end desde la UI ✅
- formulario de alta con deudor, capital, plazo, tasa, sistema y convención;
- simulación de amortización delegada al servicio de aplicación;
- asignación y validación de aportes de inversores;
- confirmación mediante `ServicioPrestamos.crear_completo()`;
- persistencia de préstamo, tasa, cuotas y participaciones;
- desembolso y auditoría verificables;
- aceptación AppTest sobre SQLite aislado.

K9 queda validado por CI sobre Python 3.11–3.14.

### K10. Personas y roles desde la UI ✅
- onboarding disponible con base SQLite vacía;
- alta y edición de personas;
- activación e inactivación;
- alta y baja histórica de roles;
- filtros por estado, rol y búsqueda;
- relación persona ↔ préstamos como deudor/inversor;
- selección de deudores e inversores en el alta de préstamo filtrada por rol;
- servicio de aplicación dedicado, sin escritura SQLite desde Streamlit;
- pruebas de servicio y aceptación AppTest.

K10 queda validado por CI sobre Python 3.11–3.14.

### K11. Ciclo de vida de préstamos desde la UI ✅
- filtro por estado en la lista de préstamos;
- transiciones explícitas y validadas;
- finalización condicionada a cuotas cerradas;
- motivo obligatorio para cancelar/refinanciar/anular;
- auditoría de cada cambio de estado;
- operaciones terminales bloqueadas;
- pruebas de servicio y aceptación AppTest.

K11 queda validado por CI sobre Python 3.11–3.14.


### K12. Auditoría global desde la UI ✅
- filtros por usuario, operación y entidad;
- detalle de evento con datos anterior/nuevo;
- reconstrucción por correlación;
- solo lectura y sin eliminación de evidencia;
- pruebas de servicio y AppTest.

### K13. Fecha real y fecha valor de pagos ✅
- ambas fechas disponibles desde la UI;
- compatibilidad por defecto con fecha valor igual a fecha real;
- comando de aplicación y motor V3 conservan la fecha valor explícita;
- pruebas de comando y aceptación UI.

### K15. Auditoría inmutable ✅
- migración v014;
- UPDATE/DELETE bloqueados mediante triggers SQLite;
- regresiones de persistencia y backup actualizadas;
- pruebas específicas de inmutabilidad.

### K14. Operador declarado en la UI ✅
- elimina usuarios hardcodeados en operaciones principales;
- permite valor inicial mediante PRESTAMOS_OPERADOR;
- utiliza el mismo operador en auditoría;
- documenta explícitamente que no reemplaza autenticación;
- pruebas de contexto y AppTest.

### K16. Exportaciones desde la UI ✅
- auditoría CSV respetando filtros;
- directorio de personas CSV;
- amortización vigente CSV;
- servicio de exportaciones de solo lectura;
- pruebas de contenido y AppTest.
 
## L — Consolidación y cut-over

Después de completar la primera vertical funcional de UI:

- J3 consolidado: unificar semántica de monto distribuible y resolver
  duplicaciones comprobadas;
- proteger main y exigir PR + CI;
- mantener conectado el entrypoint productivo al feature flag y validar su activación efectiva;
- medir evidencia SOMBRA suficiente para el criterio de adopción;
- definir y ejecutar canary/cut-over controlado;
- retirar Legacy solo con evidencia.

## M — Producto financiero avanzado

Después de estabilizar el core y el camino de adopción:
- patrimonio completo;
- planificación financiera;
- escenarios avanzados;
- análisis de poder adquisitivo;
- NPV / XIRR ampliado;
- reportes y exportaciones.
