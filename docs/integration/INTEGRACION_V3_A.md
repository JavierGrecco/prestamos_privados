# Integración V3-A corregida

Usá este paquete en lugar del V3-A anterior.

Desde la raíz de `prestamos_privados_limpio`:

```bash
git status --short
git branch --show-current
git diff --exit-code
```

Si el working tree está limpio y estás en `mejoras-financieras`:

```bash
git apply --check ~/Downloads/MOTOR_PAGOS_V3_A_CORREGIDO.patch
git apply ~/Downloads/MOTOR_PAGOS_V3_A_CORREGIDO.patch
python -m compileall -q dominio tests
python -m pytest -q tests/test_motor_pagos_v3.py
python -m pytest -q
```

Alternativa: copiar los tres archivos del ZIP sobre la raíz del repositorio.
