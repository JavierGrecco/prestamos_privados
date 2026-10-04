# Lógica de pagos

## Principio central

**El interés es el precio por usar el capital. Si el capital se
devuelve, deja de generar interés. Si sigue prestado, sigue
generando interés.**

Toda decisión del deudor se rige por este principio. El sistema
lo aplica consistentemente y lo hace visible.

## Las 3 acciones del deudor

### Acción 1 — Pago parcial de la cuota

El deudor paga menos que el total del mes.

**Qué pasa:**
- El faltante queda pendiente.
- Ese faltante se suma al mes siguiente.
- Se cobra un interés extra por el capital que sigue pendiente.
- **No se capitaliza** (no hay interés sobre interés).

**Ejemplo:**
- Cuota del mes: $124.487,13
- Pago recibido: $80.000,00
- Faltante: $44.487,13
- Interés extra del mes próximo: $44.487,13 × 2,5% = $1.112,18
- **Total a pagar el mes próximo:**
  $97.487,13 (cuota) + $44.487,13 (faltante) + $1.112,18 (extra)
  = **$143.086,44**

**Cuándo se ofrece:**
- Siempre. El deudor puede bajar el monto cuando quiera.

**Mensaje al usuario:**
> "Si pagás menos, el mes que viene te va a costar $18.599,31 más.
> Ese extra es el interés del capital que sigue en tu poder."

### Acción 2 — Adelanto de capital con reducción de cuota (RAI)

El deudor paga más que la cuota. El excedente va directo a capital.
Las próximas cuotas bajan de monto.

**Qué pasa:**
- El capital pendiente baja.
- Se recalcula la tabla con el nuevo saldo y el mismo plazo.
- Las cuotas futuras son más bajas.
- El plazo se mantiene igual.

**Ejemplo:**
- Cuota del mes: $124.487,13
- Pago recibido: $200.000,00
- Excedente: $75.512,87
- Capital pendiente antes: $853.213,56
- Capital pendiente después: $777.700,69
- Se recalculan 9 cuotas con el nuevo saldo
- Cuota nueva ≈ $91.900,00 (baja $5.587,13 por mes)

**Cuándo se ofrece:**
- Solo cuando el pago supera el total del mes.

**Mensaje al usuario:**
> "Vas a pagar cuotas más bajas los próximos meses. El plazo
> se mantiene igual."

### Acción 3 — Adelanto de capital con reducción de plazo (RNI)

El deudor paga más que la cuota. El excedente va directo a capital.
La cuota se mantiene y el plazo se acorta.

**Qué pasa:**
- El capital pendiente baja.
- Se recalcula la tabla manteniendo la cuota original.
- El préstamo termina antes.
- Se ahorran más intereses que con RAI.

**Ejemplo:**
- Cuota del mes: $124.487,13
- Pago recibido: $200.000,00
- Excedente: $75.512,87
- Capital pendiente antes: $853.213,56
- Capital pendiente después: $777.700,69
- Cuota se mantiene: $97.487,13
- Cuotas restantes antes: 9
- Cuotas restantes después: 8
- **Ahorro en intereses: $21.465,88**

**Cuándo se ofrece:**
- Solo cuando el pago supera el total del mes.

**Mensaje al usuario:**
> "Vas a terminar de pagar 1 mes antes. Ahorrás $21.465,88 en
> intereses."

## Detección automática del estado del deudor

El sistema detecta si el deudor viene al día o arrastrando:

- **Al día:** todas las cuotas anteriores están PAGADAS. La cuota
  objetivo es la primera PENDIENTE sin remanentes.
- **Arrastrando:** hay cuotas anteriores en estado PARCIAL con
  remanentes. El mensaje se adapta para mostrar el arrastre.

El mensaje cambia según el caso:

**Al día:**
> "Este mes te toca pagar $97.487,13. Si querés, podés pagar un
> poco más y adelantar capital. Vas a ahorrar intereses."

**Arrastrando:**
> "Este mes te toca pagar $124.487,13. Incluye $27.000,00 que
> quedaron pendientes del mes pasado más $1.175,00 de interés
> extra por ese capital."

## Estructura de las 3 pantallas

### Pantalla 1 — Selección de acción
- Muestra la cuota del mes con su desglose.
- Campo de monto editable.
- 3 opciones:
  - Pagar la cuota completa
  - Pagar una parte
  - Pagar de más y adelantar capital
- Cada opción tiene un botón "Ver ejemplo" con modal explicativo.

### Pantalla 2 — Vista previa del impacto
- Se adapta según la acción elegida.
- Para pago parcial: muestra el faltante, el interés extra, y el
  total del próximo mes.
- Para adelanto: muestra RAI vs RNI lado a lado, con el usuario
  eligiendo cuál prefiere.
- Botón "Ver tabla completa" con las cuotas restantes recalculadas.
- Los valores originales aparecen tachados al lado de los nuevos.

### Pantalla 3 — Confirmación
- Resumen de lo que se hizo.
- Los números clave: ahorro, meses ahorrados, capital adelantado.
- Vuelve al detalle del préstamo con la nota de éxito.

## Modelo de datos

### Columnas nuevas en `pagos`

| Campo | Qué guarda |
|-------|------------|
| `tipo_pago` | `CUOTA`, `PARCIAL`, `ADELANTO_RAI`, `ADELANTO_RNI` |
| `monto_a_capital` | Cuánto del excedente fue a capital |
| `intereses_ahorrados` | Cuánto se ahorró con el adelanto |
| `cuotas_restantes_antes` | Cuántas cuotas quedaban antes |
| `cuotas_restantes_despues` | Cuántas cuotas quedan después |
| `opcion_adelanto` | `RAI`, `RNI`, o NULL si no hubo adelanto |

### Tabla nueva `historial_recalculos`

| Campo | Qué guarda |
|-------|------------|
| `id` | ID |
| `prestamo_id` | Préstamo afectado |
| `pago_id` | Pago que lo disparó |
| `tipo` | `RAI` o `RNI` |
| `fecha` | Cuándo |
| `capital_antes` | Capital pendiente antes |
| `capital_despues` | Capital pendiente después |
| `cuotas_antes` | Cuántas cuotas quedaban |
| `cuotas_despues` | Cuántas cuotas quedan |
| `intereses_antes` | Intereses proyectados antes |
| `intereses_despues` | Intereses proyectados después |
| `detalle_json` | La tabla recalculada completa |

## Vista consolidada del detalle del préstamo

Sección "Estado del préstamo" con:

- Capital original, amortizado, pendiente.
- Interés total, cobrado, pendiente.
- Mora acumulada, cuotas con atraso.
- Adelantos realizados, capital adelantado, intereses ahorrados.
- Total pagado, total proyectado, deuda actual.
- Costo financiero total.

## Reglas de ayuda contextual

Cada opción y cada campo tiene un botón "Ver explicación" que
abre un modal con:

1. Qué hace la acción.
2. Un ejemplo con los números reales del usuario.
3. La diferencia con las otras opciones.

El objetivo: que el deudor tome una decisión informada sin
necesitar conocimientos financieros.

## Lo que NO se hace (por ahora)

- **Capitalización de intereses** (interés sobre interés). Prohibido
  por el art. 770 del CCyC sin pacto expreso.
- **Pago anticipado con descuento de interés** para cuotas futuras
  que aún no vencieron. Queda para una fase posterior.