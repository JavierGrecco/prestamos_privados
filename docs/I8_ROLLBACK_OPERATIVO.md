# I8 — Drill de rollback operativo V3 → Legacy

## Objetivo

Demostrar que una operación ejecutada por V3 puede ser seguida por una
operación posterior en Legacy sin reescribir ni duplicar la operación V3.

## Principio

El rollback cambia el modo **entre operaciones**.

No existe fallback automático a Legacy dentro de una operación V3 que ya pudo
haber persistido información.

## Drill conceptual

1. Preflight aprobado.
2. Modo persistente configurado en V3.
3. Se registra una operación V3 completa.
4. Entre operaciones, el operador vuelve explícitamente a LEGACY.
5. El siguiente comando se construye desde el estado financiero posterior a la
   operación V3.
6. Se registra la siguiente operación con Legacy.
7. Se verifican ambos motores de origen y la trazabilidad de cada operación.

## Implementación

Existe un drill reproducible en
`aplicacion/servicios/drill_rollback_motor_pago_v3.py`.

La configuración persistente del modo y la auditoría agregadas en I11 permiten
llevar este principio a la operación real.

## Límites

Este drill no simula cortes de energía, pérdida de hardware ni recuperación
ante desastre. Esas pruebas pertenecen al hardening de continuidad de negocio.
