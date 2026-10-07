# Integración V3-B corregida

V3-B es incremental sobre V3-A corregida.

Después de tener V3-A verde:

```bash
git apply --check ~/Downloads/MOTOR_PAGOS_V3_B_CORREGIDO.patch
git apply ~/Downloads/MOTOR_PAGOS_V3_B_CORREGIDO.patch
python -m compileall -q dominio tests
python -m pytest -q tests/test_motor_pagos_v3.py tests/test_devengamiento_v3.py
python -m pytest -q
```

No conectar todavía `registrar_pago()`. Este release agrega únicamente el cálculo puro de devengamientos.
