# Producto y alcance

**Corte de documentación:** 12 de octubre de 2026 (hora Argentina).  
**Estado:** el núcleo y las superficies descritas abajo están integrados en `main`; el MVP local todavía requiere aceptación funcional manual y cierre de decisiones financieras.  
**Roadmap operativo:** [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md) · **Estado verificable:** [ESTADO_DEL_PROYECTO.md](ESTADO_DEL_PROYECTO.md) · **Evaluación:** [EVALUACION_EJECUTIVA_MVP_2026-10-12.md](EVALUACION_EJECUTIVA_MVP_2026-10-12.md).

## 1. Qué problema resuelve

**Préstamos Privados** es una aplicación local, en español y orientada a Argentina, para administrar préstamos entre personas y analizar la reposición de capital de un plan propio. Su propósito es ayudar a prestar, recibir, invertir y decidir con cifras explicables y trazables, sin exigir que el usuario conozca contabilidad o la implementación del motor.

El producto une dos recorridos relacionados, pero distintos:

1. **Préstamo privado:** registrar el acuerdo, calcular cuotas, registrar pagos y explicar cómo cambia cada saldo.
2. **Autocrédito/reposición:** planificar cómo reponer capital, preservar su poder adquisitivo de referencia en USD y añadir un rendimiento objetivo/costo de oportunidad, distinguiendo los hechos reales de las proyecciones.

La aplicación es local-first: usa Python, Streamlit y SQLite. No es actualmente una plataforma SaaS, un banco, un broker ni un sistema de identidad online.

## 2. Usuarios y roles

Una persona puede participar en distintas capacidades y en más de un rol financiero: deudor, inversor, garante u operador/administrador según las relaciones permitidas. El rol describe cómo participa en una operación; no sustituye autenticación ni autorización.

- **Deudor:** consulta las condiciones, cuotas, pagos y deuda conocida.
- **Inversor/prestamista:** consulta aportes, participaciones, cobros y rendimiento respaldado por registros.
- **Garante:** queda vinculado a una garantía concreta; ese vínculo no genera deuda ni cambia pagos por sí solo.
- **Operador/administrador local:** administra datos y utiliza las funciones permitidas por las capacidades configuradas.
- **Persona que planifica su propio financiamiento:** analiza un plan interno de reposición y alternativas de inversión. Un plan de análisis no constituye automáticamente un préstamo legal contra sí misma ni un cobro exigible.

**Límite de identidad:** el modo local actual no debe describirse como autenticación multiusuario real ni exponerse a Internet. N1–N3 organizan identidad de sesión, capacidades y roles; un proveedor online, recuperación por email y operación remota pertenecen a una etapa posterior.

## 3. Funciones del producto

| Superficie | Para qué sirve | Estado real |
|---|---|---|
| **Mi espacio** | Resumen personal, próximos movimientos y actividad | Integrado; aceptación visual local pendiente |
| **Préstamos** | Alta y ciclo de vida de préstamos con un deudor y uno o varios inversores | Integrado; el alta contractual operativa admite calendario mensual |
| **Pagos** | Vista previa y registro de pagos con trazabilidad | Integrado; Legacy es la autoridad efectiva hasta resolver divergencias con V3 |
| **Detalle financiero** | Amortización, capital, intereses, mora, devengamientos y adelantos RAI/RNI | Integrado; los recorridos completos requieren aceptación con casos de referencia |
| **Posición** | Resumen de capital conocido por la aplicación | Integrado; no equivale al patrimonio total de la persona |
| **Planificar y Escenarios** | Proyección de flujos conocidos bajo supuestos explícitos | Integrado; las proyecciones no modifican el contrato |
| **Rendimiento y Comparar** | Métricas disponibles y comparación de operaciones registradas | Integrado; XIRR solo cuando hay flujos suficientes y una solución defendible |
| **Planes de reposición** | Guardar/versionar planes, registrar aportes, flujos y valuaciones declarados | Persistencia y descargas integradas; aceptación y conciliación con posiciones/reportes pendientes |
| **Correcciones auditables** | Guardar y comparar propuestas de corrección con motivo y trazabilidad | Propuestas v026 integradas; no aplican automáticamente cambios al registro original |
| **Personas y garantías** | Administrar participantes, roles y garantías vinculadas a préstamos | Integrado, con límites del modo de identidad local |
| **Auditoría y operación** | Consultar evidencia, integridad, backups y preparación del motor | Controles integrados; restauración histórica y aceptación local pendientes |

## 4. Objetivo económico del autocrédito/reposición

El objetivo no es recuperar solamente el capital nominal. El análisis debe mostrar por separado:

1. **Capital que se necesita reponer.**
2. **Conservación del poder adquisitivo**, usando la referencia USD y cotizaciones fechadas y con origen identificado.
3. **Rendimiento objetivo o costo de oportunidad**, comparando contra una alternativa explícita y sus supuestos, gastos y posibles distribuciones.

El resultado debe diferenciar dinero efectivamente cobrado/aportado, costo externo registrado, valuación declarada a una fecha y proyección. El rendimiento objetivo no es una ganancia garantizada ni una rentabilidad realizada. Una cotización o valuación ingresada manualmente no se convierte por eso en dato observado o validado externamente.

## 5. Reglas de confianza financiera

- **Contrato y cálculo coherentes:** lo que se confirma en la interfaz debe coincidir con las condiciones persistidas, el cronograma y lo que consumen pagos e informes.
- **Sin reinterpretar historia:** una regla nueva no recalcula automáticamente préstamos existentes.
- **Importes exactos:** dinero representado mediante `Decimal`, almacenado como texto decimal cuando corresponde, con redondeo explícito.
- **Una operación, una unidad atómica:** si falla una etapa financiera, debe revertirse la operación completa.
- **Imputación explicable:** la política aplicada, las fechas relevantes y las asignaciones deben quedar trazables.
- **Hecho, valuación, proyección separados:** ninguna pantalla debe presentar hipótesis como un movimiento realizado.
- **Corrección auditable:** no sobrescribir silenciosamente movimientos históricos; una propuesta no se considera efectiva hasta que exista un flujo de aprobación/aplicación definido.
- **Legacy/V3 controlado:** Legacy sigue como autoridad operativa hasta que las divergencias económicas se acepten y se autorice el canary/cut-over con evidencia.

## 6. Alcance y restricciones vigentes

El núcleo mensual de préstamos y pagos está desarrollado, pero **no se considera terminado el MVP local**. Para la entrega deben aceptarse ambos recorridos desde la interfaz, reconciliar saldos, ledger y reportes, y demostrar instalación, backup y restauración.

La autoridad por fechas y varias convenciones de días existen como base técnica y de simulación. El alta real queda restringida a `MENSUAL` mientras alta, pagos e informes no consuman la misma autoridad temporal. La etiqueta visible de la variante 30/360 especifica actualmente **30E/360 ISDA (ajuste de fin de mes)** y advierte la excepción del vencimiento final en febrero. Este rótulo describe el cálculo existente; cambiar el texto no cambia resultados.

La carencia inicial tiene simulación, convenciones y snapshots contractuales como base. **No está habilitada para operaciones reales de punta a punta** hasta acordar la regla contractual y probar calendario, cuotas, pagos parciales, adelantos, mora, ledger y reportes sin doble contar ni capitalizar accidentalmente el interés diferido.

Las propuestas de corrección v026 son inmutables y trazables. No cambian por sí solas el original, los saldos, XIRR, posiciones o informes. La aplicación efectiva de correcciones necesita una política explícita y pruebas de reconstrucción.

## 7. Qué queda fuera del primer MVP local

Salvo decisión expresa que cambie el alcance, no bloquean la primera entrega: despliegue público por Internet, autenticación OIDC/SSO, operación multiusuario remota, conciliación automática con brokers, órdenes de inversión, modelado fiscal completo, cobertura de todas las clases de instrumentos y automatización de correcciones financieras efectivas.

Esas funciones deben planificarse después de cerrar la operación local básica y no anunciarse como capacidades disponibles.

## 8. Criterio de éxito del producto

El MVP se considera aceptado cuando una persona puede, sin scripts ni SQL manual:

- crear y consultar un préstamo de prueba bajo reglas aprobadas;
- verificar calendario, cuota, costo, pagos, mora, adelantos, participación e informe;
- crear, guardar, reabrir y exportar un plan interno de reposición;
- entender cuánto capital necesita reponer, qué referencia USD usa y cuál es su rendimiento alternativo objetivo;
- distinguir hechos, valuaciones, supuestos y proyecciones;
- verificar que pantalla, ledger y reportes concilian en la misma fecha de corte;
- instalar, reiniciar y restaurar una copia en otra ruta;
- consultar el historial y explicar por qué cambió un saldo.

La evidencia y los responsables de aceptación se registran en [issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223). Los criterios ordenados por fase están en el [roadmap operativo](ROADMAP_MVP_LOCAL.md).

## 9. Documentación funcional relacionada

- [M2 — Posición financiera](M2_POSICION_FINANCIERA.md)
- [M4 — Escenarios y planificación](M4_ESCENARIOS_PLANIFICACION.md)
- [M5 — Rendimiento explicado](M5_RENDIMIENTO_EXPLICADO.md)
- [M6 — Reportes personales](M6_REPORTES_PERSONALES.md)
- [M7 — Comparador de decisiones](M7_COMPARADOR_DECISIONES.md)
- [Principios de UX](PRINCIPIOS_UX.md)
- [Arquitectura](ARCHITECTURE.md)
- [Instalación local](INSTALACION_LOCAL.md)
