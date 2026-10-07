# H2 — Atomicidad ante fallas del registro de pagos V3

## Objetivo

Demostrar que la ruta V3 completa no deja una operación financiera parcialmente persistida cuando una etapa posterior falla.

## Qué se prueba

La prueba ejecuta un pago contra una copia de una base recién migrada e inyecta una excepción en dos puntos:

1. después de persistir pago, imputaciones y devengamientos;
2. después de persistir la distribución a inversores.

En ambos casos, `RegistrarPagoV3Completo` debe ejecutar `ROLLBACK` y conservar la causa original de la excepción.

## Criterio fuerte de comprobación

No se comparan solamente cantidades de filas. Se toma un snapshot determinista de todas las tablas de aplicación antes de comenzar y se exige que el snapshot posterior al rollback sea idéntico.

Esto cubre también cambios indirectos como:

- revisión del préstamo;
- estado y saldos de cuotas;
- pagos;
- imputaciones;
- devengamientos;
- ledger;
- auditoría;
- historial de recalculaciones;
- metadatos de idempotencia.

## Qué no cubre H2

Todavía no se prueban cortes de proceso a nivel de sistema operativo, corrupción física del archivo SQLite ni concurrencia real entre procesos. Esos aspectos pertenecen a otras etapas de hardening.
