# Concurrencia de SQLite y la interfaz

## Problema que resolvemos

La interfaz mantiene la instancia `BaseDatos` en `st.cache_resource`. Ese tipo
de recurso puede compartirse entre ejecuciones de la UI, así que no corresponde
suponer que cada sesión tiene una conexión independiente.

Antes de esta mejora, `BaseDatos` utilizaba un contador de profundidad de
transacciones por instancia, pero no bloqueaba la unidad de trabajo completa.
Dos hilos podían entrar simultáneamente en `transaccion()`: el segundo podía
interpretarse como una transacción anidada dentro de la primera. Un rollback
ajeno podía entonces borrar un cambio de otra sesión o permitir que cambios de
una operación fallida quedaran confirmados.

## Garantía implementada

Cada instancia de `BaseDatos` posee un `threading.RLock` compartido por sus
operaciones públicas.

- La transacción exterior adquiere el lock antes de iniciar `BEGIN` y lo
  conserva hasta que termina en `COMMIT` o `ROLLBACK`.
- Las transacciones anidadas del mismo hilo son reentrantes y siguen formando
  parte de la unidad de trabajo exterior.
- Las operaciones `ejecutar`, `consultar`, `consultar_uno`,
  `ultimo_id_insertado`, las verificaciones de integridad, la apertura y el
  cierre usan el mismo lock.
- Los adaptadores que administran `BEGIN` y `COMMIT/ROLLBACK` en métodos
  separados deben mantener el lock entre esas llamadas. Para eso, la API
  `bloqueo_transaccion_explicita()` conserva el mismo `RLock` durante toda la
  unidad de trabajo sin iniciar por sí misma una transacción SQL.
- El repositorio de pagos V3 adquiere ese bloqueo antes de `BEGIN IMMEDIATE`
  y lo libera únicamente después de `COMMIT` o `ROLLBACK`. El estado del
  contexto se guarda por hilo, para que dos repositorios/servicios compartan
  la misma instancia sin sobrescribir el bloqueo de la otra unidad de trabajo.
- Un segundo hilo puede solicitar una transacción, pero no se incorpora a la
  transacción de otro hilo. Espera a que esa unidad de trabajo termine.

La prueba `tests/test_db_concurrencia.py` fuerza una carrera: el hilo A inserta
un movimiento y después falla; el hilo B intenta insertar otro movimiento en
la misma instancia. La condición esperada es que el rollback de A elimine solo
A, y que B pueda ejecutarse y confirmar su propio movimiento posteriormente.

Los snapshots append-only de condiciones de carencia también reservan el turno de
escritura con transaccion(inmediata=True) antes de leer la última
version_contrato. La lectura del máximo, la generación del JSON/hash y el
INSERT quedan dentro de una única unidad atómica. Así, dos conexiones
SQLite independientes no eligen simultáneamente el mismo número de versión.
Una llamada dentro del alta completa se incorpora a la transacción exterior;
el modo de inicio de esa transacción no se cambia retroactivamente.
La prueba `test_h3_dos_pagos_concurrentes_serializan_una_base_datos_compartida`
cubre específicamente el registro V3: dos servicios usan la misma instancia de
`BaseDatos` y parten de la misma revisión. El segundo inicio debe esperar;
tras confirmar el primero, el segundo relee el estado actualizado y rechaza la
revisión obsoleta, sin crear un segundo pago.

## Alcance y límites

Este cambio coordina una instancia compartida dentro de **un mismo proceso
Python**. No convierte la UI en un servicio multiusuario autenticado ni
reemplaza las políticas de autorización. La identidad del operador sigue siendo
un asunto separado.

SQLite sigue coordinando conexiones diferentes y procesos mediante sus propios
bloqueos; `busy_timeout=5000` mantiene el límite de espera configurado para
esos casos. El `RLock` no coordina procesos diferentes.

El costo deliberado es que las operaciones sobre una misma instancia se
serializan. Si se necesita mayor concurrencia o despliegue web multiusuario,
el siguiente paso arquitectónico debería ser un ciclo de vida de conexión por
unidad de trabajo o sesión y, llegado el caso, una base de datos de servidor.
No se afirma que el cambio actual resuelva escalabilidad ni reemplaza una
prueba end-to-end con dos sesiones reales de Streamlit.

La propiedad `BaseDatos.conexion` expone la conexión SQLite para operaciones
avanzadas. No debe usarse para realizar consultas o transacciones concurrentes
fuera de los métodos protegidos.

La regresión
`tests/test_repositorio_condiciones_carencia.py::test_conexiones_sqlite_independientes_serializan_versiones_concurrentes`
abre dos conexiones al mismo archivo y comprueba que dos escrituras simultáneas
generan las versiones 1 y 2, ambas con hash verificable. Esto cubre la asignación
de versiones del snapshot, no demuestra aún el ciclo E2E completo de alta de
préstamo con carencia, cuotas y pagos.

La ruta Legacy de registro de pagos también conserva el bloqueo de escritura
desde antes de leer la deuda hasta que se confirman pago, imputaciones, cuotas,
ledger y auditoría. La interfaz entrega la clave de idempotencia de la intención
de pago junto con su huella SHA-256; una repetición con la misma clave y huella
devuelve el pago original, mientras que reutilizar la clave con otro contenido
se rechaza. Esto usa las columnas e índice único ya introducidos en la migración
v009, sin alterar la política de imputación financiera.

La prueba
`tests/test_idempotencia_pago_legacy.py::test_dos_conexiones_reintentando_la_misma_operacion_crean_un_solo_pago`
ejecuta dos servicios con conexiones SQLite independientes. Ambos envían la
misma intención simultáneamente y deben recibir el mismo ID de pago, con una
sola fila, una auditoría y el ledger cuadrado. Sigue pendiente probar dos
sesiones Streamlit completas en navegador y la concurrencia de intenciones
distintas para el mismo préstamo.
## Validación pendiente

El hardening actual se verifica con pruebas deterministas de concurrencia sobre
la misma instancia y con toda la suite de tests. El issue
[#159 — Aislar conexiones SQLite y transacciones entre sesiones](https://github.com/JavierGrecco/prestamos_privados/issues/159)
sigue abierto hasta añadir una prueba end-to-end de dos sesiones UI, pagos
concurrentes al mismo préstamo, idempotencia y comportamiento bajo contención.
