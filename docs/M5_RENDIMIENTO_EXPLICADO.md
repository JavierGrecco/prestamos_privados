# M5 — Rendimiento explicado

## Propósito

M5 convierte las métricas de rendimiento que ya existen en una explicación
humana.

La aplicación no crea una segunda fórmula: reutiliza XIRR, rendimiento real y
XIRR USD calculados por el análisis financiero.

## Qué significa para cada rol

### Inversor

**Rendimiento anualizado**
Es la tasa anualizada que relaciona el dinero que aportaste con los cobros
reales registrados y sus fechas.

### Deudor

**Costo anualizado**
Es la tasa anualizada que relaciona el dinero recibido con los pagos reales
registrados y sus fechas.

## Cuándo aparece una tasa

La tasa se muestra solamente cuando existen flujos reales con ambos signos:

- dinero que salió;
- dinero que entró.

Si todavía no hay suficiente evidencia, la aplicación dice que la tasa no está
disponible. No intenta completarla con proyecciones.

Esto es deliberado: una tasa incompleta puede parecer precisa aunque no lo sea.

## Rendimiento ajustado por inflación

Se muestra separado del rendimiento anualizado nominal.

El usuario elige un supuesto de inflación mensual y el sistema reutiliza el
cálculo existente para expresar el rendimiento en términos de poder de compra.

El supuesto siempre queda visible.

## USD

XIRR USD solo aparece cuando existe una referencia USD suficiente para los
flujos reales.

Si falta esa evidencia, la aplicación no inventa un tipo de cambio.

## Histórico vs futuro

Esta pantalla usa movimientos reales hasta la fecha de corte.

Los movimientos futuros se analizan en **Escenarios**.

Por lo tanto:

`Rendimiento` = lo que muestran los hechos registrados.

`Escenarios` = lo que podría ocurrir bajo determinados supuestos.

## Qué no significa

- una tasa histórica no garantiza el futuro;
- una tasa no disponible no significa que la operación haya salido mal;
- una tasa no es una recomendación automática;
- una métrica no incluye dinero o hechos que la aplicación desconozca.

## Arquitectura

- `dominio/xirr.py` — cálculo XIRR;
- `aplicacion/consultas/analisis_financiero.py` — read model financiero existente;
- `aplicacion/consultas/rendimiento_financiero_persona.py` — contexto y
  disponibilidad del indicador;
- `ui/pagina_rendimiento.py` — experiencia humana;
- `tests/test_rendimiento_financiero_persona.py` — regresiones;
- `tests/test_ui_e2e.py` — aceptación de pantalla.

## Principio

> Una tasa no debe aparecer sola. Tiene que venir con significado, período y
> evidencia suficiente.

## Próxima evolución

Con M5 el proyecto puede avanzar hacia comparaciones de decisión: combinar
posición, planificación, escenarios y rendimiento sin mezclar hechos con
proyecciones.