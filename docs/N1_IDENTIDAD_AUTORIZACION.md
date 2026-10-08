# N1 — Identidad, persona seleccionada y autorización

## Problema

La barra superior permite elegir una persona y hoy también muestra un operador
declarado. Ninguno de esos dos elementos es autenticación real.

N1 introduce una frontera explícita:

- actor declarado de la sesión;
- persona seleccionada para la vista;
- personas que la política permite consultar.

## Política

La variable `PRESTAMOS_PERSONAS_PERMITIDAS` acepta IDs separados por comas.

Cuando está configurada, las pantallas centradas en una persona solo pueden
consultar IDs incluidos en esa allowlist.

Además, el selector de persona muestra únicamente personas autorizadas y el
entrypoint vuelve a verificar la autorización antes de despachar la pantalla.

## Modo local

Cuando no existe allowlist, la aplicación mantiene compatibilidad con el uso
local y muestra explícitamente:

**Modo local sin autenticación**.

Esto significa que el sistema no pretende haber resuelto identidad real en ese
entorno.

## Qué no es

- el operador declarado no es autenticación;
- la allowlist no es un proveedor de identidad;
- seleccionar una persona no otorga permisos adicionales;
- la política no reemplaza SSO, sesión autenticada, roles o gestión de acceso.

## Próximo paso

N2 puede conectar un proveedor de identidad real y mapear su identidad a un
alcance de personas, conservando la misma interfaz de autorización.

## Principio

> La persona seleccionada es un objeto de consulta; no es una identidad.

La arquitectura debe mantener esa separación incluso cuando se incorpore un
proveedor de autenticación real.