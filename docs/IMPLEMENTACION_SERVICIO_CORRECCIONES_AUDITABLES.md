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

## Validación disponible

El último resultado local comunicado por el responsable corresponde al código del commit `da6bd6c9b9e0a07ea1376d2efdebeefb306c87fc` (macOS, Python 3.14.8):

- Pruebas específicas: 50 aprobadas.
- Suite completa: 942 aprobadas, 0 fallidas en 20,50 s.
- `compileall`: sin errores.
- `pip check`: sin conflictos.

**Ese resultado no valida los últimos cambios.** Después se modificó la transacción de SQLite y el servicio, se agregaron pruebas para reintentos idempotentes concurrentes y se sumó una prueba de actualización desde un esquema v025 con datos existentes. El último commit que modifica código es `7104fef1a4ddd2c25a61ebbde7cdb6625ec895ee`; después se agregó un commit de documentación solamente. Las pruebas focalizadas y la suite completa deben volver a ejecutarse sobre el estado actual de la rama.

La consulta de GitHub Actions no mostró ejecuciones asociadas a los commits consultados. Los resultados locales no se presentan como CI; la automatización y sus checks deben confirmarse por separado.

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
