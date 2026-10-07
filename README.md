# Préstamos Privados

Motor financiero para administrar préstamos privados con uno o varios inversores, cuotas, pagos, mora, adelantos y trazabilidad contable.

El proyecto está construido en Python y usa Streamlit como interfaz local. La lógica financiera está separada de la interfaz y de la persistencia para que las reglas puedan probarse de forma independiente.

> **Estado del proyecto:** proyecto en evolución. El objetivo es construir un motor financiero claro, preciso y auditable, no un sistema bancario de producción.

## ¿Qué hace?

La aplicación permite modelar un préstamo y seguir su vida completa:

- Crear préstamos con uno o varios inversores.
- Generar cuadros de amortización.
- Trabajar con sistemas Francés, Alemán, Interest Only y Personalizado.
- Definir TNA o TEA y distintas convenciones de días.
- Registrar pagos completos y parciales.
- Gestionar mora y capital pendiente.
- Analizar pagos que superan la cuota y aplicar adelantos mediante RAI o RNI.
- Distribuir los cobros entre los inversores según su participación.
- Mantener ledger y auditoría de las operaciones importantes.
- Trabajar con `Decimal` para evitar errores de representación de dinero.
- Analizar el resultado financiero del préstamo y flujos mediante métricas como XIRR.

## Arquitectura

El proyecto está organizado por responsabilidades:

```text
                 Streamlit / UI
                       │
                       ▼
              Servicios de aplicación
                       │
                       ▼
               Dominio financiero
              /         │          \
             /          │           \
            ▼           ▼            ▼
      Repositorios    Ledger      Auditoría
            │
            ▼
          SQLite
```

### `dominio/`

Contiene las reglas financieras. Acá viven los cálculos de intereses, amortización, mora, imputación, recálculos y otras reglas que no deberían depender de SQLite ni de Streamlit.

### `aplicacion/`

Orquesta los casos de uso. Por ejemplo, registrar un pago no consiste solamente en calcular números: también hay que guardar el pago, actualizar las cuotas, distribuir el dinero, registrar el ledger y dejar una entrada de auditoría.

### `infraestructura/`

Se ocupa de la persistencia y de los detalles técnicos: SQLite, repositorios, migraciones, ledger y auditoría.

### `ui/`

Es la interfaz de Streamlit. Su responsabilidad es mostrar información, recibir acciones del usuario y llamar a los servicios de aplicación. No debería contener las reglas financieras.

### `tests/`

Contiene las pruebas unitarias y de integración que protegen las reglas financieras y las operaciones de persistencia.

## Precisión financiera

El proyecto no representa importes monetarios con `float`. Se utiliza `Decimal` y los importes monetarios se normalizan a centavos.

Esto es importante porque una representación binaria de coma flotante puede introducir diferencias pequeñas que, acumuladas a lo largo de cuotas y pagos, terminan afectando los resultados financieros.

Las tasas se manejan con una precisión mayor que los importes monetarios para reducir errores durante los cálculos intermedios.

## Tecnologías y dependencias

### Requisitos

- Python 3.11 o superior.
- `pip`, incluido normalmente con Python.
- Un terminal.
- Un navegador web para utilizar la interfaz de Streamlit.

El proyecto declara Python `>=3.11` en `pyproject.toml`.

### Dependencias de la aplicación

| Paquete | Uso |
| --- | --- |
| `python-dateutil` | Manejo de fechas y cálculos asociados |
| `streamlit` | Interfaz web local |
| `plotly` | Gráficos y visualizaciones |

### Dependencias de desarrollo

| Paquete | Uso |
| --- | --- |
| `pytest` | Pruebas automatizadas |
| `pytest-cov` | Medición de cobertura de pruebas |

Las versiones mínimas se encuentran en `requirements.txt` y `pyproject.toml`.

## Instalación local

La forma recomendada es crear un entorno virtual específico para este proyecto. Python incluye `venv`, y utilizarlo evita mezclar las dependencias del proyecto con las del sistema.

### Windows — PowerShell

Desde la carpeta del proyecto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación del entorno, puede ser necesario habilitar scripts para el usuario actual:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Después, volver a ejecutar:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows — CMD

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Cuando el entorno está activo, el terminal normalmente muestra `(.venv)` al comienzo de la línea.

Para salir del entorno:

```bash
deactivate
```

## Verificar la instalación

Con el entorno virtual activo:

```bash
python --version
python -m pytest -q
```

El segundo comando ejecuta toda la suite de pruebas.

## Ejecutar la aplicación

La aplicación principal se encuentra en `ui/app.py`.

Con el entorno virtual activo:

```bash
python -m streamlit run ui/app.py
```

Streamlit levantará un servidor local. Por defecto, la configuración del proyecto utiliza el puerto `8501`, por lo que la aplicación queda disponible en:

```text
http://localhost:8501
```

Para detener la aplicación:

```text
Ctrl + C
```

## Cargar datos de ejemplo

Al iniciar por primera vez, la base puede estar vacía. El proyecto incluye un script de datos de ejemplo:

```bash
python scripts/seed_datos.py
```

El script crea personas, inversores y préstamos de demostración. Es idempotente: si ya existen personas, no vuelve a cargar los datos de ejemplo.

Después se puede iniciar la aplicación:

```bash
python -m streamlit run ui/app.py
```

## Base de datos

La aplicación utiliza SQLite.

La ubicación local por defecto es:

```text
datos/prestamos.db
```

Las migraciones pendientes se aplican al arrancar la aplicación, por lo que el usuario no necesita ejecutar una migración manual para utilizar una instalación normal.

La base local es un artefacto de ejecución. No debería utilizarse como parte del código fuente ni subirse al repositorio con datos personales o financieros reales.

## Ejecutar la demo de consola

También existe una demostración sin interfaz gráfica:

```bash
python demo.py
```

Sirve para observar algunos de los cálculos financieros del dominio desde la terminal.

## Ejecutar las pruebas

Suite completa:

```bash
python -m pytest -q
```

Con cobertura:

```bash
python -m pytest --cov=dominio --cov=aplicacion --cov=infraestructura --cov-report=term-missing
```

## Cómo está pensado el motor de pagos

Un pago no es simplemente "restar dinero".

El sistema necesita determinar, según el estado del préstamo:

1. qué cuota es la objetivo;
2. qué importes vienen arrastrados de períodos anteriores;
3. qué parte corresponde a mora, intereses y capital;
4. si el pago es parcial, normal o contiene un excedente;
5. qué cuotas cambian de estado;
6. cuánto se distribuye entre los inversores;
7. qué queda registrado en el ledger y en la auditoría.

Por eso las reglas financieras deben permanecer en una única autoridad de cálculo y la capa de aplicación debe ocuparse de persistir el resultado de esa decisión dentro de una transacción.

## Principios del proyecto

### Dinero con precisión

Los importes monetarios se manejan con `Decimal` y se redondean de forma explícita.

### Separación de responsabilidades

La UI no debería calcular intereses. Los repositorios no deberían decidir reglas financieras. Y una regla financiera importante no debería existir duplicada en varios servicios.

### Trazabilidad

Una operación importante debe poder reconstruirse: qué ocurrió, sobre qué préstamo, qué importes se aplicaron y cuándo se registró.

### Atomicidad

Registrar un pago implica varias escrituras relacionadas. La operación debe confirmarse completa o revertirse completa ante un error.

### Pruebas antes de refactorizar

En las partes financieras críticas, la refactorización se realiza sobre comportamiento conocido y protegido por regresiones. Primero se caracteriza el comportamiento existente; después se cambia la implementación.

## Estructura del repositorio

```text
.
├── aplicacion/        # Casos de uso y servicios
├── dominio/           # Reglas financieras puras
├── infraestructura/   # SQLite, repositorios, migraciones, ledger y auditoría
├── ui/                # Interfaz Streamlit
├── tests/             # Pruebas unitarias e integración
├── datos/             # Base SQLite local
├── docs/              # Documentación técnica
├── scripts/           # Utilidades y datos de ejemplo
├── demo.py            # Demostración de consola
├── pyproject.toml     # Metadata y configuración Python
└── requirements.txt   # Dependencias de instalación local
```

## Configuración de Streamlit

La configuración local se encuentra en:

```text
.streamlit/config.toml
```

Entre otras cosas, define el puerto utilizado por la aplicación y la configuración visual de Streamlit.

## Importante antes de usar datos reales

Este repositorio es un proyecto de ingeniería y demostración. No debe considerarse un sistema bancario listo para producción.

Antes de utilizar información financiera real habría que incorporar, como mínimo, autenticación y autorización, gestión de secretos, cifrado y protección de datos sensibles, estrategia de backups, control de concurrencia, monitoreo, recuperación ante desastres, revisión legal y una política formal de seguridad y auditoría.

## Objetivo técnico

Además de resolver la gestión de préstamos privados, el proyecto busca demostrar prácticas de ingeniería aplicadas a un dominio donde la precisión importa:

- diseño por capas y separación de responsabilidades;
- modelado de reglas financieras;
- `Decimal` para importes monetarios;
- persistencia con SQLite y repositorios;
- transacciones y atomicidad;
- ledger y auditoría;
- pruebas unitarias y de integración;
- refactorizaciones controladas sobre código financiero existente.

## Licencia

Actualmente no se especifica una licencia de código abierto en este repositorio. Antes de distribuir el proyecto como software reutilizable conviene definir una licencia explícita.
