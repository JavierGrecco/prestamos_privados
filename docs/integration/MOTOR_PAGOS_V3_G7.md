# Motor de Pagos V3 — G7

Instalar después de G6 (o usar el bundle acumulativo F3.1→G7).

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_G7.zip -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
python -m compileall -q infraestructura/consultas aplicacion/consultas tests
python -m pytest -q tests/test_pagos_v3_read_model.py tests/test_pago_one_shot_v3.py
```

Esperado: `12 passed`.
