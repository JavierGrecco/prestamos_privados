# J3 — Consolidación de APIs de registro y monto distribuible

J3 reduce una divergencia semántica entre las rutas completas de registro V3.

## Hallazgo

Había dos expresiones distintas para distribuir el cobro entre inversores:

- `RegistrarPagoV3Completo` utilizaba `plan.monto_aplicado`;
- `RegistrarPagoV3CompletoConAdelantos` utilizaba `command.monto`.

En un pago ordinario ambos valores coinciden.

En un pago con RAI/RNI no coinciden, porque el plan distingue entre:

```text
monto aplicado a obligaciones
+
excedente recibido
=
monto total recibido
```

El excedente tratado como adelanto forma parte del cobro recibido y debe participar
en la distribución a inversores.

## Decisión

Las dos rutas utilizan ahora:

```python
plan.monto_pago_recibido
```

El plan V3 ya valida la conservación:

```text
monto aplicado + excedente = monto recibido
```

Esto evita duplicar la regla en cada caso de uso.

## Evidencia

La suite cubre:

- distribución ordinaria;
- distribución con RAI/RNI;
- idempotencia;
- rollback;
- conservación de imputaciones.

Además, `tests/test_j3_distribucion_monto.py` protege estructuralmente que
las dos rutas completas no vuelvan a divergir en la fuente del monto.

## Alcance

J3 no elimina todavía fachadas de registro ni retira Legacy.

La siguiente consolidación deberá construir una matriz de consumidores reales y
retirar componentes solo cuando exista una API de reemplazo y regresiones
equivalentes.
