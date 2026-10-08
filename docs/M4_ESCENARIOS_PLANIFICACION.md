# M4 — Escenarios de inflación y devaluación

## Propósito

M4 permite comparar los mismos flujos futuros bajo distintos supuestos macro.

El escenario no cambia las cuotas ni modifica el préstamo. Solo cambia la
forma de expresar económicamente los flujos ya proyectados.

## Escenarios disponibles

- **Optimista** — supuestos moderados de inflación y devaluación.
- **Base** — referencia central para comparar.
- **Pesimista** — mayor inflación y devaluación.
- **Crisis** — stress test extremo.
- **Personalizado** — supuestos definidos por la persona.

Los escenarios predefinidos son referencias de comparación, no pronósticos.

## Qué cambia y qué no

### No cambia

- capital original;
- cantidad de cuotas;
- monto nominal de las cuotas;
- reglas del contrato;
- datos persistidos;
- resultado nominal de los mismos flujos.

### Sí cambia

- valor de los flujos a precios de hoy bajo una inflación supuesta;
- equivalente USD bajo un tipo de cambio inicial y una devaluación supuesta.

## Valor real

Para cada flujo futuro se descuenta la inflación compuesta por la cantidad de
meses hasta su fecha.

El resultado se expresa como un valor aproximado en pesos de hoy según el
supuesto elegido.

## Equivalente USD

Cuando existe un tipo de cambio inicial de referencia:

1. se toma ese tipo de cambio como punto de partida;
2. se aplica la devaluación mensual supuesta;
3. cada flujo futuro se expresa en USD de escenario.

Cuando no existe una referencia válida, la aplicación no inventa una cifra USD
y muestra esa información como no disponible.

## Tipo de cambio de referencia

El sistema puede usar el último tipo de cambio conocido en los flujos reales
de la persona. También puede recibir un valor explícito.

Este número es solo una referencia del escenario. No significa que sea el
tipo de cambio futuro real.

## Principio de producto

> **Un escenario es una pregunta, no una predicción.**

La interfaz debe mostrar los supuestos junto con el resultado y dejar claro
que un escenario no garantiza que la realidad vaya a comportarse así.

## Arquitectura

- `dominio/escenarios.py` — factor compuesto reutilizable y escenarios base;
- `aplicacion/consultas/escenarios_persona.py` — aplica escenarios sobre
  flujos proyectados existentes;
- `ui/pagina_escenarios.py` — presentación y lenguaje humano;
- `tests/test_escenarios_persona.py` — regresiones del comportamiento;
- `tests/test_ui_e2e.py` — aceptación de la nueva pantalla.

El read model de M4 no recalcula amortizaciones y no escribe datos.

## Próxima evolución

M5 puede comparar escenarios con la posición financiera y la planificación
completa, incorporando sensibilidad y decisiones comparables sin convertir las
proyecciones en certezas.