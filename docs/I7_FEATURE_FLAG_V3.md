# I7 — Feature flag de V3 protegido por preflight

## Objetivo

Permitir una futura activación controlada de V3 sin cambiar el comportamiento
por defecto de producción.

## Política

- ausencia de configuración → LEGACY;
- LEGACY explícito → LEGACY;
- SOMBRA explícito → SOMBRA;
- V3 sin preflight → rechazo;
- V3 con preflight no apto → rechazo;
- V3 con preflight apto → V3.

No existe un fallback silencioso de V3 a Legacy cuando alguien solicita V3
explícitamente. Eso evita que una configuración de despliegue parezca activar
V3 cuando en realidad quedó funcionando Legacy.

## Separación de responsabilidades

El feature flag solamente devuelve una decisión de modo.

El preflight evalúa preparación.

El puente ejecuta.

Ninguna de estas piezas duplica reglas financieras.

## Estado actual

I7 todavía no está conectado al entrypoint productivo. El valor por defecto
continúa siendo Legacy y no se realiza ningún cut-over automático.

El siguiente paso será conectar esta decisión a un punto único de entrada y
diseñar el rollback operativo antes de habilitar V3 en un entorno real.
