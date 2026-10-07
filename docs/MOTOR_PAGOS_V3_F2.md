# Motor de Pagos V3 — F.2

## Objetivo

Definir la frontera de aplicación para pasar de `RegistrarPagoCommand` a una
persistencia transaccional, manteniendo el motor financiero como función pura
y evitando reemplazar todavía `aplicacion/servicios/pagos.py`.

## Secuencia obligatoria

1. Abrir transacción crítica.
2. Resolver idempotencia.
3. Releer préstamo y obligaciones desde persistencia.
4. Validar `revision_prestamo` (optimistic concurrency).
5. Calcular un nuevo `PlanPago` con el estado recién leído.
6. Persistir pago + imputaciones + estado materializado + ledger + auditoría
   mediante una única operación de infraestructura.
7. Confirmar con `COMMIT`.
8. Ante cualquier excepción: `ROLLBACK`.

## Idempotencia

La misma `idempotency_key` con el mismo fingerprint devuelve el `pago_id`
original sin volver a calcular ni persistir. La misma clave con otro payload es
un error de invariantes y nunca debe generar un segundo pago.

El fingerprint excluye únicamente la propia `idempotency_key`; el resto del
comando forma parte del payload protegido.

## Concurrencia

El comando puede transportar una `revision_prestamo` esperada. Si no la trae,
se utiliza la revisión releída dentro de la transacción. La persistencia debe
volver a comprobar esa revisión al ejecutar la escritura para evitar lost
updates.

## Alcance deliberado

F.2 todavía NO conecta este orquestador con SQLite ni modifica `registrar_pago`.
Tampoco decide devengamientos dinámicos, mora, RAI/RNI ni reglas de negocio
adicionales. Esas decisiones se incorporan una vez que el `PlanPago` V3 tenga
la información financiera completa necesaria.
