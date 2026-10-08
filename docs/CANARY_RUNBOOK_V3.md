# L1.1 — Runbook de canary y cut-over del Motor de Pagos V3

> Este documento prepara la ejecución operativa. No implica que el canary real haya sido ejecutado.

## Objetivo

Pasar de readiness técnico a una activación controlada de V3 sobre una copia operativa o una base de operación expresamente autorizada, manteniendo evidencia y rollback entre operaciones.

## Regla de oro

El cambio de motor es una operación de configuración separada. Nunca se cambia de motor dentro de una transacción financiera ya iniciada y nunca se usa fallback automático después de una escritura parcial.

## 0. Preparar evidencia

Usar una carpeta de evidencia fuera del repositorio Git, por ejemplo:

~~~text
evidencia/
  canary-readiness-YYYY-MM-DDTHHMMSSZ.json
  backup/
  notas/
~~~

No versionar bases SQLite, WAL/SHM, backups ni datos financieros.

## 1. Obtener una base controlada

Trabajar sobre una copia autorizada de la base real. El canary no debe comenzar sobre el único original disponible.

Registrar externamente qué base se evaluó y qué operador realizó la revisión.

## 2. Backup verificable

Crear un backup en una ruta nueva:

~~~bash
python scripts/backup_sqlite.py create datos/prestamos.db evidencia/backup/prestamos-canary.db
~~~

Verificarlo:

~~~bash
python scripts/backup_sqlite.py verify evidencia/backup/prestamos-canary.db
~~~

También ejecutar el health check sobre la base controlada:

~~~bash
python scripts/backup_sqlite.py integrity datos/prestamos.db
~~~

El backup y su SHA-256 deben conservarse junto con la decisión de canary.

## 3. Precheck y evidencia fechada

Ejecutar el mismo readiness que consume la UI:

~~~bash
python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db \
  --output evidencia/canary-readiness-YYYY-MM-DDTHHMMSSZ.json
~~~

El comando debe devolver `0` solo cuando la base esté lista. Un `2` es rechazo controlado; un `1` es error operativo.

Usar un nombre nuevo para cada evidencia. No reemplazar archivos históricos salvo que exista una razón operativa explícita y se utilice `--force-output`.

## 4. Revisión humana

Antes de activar V3, comprobar:

- integridad aprobada;
- schema mínimo aprobado;
- al menos el volumen configurado de ejecuciones SOMBRA;
- divergencias dentro del umbral;
- errores SOMBRA dentro del umbral;
- tasa de coincidencia dentro del umbral;
- modo persistido en `LEGACY` o `SOMBRA`;
- backup verificable;
- operador identificado y motivo de canary registrado.

Una divergencia no debe aceptarse por desconocimiento. Debe quedar explicada y aceptada expresamente o bloquear el canary.

## 5. Activar V3

Desde Streamlit:

1. abrir **Motor de Pagos V3**;
2. verificar que la readiness siga aprobada;
3. seleccionar `V3`;
4. informar un motivo explícito, por ejemplo `Canary V3 <fecha>`;
5. aplicar el cambio;
6. verificar que la revisión del modo aumentó y que la auditoría contiene el cambio.

La activación vuelve a ejecutar el preflight en la capa de aplicación; no debe confiar únicamente en una pantalla anterior.

## 6. Ejecutar la primera operación canary

Registrar una sola operación controlada y previamente revisada.

Antes de confirmar, comprobar en la UI el preview canónico V3 y la revisión del préstamo.

Después de confirmar, verificar como mínimo:

- `pagos.motor_version` identifica V3;
- `plan_json` existe y es JSON válido;
- `plan_hash` concilia con `plan_json`;
- las imputaciones suman exactamente el monto recibido;
- ledger balanceado;
- correlación común entre ledger y auditoría;
- la operación queda trazable por operador y correlación.

Usar los read models y las herramientas de integridad existentes. No modificar manualmente los hechos para que la prueba pase.

## 7. Decidir continuidad

Solo continuar cuando la primera operación canary haya sido revisada y la evidencia sea satisfactoria.

Si aparece una incidencia que no estaba dentro de los criterios aceptados, detener el canary y registrar la decisión.

## 8. Rollback

Para volver a Legacy:

1. finalizar la operación corriente; nunca interrumpirla cambiando el motor;
2. abrir la configuración del Motor de Pagos;
3. seleccionar `LEGACY`;
4. proporcionar el motivo del rollback;
5. aplicar el cambio;
6. verificar la nueva revisión y la auditoría;
7. construir el siguiente comando desde el estado financiero posterior a la operación V3;
8. comprobar que la siguiente operación use Legacy.

El rollback no borra ni reescribe la operación V3 anterior.

## 9. Criterio de cierre del canary

Conservar como mínimo:

- backup verificable;
- JSON de readiness previo;
- resultado de la primera operación V3;
- evidencia de auditoría/ledger/correlación;
- decisión de continuar o hacer rollback;
- cualquier incidente y su tratamiento.

El canary real de una base operativa sigue siendo una actividad manual y autorizada. Este repositorio proporciona controles para ejecutarla, pero no la ejecuta automáticamente.

## 10. Después del canary

Actualizar el issue operativo correspondiente con métricas, evidencia y decisión.

Legacy no debe retirarse todavía. Su eliminación requiere una matriz de consumidores actualizada, equivalencia suficiente, recuperación, idempotencia, concurrencia y trazabilidad demostradas.