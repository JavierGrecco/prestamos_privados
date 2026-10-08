# K5 — Operación segura desde la UI

K5 expone en Streamlit las operaciones operativas que ya existen en infraestructura, pero limita deliberadamente las acciones peligrosas.

## Salud de la base

La pantalla ejecuta quick_check, integrity_check y foreign_key_check sobre la base activa. Una falla se presenta como incidente operativo y no como un resultado financiero.

## Backups

Los backups se guardan localmente en `datos/backups/`, un directorio excluido de Git.

Crear un backup requiere confirmación explícita y nunca sobrescribe un archivo existente. Cada backup se acompaña de un manifiesto con SHA-256 y tamaño y se verifica antes de considerarlo válido.

## Verificación

Un backup puede verificarse posteriormente. Se comprueban manifiesto, tamaño, SHA-256 e integridad SQLite.

## Restore drill

La UI permite ejecutar un restore drill sobre una copia temporal. La restauración temporal se elimina automáticamente al finalizar.

Esta pantalla **no** tiene una operación de restauración sobre `datos/prestamos.db` ni sobre otra base productiva.

## Preparación de V3

También se muestran métricas SOMBRA y el resultado de preflight ya existentes.

El preflight sigue siendo un gate de solo lectura: la pantalla no activa V3 por sí misma.

## Límites

K5 no proporciona todavía almacenamiento externo, replicación, alta disponibilidad, cifrado de backups, autenticación multiusuario ni RTO/RPO medidos.