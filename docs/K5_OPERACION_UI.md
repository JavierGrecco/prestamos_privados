# K5 — Operación segura desde la UI

K5 expone en Streamlit controles operativos de solo lectura y acciones acotadas
de backup/restore drill.

## Salud de la base

La pantalla puede comprobar quick_check, integrity_check y
foreign_key_check sobre la base activa. Una falla se trata como incidente
operativo, no como resultado financiero.

## Backups

Los backups se crean localmente bajo el directorio operativo excluido de Git.

Crear un backup requiere confirmación explícita y nunca sobrescribe un archivo
existente. Cada backup tiene manifiesto, SHA-256, tamaño e integridad
verificable.

## Restore drill

La UI ejecuta restauraciones sobre una copia temporal. No restaura sobre la
base productiva desde esta pantalla.

## Preparación de V3

La pantalla muestra evidencia SOMBRA y preflight. Las capacidades I12/I13
también permiten evaluar la readiness completa de canary.

El modo persistente del Motor de Pagos se controla desde su propia pantalla y
queda auditado.

## Límites

Todavía no existe:

- almacenamiento externo de backups;
- replicación o alta disponibilidad;
- cifrado de backups;
- autenticación multiusuario;
- RTO/RPO medidos.

K5 no pretende sustituir un plan completo de continuidad de negocio.
