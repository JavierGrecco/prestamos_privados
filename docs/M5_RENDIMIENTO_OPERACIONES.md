# M5 — Rendimiento y costo efectivo por operación

## Propósito

M5 convierte las métricas XIRR y rendimiento real del núcleo financiero en una
lectura que una persona pueda entender por operación.

## Regla principal

Una tasa solo se muestra cuando los movimientos reales registrados permiten
calcularla.

Cuando no hay evidencia suficiente, la aplicación muestra que todavía no hay
una conclusión disponible y explica el motivo.

## Qué significa

### Para una inversión

- **Rendimiento efectivo**: XIRR anual sobre los movimientos reales de esa inversión.
- **Resultado real anual**: rendimiento efectivo ajustado por la inflación mensual
  supuesta en la pantalla.
- **Tasa efectiva USD**: XIRR sobre los mismos movimientos cuando todos tienen
  conversión USD disponible.

### Para una deuda

- **Costo efectivo**: XIRR anual calculado desde el punto de vista del deudor.
- **Costo real anual**: costo efectivo ajustado por la inflación supuesta.
- **Tasa efectiva USD**: disponible solo cuando toda la evidencia real tiene
  conversión USD.

## Evidencia

La pantalla muestra los movimientos reales que sustentan la tasa:

- fecha;
- movimiento;
- sentido;
- monto ARS;
- monto USD cuando existe;
- naturaleza real.

Esto evita presentar una tasa como una cifra aislada.

## Qué no hace

- no pronostica rentabilidad futura;
- no extrapola XIRR;
- no inventa movimientos faltantes;
- no modifica contratos;
- no recalcula amortizaciones;
- no convierte una tasa en una recomendación automática.

## Inflación

El resultado real usa el supuesto de inflación mensual elegido en la pantalla,
llevado a una inflación anual compuesta para aplicar la relación de Fisher que ya
existe en el dominio.

Cambiar este supuesto cambia solamente la forma de interpretar el resultado,
no los movimientos ni el contrato.

## USD

La tasa USD se muestra solamente cuando todos los movimientos reales de la
operación tienen conversión USD.

Esto evita una conclusión basada en una serie incompleta.

## Arquitectura

- `aplicacion/consultas/resultados_operaciones_persona.py` — read model;
- `ui/pagina_rendimiento.py` — experiencia humana;
- `dominio/xirr.py` — cálculo XIRR existente;
- `dominio/analisis_cambiario.py` — rendimiento real existente;
- `tests/test_resultados_operaciones_persona.py` — regresiones;
- `tests/test_ui_e2e.py` — aceptación de la pantalla.

El nuevo read model es de solo lectura y reutiliza los cálculos existentes.

## Principio de producto

> Si la evidencia no alcanza, el sistema debe decirlo.

Mostrar menos información es preferible a mostrar una conclusión financiera
aparentemente precisa pero mal sustentada.
