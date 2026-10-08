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

El entrypoint productivo todavía no está conectado al flag.

### I8. Rollback operativo ✅

Drill reproducible de vuelta explícita a Legacy después de una activación controlada.

El rollback será una transición entre operaciones, no un fallback automático en
mitad de una transacción financiera.

## J — Consolidación

La adopción controlada ya cuenta con evidencia de I1–I8. El objetivo de J es
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

## L — Consolidación y cut-over

Después de completar la primera vertical funcional de UI:

- resolver J3 y eliminar duplicaciones comprobadas;
- proteger main y exigir PR + CI;
- conectar el entrypoint productivo al feature flag;
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
