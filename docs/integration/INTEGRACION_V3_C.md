# Integración Motor Pagos V3-C

## Aplicación

Copiar solamente:

```text
dominio/exposicion_capital_v3.py
tests/test_exposicion_capital_v3.py
docs/MOTOR_PAGOS_V3_C.md
```

No reemplazar `motor_pagos_v3.py` ni `devengamiento_v3.py`.

## Comprobación

```bash
python -m compileall -q dominio tests
python -m pytest -q tests/test_exposicion_capital_v3.py
python -m pytest -q
```

El primer comando verifica sintaxis. El segundo valida V3-C en aislamiento. El tercero garantiza que no se haya introducido una regresión.

## Importante

V3-C todavía NO debe conectarse a `registrar_pago()`.

Primero hay que completar V3-D: construir la trayectoria real del capital y demostrar con casos de regresión que el interés adicional coincide con la diferencia de exposición contractual, sin doble reconocimiento del interés contractual ya previsto por el cronograma.
