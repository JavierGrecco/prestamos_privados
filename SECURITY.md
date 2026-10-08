# Seguridad

El repositorio contiene lógica financiera y puede operar sobre información
sensible aunque los datos reales no formen parte del código versionado.

## Reporte

No publicar secretos, tokens, credenciales ni datos financieros en issues
públicos. Para vulnerabilidades, utilizar el mecanismo privado de reporte de
seguridad de GitHub cuando esté disponible y proporcionar el mínimo detalle
necesario para reproducir el problema.

## Reglas

- no versionar SQLite, WAL, SHM, .env ni credenciales;
- mantener dependencias y GitHub Actions actualizados;
- revisar CodeQL y auditoría de dependencias;
- no fusionar cambios con CI rojo;
- preservar auditoría, idempotencia e integridad del ledger.

## Datos

Pruebas y fixtures deben usar datos sintéticos. Backups reales deben quedar
fuera del repositorio y bajo controles de acceso adecuados.
