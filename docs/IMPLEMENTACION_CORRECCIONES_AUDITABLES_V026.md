# Correcciones auditables de planes internos — esquema v026

**Estado funcional:** permite registrar, verificar y comparar propuestas de corrección. No aplica cambios a los datos financieros efectivos.

## Qué incluye

La migración v026 crea la bitácora append-only `correcciones_auditables`. Guarda tipo/ID del hecho original, SHA-256 original, snapshot propuesto y su hash, motivo obligatorio, actor de identidad autenticada, instante UTC, clave idempotente y referencia opcional a una propuesta previa. Triggers impiden actualizar o borrar filas de la bitácora.

El servicio y la UI incorporados por el PR #260 amplían la base inicial:

- exigen identidad autenticada y capacidades explícitas de consulta/propuesta;
- vuelven a leer y verificar hash del snapshot original;
- rechazan hashes desactualizados y payloads incompatibles;
- normalizan JSON de forma determinista y prohíben `float` en snapshots;
- validan importes, fechas, monedas, cotizaciones y equivalentes USD;
- serializan la escritura mediante `BEGIN IMMEDIATE`;
- hacen idempotentes los reintentos iguales y rechazan reutilizar una clave con otra solicitud;
- obligan a encadenar propuestas sucesivas para el mismo registro;
- exponen historial y comparación en Streamlit con motivo/antes/después.

## Alcance admitido

Solo permite proponer correcciones para aportes de reposición, flujos de inversión y valuaciones declaradas de un plan de reposición. No cambia contratos de préstamos, pagos Legacy/V3 ni el cálculo de carencia.

## Qué no hace

- No modifica el registro original.
- No cambia el rendimiento reportado, XIRR, posiciones ni reportes.
- No declara que el snapshot propuesto sea verificado por un proveedor externo.
- No tiene todavía proceso de aprobación ni mecanismo de aplicación efectiva.
- No reconstruye por sí mismo los informes históricos previos a una futura corrección.

La interfaz presenta expresamente el estado **“Registrada · no aplicada”**. Este límite es deliberado: evita que una propuesta válida se convierta de forma implícita en un hecho económico.

## Próxima fase para correcciones efectivas

Antes de aplicar propuestas habrá que definir y aprobar el mecanismo: asiento compensatorio o reconstrucción/versionado de las vistas derivadas. La implementación futura debe preservar los valores históricos por fecha, validar autoridad y motivo de aprobación, ser atómica e idempotente, evitar doble contabilización y mostrar el efecto neto sin ocultar el original.

## Validación

El código del PR #260, antes de los últimos ajustes documentales, pasó **1.061 pruebas en cada versión Python 3.11, 3.12, 3.13 y 3.14**, CodeQL y auditoría de dependencias. Los cambios finales de documentación deben pasar la matriz CI otra vez. La aceptación manual visual y la prueba de migración/restauración sobre una copia de base histórica siguen pendientes.
