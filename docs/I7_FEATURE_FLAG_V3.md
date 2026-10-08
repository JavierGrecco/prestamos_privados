# I7 — Selección del Motor V3 protegida por preflight

## Objetivo

Permitir una activación controlada de V3 sin convertir una selección de UI en
una ejecución efectiva accidental.

## Política

- LEGACY: flujo histórico efectivo;
- SOMBRA: Legacy sigue siendo efectivo y V3 se ejecuta para comparación;
- V3 sin preflight: rechazo;
- V3 con preflight no apto: rechazo;
- V3 con preflight apto: puede seleccionarse como modo efectivo.

El modo efectivo ya no depende solamente de la sesión de Streamlit: se guarda
en la configuración operacional persistente de la base.

## Responsabilidades

- la configuración persistente determina el modo efectivo;
- el preflight determina si V3 está preparado;
- el puente/registrador ejecuta el modo seleccionado;
- el dominio contiene las reglas financieras.

Estas piezas no deben duplicar cálculos.

## Estado actual

El entrypoint productivo ya está conectado al selector y a la configuración
persistente. La activación V3 requiere un cambio explícito de modo, motivo y
preflight aprobado.

El sistema mantiene Legacy como rollback entre operaciones y no implementa
fallback automático dentro de una transacción financiera.
