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

- `VER_PERSONAS`;
- `VER_AUDITORIA`;
- `VER_MOTOR_V3`;
- `OPERAR`;
- `VER_PERSONA`;
- `ADMINISTRAR_USUARIOS`.

Las páginas se ocultan según el rol y el entrypoint comprueba también la
capacidad requerida antes de renderizarlas. La navegación visual no sustituye
la verificación de autorización.


## Superficies protegidas

| Superficie | Capacidad |
| --- | --- |
| Personas | `VER_PERSONAS` |
| Auditoría | `VER_AUDITORIA` |
| Motor V3 | `VER_MOTOR_V3` |
| Operación | `OPERAR` |

Las pantallas centradas en una persona siguen además la política de alcance de
N1.

## Modo local

El proveedor local utiliza `PRESTAMOS_ROL_LOCAL`.

Por defecto usa `LOCAL_ADMIN` para no romper el uso local existente.

Esto no convierte la sesión en autenticada. El estado de identidad sigue
siendo explícitamente `autenticada=False`.

## Principio

> Tener acceso a la aplicación no significa tener acceso a todo.

El selector de persona no otorga capacidades adicionales.

## Próximo paso

N4 puede conectar roles provenientes de una identidad autenticada real y
permitir políticas por organización/tenant o por conjunto de personas.
