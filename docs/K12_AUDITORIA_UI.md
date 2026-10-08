# Auditoría global desde la UI

La pantalla **Auditoría** expone la evidencia de decisiones y cambios
importantes del sistema en modo solo lectura.

## Filtros

Puede filtrarse por:

- usuario;
- operación;
- entidad.

## Detalle

Cada evento permite inspeccionar:

- fecha;
- usuario;
- operación;
- entidad e ID;
- motivo;
- correlación;
- datos anteriores;
- datos nuevos.

La correlación permite reconstruir todos los eventos pertenecientes a una
misma operación de aplicación.

## Seguridad

La pantalla no ofrece acciones de edición ni eliminación de auditoría.
La auditoría sigue siendo evidencia append-only desde el punto de vista de la
UI.

## Relación con el canary

Los cambios de modo del Motor de Pagos y los eventos financieros importantes
pueden revisarse aquí junto con su correlación, complementando la pantalla
específica de SOMBRA y el precheck de canary.
