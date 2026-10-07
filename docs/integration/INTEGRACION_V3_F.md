# Integración V3-F.1

El ZIP ya trae las carpetas correctas. Descomprimir sobre la raíz del repositorio.

Archivos:

```text
aplicacion/comandos/__init__.py
aplicacion/comandos/registrar_pago_v3.py
tests/test_registrar_pago_command_v3.py
docs/MOTOR_PAGOS_V3_F.md
```

No reemplaza `aplicacion/servicios/pagos.py`, `aplicacion/servicios/__init__.py` ni ningún archivo de infraestructura.

Validación:

```bash
python -m compileall -q aplicacion/comandos tests
python -m pytest -q tests/test_registrar_pago_command_v3.py
python -m pytest -q
```
