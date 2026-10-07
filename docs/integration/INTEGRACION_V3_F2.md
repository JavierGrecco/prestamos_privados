# Integración V3-F.2

Instalar como overlay desde la raíz del repositorio:

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_F2.zip -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
python -m compileall -q aplicacion/servicios tests
python -m pytest -q tests/test_registro_pago_v3.py
python -m pytest -q
```

Esperado para la prueba nueva: **8 passed**.

La suite completa debería pasar sin cambios funcionales sobre el servicio
legacy. F.2 es una frontera paralela y no reemplaza `registrar_pago()`.
