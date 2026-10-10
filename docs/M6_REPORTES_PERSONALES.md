# M6 — Reportes humanos y exportaciones

## Propósito

M6 permite sacar una foto reutilizable de la situación financiera de una
persona sin obligarla a entender la estructura interna de la aplicación.

El mismo reporte reúne:

- posición financiera;
- planificación futura;
- rendimiento histórico;
- escenarios.

## Fecha de corte

Todas las secciones usan la misma fecha de corte.

Esto evita que una parte del reporte esté calculada con una fecha y otra con
otra distinta.

## Supuestos

El reporte conserva el supuesto de inflación mensual utilizado para el
rendimiento real y el horizonte utilizado para planificación y escenarios.

## Formatos

### Informe Markdown

Es el formato humano. Está pensado para leer, guardar o compartir.

### JSON

Es el formato estructurado. Conserva la composición completa de los read
models y sirve para integraciones o procesamiento posterior.

### CSV resumen

Es una tabla compacta con los indicadores principales y una columna que
indica si el dato es real, estimado, derivado, histórico con supuesto o
escenario.

## Naturaleza de los datos

El reporte diferencia:

- **Real:** hecho que ya ocurrió y está registrado.
- **Derivado:** resultado calculado a partir de hechos reales.
- **Estimado:** movimiento futuro conocido/proyectado.
- **Histórico con supuesto:** métrica histórica expresada con una hipótesis
  adicional, como inflación.
- **Escenario:** comparación bajo supuestos macroeconómicos.

## No muta datos

Generar Markdown, JSON o CSV es una operación de solo lectura.

No crea auditoría, no modifica pagos, no cambia préstamos y no activa ningún
modo del Motor V3.

## Separación respecto de planes internos

El reporte personal M6 no suma automáticamente los planes internos de reposición ni sus carteras declaradas. Esos registros no tienen necesariamente un titular/propietario consolidado y pueden representar el mismo dinero que la persona registra en otra parte. Sumarlos sin conciliación podría duplicar capital, cobros o valuaciones.

Los planes internos cuentan con un informe propio desde la sección de reposición/inversión, en Markdown, JSON y CSV. Ese informe conserva separadas tres cosas: aportes destinados a reposición, flujos de inversión declarados y valuaciones del saldo invertido. No crea una posición patrimonial consolidada ni una ganancia realizada a partir de una valuación.

## Límites

El reporte no representa todo el patrimonio de la persona.

No incorpora:

- sueldo o ingresos externos;
- gastos externos;
- efectivo o ahorros externos;
- otras deudas no registradas;
- bienes o inversiones que la aplicación no conozca.

Tampoco constituye asesoramiento financiero.

## Arquitectura

- `aplicacion/servicios/reportes_persona.py` — composición y serialización;
- `ui/pagina_reportes.py` — presentación y descargas;
- read models M1–M5 — fuente de los datos;
- `tests/test_reportes_persona.py` — contrato del reporte;
- `tests/test_ui_e2e.py` — aceptación de la pantalla.

El reporte no contiene reglas financieras propias.

## Principio

> Una exportación debe conservar el significado del dato, no solamente su número.

Por eso cada reporte conserva fecha de corte, supuestos y naturaleza del dato.