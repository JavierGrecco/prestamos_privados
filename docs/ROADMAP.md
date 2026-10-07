# Roadmap

## Estado actual

**Motor de Pagos V3:** avanzado, integrado con SQLite y con controles de integridad.

El checkpoint local del 7/10/2026 quedó en **330 tests verdes**.

El flujo legacy todavía convive con V3.

## H — Hardening financiero

Es la siguiente prioridad.

### H1. Comparación Legacy vs V3

Construir escenarios idénticos y comparar:

- mora;
- interés;
- capital;
- cuotas afectadas;
- saldos;
- imputaciones;
- devengamientos;
- distribución;
- ledger;
- auditoría.

Cada diferencia debe clasificarse como:

- diferencia esperada;
- bug;
- comportamiento legacy que debe conservarse;
- decisión funcional pendiente.

### H2. Atomicidad ante fallas

Inyectar fallas después de etapas críticas y comprobar que no queda una operación parcialmente persistida.

### H3. Concurrencia e idempotencia

Probar pagos simultáneos sobre el mismo préstamo y reintentos del mismo comando.

### H4. Datos existentes

Ejecutar migraciones sobre copias controladas de bases existentes y verificar que el saldo económico no cambie por accidente.

## I — Cut-over

Cuando H esté verde:

1. definir el único punto de entrada;
2. activar V3 de forma controlada;
3. observar;
4. mantener una estrategia clara de rollback;
5. retirar dependencias legacy cuando exista evidencia suficiente.

## J — Consolidación

- eliminar fachadas transitorias;
- unificar el concepto de `PlanPago`;
- eliminar módulos duplicados;
- estabilizar las APIs públicas;
- simplificar documentación histórica.

## K — Producto

Después de estabilizar préstamos:

- cashflow;
- patrimonio;
- poder adquisitivo;
- NPV / XIRR;
- escenarios;
- planificación financiera.

Estas extensiones deben apoyarse en el motor estabilizado, no crear un segundo motor financiero.
