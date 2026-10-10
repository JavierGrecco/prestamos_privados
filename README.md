# Préstamos Privados

Motor financiero para administrar préstamos privados con un deudor, uno o varios
inversores, cuotas, pagos, mora, adelantos y trazabilidad.

El proyecto está construido en Python con SQLite y Streamlit. La lógica
financiera está separada de la persistencia y de la interfaz para poder probarla,
explicarla y evolucionarla de forma controlada.

> **Estado actual:** M1–M7 están integrados en la experiencia de producto.
> Legacy sigue siendo la autoridad efectiva mientras se completa el cut-over
> controlado del Motor V3.

## Navegación principal

<table>
<tr>
<td align="center"><a href="docs/PRODUCTO.md">🧭<br><strong>Producto</strong></a><br>Qué hace la aplicación</td>
<td align="center"><a href="docs/ARCHITECTURE.md">🏗️<br><strong>Arquitectura</strong></a><br>Cómo está construido</td>
<td align="center"><a href="docs/ESTADO_DEL_PROYECTO.md">📊<br><strong>Estado</strong></a><br>Dónde estamos y qué sigue</td>
<td align="center"><a href="SECURITY.md">🔐<br><strong>Seguridad</strong></a><br>Controles y prácticas</td>
<td align="center"><a href="docs/INDEX.md">📚<br><strong>Documentación</strong></a><br>Índice completo</td>
<td align="center"><a href="docs/REGISTRO_DE_CAMBIOS.md">📝<br><strong>Novedades</strong></a><br>Cambios y pendientes</td>
</tr>
</table>

Estas cinco entradas son intencionalmente distintas: **Producto** explica el
qué, **Arquitectura** el cómo, **Estado** el cuándo/dónde, **Seguridad** el
riesgo y **Documentación** reúne el detalle.

Para seguir el trabajo hasta una entrega local completa, empezá por la [hoja de ruta del MVP local](docs/ROADMAP_MVP_LOCAL.md): explica qué está hecho, qué sigue, qué depende de una decisión y cuándo se considera terminada cada fase.

## Qué es

La aplicación busca resolver un problema concreto: registrar y analizar
préstamos privados sin perder precisión financiera ni trazabilidad.

Una operación de pago no es solamente “restar dinero”. Puede afectar cuotas,
mora, intereses, capital, inversores, ledger y auditoría. Por eso esas reglas se
tratan como software financiero que debe poder explicarse, probarse y auditarse.

## Qué hace

- Crea préstamos con uno o varios inversores.
- Genera y mantiene tablas de amortización.
- Registra pagos completos y parciales, mora y adelantos.
- Gestiona devengamientos, RAI/RNI y distribución entre inversores.
- Conserva ledger, auditoría y trazabilidad histórica.
- Analiza cashflows, XIRR, rendimiento real, poder de compra y escenarios.
- Compara operaciones registradas desde **Comparar**.
- Expone una vertical de producto en Streamlit con información personal,
  planificación, reportes y operación controlada.

El mapa funcional completo está en [Producto](docs/PRODUCTO.md).

## Empezar en 5 minutos

### Requisitos

- Python 3.11 o posterior.
- Git para obtener el repositorio.
- Un navegador para Streamlit.

### Instalación y primer inicio

La guía paso a paso cubre **Windows PowerShell, Windows CMD, macOS y Linux**,
incluyendo el entorno virtual correcto, la ruta explícita de la base, el primer
administrador y la actualización segura de una base existente:

**[Abrir la guía de instalación local](docs/INSTALACION_LOCAL.md)**

Desde la raíz del repositorio, el ayudante prepara las dependencias:

```bash
python scripts/preparar_entorno.py
```

Luego de activar el `.venv` de esta copia, iniciá con una ruta explícita:

```bash
python scripts/iniciar_local.py --db datos/prestamos-local.db
```

Si la base es nueva, se inicializa y el sistema guía la creación del primer
ADMIN. Si ya tiene una cuenta de acceso, aparece el login: **no hace falta
crear otro administrador**. Si una base existente necesita migraciones, el
iniciador se detiene hasta que se autorice la actualización con un backup
verificado.

La aplicación usa por defecto `http://localhost:8501`. El acceso actual es
local; no expongas el servidor a Internet. Las bases SQLite locales, WAL y SHM
no forman parte del repositorio.

Para administración de cuentas y recuperación offline, consultá
[Operación de usuarios locales](docs/OPERACION_USUARIOS_LOCALES.md).

## Principios de diseño

**Precisión.** Dinero con `Decimal` y redondeo explícito.

**Trazabilidad.** Las operaciones importantes deben poder reconstruirse.

**Atomicidad.** Una operación confirmada se persiste completa o se revierte
completa.

**Separación.** La UI no decide intereses; la persistencia no decide reglas
financieras.

**Determinismo.** El resultado económico depende del estado y de la política,
no de efectos implícitos del reloj.

**Pruebas primero.** Las reglas financieras críticas cambian acompañadas por
regresiones.

## Cómo está organizado

```text
Streamlit / UI
      ↓
Casos de uso / aplicación
      ↓
Dominio financiero
      ↓
Infraestructura / SQLite
      ↓
Ledger + auditoría + read models
```

Los detalles de capas, contratos y transición Legacy/V3 están en
[Arquitectura](docs/ARCHITECTURE.md).

<details>
<summary><strong>🗂️ Mapa rápido del repositorio</strong></summary>

```text
aplicacion/       casos de uso y servicios
dominio/          reglas financieras puras
infraestructura/  SQLite, repositorios, ledger y auditoría
ui/               Streamlit y presentación
tests/            pruebas unitarias, integración y E2E
docs/             producto, arquitectura, operación y evolución
scripts/          herramientas operativas y de soporte
SECURITY.md       política y prácticas de seguridad
README.md         puerta de entrada del proyecto
```

</details>

<details>
<summary><strong>🔎 ¿Qué documento leo primero?</strong></summary>

| Necesidad | Documento |
|---|---|
| Quiero entender el producto | [Producto](docs/PRODUCTO.md) |
| Quiero entender el código | [Arquitectura](docs/ARCHITECTURE.md) |
| Quiero saber qué está terminado | [Estado del proyecto](docs/ESTADO_DEL_PROYECTO.md) |
| Quiero saber qué sigue | [Roadmap](docs/ROADMAP.md) |
| Quiero revisar seguridad | [SECURITY.md](SECURITY.md) |
| Quiero encontrar una decisión concreta | [Centro de documentación](docs/INDEX.md) |
| Quiero desarrollar o abrir un PR | [Desarrollo](docs/DEVELOPMENT.md) |
| Quiero saber qué cambió recientemente | [Registro de cambios](docs/REGISTRO_DE_CAMBIOS.md) |

</details>

## Calidad y estado operativo

CI valida la suite sobre Python 3.11, 3.12, 3.13 y 3.14. También se ejecutan
CodeQL y auditoría de dependencias.

Esto demuestra el estado de calidad del código y no implica por sí solo que el
sistema esté listo para operar dinero real. El estado técnico y los bloqueos
actuales están en [Estado del proyecto](docs/ESTADO_DEL_PROYECTO.md).

## Seguridad

La seguridad deja de ser una sección extensa del README y vive en
[SECURITY.md](SECURITY.md). Allí se concentran reporte de vulnerabilidades,
protección de datos, identidad/autorización, controles de CI y seguridad
operativa.

## Contribuir

La forma recomendada de trabajar, validar cambios, nombrar ramas y preparar un
PR está en [Desarrollo](docs/DEVELOPMENT.md).

## Licencia

El repositorio no declara actualmente una licencia de código abierto. Si el
proyecto se va a distribuir como software reutilizable, conviene definirla
explícitamente.
