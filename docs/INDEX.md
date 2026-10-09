# Centro de documentación

Este índice organiza la documentación por **propósito**, no por orden histórico
de implementación. Los documentos de detalle conservan la evidencia técnica
necesaria; esta página indica dónde empezar.

## 🧭 Producto y experiencia

| Documento | Para qué sirve |
|---|---|
| [Producto](PRODUCTO.md) | Qué hace la aplicación, qué superficies existen y cómo se separan hechos, proyecciones y escenarios |
| [Estado del proyecto](ESTADO_DEL_PROYECTO.md) | Estado actual, prioridades y decisiones de rumbo |
| [Roadmap](ROADMAP.md) | Evolución planificada y trabajo pendiente |
| [Registro de cambios](REGISTRO_DE_CAMBIOS.md) | Qué cambió, cómo se validó y qué sigue abierto |
| [Principios UX](PRINCIPIOS_UX.md) | Reglas permanentes de claridad, lenguaje y presentación |
| [Reglas UI](REGLAS_UI.md) | Criterios funcionales que debe respetar la interfaz |
| [Plan de evolución UX e identidad polifuncional](PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md) | Entregas, permisos, navegación, roles financieros y criterios de cierre |
| [D2 — Modelo de personas y garantías](D2_MODELO_PERSONAS_GARANTIAS.md) | Contrato de roles financieros, vínculo opcional cuenta-persona y garantías por préstamo |

## 🏗️ Arquitectura y desarrollo

- [Arquitectura](ARCHITECTURE.md)
- [Desarrollo](DEVELOPMENT.md)
- [Instalación local reproducible](INSTALACION_LOCAL.md)
- [Diseño financiero de carencia inicial](DISENO_CARENCIA_INICIAL.md)
- [Lógica de pagos](LOGICA_PAGOS.md)
- [Roles en préstamos](ROLES_PRESTAMOS.md)
- [Plan de refactorización del motor](PLAN_REFACTORIZACION_MOTOR_PAGOS.md)

## 💰 Producto financiero M2–M7

- [M2 — Posición financiera](M2_POSICION_FINANCIERA.md)
- [M4 — Escenarios y planificación](M4_ESCENARIOS_PLANIFICACION.md)
- [M5 — Rendimiento explicado](M5_RENDIMIENTO_EXPLICADO.md)
- [M6 — Reportes financieros personales](M6_REPORTES_PERSONALES.md)
- [M7 — Comparador de decisiones](M7_COMPARADOR_DECISIONES.md)

## 🔐 Seguridad, identidad y autorización

- [SECURITY.md](../SECURITY.md)
- [Auditoría de HTML en la interfaz](AUDITORIA_HTML_UI.md)
- [N1 — Identidad y autorización](N1_IDENTIDAD_AUTORIZACION.md)
- [N2 — Identidad de sesión](N2_IDENTIDAD_SESION.md)
- [N3 — Capacidades y roles](N3_CAPACIDADES_ROLES.md)
- [Operación de usuarios locales](OPERACION_USUARIOS_LOCALES.md)
- [K14 — Operador declarado](K14_OPERADOR_UI.md)
- [K15 — Auditoría inmutable](K15_AUDITORIA_INMUTABLE.md)
- [K12 — Auditoría global](K12_AUDITORIA_UI.md)
- [K16 — Exportaciones](K16_EXPORTACIONES_UI.md)

## 🛡️ Operación y adopción controlada de V3

### Canary, preflight y rollback

- [Runbook de canary V3](CANARY_RUNBOOK_V3.md)
- [Precheck de canary](CANARY_PRECHECK_V3.md)
- [Paquete reproducible de decisión de canary](L1_2_PAQUETE_CANARY.md)
- [Informe de preflight V3](PREFLIGHT_V3_CLI.md)
- [Readiness de canary en UI](I13_CANARY_READINESS_UI.md)
- [Modo persistente del motor](I11_MODO_PERSISTENTE_MOTOR_PAGO.md)
- [Rollback operativo](I8_ROLLBACK_OPERATIVO.md)
- [Revisión de evidencia SOMBRA](I9_SOMBRA_EVIDENCE_REVIEW.md)
- [Evidencia de canary](I16_EVIDENCIA_CANARY.md)
- [Readiness con snapshot único](I18_READINESS_PREFLIGHT_SNAPSHOT.md)
- [Preflight y evidencia](I15_PREFLIGHT_Y_EVIDENCIA.md)

### UI y operación

- [Integración V3 en UI](K1_UI_V3.md)
- [Dashboard financiero](K2_DASHBOARD_FINANCIERO.md)
- [Preview de pagos V3](K3_PREVIEW_PAGO_V3.md)
- [Historial de pagos](K4_HISTORIAL_PAGOS.md)
- [Operación desde UI](K5_OPERACION_UI.md)
- [Detalle financiero](K6_DETALLE_FINANCIERO.md)
- [Aceptación UI end-to-end](K7_UI_E2E.md)
- [Pago end-to-end](K8_UI_PAGO_E2E.md)
- [Alta de préstamo end-to-end](K9_UI_ALTA_PRESTAMO_E2E.md)
- [Personas desde UI](K10_PERSONAS_UI.md)
- [Ciclo de vida de préstamos](K11_PRESTAMO_LIFECYCLE_UI.md)
- [Fecha real y fecha valor](K13_FECHA_VALOR_PAGOS.md)

### Backups, migraciones y recuperación

- [Backup y restore](J2_BACKUP_RESTORE.md)
- [Operación de migraciones SQLite](OPERACION_MIGRACIONES.md)
- [Concurrencia de SQLite](CONCURRENCIA_SQLITE.md)
- [Consumidores Legacy](LEGACY_CONSUMERS.md)

## 🧪 Hardening y evidencia técnica

### H — Hardening financiero

- [H1 — Comparación Legacy vs V3](H1_COMPARACION_LEGACY_V3.md)
- [H2 — Atomicidad ante fallas](H2_ATOMICIDAD_FALLAS.md)
- [H3 — Concurrencia e idempotencia](H3_CONCURRENCIA_IDEMPOTENCIA.md)
- [H4 — Migraciones y compatibilidad](H4_MIGRACIONES_COMPATIBILIDAD.md)

### I — Adopción controlada

- [I1 — Snapshot SOMBRA](I1_SOMBRA_SNAPSHOT.md)
- [I2 — SOMBRA sobre SQLite](I2_SOMBRA_SQLITE.md)
- [I3 — Observabilidad SOMBRA](I3_OBSERVABILIDAD_SOMBRA.md)
- [I4 — Métricas SOMBRA](I4_METRICAS_SOMBRA.md)
- [I5 — Ejecuciones SOMBRA](I5_EJECUCIONES_SOMBRA.md)
- [I6 — Preflight V3](I6_PREFLIGHT_V3.md)
- [I7 — Feature flag V3](I7_FEATURE_FLAG_V3.md)
- [I8 — Rollback operativo](I8_ROLLBACK_OPERATIVO.md)
- [I9 — Revisión de evidencia SOMBRA](I9_SOMBRA_EVIDENCE_REVIEW.md)
- [I11 — Modo persistente](I11_MODO_PERSISTENTE_MOTOR_PAGO.md)
- [I13 — Readiness en UI](I13_CANARY_READINESS_UI.md)
- [I15 — Preflight y evidencia](I15_PREFLIGHT_Y_EVIDENCIA.md)
- [I16 — Evidencia de canary](I16_EVIDENCIA_CANARY.md)
- [I18 — Snapshot único de readiness](I18_READINESS_PREFLIGHT_SNAPSHOT.md)

### J — Consolidación

- [J1 — Mapa de APIs de pago](J1_MAPA_APIS_PAGO.md)
- [J1 — Consolidación de PlanPago](J1_CONSOLIDACION_PLAN_PAGO.md)
- [J2 — Backup y restore](J2_BACKUP_RESTORE.md)
- [J3 — Consolidación de APIs de pago](J3_CONSOLIDACION_APIS_PAGO.md)
- [J17 — Fachada única de preview](J17_PREVIEW_FACADE.md)

## 📚 Historial del Motor V3

Los documentos siguientes conservan decisiones y evolución técnica del motor.
Son útiles para reconstruir el porqué de la arquitectura, pero no son el punto
de entrada para un lector nuevo.

- [V3 — A](MOTOR_PAGOS_V3_A.md)
- [V3 — B](MOTOR_PAGOS_V3_B.md)
- [V3 — C](MOTOR_PAGOS_V3_C.md)
- [V3 — D](MOTOR_PAGOS_V3_D.md)
- [V3 — E](MOTOR_PAGOS_V3_E.md)
- [V3 — F](MOTOR_PAGOS_V3_F.md)
- [V3 — F2](MOTOR_PAGOS_V3_F2.md)
- [V3 — F3.1](MOTOR_PAGOS_V3_F3_1.md)
- [V3 — G1](MOTOR_PAGOS_V3_G1.md)
- [V3 — G2](MOTOR_PAGOS_V3_G2.md)
- [V3 — G3](MOTOR_PAGOS_V3_G3.md)
- [V3 — G4/G5](MOTOR_PAGOS_V3_G4_G5.md)
- [V3 — G7](MOTOR_PAGOS_V3_G7.md)
- [V3 — compatibilidad de tipos](MOTOR_PAGOS_V3_COMPAT_TIPOS.md)
- [V3-B — propiedades financieras](V3B_PROPIEDADES_FINANCIERAS.md)
