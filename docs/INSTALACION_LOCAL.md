# Instalación local reproducible

Esta guía sirve para Windows (PowerShell y CMD), macOS y Linux. Los comandos
preparan el entorno local y dejan explícita la ruta de la base. No necesitás
crear un segundo administrador si la base elegida ya tiene cuentas de acceso.

## Requisitos

- Python 3.11 o posterior.
- Git para clonar o actualizar el repositorio.
- Conexión a Internet durante la instalación de dependencias.
- Un navegador para abrir Streamlit en `http://localhost:8501`.

La instalación es local. No publiques el puerto ni expongas la aplicación a
Internet: el login disponible no equivale a una solución de identidad online.

## 1. Obtener el código

Si todavía no tenés una copia:

```bash
git clone https://github.com/JavierGrecco/prestamos_privados.git
cd prestamos_privados
```

Si ya tenés el repositorio, no vuelvas a clonarlo. Entrá a la carpeta exacta
que querés utilizar y revisá `git status` antes de actualizar.

## 2. Crear el entorno e instalar dependencias

El ayudante comprueba Python 3.11+, verifica que estás en la raíz de este
checkout, crea `.venv` si hace falta e instala dependencias. No abre ni migra la
base. Si encuentra un `.venv` incompleto o copiado de otro sistema, se detiene
en lugar de borrarlo silenciosamente.

### Windows — PowerShell

Desde la raíz del repositorio:

```powershell
py -3.11 scripts\preparar_entorno.py
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
```

Si PowerShell bloquea la activación, no cambies la política del equipo a ciegas.
Podés invocar el intérprete del entorno directamente:

```powershell
.\.venv\Scripts\python.exe scripts\iniciar_local.py --db datos\prestamos-local.db
```

### Windows — CMD

Desde la raíz:

```bat
py -3.11 scripts\preparar_entorno.py
.\.venv\Scripts\activate.bat
python --version
python -c "import sys; print(sys.executable)"
```

### macOS y Linux

Desde la raíz:

```bash
python3.11 scripts/preparar_entorno.py
source .venv/bin/activate
python --version
python -c "import sys; print(sys.executable)"
```

Si el alias `python3.11` no existe, usá el comando disponible para Python
3.11 o posterior, por ejemplo `python3`, y comprobá la versión antes de seguir.

El comando instala herramientas de desarrollo por defecto. Para instalar solo
las dependencias de ejecución, usá `python scripts/preparar_entorno.py --runtime`.

## 3. Iniciar la aplicación con una base explícita

Activá el entorno `.venv` de este repositorio y ejecutá desde su raíz. Elegí
una ruta que identifique claramente la base que querés usar.

### Windows — PowerShell o CMD

```powershell
python scripts\iniciar_local.py --db datos\prestamos-local.db
```

### macOS y Linux

```bash
python scripts/iniciar_local.py --db "$PWD/datos/prestamos-local.db"
```

El ayudante imprime qué archivo SQLite seleccionó e inspecciona su historial:

- **Base nueva:** prepara el esquema y luego inicia la aplicación.
- **Base actualizada:** inicia sin migrar.
- **Base con migraciones pendientes:** se detiene sin alterar el esquema.
- **Historial desconocido o inválido:** se detiene para que se revise una copia.

La aplicación se abre en `http://localhost:8501`.

## 4. Primera cuenta o cuenta existente

La pantalla depende de las cuentas de acceso guardadas en **esa base**:

- Si no existen cuentas, aparece **Configurar administrador local**. Creá una
  contraseña larga, de al menos 12 caracteres, y guardala de forma segura.
- Si ya existe una cuenta, aparece **Iniciar sesión**. Usá tu usuario actual;
  no hace falta crear otro ADMIN.
- Las personas de la cartera (deudores, inversores o garantes) no son cuentas
  de acceso. Puede haber personas y préstamos sin un usuario local.
- Si aparece el asistente de ADMIN cuando esperabas encontrar una cuenta, no
  sigas creando usuarios. Comprobá la ruta que imprime el ayudante y confirmá
  que sea el archivo correcto; es fácil estar usando otra base o checkout.

La primera cuenta se crea una sola vez por base. Las cuentas adicionales se
gestionan desde **Usuarios**, según los permisos de la cuenta autenticada. El
tema se puede elegir antes de iniciar sesión; oscuro es el predeterminado.

## 5. Actualizar una base existente

Primero inspeccioná el estado. Esto no aplica migraciones:

```bash
python -m scripts.migrar_base datos/prestamos.db
```

Si hay migraciones pendientes, el iniciador se detiene. Solo después de revisar
el resultado y autorizar el cambio, elegí una ruta de backup nueva.

Ejemplo para macOS/Linux (creá antes la carpeta `datos/backups` si no existe):

```bash
mkdir -p datos/backups
python scripts/iniciar_local.py \
  --db "$PWD/datos/prestamos.db" \
  --actualizar-migraciones \
  --backup "$PWD/datos/backups/prestamos-antes-$(date +%Y%m%d-%H%M%S).db"
```

En PowerShell, primero creá la carpeta si hace falta y usá una ruta nueva:

```powershell
New-Item -ItemType Directory -Force datos\backups
python scripts\iniciar_local.py --db datos\prestamos.db --actualizar-migraciones --backup datos\backups\prestamos-antes-20261009.db
```

En CMD:

```bat
if not exist datos\backups mkdir datos\backups
python scripts\iniciar_local.py --db datos\prestamos.db --actualizar-migraciones --backup datos\backups\prestamos-antes-20261009.db
```

El archivo de backup no debe existir todavía y no puede ser la misma ruta que
la base. El iniciador delega el proceso en `scripts.migrar_base`, que verifica
integridad y SHA-256 del backup antes de migrar. Si la migración o la comprobación
posterior falla, no inicia la interfaz.

Para historiales inválidos o bases sin versión reconocida, no fuerces el
procedimiento: conservá el original y revisá una copia.

## 6. Administrar o recuperar cuentas

Con una cuenta ADMIN activa, abrí **Usuarios** para crear cuentas OPERADOR o
LECTURA, modificar roles, desactivar cuentas y restablecer contraseñas. Los
cambios de seguridad invalidan la sesión anterior.

Si olvidaste la contraseña del ADMIN, desde una terminal local:

```bash
python -m scripts.restablecer_password_local datos/prestamos-local.db --usuario admin
```

La herramienta pide la nueva contraseña sin mostrarla. Requiere acceso al
archivo SQLite; no es una función web.

## 7. Problemas frecuentes

### El asistente pide crear ADMIN pero yo ya tenía un usuario

No crees otra cuenta. Compará la ruta que imprime el iniciador con la base que
usabas antes. Configurá `--db` explícitamente y volvé a iniciar. Las cuentas
están en SQLite; no se deducen del nombre de una persona ni de otra copia.

### El comando dice que no estoy en el entorno virtual de este checkout

Volvé a la raíz correcta, activá el `.venv` que está dentro de esa carpeta y
confirmá `python -c "import sys; print(sys.executable)"`. No reutilices el
entorno de otra copia o de otro sistema operativo.

### Una base existente necesita migraciones

La detención es deliberada. Inspeccioná la base y elegí un backup nuevo. No se
actualiza una base existente automáticamente al iniciar la UI.

## Validación conocida

Hay pruebas automatizadas para la raíz del checkout, Python mínimo, ubicación
del intérprete, inicialización de una base nueva y de un archivo SQLite vacío,
rechazo de migraciones silenciosas, actualización explícita con backup y
verificación de dependencias.

El workflow `local-install-smoke` prepara el entorno real y ejecuta las
regresiones en Ubuntu, Windows y macOS con Python 3.11. La matriz principal de
CI también valida la suite en Python 3.11–3.14, además de CodeQL y auditoría de
dependencias. Esto verifica el aprovisionamiento automatizado, pero no sustituye
una inspección manual de la aplicación en un navegador de cada sistema.

Los manifiestos actuales declaran rangos de versiones y no constituyen un lock
transitivo exacto de todas las dependencias. El procedimiento y la versión
mínima se verifican, pero dos instalaciones en fechas distintas podrían resolver
versiones diferentes. La fijación completa del árbol de dependencias, si se
requiere repetibilidad bit a bit, debe tratarse como una tarea diferenciada.

La inspección manual de la UI, el primer acceso y el reinicio deben registrarse
por plataforma después de ejecutarlos en un entorno real. No se afirma que esas
comprobaciones manuales se hayan realizado cuando solo hay pruebas automatizadas.
