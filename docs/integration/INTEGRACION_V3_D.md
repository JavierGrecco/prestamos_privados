# Integración V3-D

## Archivos

Copiar:

```text
dominio/trayectoria_capital_v3.py
        -> dominio/

tests/test_trayectoria_capital_v3.py
        -> tests/

docs/MOTOR_PAGOS_V3_D.md
        -> docs/
```

No reemplazar en esta fase:

```text
dominio/motor_pagos_v3.py
dominio/devengamiento_v3.py
dominio/exposicion_capital_v3.py
aplicacion/servicios/pagos.py
```

## Validación

```bash
python -m compileall -q dominio tests
python -m pytest -q tests/test_motor_pagos_v3.py tests/test_devengamiento_v3.py tests/test_exposicion_capital_v3.py tests/test_trayectoria_capital_v3.py
python -m pytest -q
```

El registro real de pagos permanece sin cambios. Esta fase sólo agrega el puente puro entre las aplicaciones de capital de un `PlanPago` y la trayectoria temporal de capital real.
