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

El servicio rechaza identidades no autenticadas. La UI todavía no usa este flujo: la siguiente integración debe obtener la identidad del contexto de sesión de la aplicación y crear el servicio por solicitud.

## Validación confirmada y pendiente

El commit `e9583d36fa3f0fc91c6adf47d6f7d8deac3feca5` pasó en GitHub Actions la suite completa en Python 3.11, 3.12, 3.13 y 3.14: 944 pruebas aprobadas en cada versión. También pasaron `compileall`, `pip check` y `git diff --check`.

- [Ejecución de CI por pull request](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093728876)
- [Ejecución de CI por push](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38093725778)

**Ese resultado es anterior a la incorporación de la política de identidad autenticada y capacidades.** Los nuevos controles de seguridad y sus pruebas deben validarse en el HEAD actual antes de considerar esta extensión lista. La última prueba local del responsable en el código anterior sí terminó con 944 aprobadas; la próxima comprobación local debe repetirse tras estos cambios.

## Límites actuales

Esta entrega **todavía no es una función terminada para usar desde la UI**:

- no modifica aportes, flujos ni valuaciones originales;
- no cambia rendimiento, XIRR ni reportes;
- no incluye formularios, comparación antes/después ni pantalla de historial;
- la UI todavía no crea el servicio a partir de la identidad de sesión; la frontera está implementada en el servicio, pero falta conectar la pantalla al contexto autenticado;
- una escritura SQL directa puede eludir reglas de aplicación, aunque los triggers impidan UPDATE/DELETE en la bitácora.

Por lo tanto, las propuestas quedan como evidencia separada y no alteran el resultado financiero.

## Próximas entregas

1. Ejecutar las pruebas focalizadas y la suite completa después de la integración de identidad/capacidades.
2. Conectar la UI al proveedor autenticado de sesión y probar acceso ADMIN, OPERADOR y LECTURA.
3. Revisar migración desde copias históricas representativas y comprobar backup/restauración.
4. Incorporar comparación e historial en UI sin cambiar los cálculos.
5. Diseñar, probar y auditar cómo una corrección aprobada pasa a reportes y XIRR, evitando doble contabilización.
6. Realizar aceptación manual antes de habilitar la función.
