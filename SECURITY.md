# Seguridad

Este repositorio contiene lógica financiera y puede trabajar con información
sensible. La seguridad se considera una propiedad transversal: datos,
identidad, autorización, integridad, dependencias y operación.

## Reporte de vulnerabilidades

No publicar secretos, tokens, credenciales ni datos financieros en issues,
pull requests o documentación pública.

Para una vulnerabilidad que pueda afectar al proyecto, utilizar el mecanismo
privado de reporte de seguridad de GitHub cuando esté disponible y proporcionar
solo el detalle necesario para reproducir y corregir el problema.

## Controles principales

| Área | Criterio |
|---|---|
| **Dependencias** | Revisar auditoría de dependencias y mantener dependencias actualizadas |
| **Código** | Ejecutar CodeQL y mantener la suite de pruebas verde |
| **Integridad financiera** | Preservar invariantes, atomicidad, idempotencia, concurrencia y ledger |
| **Auditoría** | No reescribir ni eliminar evidencia histórica |
| **Datos** | No versionar SQLite, WAL, SHM, `.env`, tokens ni credenciales |
| **Operación** | Verificar backup, integridad y readiness antes de activar cambios sensibles |

Una fusión no debe tratarse como aprobada por el simple hecho de que una prueba
aislada sea verde: los cambios deben superar la validación completa definida por
CI.

## Identidad y autorización

La seguridad de acceso está diseñada por capas:

1. **N1** separa operador declarado, persona seleccionada y política de acceso.
2. **N2** introduce `IdentidadSesion` y una frontera para un proveedor de
   identidad real.
3. **N3** centraliza capacidades y roles.
4. **N4**, pendiente, integrará autenticación real para un despliegue
   multiusuario.

Documentación:

- [N1 — Identidad y autorización](docs/N1_IDENTIDAD_AUTORIZACION.md)
- [N2 — Identidad de sesión](docs/N2_IDENTIDAD_SESION.md)
- [N3 — Capacidades y roles](docs/N3_CAPACIDADES_ROLES.md)
- [N4 — Identidad autenticada real](https://github.com/JavierGrecco/prestamos_privados/issues/137)
- [K14 — Operador declarado](docs/K14_OPERADOR_UI.md)

El operador declarado de la aplicación local no debe interpretarse como
autenticación. El proveedor local de identidad está documentado explícitamente
como no autenticado.

## Datos financieros

Las bases SQLite locales no se versionan. Esto incluye archivos principales,
WAL y SHM.

Las pruebas y fixtures deben usar datos sintéticos. Los backups reales deben
quedar fuera del repositorio y bajo controles de acceso adecuados.

Para un uso real todavía deben definirse controles adicionales según el entorno:
gestión de secretos, cifrado, almacenamiento externo de backups, retención,
recuperación ante desastres, monitoreo y requisitos legales/regulatorios.

## Integridad y trazabilidad

Las operaciones financieras críticas deben conservar:

- atomicidad;
- idempotencia;
- control de concurrencia;
- ledger;
- auditoría;
- evidencia SOMBRA cuando corresponda.

La auditoría y determinadas evidencias están protegidas como información
inmutable en SQLite. Las correcciones financieras deben expresarse mediante
operaciones correctivas o compensatorias, no reescribiendo historia.

## Seguridad de la transición Legacy → V3

Durante la adopción de V3 se mantiene un criterio fail-closed:

- V3 requiere preflight aprobado;
- el modo efectivo se persiste y audita;
- la activación requiere un motivo explícito;
- el canary necesita backup verificable y revisión humana;
- el rollback es una transición entre operaciones, no un cambio de motor en mitad
  de una transacción;
- Legacy no se retira hasta reunir evidencia suficiente.

Documentación operativa:

- [Runbook de canary V3](docs/CANARY_RUNBOOK_V3.md)
- [Precheck de canary](docs/CANARY_PRECHECK_V3.md)
- [Paquete de decisión de canary](docs/L1_2_PAQUETE_CANARY.md)
- [Modo persistente del motor](docs/I11_MODO_PERSISTENTE_MOTOR_PAGO.md)
- [Revisión de evidencia SOMBRA](docs/I9_SOMBRA_EVIDENCE_REVIEW.md)
- [Consumidores Legacy](docs/LEGACY_CONSUMERS.md)

## Seguridad del repositorio

Se recomienda mantener:

- PRs como mecanismo normal de integración;
- CI obligatoria cuando la configuración administrativa lo permita;
- revisiones de cambios sensibles;
- secretos fuera del código y de SQLite;
- documentación actualizada cuando cambien controles de seguridad.

La protección administrativa de `main` depende de configuración de GitHub que no
está expuesta por la integración utilizada actualmente.

## Documentación relacionada

El índice completo está en [Centro de documentación](docs/INDEX.md). Para
desarrollo y validación local, consultar [DEVELOPMENT.md](docs/DEVELOPMENT.md).
