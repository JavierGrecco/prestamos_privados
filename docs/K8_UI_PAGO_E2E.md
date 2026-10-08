# K8 — Registro de pago end-to-end desde la UI

K8 verifica la primera operación financiera completa iniciada por el usuario
desde Streamlit.

## Recorrido

La aceptación automatizada realiza:

```text
Préstamos
   ↓
Ver detalle
   ↓
Registrar pago
   ↓
Preview
   ↓
Confirmar pago
   ↓
ServicioRegistroPagoUI
   ↓
SOMBRA
   ├─ Legacy registra efectivamente
   └─ V3 calcula sobre snapshot previo
   ↓
SQLite
   ├─ pagos
   ├─ imputaciones
   ├─ cuotas
   ├─ ledger
   ├─ auditoría
   └─ evidencia SOMBRA
```

La UI no escribe SQLite directamente.

## Evidencia

Después de confirmar, la prueba verifica:

- pago persistido;
- monto conservado en imputaciones;
- versión efectiva Legacy durante SOMBRA;
- plan y hash persistidos;
- movimientos de ledger;
- auditoría;
- ejecución SOMBRA;
- observación adicional solo cuando corresponde por divergencia/error.

## Preview Legacy

La pantalla ya no reconstruye el waterfall parcial con `min()` ni utiliza una
tasa fija en el código de presentación.

Cuando el modo efectivo es Legacy, utiliza
`ServicioPagosConSimulacion.simular_pago()` y presenta el resultado devuelto
por la capa de aplicación/dominio.

Cuando el modo es SOMBRA o V3, continúa utilizando el preview canónico de V3.

## Estado de preflight

K8 no reduce el umbral real del preflight. El modo de prueba elegido es SOMBRA:

- Legacy continúa siendo efectivo;
- V3 se ejecuta como cálculo sombra;
- la evidencia queda registrada;
- una divergencia no convierte la operación en V3 efectiva.

## Pruebas

La prueba específica es:

```bash
python -m pytest -q tests/test_k8_ui_pago_e2e.py
```

La suite completa:

```bash
python -m pytest -q
```

Compilación:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
```

## Criterio de cierre

K8 queda cerrado cuando la aceptación pasa en CI sobre Python 3.11–3.14 y no
existen cálculos financieros de negocio duplicados dentro de la pantalla de
registro.

## Límites

K8 no realiza cut-over a V3. Tampoco sustituye autenticación, autorización,
pruebas de navegador, carga, monitoreo externo o un despliegue productivo.
