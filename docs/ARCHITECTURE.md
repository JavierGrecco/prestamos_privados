# Arquitectura

## Objetivo

Mantener una separación clara entre las reglas financieras, los casos de uso, la persistencia y la presentación.

## Capas

### Dominio

El dominio no debería conocer Streamlit ni SQLite.

Responsabilidades actuales principales:

- tablas de amortización existentes;
- imputación;
- mora;
- cálculo de devengamientos;
- planificación de pagos V3;
- exposición y trayectoria de capital;
- adelantos;
- distribución a inversores.

La autoridad de cálculo debe ser determinista y trabajar con `Decimal`.

### Aplicación

La aplicación transforma una intención del usuario en una operación de negocio.

En V3 existe una separación deliberada entre:

```text
Command
  ↓
lectura de estado
  ↓
plan financiero
  ↓
persistencia transaccional
```

El registro V3 incorpora idempotencia, revisión del préstamo y control transaccional.

### Infraestructura

SQLite, migraciones, repositorios, ledger, auditoría y read models viven aquí.

La infraestructura no debería decidir qué resultado financiero corresponde; debería persistir el resultado que la aplicación y el dominio ya determinaron.

### UI

Streamlit presenta información y captura acciones.

Las reglas financieras no deben duplicarse en esta capa.

## Persistencia financiera

El proyecto combina:

- **hechos e historial**, que deben conservar trazabilidad;
- **estado materializado**, para operar y consultar rápidamente.

El ledger es tratado como información inmutable: las correcciones financieras deben representarse mediante operaciones compensatorias o correctivas, no reescribiendo historia.

## Pago V3

El flujo conceptual es:

```text
RegistrarPagoCommand
        ↓
BEGIN
        ↓
idempotencia
        ↓
releer préstamo y revisión
        ↓
construir snapshot
        ↓
calcular PlanPago
        ↓
validar invariantes
        ↓
persistir pago + imputaciones
        ↓
actualizar cuotas
        ↓
devengamientos / adelanto / distribución
        ↓
ledger + auditoría
        ↓
COMMIT
```

Ante cualquier excepción, la operación debe terminar en rollback.

## Estado transicional

El código actual conserva el servicio legacy junto con V3. Esta convivencia es intencional.

Hay varias fachadas intermedias creadas durante la migración, entre ellas:

- `registro_pago_v3.py`
- `registro_pago_v3_completo.py`
- `registro_pago_v3_completo_adelantos.py`
- `registro_pago_v3_devengamientos.py`
- `puente_motor_pago_v3.py`
- `fabrica_registro_pago_v3.py`

También existen conceptos de plan de pago en más de un módulo.

No se deben eliminar todavía. Primero se necesita una comparación Legacy vs V3 que demuestre qué piezas son realmente necesarias y cuál debe ser la única API estable.

## Regla de diseño

Una misma regla financiera importante no debería tener dos implementaciones independientes.

El objetivo final es:

```text
1 autoridad de cálculo
        ↓
múltiples adaptadores de aplicación/persistencia
        ↓
múltiples formas de lectura
```

y no:

```text
registro → cálculo A
simulación → cálculo B
UI → cálculo C
```
