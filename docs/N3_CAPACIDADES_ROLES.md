# N3 — Autorización por capacidades y roles

## Propósito

N3 centraliza qué puede hacer una identidad una vez que la aplicación ya tiene
una identidad de sesión.

Autenticación e autorización son cosas distintas:

**autenticación** → quién es la identidad;

**autorización** → qué capacidades tiene.

## Roles

- **ADMIN** — acceso completo;
- **OPERADOR** — puede consultar y operar, pero no administrar/ver Motor V3;
- **LECTURA** — puede consultar personas y datos de persona, pero no operar ni
  ver Auditoría;
- **LOCAL_ADMIN** — compatibilidad del modo local sin autenticación real.

Los roles están en `aplicacion/seguridad/capacidades.py`.

## Capacidades

- `VER_PERSONAS`;
- `VER_AUDITORIA`;
- `VER_MOTOR_V3`;
- `OPERAR`;
- `VER_PERSONA`.

Las pantallas transversales declaran su capacidad requerida y el entrypoint la
verifica antes de renderizar.

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
