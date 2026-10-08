# Préstamos Privados

Motor financiero para administrar préstamos privados con un deudor, uno o varios inversores, cuotas, pagos, mora, adelantos y trazabilidad.

El proyecto está construido en Python con SQLite y Streamlit. La lógica financiera está separada de la persistencia y de la interfaz para que las reglas puedan probarse y evolucionar de forma controlada.

> **Estado actual:** la primera vertical funcional de la aplicación está integrada en Streamlit (alta de préstamos, pagos, análisis, trazabilidad y operación). Legacy sigue siendo la autoridad efectiva mientras se prepara el cut-over controlado de V3.

## Por qué existe

La aplicación busca resolver un problema concreto: registrar y analizar préstamos privados sin perder precisión financiera ni trazabilidad.

Una operación de pago no es solamente “restar dinero”. Puede afectar cuotas, mora, intereses, capital, inversores, ledger y auditoría. Por eso el proyecto trata esas reglas como software financiero que debe poder explicarse, probarse y auditarse.

## Qué hace

- Crea préstamos con uno o varios inversores.
- Genera tablas de amortización.
- Soporta las convenciones de tasa y tiempo definidas por el dominio.
- Registra pagos completos y parciales.
- Gestiona mora y saldos arrastrados.
- Modela adelantos con RAI y RNI.
- Calcula devengamientos e impacto sobre el capital pendiente.
- Distribuye cobros entre inversores.
- Mantiene ledger y auditoría.
- Permite consultas/read models auditables.
- Usa `Decimal` para importes monetarios.
- Incluye pruebas unitarias, de integración y de consistencia.

## Arquitectura

```text
                         Streamlit / UI
                              │
                              ▼
                    Casos de uso / aplicación
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          Motor financiero V3        Read models
                 │                         │
                 ▼                         │
              SQLite ◄─────────────────────┘
                 │
        ┌────────┼──────────┐
        ▼        ▼          ▼
     Ledger   Auditoría   Migraciones
```

Las responsabilidades principales son:

- **`dominio/`** — reglas financieras puras: planes de pago, devengamientos, capital, adelantos y distribución.
- **`aplicacion/`** — casos de uso y orquestación transaccional.
- **`infraestructura/`** — SQLite, repositorios, migraciones, ledger, auditoría y consultas.
- **`ui/`** — interfaz Streamlit; no debe ser autoridad de cálculo financiero.
- **`tests/`** — pruebas de reglas, persistencia e integración.
- **`docs/`** — arquitectura, reglas, decisiones y notas de integración.

## Estado de la aplicación

La UI ya expone una vertical funcional completa para operar el sistema:

```text
Alta préstamo → simulación → persistencia
        ↓
Registro pago → preview → confirmación → SOMBRA/V3
        ↓
Detalle → historial auditable → capital/devengamientos/RAI-RNI
        ↓
Análisis → cashflow/XIRR/poder de compra/escenarios
        ↓
Operación → integridad/backups/restore/preflight
```

El Motor V3 ya está integrado con SQLite y protegido por preflight. Legacy sigue
siendo la ruta efectiva mientras se mide la evidencia necesaria para el cut-over.

La idea central es separar:

```text
estado financiero
      ↓
planificación
      ↓
plan de pago
      ↓
aplicación
      ↓
persistencia
```

La simulación no debe mutar la base y el registro debe persistir de forma atómica el resultado calculado.

## Estado de calidad

La suite se ejecuta en CI sobre Python 3.11, 3.12, 3.13 y 3.14. El número de
tests puede crecer con cada etapa y no se fija en esta documentación.

El resultado de CI es un indicador del estado de pruebas, no una afirmación de
que el sistema esté listo para operar con dinero real.

Antes de retirar el flujo legacy todavía hay que demostrar:

- equivalencia financiera donde corresponda;
- atomicidad frente a fallas inyectadas;
- comportamiento concurrente;
- idempotencia;
- migración segura de datos existentes;
- consistencia de participaciones, ledger y auditoría.

## Empezar en 5 minutos

### Requisitos

- Python 3.11+
- `pip`
- navegador web para Streamlit

### Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Verificar

```bash
python -m compileall -q aplicacion dominio infraestructura tests
python -m pytest -q
```

### Ejecutar la aplicación

```bash
python -m streamlit run ui/app.py
```

La aplicación usa por defecto:

```text
http://localhost:8501
```

### Base de datos de la UI

La aplicación usa por defecto `datos/prestamos.db`. Para pruebas o entornos
aislados se puede indicar otra ruta:

```bash
PRESTAMOS_DB_PATH=/ruta/a/prestamos.db python -m streamlit run ui/app.py
```

### Datos de ejemplo

La base local se crea automáticamente cuando hace falta.

Para cargar datos de demostración:

```bash
python scripts/seed_datos.py
```

Los datos de ejemplo son locales y no forman parte del repositorio.

## Base de datos

SQLite se usa como almacenamiento local.

La aplicación trabaja con:

```text
datos/prestamos.db
```

La base y sus archivos WAL/SHM están excluidos de Git. Esto es deliberado: el repositorio debe contener código y migraciones, no datos financieros locales.

Las pruebas crean sus propias bases temporales.

## Cómo trabajamos en las partes financieras

Las refactorizaciones críticas se hacen en este orden:

```text
caracterizar comportamiento existente
        ↓
agregar invariantes y regresiones
        ↓
implementar la nueva capa
        ↓
comparar resultados
        ↓
integrar
        ↓
eliminar duplicaciones
```

No se reemplaza una regla financiera únicamente porque una nueva implementación “parezca más limpia”.

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md) — cómo está organizado el sistema y dónde vive cada responsabilidad.
- [Desarrollo](docs/DEVELOPMENT.md) — cómo instalar, probar y trabajar en el proyecto.
- [Roadmap](docs/ROADMAP.md) — qué falta y en qué orden.
- [Operación y backups](docs/J2_BACKUP_RESTORE.md) — integridad, backup y restore drill de SQLite.
- [Integración V3 en UI](docs/K1_UI_V3.md) — modos Legacy, SOMBRA y V3 protegido por preflight.
- [Dashboard financiero](docs/K2_DASHBOARD_FINANCIERO.md) — cashflow, XIRR, poder de compra y escenarios.
- [Historial auditable de pagos](docs/K4_HISTORIAL_PAGOS.md) — trazabilidad de pagos, planes, ledger y SOMBRA.
- [Operación desde UI](docs/K5_OPERACION_UI.md) — integridad, backups verificables y restore drill seguro.
- [Detalle financiero](docs/K6_DETALLE_FINANCIERO.md) — amortización, capital, devengamientos y RAI/RNI.
- [Aceptación end-to-end](docs/K7_UI_E2E.md) — arranque aislado, navegación y regresión de integración de la UI.
- [Pago end-to-end](docs/K8_UI_PAGO_E2E.md) — confirmación real desde Streamlit y verificación posterior de la base.
- [Alta de préstamo end-to-end](docs/K9_UI_ALTA_PRESTAMO_E2E.md) — creación, simulación, aportes y persistencia desde Streamlit.
- [Personas y roles](docs/K10_PERSONAS_UI.md) — onboarding, administración de personas y roles desde Streamlit.
- [Auditoría global](docs/K12_AUDITORIA_UI.md) — trazabilidad de cambios y reconstrucción de operaciones desde Streamlit.
- [Auditoría inmutable](docs/K15_AUDITORIA_INMUTABLE.md) — la evidencia no puede modificarse ni eliminarse en SQLite.
- [Fechas real y valor de pagos](docs/K13_FECHA_VALOR_PAGOS.md) — separación explícita de recepción y efecto financiero.
- [Validación de roles en préstamos](docs/ROLES_PRESTAMOS.md) — consistencia de deudor/inversor en la capa de aplicación.
- [Ciclo de vida de préstamos](docs/K11_PRESTAMO_LIFECYCLE_UI.md) — estados y transiciones controladas desde Streamlit.
- [Revisión de evidencia SOMBRA](docs/I9_SOMBRA_EVIDENCE_REVIEW.md) — inspección operativa de divergencias y errores antes del cut-over.
- [Informe de preflight V3](scripts/preflight_motor_pago_v3.py) — evaluación reproducible sobre una base SQLite existente, sin mutaciones.
- [Modo persistente del Motor de Pagos](docs/I11_MODO_PERSISTENTE_MOTOR_PAGO.md) — activación V3 con preflight, auditoría y rollback explícito.
- [Precheck de canary V3](docs/CANARY_PRECHECK_V3.md) — evaluación reproducible previa a la activación, sin mutaciones.
- [Evidencia de canary](docs/CANARY_PRECHECK_V3.md) — permite conservar el JSON fechado generado por el precheck.
- [Readiness de canary en la UI](docs/I13_CANARY_READINESS_UI.md) — el mismo criterio de preparación visible desde Streamlit.
- [Lógica de pagos](docs/LOGICA_PAGOS.md) — reglas funcionales de pagos y decisiones del usuario.
- [Plan de refactorización](docs/PLAN_REFACTORIZACION_MOTOR_PAGOS.md) — estrategia para eliminar lógica financiera duplicada.
- [Historial de integración](docs/integration/) — evolución incremental del Motor V3.

## Qué no es todavía

Este proyecto no debe considerarse un sistema bancario de producción.

Antes de usar información financiera real hacen falta, entre otras cosas, autenticación/autorización, protección de datos sensibles, gestión de secretos, backups formales, monitoreo, recuperación ante desastres, revisión legal y un proceso operativo controlado.

## Principios

**Precisión.** Dinero con `Decimal` y redondeo explícito.

**Trazabilidad.** Las operaciones importantes deben poder reconstruirse.

**Atomicidad.** Un pago se confirma completo o se revierte completo.

**Separación.** La UI no decide intereses; la persistencia no decide reglas financieras.

**Determinismo.** El resultado económico depende del estado y de la política, no de efectos implícitos del reloj.

**Pruebas primero.** Las reglas financieras críticas se cambian acompañadas por regresiones.

## Licencia

El repositorio no declara actualmente una licencia de código abierto. Si el proyecto se va a distribuir como software reutilizable, conviene definirla explícitamente.

## Seguridad

Las reglas de seguridad están en [SECURITY.md](SECURITY.md). CI ejecuta auditoría de dependencias y CodeQL.
