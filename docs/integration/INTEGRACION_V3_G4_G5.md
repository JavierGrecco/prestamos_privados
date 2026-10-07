# Integración V3 — G4 + G5

1. Instalar previamente F3.1, G1, G2 y G3.
2. Extraer este ZIP sobre la raíz del repositorio.
3. Compilar:

```bash
python -m compileall -q aplicacion/servicios dominio infraestructura tests
```

4. Ejecutar los tests específicos:

```bash
python -m pytest -q \
  tests/test_distribucion_pago_v3.py \
  tests/test_registro_pago_v3_completo.py \
  tests/test_estado_registro_pago_v3_horizonte.py \
  tests/test_adelanto_v3.py \
  tests/test_registro_pago_v3_adelantos_sqlite.py
```

Esperado: `25 passed`.

La ruta productiva legacy no se reemplaza en esta etapa.
