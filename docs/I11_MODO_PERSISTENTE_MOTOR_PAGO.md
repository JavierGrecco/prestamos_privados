# I11 — Modo persistente del Motor de Pagos

El modo del Motor de Pagos deja de ser solamente un valor de sesión de
Streamlit y pasa a una configuración operacional persistente.

## Modos

- LEGACY: escritura histórica efectiva.
- SOMBRA: Legacy efectivo y V3 calculado sobre el snapshot para comparar.
- V3: escritura efectiva V3.

## Activación

Para cambiar el modo:

1. el operador selecciona el nuevo modo en la pantalla Motor de Pagos;
2. proporciona un motivo;
3. si el destino es V3, se ejecuta un preflight sobre el estado actual;
4. solo si el preflight está aprobado se persiste el cambio;
5. el cambio queda auditado con configuración anterior y nueva.

## Rollback

El operador puede volver a Legacy entre operaciones, indicando el motivo.
No existe fallback automático dentro de una operación financiera.

## Concurrencia

La configuración tiene una revisión incremental y el UPDATE exige la revisión
esperada. Si otro proceso la cambió, la operación es rechazada y debe
consultarse nuevamente el estado.

## Seguridad

La selección que aparece en la sesión no constituye por sí sola el modo
efectivo. Hasta confirmar el cambio, el sistema continúa usando la
configuración persistida.

Al iniciar una nueva sesión, ambas pantallas consultan la misma configuración
persistida.
