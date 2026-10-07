# Integración V3-G3

G3 depende de V3-F3.1 + G1 + G2.

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_G3.zip \
  -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
```

Validar:

```bash
python -m compileall -q aplicacion infraestructura dominio tests
python -m pytest -q tests/test_registro_pago_v3_devengamientos_sqlite.py
python -m pytest -q
```

G3 agrega **6 tests**. Partiendo de los 268 esperados después de G2, la suite
esperada queda en **274 passed**.
