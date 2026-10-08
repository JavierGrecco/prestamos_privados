# Informe reproducible de preflight V3

El script `scripts/preflight_motor_pago_v3.py` permite evaluar una base SQLite
existente antes de un canary o cut-over.

## Importante

El comando:

- no ejecuta pagos;
- no aplica migraciones;
- no modifica observaciones;
- no cambia el modo efectivo del motor.

## Uso

```bash
python -m scripts.preflight_motor_pago_v3 datos/prestamos.db
```

Los umbrales pueden sobreescribirse para una revisión controlada:

```bash
python -m scripts.preflight_motor_pago_v3 datos/prestamos.db \
  --min-runs 100 \
  --min-match 1 \
  --max-divergences 0 \
  --max-errors 0 \
  --min-schema 12
```

## Salidas

La salida estándar es JSON e incluye:

- base evaluada;
- resultado `apto`;
- todos los criterios;
- detalle de cada criterio;
- motivos de rechazo.

El código de salida es:

- `0`: preflight aprobado;
- `2`: preflight rechazado;
- `1`: error operativo al abrir/evaluar la base.

Esto permite incorporar el preflight a una checklist o pipeline sin confundir
un rechazo controlado con un fallo técnico.
