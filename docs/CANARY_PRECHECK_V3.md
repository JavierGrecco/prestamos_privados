# Precheck operativo de canary V3

El comando `scripts/canary_precheck_motor_pago_v3.py` reúne en una sola
evaluación las condiciones necesarias antes de realizar un canary.

Evalúa:

- integridad V3 de la base;
- preflight con schema mínimo v013;
- cantidad de ejecuciones SOMBRA;
- tasa de coincidencia;
- divergencias y errores máximos permitidos;
- modo operacional persistido;
- revisión del modo.

Por seguridad, un modo actual `V3` no se considera `listo_para_canary` por
sí mismo: la herramienta está pensada para comprobar el estado previo al
canary mientras Legacy o SOMBRA siguen siendo la operación efectiva.

## Uso

```bash
python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db
```

Se pueden ajustar los umbrales:

```bash
python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db \
  --min-runs 100 \
  --min-match 1 \
  --max-divergences 0 \
  --max-errors 0
```

## Salidas

`listo_para_canary = true` significa que la base pasó integridad y preflight
y todavía se encuentra en un modo previo al canary (`LEGACY` o `SOMBRA`).

Código `0`: listo.
Código `2`: no listo.
Código `1`: error operativo.

El comando es de solo lectura respecto de la configuración y evidencia.
