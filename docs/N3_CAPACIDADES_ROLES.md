# N3 — Autorización por capacidades y roles

## Propósito

N3 centraliza qué puede hacer una identidad una vez que la aplicación ya tiene
una identidad de sesión.

Autenticación e autorización son cosas distintas:

**autenticación** → quién es la identidad;

**autorización** → qué capacidades tiene.

## Roles de cuenta local

La UI local utiliza cuentas separadas de las personas del negocio, guardadas
en la tabla `usuarios_app`. Las contraseñas se derivan con scrypt y nunca se
persisten en texto plano. En una base sin cuentas, el primer inicio permite
crear el administrador inicial; no existe una contraseña predeterminada.

- **ADMIN** — acceso completo, incluida la administración de cuentas;
- **OPERADOR** — puede consultar y operar, pero no administrar usuarios ni
  configurar Motor V3;
- **LECTURA** — puede usar los paneles de consulta; no ve ni abre las pantallas
  de operación, pagos, personas o administración de usuarios.

La pantalla **Usuarios** permite crear cuentas, cambiar nombre/rol/estado y
restablecer contraseñas. Los cambios quedan auditados. La aplicación impide
desactivar o degradar al último administrador activo.

`LOCAL_ADMIN` y `ProveedorIdentidadLocal` permanecen por compatibilidad con
código local anterior y pruebas internas; no son el mecanismo de inicio de
sesión de la UI.

## Capacidades

- `VER_PERSONA`: acceso a paneles personales, planificación, análisis y reportes de consulta.
- `OPERAR`: uso de Personas, Préstamos, Pagos y detalle financiero.
- `VER_PERSONAS`: capacidad disponible para una futura vista de directorio estrictamente de solo lectura; no habilita por sí misma la interfaz de administración de Personas.
- `VER_AUDITORIA`: consulta de evidencia histórica.
- `ADMINISTRAR_USUARIOS`: gestión de cuentas, credenciales y vinculación opcional con una persona.
- `ADMINISTRAR_SISTEMA`: backups, restauración y controles operativos del sistema.
- `VER_MOTOR_V3`: consulta del estado y readiness de Motor V3.
- `CONFIGURAR_MOTOR_V3`: cambio del modo efectivo del motor; requiere permiso propio aunque la pantalla permita consultar su estado.

El catálogo único en [ui/navegacion.py](../ui/navegacion.py) define por pantalla
el grupo, la capacidad requerida, si necesita una persona en contexto y si es
una ruta navegable o contextual. La aplicación deriva el menú de ese catálogo
y vuelve a comprobar la capacidad antes de renderizar cada ruta. La navegación
visual nunca es la única barrera de autorización.

## Superficies protegidas

| Superficie | Capacidad | Ubicación |
| --- | --- | --- |
| Resumen, Mi espacio, Planificación, Escenarios, Análisis, Rendimiento, Comparar y Reportes | `VER_PERSONA` | Inicio / análisis |
| Personas, Préstamos, Pagos | `OPERAR` | Cartera |
| Detalle financiero | `OPERAR` | Contextual: se abre desde un préstamo |
| Auditoría | `VER_AUDITORIA` | Administración |
| Usuarios y accesos | `ADMINISTRAR_USUARIOS` | Administración |
| Operación del sistema | `ADMINISTRAR_SISTEMA` | Administración, solo ADMIN |
| Motor de pagos avanzado | `VER_MOTOR_V3` | Administración, solo ADMIN actualmente |
| Cambiar el modo efectivo de Motor V3 | `CONFIGURAR_MOTOR_V3` | Acción avanzada, solo ADMIN actualmente |

Las pantallas financieras que requieren una persona seleccionada usan además
la política de alcance de N1. **Mi espacio** es diferente: consulta la persona
vinculada a la cuenta y no reutiliza la selección global del operador.

## Identidad local actual

La UI obtiene la identidad de la cuenta local autenticada guardada en
`usuarios_app`; el rol y el estado no vienen de un campo editable ni de
`PRESTAMOS_ROL_LOCAL`. Las cuentas nuevas se crean desde el administrador.
La clave se deriva con scrypt, hay bloqueo temporal tras cinco intentos fallidos
y los cambios de cuentas se registran en auditoría. La migración v018 agrega
una revisión de sesión y las migraciones v019/v020 incorporan la vinculación
opcional cuenta-persona y las garantías ligadas a préstamos: los cambios de contraseña, rol o estado invalidan
sesiones anteriores y exigen un nuevo inicio de sesión.

El asistente inicial permite crear la primera cuenta ADMIN, porque una base
nueva no tiene todavía quién administre las cuentas. No existe usuario ni clave
predeterminados. Esta configuración es **solo local** y no se debe exponer a
Internet.

La recuperación de ADMIN funciona como mantenimiento offline con acceso al
equipo y al archivo SQLite. No hay registro público ni recuperación por email
en esta etapa; esos flujos requieren un proveedor de identidad real (N4).

## Principio

> Tener acceso a la aplicación no significa tener acceso a todo.

El selector de persona no otorga capacidades adicionales.

## Próximo paso

N4 puede conectar roles provenientes de una identidad autenticada real y
permitir políticas por organización/tenant o por conjunto de personas.
