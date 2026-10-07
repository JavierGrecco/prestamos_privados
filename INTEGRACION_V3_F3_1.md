# Integración V3-F3.1

## Instalación

Desde el repositorio limpio:

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_F3_1.zip \
  -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio
```

## Validación

```bash
python -m compileall -q aplicacion infraestructura dominio tests
python -m pytest -q tests/test_migracion_v009.py tests/test_registro_pago_v3_sqlite.py
python -m pytest -q
```

Con el estado V3-F2 validado de 230 tests, esta etapa agrega 13 tests: la suite
esperada queda en **243 passed**.

## Uso controlado

El nuevo caso de uso se construye mediante:

```python
from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3

registrador = crear_registrador_pago_v3(db)
resultado = registrador.ejecutar(command)
```

No se modifica todavía `ServicioPagos.registrar_pago()` ni la navegación de
Streamlit. La integración con producción se hará después de lograr equivalencia
financiera con el flujo actual.

## Criterio de avance

No avanzar al reemplazo del servicio legacy solo porque los tests de
infraestructura estén verdes. Primero deben quedar resueltos:

1. devengamientos dinámicos persistibles y reproducibles;
2. mora e interés adicional sin doble cobro del interés contractual francés;
3. RAI/RNI y recalculación de cuotas;
4. distribución a inversores;
5. compensaciones/anulación;
6. pruebas de caracterización que demuestren equivalencia donde corresponda.
