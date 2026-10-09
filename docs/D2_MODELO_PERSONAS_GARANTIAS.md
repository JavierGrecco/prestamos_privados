# D2 — Modelo de personas polifuncionales, cuentas y garantías

**Estado:** diseño de implementación para la entrega D2; sujeto a revisión en el PR.  
**Issue:** [#175](https://github.com/JavierGrecco/prestamos_privados/issues/175)  
**Programa:** [Plan de evolución UX e identidad polifuncional](PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md)

## 1. Contrato del modelo

Se separan cuatro conceptos que no deben darse permisos ni sustituirse entre sí:

1. **Cuenta de acceso**: usuario, contraseña, estado y capacidad de aplicación (`ADMIN`, `OPERADOR`, `LECTURA`).
2. **Persona**: individuo del negocio identificado por los datos de la tabla `personas`.
3. **Rol financiero general**: funciones posibles de la persona: `DEUDOR`, `INVERSOR`, `GARANTE`.
4. **Relación por préstamo**: participación concreta como deudor, inversor o garante, con su estado y su trazabilidad.

Los roles financieros se acumulan; no son mutuamente excluyentes entre préstamos. Una persona puede ser deudora en A, inversora en B y garante en C. El servicio financiero conserva reglas específicas por operación: por ejemplo, no permite que el deudor sea inversor de su propio préstamo. Un rol general no invalida esa regla ni la reemplaza.

**ADMIN de aplicación no es un rol financiero.** La capacidad administrativa procede de la cuenta autenticada. Nunca se deriva de `roles_persona`.

## 2. Tratamiento de ADMIN histórico en roles de persona

La tabla histórica `roles_persona` y la constraint de su migración inicial aceptan `ADMIN`. No se va a reconstruir esa tabla ni transformar automáticamente sus filas: podrían existir registros históricos de uso previo.

La transición segura es:
- las altas nuevas solo admiten `DEUDOR`, `INVERSOR` y `GARANTE`;
- no se agregan nuevas filas `ADMIN` desde el servicio ni desde la UI;
- las filas antiguas `ADMIN` se conservan y se presentan como legado, con una explicación de que **no otorgan permisos de acceso**;
- su eventual baja debe ser explícita y conservar `fecha_baja` y `motivo_baja`; nunca se elimina el registro;
- los permisos de la aplicación siguen resolviéndose exclusivamente desde `usuarios_app.rol`.

No se requiere una migración que borre o reescriba los antiguos roles para aplicar esa regla a las altas nuevas.

## 3. Asociación opcional cuenta-persona

La cuenta puede quedar vinculada a **cero o una persona**. La relación es opcional para soportar administradores, operadores de oficina y cuentas técnicas que necesitan entrar antes de que exista una persona vinculada.

Reglas:
- una cuenta puede vincularse o desvincularse desde administración de usuarios;
- el sistema no intenta inferir una identidad comparando nombre de usuario y nombre de persona;
- se permite que una persona tenga más de una cuenta explícitamente vinculada; no se crea una restricción `UNIQUE` que impida escenarios de gestión legítimos;
- editar este vínculo no cambia el rol de acceso ni agrega capacidades;
- un cambio de vínculo incrementa la revisión de sesión, igual que un cambio que afecta el contexto de seguridad;
- borrar una persona debe quedar restringido por sus relaciones financieras existentes; la cuenta queda desvinculada si la persona se elimina en un flujo autorizado futuro.

La asociación sirve para personalizar y determinar el contexto de **Mi espacio**. No se debe considerar, por sí sola, una frontera de autorización por datos. D3 define y prueba el alcance efectivo que cada rol puede consultar. En modo local no se habilita acceso público ni identidad online.

## 4. Garantías personales vinculadas a un préstamo

La marca global `GARANTE` en una persona solo indica que puede cumplir ese papel. No expresa qué préstamo garantiza. Para eso se introduce una relación independiente con su propio identificador.

Campos de la relación:
- préstamo y persona garante;
- descripción obligatoria del alcance acordado;
- importe máximo opcional en ARS, representado como texto decimal;
- estado `ACTIVA`, `LIBERADA` o `ANULADA`;
- fecha de constitución y, cuando corresponde, fecha/motivo de finalización;
- autor y fechas de creación/actualización.

Reglas:
- solo se asocia una persona existente y activa con un préstamo existente que no esté cancelado, anulado ni finalizado;
- la misma persona no puede ser garante de su propio préstamo como deudora;
- puede tener otras funciones financieras en esa misma cartera; toda incompatibilidad específica queda validada por la operación correspondiente, no mediante prohibiciones globales sobre los roles;
- se admite como máximo una relación de garantía `ACTIVA` para el mismo par préstamo-persona. Un vínculo liberado o anulado queda como historial y una nueva constitución genera otra fila;
- la descripción del alcance es obligatoria. Un importe máximo vacío significa **“no se registró un tope”**, no que el sistema haya determinado la cobertura jurídica;
- asignar una garantía activa también asegura que el rol general `GARANTE` quede activo para esa persona. Liberar una garantía no da de baja automáticamente el rol, porque puede usarlo en otras operaciones;
- liberar/anular conserva la fila y el motivo, y deja auditoría. No se eliminan pagos, cuotas, ledger ni historial;
- la garantía es un registro de la relación declarada: no cambia automáticamente deuda, interés, mora, waterfall, saldo o pagos y no sustituye la documentación legal del acuerdo.

## 5. Migraciones

- **v019 — vínculo cuenta-persona:** agrega `usuarios_app.persona_id` nullable con FK a `personas`, e índice de búsqueda. Las cuentas existentes quedan sin vínculo; no se intenta deducirlo.
- **v020 — garantías por préstamo:** crea el registro de relaciones de garantía y sus índices, con FK restrictivas para preservar el historial.

Ambas migraciones son aditivas y no reescriben hechos financieros previos. Deben tener pruebas de upgrade y de restricciones, además de una verificación de integridad con `PRAGMA foreign_key_check`.

## 6. Pruebas de aceptación

1. Una persona conserva simultáneamente `DEUDOR`, `INVERSOR` y `GARANTE`.
2. Esa misma persona puede tener una deuda, una inversión y una garantía vinculadas a préstamos distintos.
3. Un préstamo no permite que su propio deudor se registre como garante.
4. No se puede asignar una garantía a una persona inexistente/inactiva ni a un préstamo terminal.
5. Un mismo par préstamo-garante no admite dos garantías activas; al liberar una, su historial queda y se permite una nueva constitución posterior.
6. La liberación exige motivo y conserva los datos originales de la relación.
7. Ninguna alta nueva permite el rol financiero `ADMIN`; un registro histórico que ya exista sigue disponible para inspección sin conferir permisos.
8. Las cuentas existentes sobreviven a v019 sin perder roles, revisiones de sesión ni contraseñas derivadas; quedan sin persona vinculada.
9. La creación o edición de un vínculo cuenta-persona no altera el rol de la cuenta, y revoca la sesión cuando cambia la asociación.
10. Crear/liberar garantías no modifica saldos, deuda, cuotas, pagos, participaciones ni ledger.
