# N2 — Identidad autenticada y contexto de sesión

## Propósito

N2 crea una frontera estable para recibir la identidad autenticada de una sesión
sin usar el selector de persona ni el operador declarado como sustitutos.

## Modelo

`IdentidadSesion` contiene:

- subject estable del proveedor;
- nombre para presentación;
- proveedor que emitió la identidad;
- indicador explícito de si la sesión está autenticada.

`ContextoSesionSeguridad` reúne:

- identidad;
- actor declarado para auditoría;
- persona seleccionada;
- resultado de la política de autorización.

Estos conceptos permanecen separados.

## Proveedor

`ProveedorIdentidad` es un protocolo mínimo.

El repositorio incluye `ProveedorIdentidadLocal`, que toma `PRESTAMOS_OPERADOR`
solo como identidad declarada de desarrollo y siempre marca `autenticada=False`.

Esto no implementa OIDC, SSO, contraseñas ni tokens.

Un proveedor real puede implementar el mismo contrato y sustituir el adaptador
local sin reescribir las pantallas ni la política.

## UI

La barra superior muestra por separado:

- **Operador declarado** — quién dice estar operando para la auditoría;
- **Persona autorizada** — persona que la política permite consultar;
- estado de la identidad de sesión — indicando si existe autenticación real.

El entrypoint construye el contexto de sesión antes de despachar las pantallas
centradas en personas.

## Seguridad

N2 no afirma que la aplicación esté autenticada en producción.

El proveedor local está diseñado para que esa diferencia quede visible y no se
confunda con una identidad real.

## Límites

- no valida credenciales;
- no verifica tokens;
- no conoce un IdP externo;
- no implementa SSO;
- no reemplaza controles de acceso del proveedor;
- no convierte el operador declarado en una identidad confiable.

## Próximo paso

N3 puede incorporar autorización por rol/alcance para superficies transversales
como Personas y Auditoría y luego conectar un proveedor autenticado real.

## Principio

> La autenticación pertenece al proveedor; la aplicación consume la identidad.

La aplicación debe poder cambiar el proveedor sin cambiar la lógica de negocio
ni las pantallas que muestran información financiera.