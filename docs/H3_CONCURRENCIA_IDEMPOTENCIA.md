# H3 — Concurrencia e idempotencia del registro de pagos V3

## Objetivo

Demostrar que dos solicitudes concurrentes sobre el mismo préstamo se serializan correctamente y que un reintento idempotente no duplica una operación financiera.

## Concurrencia

La prueba utiliza dos conexiones SQLite independientes sobre el mismo archivo.

Una conexión adquiere `BEGIN IMMEDIATE` y se mantiene bloqueada mediante `threading.Event`. La segunda intenta iniciar la operación durante ese período. No se utilizan `sleep` para sincronizar los hilos.

Cuando ambos comandos llevan la misma `revision_prestamo`, el primero puede persistir y avanzar la revisión. El segundo, al obtener el lock posteriormente, relee el estado vigente y rechaza la revisión obsoleta.

## Idempotencia

Con la misma `idempotency_key` y el mismo fingerprint:

- se crea un solo pago;
- el reintento devuelve el mismo `pago_id`;
- el segundo resultado se identifica como repetición idempotente;
- no se ejecuta una segunda aplicación financiera.

También se comprueba que reutilizar una `idempotency_key` con un payload diferente sea rechazado sin mutar la base.

## Qué cubre

- serialización de escritores mediante `BEGIN IMMEDIATE`;
- revisión optimista releída dentro de la transacción;
- idempotencia concurrente;
- protección frente a reutilización de clave con payload distinto.

## Qué no cubre H3

No prueba todavía carga masiva, concurrencia entre procesos del sistema operativo, PostgreSQL ni políticas de reintento de un cliente externo. Son extensiones posteriores del hardening.
