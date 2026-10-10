# Servicio de correcciones auditables

**Estado:** primera capa de aplicación implementada en una rama de trabajo; pendiente de validación local y CI.  
**Versión de esquema requerida:** v026.  
**Alcance:** aportes, flujos de inversión y valuaciones declaradas de planes internos de reposición.

## Qué hace esta entrega

El servicio **ServicioCorreccionesAuditables** permite registrar una **propuesta de corrección** sin editar ni borrar el registro financiero original. Antes de guardarla:

- vuelve a leer el hecho original desde su tabla;
- calcula el SHA-256 del snapshot almacenado y comprueba que coincida con el hash persistido y con la huella que envió quien solicita la corrección;
- normaliza el snapshot corregido de forma determinista y rechaza valores tipo float;
- valida que se conserven los campos, la identidad del plan y los metadatos originales, y que los importes, cotizaciones y equivalentes sean coherentes;
- exige motivo, responsable y clave de idempotencia;
- registra fecha/hora UTC, hashes y vínculo a la corrección anterior;
- permite volver a consultar el historial cronológico y verifica que cada hash de corrección corresponda al contenido, que la cadena anterior no esté rota y que no cambie la huella del registro original.

Los reintentos con la misma clave y los mismos datos devuelven la corrección ya registrada. Reutilizar una clave para otra solicitud se rechaza. Una nueva corrección de la misma entidad debe indicar como anterior la última de la cadena.

## Uso desde código

    from aplicacion.servicios import ServicioCorreccionesAuditables

    servicio = ServicioCorreccionesAuditables(db)
    propuesta = servicio.registrar_propuesta(
        entidad_tipo="APORTE_REPOSICION",
        entidad_id=aporte.id,
        hash_original=aporte.snapshot_sha256,
        snapshot_corregido=snapshot_corregido,
        motivo="El importe se había cargado incorrectamente",
        corregido_por=usuario_operador,
        clave_idempotencia=clave_unica_de_la_operacion,
    )
    historial = servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION",
        entidad_id=aporte.id,
    )

El primer registro deja correccion_anterior_id en null. Para otra propuesta sobre el mismo registro, se pasa el identificador de la última corrección.

## Qué no hace todavía

Esta entrega **no debe usarse como una función terminada de corrección desde la UI**:

- no modifica los aportes, flujos ni valuaciones originales;
- no cambia los cálculos de rendimiento ni la XIRR;
- los reportes actuales no interpretan todavía esta bitácora como el conjunto efectivo de datos;
- no crea formularios, comparación antes/después ni pantalla de historial;
- recibe el responsable como dato de entrada; no sustituye la autenticación ni implementa una política de autorización;
- la integridad de la cadena se valida al pasar por el servicio; una escritura SQL directa puede saltarse reglas de aplicación aunque los triggers de v026 sigan bloqueando UPDATE/DELETE.

La UI y los informes deben integrarse en entregas posteriores. Hasta entonces, la propuesta auditada es evidencia separada y **no altera el resultado financiero**.

## Validación pendiente de esta rama

En el clon de pruebas se deben ejecutar primero las pruebas nuevas y las de reposición, luego toda la suite:

    python -m pytest -q tests/test_servicio_correcciones_auditables.py tests/test_migracion_correcciones_auditables.py tests/test_repositorio_planes_reposicion.py tests/test_reporte_inversion_reposicion.py
    python -m compileall -q aplicacion dominio infraestructura tests
    python -m pip check
    python -m pytest -q

La suite completa de 927 pruebas pasó localmente en el commit anterior f854b16. Ese resultado no valida automáticamente esta nueva rama; hay que volver a ejecutar los comandos aquí indicados. No se detectaron ejecuciones de GitHub Actions asociadas al commit previo.

## Próximas entregas

1. Validar esta capa, incluyendo rollback e idempotencia.
2. Incorporar pruebas de correcciones para flujos y valuaciones, así como migración desde una copia de base histórica.
3. Exponer comparación e historial en la UI con autorización explícita.
4. Conectar el conjunto corregido a los reportes y a XIRR, sin doble contabilización y preservando informes anteriores.
5. Ejecutar CI y aceptación manual antes de considerar habilitada la función.
