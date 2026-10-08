# K16 — Exportaciones de datos desde la UI

La aplicación permite descargar información de solo lectura en CSV, evitando
copias manuales desde SQLite.

## Exportaciones

### Auditoría

Respeta los filtros activos de usuario, operación y entidad y exporta eventos
con fecha, operador, operación, entidad, motivo, correlación y datos anterior/
nuevo.

### Personas

Exporta el directorio de personas con estado y roles activos.

### Amortización

El detalle financiero permite exportar la amortización vigente del préstamo,
incluyendo importes contractuales y saldos pendientes.

## Seguridad y reproducibilidad

Las exportaciones:

- no modifican SQLite;
- no recalculan hechos históricos;
- consumen read models/casos de uso existentes;
- se entregan como UTF-8 con BOM para compatibilidad con Excel;
- mantienen los valores monetarios como texto decimal en el CSV.

La exportación no reemplaza los controles de acceso. Los archivos descargados
deben tratarse como información financiera sensible.
