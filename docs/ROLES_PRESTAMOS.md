# Roles de personas en préstamos

## Cuenta de acceso vs. rol financiero

Los permisos para entrar a la aplicación pertenecen a `usuarios_app.rol`:
`ADMIN`, `OPERADOR` o `LECTURA`. El rol de una persona en el negocio no
concede permisos de inicio de sesión ni capacidades de administración.

Los roles financieros son acumulables:
- **DEUDOR:** la persona recibe un préstamo.
- **INVERSOR:** la persona aporta capital a una operación.
- **GARANTE:** la persona tiene una garantía registrada para una o más operaciones.

Una misma persona puede tener los tres roles, participando en operaciones
distintas. Las reglas de cada préstamo se validan por operación; por ejemplo,
el sistema no permite que el deudor sea inversor ni garante de su propio
préstamo. Eso no impide que la persona cumpla otras funciones en operaciones
diferentes.

## Validación de alta de préstamo

El alta de préstamos valida los roles cuando una persona tiene roles explícitos
administrados por el módulo Personas:

- el deudor debe tener el rol DEUDOR;
- cada inversor debe tener el rol INVERSOR;
- la persona debe estar ACTIVA;
- una persona histórica sin roles sigue siendo aceptada para mantener
  compatibilidad con datos anteriores a K10.

Esta validación está en la capa de aplicación y no depende de la UI, por lo
tanto una llamada programática recibe las mismas garantías que Streamlit.

## Garantías por préstamo

El rol general GARANTE clasifica a una persona, pero no dice qué préstamo está
garantizando ni qué alcance se registró. La relación concreta se guarda en
`garantias_prestamo`, con el préstamo, la persona, el alcance declarado, un
tope ARS opcional, estado e historial de finalización.

- solo se registra una garantía para una persona existente y activa;
- el deudor no puede garantizar su propio préstamo;
- un par préstamo-persona tiene como máximo una garantía ACTIVA;
- liberar o anular requiere un motivo y conserva el registro histórico;
- liberar una garantía no baja automáticamente el rol general GARANTE porque
  puede seguir aplicando a otras operaciones;
- registrar una garantía no modifica intereses, mora, deuda, cuotas, pagos,
  participaciones ni ledger.

El campo de tope vacío significa “no se registró un tope”; no supone que la
aplicación haya determinado la cobertura jurídica del acuerdo. La ficha del
sistema registra el alcance declarado y no sustituye los documentos legales.

## ADMIN financiero histórico

La migración inicial permitía `ADMIN` en `roles_persona`. Ese valor se
conserva como legado para no alterar el historial; no otorga permisos de
aplicación. No se admite en altas nuevas. Si se da de baja un rol ADMIN histórico,
la operación debe ser explícita y registrar un motivo.

## Migraciones y compatibilidad

D2 agrega:
- v019, asociación opcional entre una cuenta y una persona; cuentas existentes
  permanecen desvinculadas;
- v020, tabla de garantías por préstamo con claves foráneas restrictivas.

Ninguna migración altera hechos financieros históricos. Antes de actualizar una
base existente, seguir [Operación de migraciones](OPERACION_MIGRACIONES.md) y
crear el backup verificado exigido por la herramienta.
