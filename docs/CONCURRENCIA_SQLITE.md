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
- Un segundo hilo puede solicitar una transacción, pero no se incorpora a la
  transacción de otro hilo. Espera a que esa unidad de trabajo termine.

La prueba `tests/test_db_concurrencia.py` fuerza una carrera: el hilo A inserta
un movimiento y después falla; el hilo B intenta insertar otro movimiento en
la misma instancia. La condición esperada es que el rollback de A elimine solo
A, y que B pueda ejecutarse y confirmar su propio movimiento posteriormente.

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

## Validación pendiente

El hardening actual se verifica con pruebas deterministas de concurrencia sobre
la misma instancia y con toda la suite de tests. El issue
[#159 — Aislar conexiones SQLite y transacciones entre sesiones](https://github.com/JavierGrecco/prestamos_privados/issues/159)
sigue abierto hasta añadir una prueba end-to-end de dos sesiones UI, pagos
concurrentes al mismo préstamo, idempotencia y comportamiento bajo contención.
