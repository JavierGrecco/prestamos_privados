# K14 — Operador declarado en la UI

La aplicación permite indicar un operador para que las operaciones registradas
desde Streamlit tengan una identidad consistente en la auditoría.

## Alcance

Aplica a:

- alta de préstamos;
- registro de pagos;
- cambios de estado;
- cambios de modo del Motor de Pagos.

El valor inicial puede venir de PRESTAMOS_OPERADOR. También puede revisarse y
editarse desde la barra superior.

## Importante

El operador declarado **no es autenticación** y no constituye una prueba de
identidad confiable. Una futura integración de autenticación deberá proporcionar
la identidad y los permisos desde una fuente confiable.

La mejora busca eliminar usuarios hardcodeados y mejorar la trazabilidad sin
simular una barrera de seguridad que todavía no existe.
