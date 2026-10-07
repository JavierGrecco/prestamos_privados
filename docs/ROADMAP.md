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

### I6. Preflight objetivo 🚧

El servicio de preflight evalúa schema, integridad, volumen de ejecuciones,
divergencias, errores y tasa de coincidencia.

Todavía no activa V3.

### I7. Feature flag y activación reversible

Siguiente etapa después de demostrar que el preflight puede cumplirse en un
entorno controlado.

### I8. Rollback operativo

Probar una vuelta explícita a Legacy después de una activación controlada.

## J — Consolidación

- eliminar fachadas transitorias;
- unificar el concepto de PlanPago;
- eliminar módulos duplicados;
- estabilizar APIs públicas;
- simplificar documentación histórica.

La limpieza estructural se hará después de la evidencia de adopción, no antes.

## K — Producto

Después de estabilizar la ruta de préstamos:

- cashflow;
- patrimonio;
- poder adquisitivo;
- NPV / XIRR;
- escenarios;
- planificación financiera.

Estas extensiones deben consumir el motor estabilizado y no crear una segunda
autoridad de cálculo.
