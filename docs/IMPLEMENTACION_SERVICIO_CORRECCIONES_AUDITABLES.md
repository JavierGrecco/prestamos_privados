# Servicio de correcciones auditables

**Estado:** servicio de propuestas implementado en una rama de trabajo; validado localmente por el responsable sobre el commit de código `da6bd6c9b9e0a07ea1376d2efdebeefb306c87fc`. Sigue sin estar integrado en `main` ni habilitado para uso desde la UI.
**Versión de esquema requerida:** v026.
**Alcance:** aportes, flujos de inversión y valuaciones de planes internos de reposición.

## Qué hace esta entrega

El servicio **ServicioCorreccionesAuditables** permite registrar una **propuesta de corrección** sin editar ni borrar el registro financiero original. Antes de guardarla:

- vuelve a leer el hecho original desde su tabla;
- calcula el SHA-256 del snapshot almacenado y comprueba que coincida con el hash persistido y con la huella recibida;
- normaliza el snapshot corregido de forma determinista y rechaza valores tipo `float`;
- valida que se conserven los campos, la identidad del plan y los metadatos originales, y que importes, cotizaciones y equivalentes sean coherentes;
- exige motivo, responsable y clave de idempotencia;
- registra fecha/hora UTC, hashes y vínculo a la corrección anterior;
- permite consultar el historial cronológico y comprueba los hashes, la continuidad de la cadena y la consistencia de la huella original.

Los reintentos con la misma clave y los mismos datos devuelven la propuesta registrada. Reutilizar una clave para otra solicitud se rechaza. Una nueva propuesta para la misma entidad debe indicar la última corrección de la cadena.

## Validación realizada

En el equipo del responsable, con Python 3.14.8:

| Control | Resultado |
| --- | ---: |
| Pruebas específicas de correcciones, migración y reportes | 50 aprobadas |
| Suite completa | 942 aprobadas, 0 fallidas (20,50 s) |
| `compileall` sobre aplicación, dominio, infraestructura y tests | Sin errores |
| `pip check` | Sin conflictos |

Los resultados corresponden al código del commit `da6bd6c9b9e0a07ea1376d2efdebeefb306c87fc`. El commit de documentación que registra estos resultados no modifica el código probado. Esta es una validación local aportada por el responsable; no se presenta como CI de GitHub. En la consulta realizada no aparecieron ejecuciones de Actions asociadas al commit, por lo que CI todavía debe confirmarse o configurarse.

## Qué no hace todavía

Esta entrega **no debe usarse como una función terminada de corrección desde la UI**:

- no modifica los aportes, flujos ni valuaciones originales;
- no cambia los cálculos de rendimiento ni la XIRR;
- los reportes actuales todavía no interpretan la bitácora como el conjunto efectivo de datos;
- no incluye formulario, comparación antes/después ni pantalla de historial;
- recibe el responsable como dato de entrada; no sustituye la autenticación ni implementa una política de autorización;
- las reglas de aplicación y la validación de la cadena pueden eludirse con escrituras SQL directas, aunque los triggers de v026 bloqueen UPDATE/DELETE en la bitácora.

La propuesta queda como evidencia separada y **no altera los resultados financieros actuales**.

## Próximas entregas

1. Revisar con más profundidad idempotencia concurrente, límites transaccionales y pruebas de migración desde copias históricas.
2. Definir cómo se obtiene la identidad autenticada y qué permisos requiere proponer, revisar y aprobar una corrección.
3. Incorporar comparación e historial en la UI, inicialmente sin cambiar los cálculos financieros.
4. Diseñar la activación de propuestas aprobadas en reportes y XIRR, sin doble contabilización y preservando la trazabilidad del dato original.
5. Ejecutar CI, migración sobre copias de bases representativas y aceptación manual antes de considerar la función habilitada.
