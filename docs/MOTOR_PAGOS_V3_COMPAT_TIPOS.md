# Compatibilidad V3 — `dominio/tipos.py`

El bundle F2→G7 presupone dos símbolos que no están presentes en la versión
base de `dominio/tipos.py` de algunas ramas:

- `ZERO = Decimal("0")`
- `TipoRecalculo` con `RAI` y `RNI`

La corrección es deliberadamente mínima: no reemplaza `dominio/tipos.py` y no
modifica las reglas existentes de dinero, tasas, amortización o imputación.
Solo agrega los símbolos ausentes.

Uso:

```bash
python scripts/corregir_tipos_v3_compat.py --root .
python -m compileall -q aplicacion dominio infraestructura tests
python -m pytest -q
```

El script es idempotente: una segunda ejecución no cambia el archivo.
