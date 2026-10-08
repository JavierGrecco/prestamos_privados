# M6 — Reporte financiero personal

## Propósito

M6 reúne en una sola vista la información financiera que la aplicación ya
conoce de una persona.

No agrega una nueva lógica financiera. Compone los read models existentes.

## Contenido

El reporte contiene:

- posición de capital;
- movimientos reales;
- planificación futura;
- escenarios macroeconómicos;
- rendimiento histórico cuando existe evidencia suficiente;
- fecha de corte;
- supuestos usados.

## Naturaleza de los datos

Cada dato del CSV se clasifica como:

- real — hecho registrado;
- estimado — proyección contractual;
- derivado — resultado calculado desde otros datos;
- escenario — resultado condicionado a un supuesto;
- supuesto — valor elegido para interpretar;
- evidencia — cantidad o calidad de información utilizada.

Esto hace que el CSV sea útil también fuera de la interfaz.

## Exportación

La pantalla permite descargar un CSV UTF-8 estructurado con cinco columnas:
seccion, campo, valor, naturaleza y nota.

El archivo mantiene el contexto suficiente para saber qué significa cada cifra.

## Seguridad

El reporte no modifica datos, no recalcula hechos y no reemplaza los controles
de acceso.

Los archivos descargados contienen información financiera y deben tratarse como
información sensible.

## Límites

El reporte no representa patrimonio total de la persona.

No incluye sueldo, gastos personales, efectivo, ahorros, activos o deudas
externas que no estén registradas.

## Arquitectura

- aplicacion/consultas/reporte_financiero_persona.py — composición de read models;
- aplicacion/servicios/exportaciones.py — CSV;
- ui/pagina_reporte.py — pantalla;
- tests/test_reporte_financiero_persona.py — regresiones;
- tests/test_ui_e2e.py — aceptación.

## Principio de producto

> Un reporte debe poder entenderse fuera de la pantalla que lo generó.

El CSV debe conservar no solo el valor sino también su naturaleza y el contexto
necesario para interpretarlo.