# Préstamos Privados

Aplicación local para administrar préstamos privados entre personas y analizar planes de reposición de capital. Está construida con **Python, Streamlit y SQLite**. Su objetivo es que cada cálculo financiero se pueda explicar y cada movimiento se pueda rastrear.

El producto reúne dos recorridos relacionados: la operación de préstamos (cuotas, pagos, mora, adelantos e inversores) y el análisis de capital propio que se busca reponer, conservar en poder adquisitivo de referencia y comparar con un rendimiento objetivo.

## Estado del proyecto

<details>
<summary><strong>Estado técnico verificado — 26 de noviembre de 2026</strong></summary>

- Rama estable: `main`, commit [`1192e5d3`](https://github.com/JavierGrecco/prestamos_privados/commit/1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908), posterior a PR #387.
- PR #387 incorporó un simulacro reproducible de restauración SQLite con datos sintéticos y una verificación real de integridad; no usa bases ni datos personales.
- CI post-merge: **1.372 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14**.
- Compilación, consistencia de dependencias, CodeQL y auditoría de dependencias: aprobados. El inventario modular analizó 321 archivos Python sin errores de parseo en el job que lo ejecutó.
- [Suite de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138022) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138013) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138016).
- [Revisión de ramas históricas](docs/REVISION_RAMAS_HISTORICAS_2026-11-26.md) · [Archivo de ramas históricas](docs/ARCHIVO_RAMAS_HISTORICAS.md): los 14 HEAD se conservan en el anclaje histórico, alcanzable desde una única referencia cuyo árbol es idéntico a `main`; el retiro de referencias se confirma solo después del workflow y una nueva consulta. M5 queda preservado para adaptación en [#388](https://github.com/JavierGrecco/prestamos_privados/issues/388).

**Importante:** el núcleo del producto está integrado y cuenta con una suite amplia, pero el MVP local todavía no tiene aceptación funcional y operativa completa. No debe presentarse como una aplicación lista para producción ni para operar dinero real sin supervisión.

</details>

## Qué está construido

### Préstamos privados

- Alta y consulta de préstamos con deudores e inversores.
- Cronogramas de cuotas y cálculo de amortización.
- Registro de pagos completos y parciales.
- Tratamiento de mora, adelantos y alternativas RAI/RNI.
- Distribución de cobros, ledger y auditoría de movimientos.

### Autocrédito y reposición de capital

- Planes guardados y versionados.
- Registro de aportes, flujos de inversión y valuaciones declaradas.
- Análisis de flujos de fondos y XIRR cuando existen datos suficientes.
- Referencias de cotización y benchmark con fecha y supuestos explícitos.
- Informes exportables en Markdown, JSON y CSV.

El objetivo económico distingue tres conceptos que no deben mezclarse: **capital que se necesita reponer, conservación del poder adquisitivo de referencia en USD y rendimiento objetivo o costo de oportunidad**. Una valuación declarada o una proyección no se presentan como dinero cobrado ni como ganancia realizada.

### Integridad y trazabilidad

Las reglas financieras importantes se desarrollan con:

- importes representados mediante `Decimal` y redondeo explícito;
- operaciones transaccionales, idempotencia y rollback;
- ledger e historial de auditoría;
- snapshots y huellas de integridad para determinados registros;
- pruebas de caracterización para proteger el comportamiento histórico.

### Arquitectura y calidad

El código está separado en cuatro áreas principales:

| Área | Responsabilidad |
|---|---|
| `dominio/` | Reglas monetarias, intereses, mora, amortización, imputaciones y rendimiento |
| `aplicacion/` | Casos de uso, servicios, consultas y contratos |
| `infraestructura/` | SQLite, repositorios, adaptadores y composición |
| `ui/` | Pantallas y presentación Streamlit |

El inventario automático de dependencias analizó **318 archivos Python sin errores**, encontró 1.697 importaciones, 303 cruces entre capas, 55 hallazgos clasificados y **cero ciclos de importación**. Los 55 hallazgos se distribuyen en 7 dependencias pendientes de migración, 3 excepciones temporales documentadas y 45 usos de composición de borde. Es una fotografía de arquitectura, no un porcentaje de modularización terminada.

## Límites actuales: qué falta antes de aceptar el MVP

- **Motor de pagos:** Legacy sigue siendo la autoridad efectiva. V3 cuenta con preview, SOMBRA y preflight, pero no está autorizado el cambio definitivo de motor.
- **Contratos y calendario:** el alta real de préstamos sigue limitada a cuotas mensuales. El cálculo por fechas existe como base técnica, pero las distintas convenciones y la carencia inicial no están integradas de punta a punta.
- **Conciliación:** falta aceptar los recorridos completos desde la interfaz y demostrar que saldos, pagos, ledger y reportes coinciden con el mismo corte.
- **Pagos con arrastre:** sigue pendiente decidir y validar la atribución por cuota de ciertas imputaciones Legacy cuando un pago cubre obligaciones anteriores ([#332](https://github.com/JavierGrecco/prestamos_privados/issues/332)).
- **Operación local:** falta la aceptación manual desde una instalación limpia y el simulacro completo de backup/restauración en otra ruta.
- **Concurrencia:** ya se aíslan las conexiones SQLite por sesión Streamlit y existe una prueba automatizada de dos sesiones sobre el mismo archivo. Sigue pendiente el recorrido financiero E2E de pagos concurrentes, idempotencia, revisión obsoleta y rollback ([#159](https://github.com/JavierGrecco/prestamos_privados/issues/159)).
- **Seguridad de interfaz:** hay escape de texto y pruebas para superficies conocidas, pero el análisis HTML no cubre de forma universal todas las construcciones posibles; el seguimiento continúa abierto ([#158](https://github.com/JavierGrecco/prestamos_privados/issues/158)).
- **Gobierno del repositorio:** `main` todavía no tiene protección administrativa que obligue a integrar por PR y exigir checks ([#157](https://github.com/JavierGrecco/prestamos_privados/issues/157)).

El modo actual es local. No es un SaaS, no ofrece autenticación online multiusuario y no debe exponerse a Internet. El repositorio tampoco declara una licencia pública ni tiene releases publicados.

## Empezar en local

**Requisitos:** Python 3.11 o posterior, Git y un navegador.

La guía completa cubre Windows (PowerShell y CMD), macOS y Linux:

**[Instalación local reproducible](docs/INSTALACION_LOCAL.md)**

Desde la raíz del repositorio:

```bash
python scripts/preparar_entorno.py
```

Activá el entorno virtual creado para esta copia y luego iniciá la aplicación con una ruta explícita para la base:

```bash
python scripts/iniciar_local.py --db datos/prestamos-local.db
```

La aplicación usa por defecto `http://localhost:8501`. Para cuentas locales, migraciones y recuperación, seguí la guía de instalación. No uses datos financieros reales en issues, fixtures ni pruebas.

## Estructura del repositorio

```text
aplicacion/       Casos de uso, consultas, servicios y contratos
dominio/          Reglas financieras y tipos monetarios
infraestructura/  SQLite, repositorios, ledger, auditoría y composición
ui/               Streamlit y presentación
tests/            Pruebas unitarias, de integración y de interfaz
docs/             Producto, arquitectura, operación y decisiones
scripts/          Instalación, migraciones, auditorías y soporte
```

## Documentación para orientarse

| Quiero entender… | Empezar por… |
|---|---|
| Qué problema resuelve y qué funciones existen | [Producto y alcance](docs/PRODUCTO.md) |
| Cómo se plantea el presupuesto y la capacidad de pago personal | [Finanzas personales y capacidad de pago](docs/FINANZAS_PERSONALES_CAPACIDAD_PAGO.md) |
| Cómo está organizado el código | [Arquitectura](docs/ARCHITECTURE.md) |
| Qué está integrado y qué sigue pendiente | [Estado del proyecto](docs/ESTADO_DEL_PROYECTO.md) |
| Qué falta para cerrar la entrega local | [Roadmap del MVP](docs/ROADMAP_MVP_LOCAL.md) |
| Qué dependencias entre capas quedan por resolver | [Estado de modularización](docs/ESTADO_MODULARIZACION.md) |
| Cómo instalar y ejecutar | [Instalación local](docs/INSTALACION_LOCAL.md) |
| Qué controles y límites de seguridad existen | [Seguridad](SECURITY.md) |
| Cómo contribuir sin fragmentar el trabajo | [Flujo de trabajo Git](docs/FLUJO_DE_TRABAJO_GIT.md) |
| Dónde encontrar especificaciones y evidencia | [Índice de documentación](docs/INDEX.md) |
| Qué reveló la revisión técnica actual | [Revisión técnica del 26/11/2026](docs/REVISION_TECNICA_2026-11-26.md) |

La [evaluación ejecutiva del 12/10/2026](docs/EVALUACION_EJECUTIVA_MVP_2026-10-12.md) es una fotografía histórica, no una calificación actual del estado de `main`.

## Evolución futura del producto

Está documentada una capacidad futura de **operación financiera asistida**: preparar borradores de operaciones a partir de instrucciones textuales, responder consultas de solo lectura y reunir el progreso de reposición. Es diseño de producto, no una función implementada. Su prioridad es posterior a la aceptación del MVP local. Ver [Capacidad de operación financiera asistida](docs/CAPACIDAD_OPERATIVA_ASISTIDA.md).

La sección [Finanzas personales y capacidad de pago](docs/FINANZAS_PERSONALES_CAPACIDAD_PAGO.md), seguida en [#375](https://github.com/JavierGrecco/prestamos_privados/issues/375), ya tiene en **Mi espacio** una evaluación directa de nueva cuota con margen declarado, ahorro líquido protegido y escenarios de meses ajustados. Para personas inversoras, también muestra cobros contractuales proyectados por fecha y permite probar demoras de 30/60 días o ausencia de cobro dentro del año. Esas entradas no se suman automáticamente al margen declarado y no se presentan como efectivo recibido. La evaluación directa sigue siendo temporal, en ARS y para una cuota representativa. El presupuesto guiado, registro detallado, cobros externos y comparación completa del cronograma siguen pendientes. No modifica las reglas de préstamos ni persiste los importes personales.

## Licencia

El repositorio no declara actualmente una licencia de código abierto. No debe asumirse permiso de reutilización o redistribución hasta que se defina una licencia explícita.
