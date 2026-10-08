# Seguridad

Este proyecto maneja información financiera y debe tratar la base SQLite como
dato sensible aunque el repositorio no contenga bases reales.

## Reporte de vulnerabilidades

No publicar secretos, credenciales, tokens ni datos financieros en issues.

Para una vulnerabilidad de seguridad, utilizar los mecanismos privados de
reporte de vulnerabilidades disponibles en GitHub. Cuando no estén disponibles,
abrir un contacto privado con el mantenedor antes de revelar detalles
explotables públicamente.

## Reglas del repositorio

- no versionar bases SQLite, WAL, SHM ni archivos `.env`;
- no incluir credenciales en código o configuración;
- mantener dependencias actualizadas;
- revisar los resultados de Dependency Review y CodeQL;
- no fusionar cambios financieros con CI rojo;
- no desactivar controles de auditoría para facilitar una operación.

## Datos financieros

Las pruebas deben utilizar bases temporales y datos sintéticos. Un backup real
debe mantenerse fuera del repositorio y bajo control de acceso apropiado.
