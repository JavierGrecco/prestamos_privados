# Integración V3-G2

G2 depende de V3-F3.1 + G1 instalados.

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_G2.zip \
  -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
```

Validar:

```bash
python -m compileall -q aplicacion dominio tests
python -m pytest -q tests/test_plan_pago_v3_devengamientos.py
python -m pytest -q
```

G2 incorpora **5 tests**. Partiendo de los 263 esperados después de G1, la
suite esperada queda en **268 passed**.
