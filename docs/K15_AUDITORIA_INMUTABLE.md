# Inmutabilidad de la auditoría

La migración v014 agrega triggers que impiden modificar o eliminar filas de
la tabla `auditoria`.

Esto alinea la evidencia de auditoría con las garantías ya existentes para
ledger, observaciones SOMBRA y ejecuciones SOMBRA.

Las nuevas operaciones de auditoría se agregan mediante INSERT y quedan
reconstruibles por correlación. La UI no tiene mecanismos de edición o
eliminación.

El cambio no modifica datos históricos existentes; solo impide operaciones
futuras de UPDATE/DELETE sobre la evidencia.
