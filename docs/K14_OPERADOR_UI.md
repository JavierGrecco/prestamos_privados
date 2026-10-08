# Operador declarado en la UI

La aplicación deja de fijar el usuario de las principales operaciones en
`admin`. La sesión de Streamlit mantiene un operador declarado que se utiliza
para registrar auditoría.

## Alcance

Se aplica a:

- alta de préstamos;
- registro de pagos;
- cambios de estado del préstamo;
- cambios de modo del Motor de Pagos.

Puede establecerse mediante la variable de entorno `PRESTAMOS_OPERADOR` o
editarse en la barra superior de la aplicación.

## Importante

El operador declarado mejora la trazabilidad, pero **no es autenticación**.
No debe interpretarse como una barrera de seguridad contra suplantación.
Una futura capa de autenticación deberá aportar la identidad confiable y
autorización de permisos.
