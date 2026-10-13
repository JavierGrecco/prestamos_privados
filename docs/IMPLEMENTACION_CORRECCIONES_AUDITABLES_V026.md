# Correcciones auditables — entrega de persistencia v026

**Estado:** base de datos y restricciones iniciales implementadas en una rama de trabajo.  
**No significa que la función ya esté disponible en la interfaz.**

## Qué agrega esta entrega

La migración v026 crea `correcciones_auditables`, una bitácora append-only que guarda:

- tipo e identificador del hecho original;
- hash del original y hash del snapshot corregido;
- snapshot corregido en JSON;
- motivo y usuario responsable;
- fecha/hora declarada en UTC;
- clave de idempotencia única;
- referencia opcional a una corrección anterior.

La base rechaza tipos de entidad no admitidos, identificadores inválidos, hashes con formato incorrecto, JSON que no sea un objeto, motivos vacíos y claves de idempotencia repetidas. También bloquea UPDATE y DELETE sobre la bitácora.

## Qué todavía no habilita

Esta entrega es infraestructura, no un flujo operativo completo:

1. No crea ni modifica aportes, flujos o valuaciones originales.
2. No valida todavía desde un servicio que el hash enviado corresponda al registro original actual.
3. No calcula ni comprueba el hash del snapshot corregido en la capa de aplicación.
4. No expone formularios ni botones en Streamlit.
5. No hace que los reportes consuman las correcciones ni reconstruyan una vista corregida.
6. No debe usarse todavía para corregir datos reales.

Por eso la interfaz y los reportes siguen mostrando los registros vigentes que ya existían; no hay cambio de criterio financiero por esta migración.

## Próximo paso

Implementar un servicio de aplicación transaccional que vuelva a leer el registro original, compruebe su hash, valide y normalice el snapshot con `Decimal`, registre la corrección de forma idempotente y atómica, y devuelva el historial para consulta. Luego conectar el servicio a reportes y UI, con pruebas de concurrencia, rollback, integridad y no doble contabilización.

## Validación requerida antes de integrar

- Suite completa de tests y comprobación de migración sobre base nueva y copia de una base histórica.
- Reintento con la misma clave sin duplicar la corrección.
- Rechazo de hash original desactualizado.
- Inyección de fallo para verificar rollback.
- Dos correcciones concurrentes del mismo hecho.
- Trazabilidad en Markdown, JSON y CSV.
- Aceptación manual de corrección e historial desde la interfaz.

La migración y sus pruebas deben pasar CI antes de considerar esta entrega aceptada.