# Motor de Pagos V3-B — Devengamientos

V3-B agrega el cálculo puro y reproducible de intereses por período.

## Alcance

Incluye `PoliticaInteres`, `calcular_devengamiento_interes`, conteo de días y fracción anual para las convenciones existentes:

- `MENSUAL`: meses completos; mismo día o ambos cierres de mes.
- `ACTUAL_365`: días reales / 365.
- `ACTUAL_360`: días reales / 360.
- `TREINTA_360`: implementación explícita 30E/360.
- `ACTUAL_ACTUAL`: fracción por cada año calendario, respetando bisiestos.

`TNA` se aplica linealmente sobre la fracción anual. `TEA` se transforma mediante `(1 + TEA) ** fracción_anual - 1`.

## Límite deliberado

V3-B no decide todavía qué parte del interés corresponde a `INTERES_CONTRACTUAL`, `INTERES_ADICIONAL` o `MORA`, ni determina cuál es la base económicamente correcta para un préstamo francés atrasado. Eso será una capa de política del crédito, no una consecuencia automática del simple paso del tiempo.

## Integración

Aplicar sobre V3-A y ejecutar:

```bash
python -m compileall -q dominio tests
python -m pytest -q tests/test_motor_pagos_v3.py tests/test_devengamiento_v3.py
python -m pytest -q
```
