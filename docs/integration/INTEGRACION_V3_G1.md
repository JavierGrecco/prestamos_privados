# Integración V3-G1

G1 depende de haber instalado V3-F3.1.

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_G1.zip \
  -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
```

Validación específica:

```bash
python -m compileall -q dominio infraestructura tests
python -m pytest -q \
  tests/test_migracion_v010.py \
  tests/test_devengamientos_repo_v3.py \
  tests/test_politica_devengamiento_v3.py
python -m pytest -q
```

Con 243 tests después de F3.1, G1 agrega 20 tests nuevos (4 en el test de
migraciones, 1 de v010, 8 del repositorio y 7 de la política pura), por lo que
la suite esperada queda en **263 passed**.

G1 sigue siendo una etapa paralela y no reemplaza el registrador legacy ni
activa automáticamente devengamientos durante un pago.
