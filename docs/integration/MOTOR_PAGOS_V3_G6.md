# Motor de Pagos V3 — G6: migración gradual

## Objetivo

Evitar un cambio brusco del servicio legacy al motor V3.

## Modos

- `LEGACY`: el registrador legacy es el único efectivo.
- `SOMBRA`: legacy registra; V3 calcula en modo sin efectos secundarios; se comparan resultados y se observa cualquier divergencia.
- `V3`: el registrador V3 es el efectivo.

## Regla de seguridad

El modo `SOMBRA` nunca llama al registrador V3 persistente. Solo acepta un planificador V3 sin efectos secundarios.

## Tests

7 tests enfocados cubren selección de motor, sombra, divergencias y configuración inválida.
