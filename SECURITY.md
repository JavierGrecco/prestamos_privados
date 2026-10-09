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

1. **N1** separa actor de auditoría, persona seleccionada y política de alcance.
2. **N2** introduce `IdentidadSesion` y una frontera para proveedores de
   identidad.
3. **N3** centraliza capacidades y roles. La UI local ya autentica cuentas en
   SQLite (`usuarios_app`), con hashes scrypt, bloqueo temporal por intentos
   fallidos y roles persistidos `ADMIN`, `OPERADOR` y `LECTURA`.
4. **N4**, pendiente, integrará un proveedor de identidad online para registro
   de usuarios, verificación/recuperación por email y despliegue multiusuario.

Documentación:

- [N1 — Identidad y autorización](docs/N1_IDENTIDAD_AUTORIZACION.md)
- [N2 — Identidad de sesión](docs/N2_IDENTIDAD_SESION.md)
- [N3 — Capacidades y roles](docs/N3_CAPACIDADES_ROLES.md)
- [N4 — Identidad autenticada real](https://github.com/JavierGrecco/prestamos_privados/issues/137)
- [K14 — Operador declarado](docs/K14_OPERADOR_UI.md)

El campo de operador declarado ya no se utiliza como credencial de la UI. El
actor de auditoría de la sesión autenticada local procede del nombre de usuario
verificado. Las clases antiguas de identidad local no autenticada siguen
disponibles por compatibilidad, pero no sustituyen las cuentas `usuarios_app`.

**Límite operativo:** esta autenticación está pensada para una ejecución local.
No desplegar Streamlit públicamente ni tratar este flujo como preparado para
Internet. El registro público, la recuperación por email y un proveedor OIDC/SSO
quedan pendientes de N4. Consultá la
[guía de usuarios locales](docs/OPERACION_USUARIOS_LOCALES.md).

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

### Revisión pendiente de HTML en la interfaz

La interfaz usa plantillas HTML personalizadas. Se integraron varias capas de escape y una primera comprobación estática mediante los [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162), [#164](https://github.com/JavierGrecco/prestamos_privados/pull/164), [#165](https://github.com/JavierGrecco/prestamos_privados/pull/165) y [#167](https://github.com/JavierGrecco/prestamos_privados/pull/167), pero la revisión completa sigue abierta en [#158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158). La [Auditoría de HTML en la interfaz](docs/AUDITORIA_HTML_UI.md) explica qué se revisó y qué controles faltan. La comprobación automática cubre campos conocidos, no cualquier forma de construir HTML; falta ampliar su alcance y validar los flujos relevantes.

El avance y lo que falta se explica en el [Registro de cambios](docs/REGISTRO_DE_CAMBIOS.md).

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
