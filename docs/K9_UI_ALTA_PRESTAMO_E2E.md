# K9 — Alta de préstamo end-to-end desde la UI

K9 certifica el segundo flujo de negocio completo iniciado desde Streamlit:
crear un préstamo nuevo y dejarlo disponible para operar.

## Recorrido

```text
Préstamos
   ↓
+ Nuevo préstamo
   ↓
Formulario
   ├─ deudor
   ├─ capital
   ├─ plazo
   ├─ tasa/modalidad
   ├─ sistema
   ├─ convención
   └─ inversores
   ↓
Simulación
   ↓
Confirmar y guardar
   ↓
ServicioPrestamos.crear_completo()
   ↓
SQLite
   ├─ préstamo ACTIVO
   ├─ versión de tasa
   ├─ cuotas
   ├─ participaciones
   ├─ ledger
   └─ auditoría
```

## Frontera de responsabilidades

La UI no implementa las fórmulas de amortización ni el interés de período.

La simulación utiliza `ServicioSimulacionPrestamo`, que delega al dominio
financiero. La confirmación utiliza `ServicioPrestamos`, que mantiene la
transacción atómica del alta.

La pantalla conserva exclusivamente:

- interacción con el usuario;
- estado del formulario;
- presentación y formato;
- navegación.

## Evidencia verificada

La aceptación comprueba:

- el préstamo termina en estado `ACTIVO`;
- capital, plazo, sistema y destino coinciden;
- existe la versión inicial de tasa;
- la cantidad de cuotas coincide con el plazo;
- el inversor aporta exactamente el capital;
- la participación suma 100%;
- existe el desembolso en el ledger;
- existen las auditorías de creación y activación;
- la base supera el chequeo de integridad;
- el préstamo queda visible después de confirmar.

## Reglas importantes

No se permite confirmar sin inversores.

La suma de los aportes debe coincidir exactamente con el capital.

El alta no escribe SQL directamente desde Streamlit.

## Pruebas

Flujo end-to-end:

```bash
python -m pytest -q tests/test_k9_ui_alta_prestamo_e2e.py
```

Servicio de simulación:

```bash
python -m pytest -q tests/test_simulacion_prestamo.py
```

Suite completa:

```bash
python -m pytest -q
```

Compilación:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
```

## Estado

K9 se considera completo solo después de CI verde en Python 3.11–3.14.

Este trabajo no cambia la matemática financiera ni activa V3 como motor
efectivo.
