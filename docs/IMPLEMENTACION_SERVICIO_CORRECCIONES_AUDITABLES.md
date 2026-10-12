# Servicio de correcciones auditables

**Estado:** implementación en revisión; no integrada en `main` ni habilitada desde la UI.  
**Esquema requerido:** v026.  
**Alcance:** propuestas de corrección de aportes, flujos de inversión y valuaciones de planes internos de reposición.

## Qué hace

El servicio `ServicioCorreccionesAuditables` registra una propuesta sin editar ni borrar el hecho financiero original. Antes de guardarla:

- vuelve a leer el registro original y verifica el SHA-256 real del snapshot contra el valor guardado y la huella recibida;
- normaliza el snapshot de forma determinista y rechaza valores `float`;
- conserva la identidad del registro y sus campos de trazabilidad;
- valida importes, fechas, cotizaciones, moneda y equivalentes en USD;
- exige motivo, responsable y clave de idempotencia;
- conserva fecha/hora UTC, hashes y enlace a la propuesta anterior;
- permite consultar el historial y detectar alteraciones en los snapshots o roturas en la cadena.

La persistencia de la propuesta usa una transacción SQLite `BEGIN IMMEDIATE` para reservar el turno de escritura antes de leer el estado. El objetivo es serializar solicitudes concurrentes y permitir que dos reintentos simultáneos con la misma clave y los mismos datos devuelvan la misma propuesta, en vez de dejar una carrera de idempotencia.

## Validación confirmada en GitHub Actions

El commit `e9583d36fa3f0fc91c6adf47d6f7d8deac3feca5` ejecutó con éxito el workflow `tests` tanto por `push` como por `pull_request`. Los cuatro jobs finalizaron en verde:

| Python | Suite completa |
| --- | ---: |
| 3.11.17 | 944 aprobadas |
| 3.12.15 | 944 aprobadas |
| 3.13.16 | 944 aprobadas |
| 3.14.8 | 944 aprobadas |

Cada job también completó instalación de dependencias, `compileall`, `pip check` y `git diff --check` antes de ejecutar pytest.

- [Ejecución de CI por pull request](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093728876)
- [Ejecución de CI por push](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093725778)

Estos resultados sí cubren los cambios transaccionales, las nuevas pruebas de reintentos concurrentes y la migración de v025 con datos que están incluidos en ese commit. La prueba local del responsable sigue siendo útil, pero su último intento no llegó a ejecutar pytest porque el shell no encontró el comando `python`; eso es un problema de activación del entorno local, no un fallo de tests.

## Límites actuales

Esta entrega **todavía no es una función terminada para usar desde la UI**:

- no modifica aportes, flujos ni valuaciones originales;
- no cambia rendimiento, XIRR ni reportes;
- no incluye formularios, comparación antes/después ni pantalla de historial;
- el responsable se recibe como un dato: la autenticación y la autorización no están conectadas;
- una escritura SQL directa puede eludir reglas de aplicación, aunque los triggers impidan UPDATE/DELETE en la bitácora.

Por lo tanto, las propuestas quedan como evidencia separada y no alteran el resultado financiero.

## Próximas entregas

1. Reejecutar las pruebas focalizadas y la suite completa en el HEAD actual; corregir cualquier fallo.
2. Revisar la migración desde copias históricas representativas y comprobar backup/restauración.
3. Definir identidad autenticada y permisos para proponer, revisar y aprobar correcciones.
4. Incorporar primero una UI de comparación e historial sin cambiar cálculos.
5. Diseñar, probar y auditar cómo una corrección aprobada pasa a reportes y XIRR, evitando doble contabilización.
6. Configurar o confirmar CI y realizar aceptación manual antes de habilitar la función.
