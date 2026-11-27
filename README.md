# Préstamos Privados

Aplicación local para administrar préstamos privados entre personas y analizar planes de reposición de capital. Está construida con **Python, Streamlit y SQLite**. Su objetivo es que cada cálculo financiero se pueda explicar y cada movimiento se pueda rastrear.

El producto reúne dos recorridos relacionados: la operación de préstamos (cuotas, pagos, mora, adelantos e inversores) y el análisis de capital propio que se busca reponer, conservar en poder adquisitivo de referencia y comparar con un rendimiento objetivo.

## Estado del proyecto

<details>
<summary><strong>Estado técnico verificado — 27 de noviembre de 2026 (post-merge PR #433)</strong></summary>

- **Base de código con la última cobertura integrada:** [`2535613`](https://github.com/JavierGrecco/prestamos_privados/commit/25356135858cd8d5e79f4ef58436d787089f9424), PR #433, suma pruebas generativas al simulador puro de pagos Legacy; no cambia su implementación. **Último cambio funcional del dominio:** PR #429, commit [`0278632`](https://github.com/JavierGrecco/prestamos_privados/commit/0278632ea77d987f5fa3bf7998bd5d6227c5abda), que endureció `money()` y `rate()` frente a entradas no finitas, no convertibles y fuera del rango de cuantización.
- **Última mejora de interfaz:** [PR #427](https://github.com/JavierGrecco/prestamos_privados/pull/427) corrigió un desbordamiento real detectado a 768 px al reemplazar columnas proporcionales fijas. No modificó permisos, rutas, reglas financieras ni persistencia.
- **Última ampliación de pruebas financieras:** [PR #433](https://github.com/JavierGrecco/prestamos_privados/pull/433) agrega 600 escenarios Hypothesis al simulador Legacy `simular_pago()`: conservación del monto, límites por concepto, faltante/excedente y proyección de capital e intereses bajo las seis permutaciones de MORA/INTERES/CAPITAL. Junto con [PR #431](https://github.com/JavierGrecco/prestamos_privados/pull/431), que aporta 500 escenarios de reparto entre inversores, son hasta 1.100 escenarios generados entre cuatro propiedades. Ambas PR solo agregan pruebas; no cambian reglas ni activan V3.
- **Decisión tecnológica:** Python mantiene la autoridad única del dominio y los cálculos financieros; Streamlit sigue siendo la interfaz del MVP local; SQLite, la persistencia; CSS, la presentación. No se agregó JavaScript/TypeScript general. TypeScript queda como opción para componentes interactivos puntuales si Streamlit/Plotly no alcanzan. Ver [decisión tecnológica](docs/DECISIONES_TECNOLOGICAS.md) y [arquitectura](docs/ARCHITECTURE.md).
- **CI post-merge de PR #433 / HEAD `2535613`:** **1.475 pruebas aprobadas + 4 omitidas** en cada Python 3.11, 3.12, 3.13 y 3.14; Chromium **4/4**; CodeQL, `pip-audit` y branch housekeeping aprobados. [Tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46036966627) · [Browser](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46036966677) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46036966635) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46036966632).
- **Cobertura de navegador:** 4/4 recorridos aprobados: XSS de nombre/destino y metadatos de pago; bloqueo de preview obsoleto en dos contextos; restore/reinicio entre procesos; y navegación/teclado/responsive con datos sintéticos. No equivalen a certificación universal de XSS ni a aceptación visual manual completa.
- **Auditoría modular:** 323 archivos Python analizados sin errores, 1.748 importaciones, 318 cruces entre capas, 54 observaciones (7 construcciones pendientes de migración, 1 excepción temporal documentada y 46 usos de composición en el borde) y cero ciclos. Es un inventario de dependencias, no un porcentaje de modularización terminada.
- **Ramas:** solo `main` y `archive/legacy-branches-2026-11`; no hay PR abiertas tras integrar #433. Las ramas temporales de #427–#433 se eliminaron después de sus squash merges.
- **Pendientes relevantes:** #157 (protección administrativa de `main`), #158 (revisión XSS ampliada y aceptación manual), #159 (aceptación manual de concurrencia), #177 (inspección visual manual D4), #179 (aceptación UX integral D6), #223 (aceptación del MVP), #332 (política de imputación por cuota) y #374 (restore drill manual). La integración no tiene permisos administrativos para configurar ni verificar branch protection.

**Importante:** el MVP local todavía no tiene aceptación funcional y operativa completa. Las pruebas automatizadas son evidencia técnica, no autorización para operar dinero real ni declarar el producto listo para producción.

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

El inventario modular post-merge analizó **323 archivos Python sin errores**, encontró 1.747 importaciones, 318 cruces entre capas, 54 hallazgos clasificados y **cero ciclos de importación**. Los hallazgos se distribuyen en 7 construcciones de repositorio pendientes de migración, 1 excepción temporal documentada y 46 usos de composición de borde. Es una fotografía de arquitectura, no un porcentaje de modularización terminada.

## Límites actuales: qué falta antes de aceptar el MVP

- **Motor de pagos:** Legacy sigue siendo la autoridad efectiva. V3 cuenta con preview, SOMBRA y preflight, pero no está autorizado el cambio definitivo de motor.
- **Contratos y calendario:** el alta real de préstamos sigue limitada a cuotas mensuales. El cálculo por fechas existe como base técnica, pero las distintas convenciones y la carencia inicial no están integradas de punta a punta.
- **Conciliación:** falta aceptar los recorridos completos desde la interfaz y demostrar que saldos, pagos, ledger y reportes coinciden con el mismo corte.
- **Pagos con arrastre:** sigue pendiente decidir y validar la atribución por cuota de ciertas imputaciones Legacy cuando un pago cubre obligaciones anteriores ([#332](https://github.com/JavierGrecco/prestamos_privados/issues/332)).
- **Operación local:** falta la aceptación manual desde una instalación limpia y el simulacro completo de backup/restauración en otra ruta.
- **Concurrencia:** las conexiones SQLite se aíslan por sesión Streamlit y las pruebas E2E ahora cubren pagos desde dos sesiones, idempotencia de la misma intención, rechazo de una intención distinta con revisión obsoleta y rollback tras un fallo inducido. Sigue pendiente la aceptación manual en navegador/sesiones reales y el registro de esa evidencia en [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159).
- **Seguridad de interfaz:** los componentes compartidos escapan por defecto; PR #413 amplía la guarda AST, PR #414 agrega E2E AppTest y PR #415 agrega aceptación Chromium para nombre/destino en Mi espacio. Sigue pendiente revisar helpers/atributos indirectos, otras superficies (notas, motivos y referencias) y aceptar manualmente el recorrido ampliado ([#158](https://github.com/JavierGrecco/prestamos_privados/issues/158)).
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
| Cómo está organizado el código | [Arquitectura](docs/ARCHITECTURE.md) y [decisión tecnológica](docs/DECISIONES_TECNOLOGICAS.md) |
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

La sección [Finanzas personales y capacidad de pago](docs/FINANZAS_PERSONALES_CAPACIDAD_PAGO.md), seguida en [#375](https://github.com/JavierGrecco/prestamos_privados/issues/375), ya integra margen declarado, reserva líquida protegida, cobros contractuales y externos por fecha, y comparación de cada cuota de una nueva propuesta con el margen. La propuesta se genera con el simulador oficial, sin crear ni guardar un préstamo; se admiten sistemas francés/alemán y tasas TNA/TEA. La comparación del margen recorre el cronograma completo (1–360 cuotas); el consumo de reserva y la caja con cobros se estresan solo sobre los primeros 1–24 vencimientos elegidos. La función permanece en ARS y en sesión, no genera pagos reales ni persiste datos personales. Siguen pendientes calidad/evidencia de cobros externos, conciliación al recibirlos, presupuesto guiado y registro de ingresos/gastos. F1 continúa como Post-MVP y no modifica la aceptación del MVP #223.

## Licencia

El repositorio no declara actualmente una licencia de código abierto. No debe asumirse permiso de reutilización o redistribución hasta que se defina una licencia explícita.
