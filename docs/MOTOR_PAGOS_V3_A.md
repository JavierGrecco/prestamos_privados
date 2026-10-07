# Motor de Pagos V3-A — Overlay

Núcleo puro y determinista del waterfall de pagos. No reemplaza los módulos existentes.

Validación:

```bash
python -m compileall -q dominio tests
python -m pytest -q tests/test_motor_pagos_v3.py
python -m pytest -q
```

No conectar todavía `registrar_pago()`, migraciones, RAI/RNI ni UI.
