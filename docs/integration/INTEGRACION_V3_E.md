# Integración V3-E

Copiar preservando estas carpetas:

```text
aplicacion/servicios/simulacion_pagos_v3.py -> aplicacion/servicios/
tests/test_simulacion_pagos_v3.py            -> tests/
docs/MOTOR_PAGOS_V3_E.md                    -> docs/
INTEGRACION_V3_E.md                          -> raíz
```

No reemplazar `aplicacion/servicios/__init__.py`, `pagos.py` ni `pagos_simulacion.py` todavía.

Validación:

```bash
python -m compileall -q dominio aplicacion tests
python -m pytest -q tests/test_simulacion_pagos_v3.py
python -m pytest -q
```

La incorporación es deliberadamente paralela. Si todo queda verde, el próximo cambio puede introducir una comparación `simulación V2 vs simulación V3` sobre escenarios de caracterización, sin modificar todavía el registro.
