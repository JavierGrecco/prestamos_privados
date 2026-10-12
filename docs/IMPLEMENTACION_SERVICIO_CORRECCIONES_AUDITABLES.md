# Servicio de correcciones auditables

**Estado:** servicio y pantalla inicial de historial/comparación implementados en ramas de revisión; no integrados en `main`.  
**Esquema requerido:** v026.  
**Alcance:** propuestas de corrección de aportes, flujos de inversión y valuaciones de planes internos de reposición.

## Qué hace

El servicio `ServicioCorreccionesAuditables` registra una propuesta sin editar ni borrar el hecho financiero original y verifica la identidad/capacidad del actor. Antes de guardarla:

- vuelve a leer el registro original y verifica el SHA-256 real del snapshot contra el valor guardado y la huella recibida;
- normaliza el snapshot de forma determinista y rechaza valores `float`;
- conserva la identidad del registro y sus campos de trazabilidad;
- valida importes, fechas, cotizaciones, moneda y equivalentes en USD;
- exige motivo y clave de idempotencia; el responsable se deriva del proveedor y del subject de una identidad de sesión autenticada, no de un nombre escrito en la UI;
- comprueba las capacidades `PROPONER_CORRECCIONES_AUDITABLES` o `VER_CORRECCIONES_AUDITABLES` antes de registrar o consultar;
- ADMIN y OPERADOR tienen acceso a esas capacidades; LECTURA no puede proponer ni consultar esta bitácora;
- conserva fecha/hora UTC, hashes y enlace a la propuesta anterior;
- permite consultar el historial y detectar alteraciones en los snapshots o roturas en la cadena.

La persistencia de la propuesta usa una transacción SQLite `BEGIN IMMEDIATE` para reservar el turno de escritura antes de leer el estado. El objetivo es serializar solicitudes concurrentes y permitir que dos reintentos simultáneos con la misma clave y los mismos datos devuelvan la misma propuesta, en vez de dejar una carrera de idempotencia.

### Uso desde la aplicación

La identidad debe provenir del proveedor de autenticación ya resuelto por la aplicación. No se debe construir a partir de un nombre editable del operador.

```python
from aplicacion.servicios import ServicioCorreccionesAuditables

# identidad_sesion debe ser la identidad autenticada que entregó el proveedor
servicio = ServicioCorreccionesAuditables(
    db,
    identidad=identidad_sesion,
)
propuesta = servicio.registrar_propuesta(
    entidad_tipo="APORTE_REPOSICION",
    entidad_id=aporte.id,
    hash_original=aporte.snapshot_sha256,
    snapshot_corregido=snapshot_corregido,
    motivo="El importe se había cargado incorrectamente",
    clave_idempotencia=clave_unica_de_la_operacion,
)
historial = servicio.listar_historial(
    entidad_tipo="APORTE_REPOSICION",
    entidad_id=aporte.id,
)
```

El servicio rechaza identidades no autenticadas. La pantalla de consulta ya obtiene la identidad autenticada del contexto de sesión y crea el servicio por solicitud; todavía no hay un formulario de creación ni un flujo de aprobación/aplicación desde la UI.


## Pantalla de historial y comparación

La rama de UI agrega la ruta **Correcciones auditables** en el grupo Análisis e informes. ADMIN y OPERADOR pueden acceder; LECTURA no ve la ruta y el servicio vuelve a exigir permiso al consultar.

La pantalla:

- lista las 200 propuestas más recientes, ordenadas desde la última;
- valida el hash de cada snapshot propuesto y la continuidad de la cadena completa de cada registro incluido;
- presenta el motivo, responsable identificado por proveedor/subject, fecha UTC y enlace con la propuesta anterior;
- compara el snapshot original actual con el snapshot propuesto, y solo muestra el lado original si vuelve a verificar el SHA-256 almacenado;
- permite inspeccionar ambos snapshots y sus hashes.

La vista es estrictamente de consulta. No crea, aprueba ni aplica propuestas. Si el original cambió o no supera la comprobación de integridad, la UI muestra una advertencia y no presenta la comparación como confiable.

## Validación confirmada y pendiente

El commit `e9583d36fa3f0fc91c6adf47d6f7d8deac3feca5` pasó en GitHub Actions la suite completa en Python 3.11, 3.12, 3.13 y 3.14: 944 pruebas aprobadas en cada versión. También pasaron `compileall`, `pip check` y `git diff --check`.

- [Ejecución de CI por pull request](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093728876)
- [Ejecución de CI por push](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093725778)

**Ese resultado es anterior a la incorporación de la política de identidad, capacidades y pantalla de comparación.** Los nuevos controles de seguridad, método de consulta reciente y navegación deben validarse en los HEAD de sus ramas antes de considerar estas extensiones listas. La última prueba local del responsable en el código previo terminó con 944 aprobadas.

## Límites actuales

Esta entrega **todavía no es una función terminada para usar desde la UI**:

- no modifica aportes, flujos ni valuaciones originales;
- no cambia rendimiento, XIRR ni reportes;
- no incluye formularios, comparación antes/después ni pantalla de historial;
- la UI de consulta ya recibe la identidad autenticada de la sesión; todavía no incorpora creación, aprobación ni aplicación de propuestas;
- una escritura SQL directa puede eludir reglas de aplicación, aunque los triggers impidan UPDATE/DELETE en la bitácora.

Por lo tanto, las propuestas quedan como evidencia separada y no alteran el resultado financiero.

## Próximas entregas

1. Validar CI y suite local de servicio, autorización y pantalla de historial.
2. Probar visualmente acceso y comparación con ADMIN, OPERADOR y LECTURA.
3. Revisar migración desde copias históricas representativas y comprobar backup/restauración.
4. Diseñar una pantalla separada para proponer y luego revisar/aprobar correcciones con doble control si corresponde.
5. Diseñar, probar y auditar cómo una corrección aprobada pasa a reportes y XIRR, evitando doble contabilización.
6. Realizar aceptación manual antes de habilitar cualquier aplicación financiera.
