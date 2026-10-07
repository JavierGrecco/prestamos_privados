# I8 — Drill de rollback operativo V3 → Legacy

## Objetivo

Demostrar que una activación de V3 puede revertirse explícitamente a Legacy para
las operaciones siguientes sin perder las operaciones ya confirmadas.

## Principio

El rollback cambia el modo entre operaciones.

No existe fallback automático a Legacy dentro de una operación V3 que ya pudo
haber persistido información. Hacerlo podría duplicar efectos o producir una
segunda aplicación financiera.

## Drill

1. El preflight del entorno controlado está aprobado.
2. Se registra una operación por V3.
3. Se decide explícitamente volver a LEGACY.
4. Se construye el siguiente comando desde el estado financiero posterior a V3.
5. Se registra la siguiente operación por Legacy.
5. Se comprueba que existen ambas operaciones y que conservan su motor de origen.

## Resultado esperado

- el pago V3 permanece registrado;
- el pago posterior Legacy también se registra;
- no existe una tercera operación por fallback automático;
- el cambio de modo es explícito y reproducible.

## Alcance

El drill valida la transición entre operaciones sobre SQLite. No pretende
simular fallos de energía, procesos abortados o recuperación ante desastre.

Esas pruebas pertenecen al hardening operativo posterior.
