# J2 — Backup verificable y restore drill

## Objetivo

J2 agrega una capacidad operativa mínima y reproducible para detectar
problemas de integridad y demostrar que una base SQLite puede recuperarse.

No modifica reglas financieras ni activa V3.

## Qué se verifica

El health check ejecuta tres controles:

1. PRAGMA quick_check;
2. PRAGMA integrity_check;
3. PRAGMA foreign_key_check.

Una base solo se considera íntegra cuando los tres pasan.

## Backup

El backup usa la API online backup de SQLite mediante Connection.backup().
Esto permite copiar una base consistente mientras la aplicación mantiene su
conexión y puede tener WAL activo.

Cada backup produce:

- un archivo SQLite autocontenido;
- un manifiesto JSON;
- un SHA-256 del archivo;
- tamaño del archivo;
- evidencia de integridad.

El destino no puede existir previamente. Esta política evita sobrescrituras
accidentales.

## Restore

El restore solo admite una ruta destino que todavía no exista.

El procedimiento es:

1. verificar manifiesto y SHA-256 del backup;
2. copiar el artefacto a una ruta temporal;
3. publicar la restauración sin sobrescribir otro archivo;
4. ejecutar los mismos controles de integridad;
5. devolver evidencia verificable del resultado.

Esto sirve tanto para recuperación como para un restore drill.

## CLI

Health check:

    python scripts/backup_sqlite.py integrity datos/prestamos.db

Crear backup:

    python scripts/backup_sqlite.py create datos/prestamos.db backups/prestamos-001.db

Verificar backup:

    python scripts/backup_sqlite.py verify backups/prestamos-001.db

Restaurar:

    python scripts/backup_sqlite.py restore backups/prestamos-001.db restore/prestamos.db

Las rutas son ejemplos. La base financiera local y los artefactos de backup
siguen fuera de Git.

## Límites actuales

J2 no resuelve por sí solo:

- almacenamiento externo;
- replicación;
- alta disponibilidad;
- recuperación ante pérdida física del equipo;
- objetivos RTO/RPO definitivos;
- cifrado o gestión de claves.

Esos temas requieren una etapa operativa posterior y decisiones de
infraestructura reales.


## Restore drill sintético del dominio

El script `scripts/restore_drill_sintetico.py` automatiza una prueba más representativa que la fixture genérica:

- crea una base aislada en una ruta nueva y aplica el esquema vigente;
- registra dos personas con roles de deudor e inversor;
- crea un préstamo francés mensual de prueba con participación de inversor;
- registra un pago mediante el servicio Legacy que mantiene la autoridad operativa actual;
- captura el esquema SQL, migraciones, secuencias y registros de personas, préstamo, tasas, cuotas, participación, pago, imputaciones, ledger y auditoría;
- crea y verifica el backup, restaura en otro archivo, vuelve a abrir la restauración con `BaseDatos` y compara el snapshot lógico completo;
- comprueba que el archivo de origen no cambió, que el ledger siga cuadrado y que un backup alterado no se pueda restaurar;
- no lee ni modifica `PRESTAMOS_DB_PATH`, no usa datos personales reales y no sobrescribe un directorio existente.

### Ejecución

Elegí una ruta nueva, por ejemplo:

    python scripts/restore_drill_sintetico.py --directorio /tmp/prestamos-restore-drill-2026-11-26

El resultado se imprime como JSON e informa rutas, cantidades de registros, hashes, versión de esquema y resultado de cada control. El directorio de salida queda disponible para inspección. No subir esos artefactos a Git.

Para abrir manualmente la copia restaurada:

    PRESTAMOS_DB_PATH="/tmp/prestamos-restore-drill-2026-11-26/restore/prestamos_restaurados.db" streamlit run ui/app.py

La prueba automatizada demuestra que la base restaurada puede abrirse y consultarse mediante las capas de infraestructura y repositorios. **No demuestra por sí sola la aceptación visual de la UI ni el reinicio manual de la aplicación en un entorno de usuario.** Esos pasos siguen siendo parte de #374 y del paquete de aceptación de #223. No usar una base financiera real para ensayar este procedimiento.
