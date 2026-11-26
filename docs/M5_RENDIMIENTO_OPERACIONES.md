# M5 — Rendimiento y costo efectivo por operación

## Objetivo

La pantalla **Rendimiento** presenta el resultado de cada préstamo por separado y
desde el rol que ocupa la persona en esa operación:

- **Inversor:** rendimiento efectivo anual sobre sus aportes y cobros reales.
- **Deudor:** costo efectivo anual sobre el desembolso recibido y sus pagos reales.

Una persona puede participar en distintos préstamos y con roles diferentes. Cada
combinación préstamo/rol se analiza de forma independiente. Nunca se mezclan los
flujos de dos préstamos en una misma XIRR.

## Qué muestra cada operación

La vista identifica número y destino del préstamo, rol, tasa efectiva ARS,
resultado real anual, tasa USD, cantidad de movimientos, período y estado de la
evidencia. El detalle presenta cada movimiento con fecha, tipo, sentido, importe
ARS e importe USD cuando existe una referencia suficiente.

La tasa no aparece como una conclusión confiable si los flujos no contienen
entradas y salidas reales con fechas suficientes, si los netos por fecha se
compensan o si la XIRR no tiene una solución única dentro del rango admitido.
El motivo queda visible en lugar de mostrar cero o una tasa aproximada.

## Reglas de cálculo

- Se reutiliza `dominio/xirr.py`; no se implementa una segunda fórmula.
- Los movimientos de una misma fecha se compensan antes de resolver la XIRR.
- Si los flujos netos alternan de signo más de una vez, la tasa se considera
  ambigua y no se informa.
- El resultado real aplica la inflación mensual supuesta, compuesta a un año,
  mediante `calcular_rendimiento_real`.
- La tasa USD se calcula únicamente si **todos** los movimientos reales de esa
  operación tienen un importe USD explícito o una referencia de conversión válida.
  No se completa un movimiento faltante con una cotización inventada.
- La fecha de corte se comparte entre operaciones. Los pagos posteriores no
  participan en el análisis.

## Operaciones cerradas

El análisis financiero general conserva su comportamiento por defecto: los
saldos vigentes y las proyecciones se construyen con préstamos `ACTIVO` y
`EN_MORA`.

M5 solicita explícitamente un modo histórico de solo lectura que incorpora
flujos reales de préstamos `FINALIZADO`, `CANCELADO` y `REFINANCIADO`, además
de los que siguen abiertos. Estos flujos cerrados sirven para medir el resultado
histórico, pero **no** se suman al capital pendiente ni a las proyecciones.
Los estados `BORRADOR` y `ANULADO` no se presentan como operaciones con
rendimiento efectivo.

Los cobros de inversor sin correlación verificable con un pago/préstamo no se
asignan artificialmente a una operación. Se conservan como advertencia del
análisis, fuera de las tasas por préstamo.

## Qué no hace

- no pronostica pagos ni rendimiento futuro;
- no modifica préstamos, tasas, cuotas, pagos, ledger ni auditoría;
- no recalcula amortizaciones;
- no combina inversiones y deudas de una persona en una tasa única;
- no infiere cotizaciones USD faltantes;
- no convierte una tasa en recomendación automática;
- no afirma que un dato financiero exista si no está registrado.

## Arquitectura

- `aplicacion/consultas/analisis_financiero.py`: construye los flujos reales y
  mantiene separados saldo vigente, proyecciones y modo histórico opcional;
- `aplicacion/consultas/resultados_operaciones_persona.py`: agrupa por préstamo
  y rol y calcula métricas reutilizando dominio;
- `aplicacion/puertos/analisis_financiero.py`: contrato de lectura, incluido
  el destino de la operación;
- `infraestructura/consultas/analisis_financiero.py`: adaptación SQLite;
- `infraestructura/composicion/analisis_financiero.py`: punto único de
  composición del servicio;
- `ui/pagina_rendimiento.py`: tabla, detalle y evidencia por operación.

El read model de aplicación no importa SQLite, repositorios ni infraestructura.
La pantalla no construye repositorios ni ejecuta SQL. No se agrega ninguna
migración ni tabla nueva.

## Pruebas de aceptación

- dos inversiones de una misma persona producen dos resultados independientes;
- el rol deudor obtiene el costo del desembolso y los pagos reales;
- una operación finalizada conserva su historial sin reaparecer en el saldo actual;
- un flujo sin conversión impide una XIRR USD parcial;
- la fecha de corte excluye movimientos posteriores;
- persona inexistente e inflación no válida se rechazan;
- read model y UI mantienen los límites arquitectónicos;
- la pantalla se recorre mediante Streamlit AppTest;
- la matriz CI debe aprobar Python 3.11–3.14, CodeQL y auditoría de dependencias.

## Principio

> Una tasa pertenece a una operación concreta, a un rol concreto y a una
> evidencia concreta. Si alguno de esos vínculos no está demostrado, no se
> muestra una conclusión financiera.
