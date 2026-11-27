# Concurrencia de SQLite y la interfaz

## Ciclo de vida de la conexión en Streamlit

La UI obtiene su recurso mediante
`st.cache_resource(scope="session", on_release=liberar_recurso_db)`.
La conexión se reutiliza entre reruns de la misma sesión, pero no se comparte
con otras sesiones. Todas las instancias apuntan al mismo archivo SQLite local:
los datos siguen siendo comunes, mientras que la conexión y el estado de cada
unidad de trabajo quedan aislados.

Cuando Streamlit libera una sesión, `liberar_recurso_db()` invoca
`BaseDatos.cerrar()`. El cierre es idempotente y realiza el checkpoint WAL
cuando corresponde. La composición de infraestructura sigue siendo responsable
de abrir e inspeccionar la base; la UI solo controla el ciclo de vida del
recurso que recibió.

Este cambio no crea una base por usuario, no habilita acceso remoto ni sustituye
la autorización de personas. Reduce la posibilidad de mezclar conexiones y
contadores transaccionales entre sesiones del mismo proceso.

## Problema que resolvemos

Con el alcance global predeterminado de `st.cache_resource`, distintas
sesiones podían recibir el mismo objeto `BaseDatos`. Aunque esa instancia
protege sus operaciones públicas con un `RLock`, compartirla acopla el estado
de las sesiones y provoca que todas compitan por el mismo recurso. El diseño
actual conserva un recurso por sesión y permite que SQLite coordine las
conexiones independientes sobre el mismo archivo.

## Garantía implementada

Cada instancia de `BaseDatos` posee un `threading.RLock` compartido por sus
operaciones públicas. Como Streamlit entrega una instancia por sesión, el lock
protege los hilos que puedan usar esa conexión, sin serializar a todas las
sesiones entre sí.

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

La prueba `tests/test_db_concurrencia.py` fuerza una carrera dentro de una
misma instancia: el hilo A inserta un movimiento y después falla; el hilo B
intenta insertar otro movimiento. El rollback de A debe eliminar solo A, y B
debe confirmar su propio movimiento cuando obtiene el lock.

La prueba `tests/test_ui_sesiones_sqlite.py` ejecuta dos sesiones Streamlit
separadas contra el mismo archivo SQLite. Verifica que reciben objetos
`BaseDatos` distintos y que una escritura confirmada por la sesión A queda
visible para la sesión B a través de su conexión independiente. También verifica
que el liberador cierra el recurso y tolera un cierre repetido.

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

La conexión se aísla por sesión dentro de **un mismo proceso Python**. Las
sesiones siguen leyendo y escribiendo el mismo archivo; SQLite coordina las
conexiones independientes mediante sus bloqueos y
`busy_timeout=5000`. El `RLock` protege una instancia concreta y no coordina
procesos diferentes.

Esto evita compartir un cursor, conexión o contador transaccional entre
sesiones, pero no convierte la UI en un servicio remoto multiusuario
autenticado ni reemplaza las políticas de autorización. La identidad del
operador sigue siendo local. Tampoco demuestra escalabilidad para varios
procesos o despliegue en Internet.

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
sola fila, una auditoría y el ledger cuadrado.

## Validación automatizada del circuito de pagos

La prueba E2E `tests/test_k8_ui_pago_e2e.py` recorre tres escenarios mediante
AppTest sobre el entrypoint de Streamlit. Es integración de UI, pero no abre
un servidor HTTP ni un navegador real:

- Dos sesiones Streamlit independientes confirman la misma intención en
  paralelo. Se conserva un único pago, una auditoría, una ejecución SOMBRA y
  un ledger cuadrado.
- Dos sesiones abren el mismo preview, pero representan intenciones distintas.
  La primera confirma y avanza la revisión; la segunda detecta que su preview
  quedó obsoleto, bloquea la confirmación y exige una revisión explícita antes
  de habilitarla.
- Se inyecta un fallo después de escribir la auditoría. El snapshot de las
  tablas persistentes debe quedar idéntico al previo: pago, imputaciones,
  cuotas, ledger, auditoría, observabilidad y revisión se revierten juntos.

La prueba de integración
`tests/test_idempotencia_pago_legacy.py::test_legacy_rechaza_una_intencion_distinta_con_revision_obsoleta`
comprueba la defensa en la capa de aplicación, fuera de Streamlit. El test de
reintento usa además la revisión original ya vencida: la misma clave y huella
devuelven el pago previo sin incrementar de nuevo la revisión. La idempotencia
se resuelve antes de comprobar la revisión de una nueva intención.

## Revisión optimista en Legacy y SOMBRA

El preview del motor V3 contiene `revision_prestamo`. La interfaz conserva la
revisión que presentó al usuario durante la operación; un rerun no la reemplaza
silenciosamente por la versión actual. Si detecta una diferencia en una
intención nueva, muestra el aviso y exige pulsar **Actualizar cálculo y
revisar**. La única excepción es una clave de idempotencia que quedó pendiente
tras un resultado transaccional incierto: en ese caso permite repetir el mismo
comando, sin cambiar datos ni clave, para que el servicio compruebe si ya se
confirmó. Si no existe el pago, la revisión obsoleta sigue rechazando la
intención; si el contenido cambió, la huella evita reutilizar esa clave.

Al confirmar, el comando envía esa revisión tanto en modo V3 como en SOMBRA.
En SOMBRA, Legacy sigue siendo el escritor efectivo, por lo que
`ManejadorRegistroPagoLegacy` comprueba la revisión dentro de
`BEGIN IMMEDIATE`, después de resolver una repetición idempotente. Si la
intención es nueva y la revisión ya no coincide, rechaza la operación antes de
mutar el préstamo. Cuando el pago es válido, incrementa la revisión dentro de
la misma unidad de trabajo que guarda pago, imputaciones, cuotas, ledger y
auditoría. Un rollback también revierte ese incremento.

La composición de SOMBRA transmite además `fecha_valor` al servicio Legacy;
la fecha económica del cálculo ya no se pierde al pasar de la pantalla al
escritor efectivo.

## Aceptación automatizada con navegador real

La prueba `tests/test_ui_browser_concurrency.py` inicia un único proceso
Streamlit con una base SQLite sintética y abre dos contextos Chromium separados.
Cada contexto tiene cookies/sesión de navegador independientes; ambos trabajan
sobre el mismo préstamo y el mismo archivo de datos.

El recorrido comprueba que:

1. Las dos sesiones abren el preview antes de que cambie la revisión.
2. La sesión A confirma el pago y la base avanza una sola revisión.
3. La sesión B intenta confirmar desde su preview anterior.
4. La UI detecta la revisión obsoleta, muestra el aviso, descarta la
   confirmación pendiente y deshabilita el botón de pago.
5. La sesión B solo vuelve a habilitar una nueva confirmación después de pulsar
   **Actualizar cálculo y revisar**; ese paso no registra por sí mismo otro pago.

La prueba también comprueba en SQLite que el intento obsoleto no crea una
segunda fila de pago ni avanza otra vez la revisión. Se ejecuta junto con la
aceptación XSS en el workflow `.github/workflows/browser-security.yml`.

Comando local (el test levanta y detiene su propio servidor y usa una base
temporal; no requiere ni debe apuntar a una base de producción):

```bash
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python -m pytest -q tests/test_ui_browser_concurrency.py
```

Esta aceptación real de navegador complementa, pero no reemplaza, los tests de
idempotencia/reintento con resultado incierto de `tests/test_k8_ui_pago_e2e.py`
y de servicios. Tampoco equivale a una exploración manual de operación ni
demuestra concurrencia entre procesos del sistema operativo.

## Validación manual pendiente

Las regresiones automatizadas cubren el rechazo por revisión obsoleta, el
reintento idempotente, el rollback inyectado y los invariantes de ledger y
auditoría. Sigue pendiente la aceptación manual en navegador con el flujo
operativo completo y la inspección visual del aviso de preview obsoleto.

El issue [#159 — Aislar conexiones SQLite y transacciones entre sesiones](https://github.com/JavierGrecco/prestamos_privados/issues/159)
permanece abierto hasta registrar esa aceptación manual. El cambio actual no
habilita despliegue remoto ni autenticación multiusuario.