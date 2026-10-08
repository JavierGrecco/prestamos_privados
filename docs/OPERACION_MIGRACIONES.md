# Operación de migraciones de SQLite

## Objetivo

Evitar que abrir la interfaz actualice silenciosamente una base existente. Las
migraciones cambian el esquema y pueden incluir backfills; por eso una base con
datos debe actualizarse de forma explícita y con una copia verificable previa.

## Comportamiento de la aplicación

- **Base nueva o vacía:** la primera apertura prepara el esquema automáticamente
  para que el inicio local siga siendo sencillo.
- **Base existente y actualizada:** la interfaz abre normalmente.
- **Base existente con migraciones pendientes:** la interfaz muestra la versión
  origen y destino, se detiene y no ejecuta el upgrade. El comando indicado
  permite crear un backup verificado y luego aplicar los cambios.
- **Historial ausente, incompleto o desconocido:** la aplicación no intenta
  adivinar la versión ni aplicar migraciones. Requiere revisión de una copia.

## 1. Inspeccionar antes de actualizar

El comando por defecto informa la versión registrada, la versión objetivo y las
migraciones pendientes. No aplica migraciones ni crea la tabla de historial.

```bash
python -m scripts.migrar_base datos/prestamos.db
```

La salida es JSON para poder conservarla como evidencia y procesarla después.
Si la ruta todavía no existe, el modo de inspección no crea el archivo.

## 2. Actualizar una base existente

Usá una ruta de backup **nueva**, que no exista todavía:

```bash
python -m scripts.migrar_base datos/prestamos.db \
  --aplicar \
  --backup backups/prestamos-pre-migracion-20261008.db
```

El comando se niega a actualizar una base existente sin `--backup`. Antes de
aplicar cambios crea una copia autocontenida con la API de backup de SQLite,
verifica integridad y claves foráneas, genera su manifiesto y registra SHA-256.
Si la copia no pasa las verificaciones, cancela la migración.

Se puede comprobar el artefacto por separado:

```bash
python -m scripts.backup_sqlite verify backups/prestamos-pre-migracion-20261008.db
```

El backup y su manifiesto no se sobrescriben. Para un nuevo intento, conservá la
evidencia anterior y elegí otra ruta.

## 3. Inicializar una base nueva

Para preparar una base vacía desde la terminal:

```bash
python -m scripts.migrar_base datos/nueva.db --aplicar
```

No hace falta un backup para una base nueva que no contiene datos. La UI también
puede inicializarla durante su primer arranque.

## Casos que requieren revisión humana

Una base con tablas de aplicación, pero sin historial de migraciones reconocido,
no se trata automáticamente como una base nueva. Lo mismo ocurre si el historial
contiene versiones desconocidas o saltos. En esos casos, no ejecutes migraciones
a ciegas: preservá el archivo original, trabajá sobre una copia y reconstruí su
procedencia antes de continuar.

Cada migración tiene una transacción propia. Si una migración falla, la
transacción de esa migración se revierte y la UI no abre una base que todavía
tiene cambios pendientes. Las migraciones anteriores que ya se confirmaron
siguen registradas; para reintentar, inspeccioná el estado resultante y creá un
nuevo backup antes de repetir la operación.

## Alcance actual

Esta capa elimina el upgrade silencioso al iniciar la UI y ofrece inspección,
backup verificable y ejecución explícita. El issue
[#160 — Separar migraciones del arranque](https://github.com/JavierGrecco/prestamos_privados/issues/160)
permanece abierto hasta ampliar pruebas de fallos inyectados, recuperación
operativa y la experiencia de revisión de bases históricas sin versionado.
