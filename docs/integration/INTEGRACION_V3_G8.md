# Motor de Pagos V3 — G8: gate de integridad pre-cutover

## Objetivo

Agregar una auditoría global **solo lectura** antes de activar V3 como motor
productivo. El auditor verifica que las operaciones V3 ya persistidas puedan
reconciliarse sin modificar datos.

## Qué verifica

- migración V3 mínima disponible (v010);
- revisiones de préstamo no negativas;
- saldos de cuotas no negativos y cuotas PAGADA sin saldo;
- idempotency keys duplicadas;
- `plan_json` válido y `plan_hash` coincidente;
- suma de imputaciones igual al monto del pago;
- referencias de devengamientos existentes;
- ledger balanceado y sus movimientos principales conciliados;
- una única correlación contable por pago;
- correlación compartida con auditoría;
- devengamientos positivos, con períodos positivos y huellas sin duplicación.

## API

```python
from infraestructura.consultas.integridad_v3 import (
    auditar_integridad_v3,
    exigir_integridad_v3,
)

informe = auditar_integridad_v3(db)
print(informe.ok, informe.cantidad_incidencias)

# Para un gate estricto:
exigir_integridad_v3(db)
```

`db` debe ser la instancia `BaseDatos` ya utilizada por la aplicación.

## Seguridad

G8 no escribe en SQLite, no recalcula préstamos, no llama al registrador y no
modifica Streamlit. Una incidencia se informa; no se intenta auto-reparar.

## Instalación

Extraer este ZIP sobre la raíz del repositorio.

Luego:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
python -m pytest -q tests/test_registro_pago_v3_sqlite.py tests/test_integridad_v3.py
python -m pytest -q
```

Partiendo del estado actual observado de 320/321, esta versión corrige la
aserción restante y agrega 8 pruebas G8. El objetivo de la suite pasa a ser
**329/329 passed**.
