# Motor de Pagos V3-C — Exposición adicional de capital

## Objetivo

V3-C separa una cuestión que no debe resolverse con `capital pendiente × tasa` sin contexto: el interés adicional atribuible al capital que permanece por encima de la exposición contractual esperada.

El motor compara dos trayectorias temporales:

- capital programado según el cronograma contractual;
- capital real pendiente después de los hechos ya materializados.

Sólo el exceso positivo de capital genera interés adicional.

## Regla

Para cada tramo `[t0, t1)`:

```text
exceso_capital = capital_real - capital_programado

si exceso_capital > 0:
    interés_adicional = devengar(exceso_capital, t0, t1, política)
si exceso_capital <= 0:
    interés_adicional = 0
```

Una exposición real inferior a la programada no se interpreta aquí como prepago. La decisión de prepago y su efecto sobre el cronograma pertenece a otro caso de uso.

## Temporalidad

Los puntos son efectivos desde su fecha inclusive hasta el siguiente punto. Los cambios de capital real por pagos deben llegar al motor como puntos explícitos de la trayectoria real.

Esto permite representar, por ejemplo:

```text
01/09 ─────────────── 16/09 ─────────────── 01/10
   exceso $20.000          exceso $10.000
```

El primer tramo y el segundo tienen su propio devengamiento y referencia.

## Integración con la amortización existente

`puntos_programados_desde_tabla()` adapta la tabla existente del proyecto usando:

- `fecha_inicio` + `capital_inicial` como punto inicial;
- `vencimiento` + `saldo` como capital programado posterior a cada cuota.

No recalcula una segunda tabla de amortización.

## Lo que V3-C NO hace

- no registra pagos;
- no modifica cuotas;
- no aplica waterfall;
- no capitaliza intereses impagos;
- no decide RAI/RNI;
- no persiste devengamientos;
- no determina por sí mismo cómo una aplicación de pago cambia el capital real.

## Próxima integración

V3-D deberá construir la trayectoria real de capital a partir del estado materializado y de las aplicaciones de pagos, y luego alimentar V3-C. Sólo después de esa conciliación debe calcularse el interés adicional que corresponde al período.
