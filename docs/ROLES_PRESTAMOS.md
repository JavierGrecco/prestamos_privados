# Roles de personas en alta de préstamos

El alta de préstamos valida ahora los roles cuando una persona ya tiene roles
explícitos administrados por el módulo de Personas.

## Regla

- el deudor debe tener el rol DEUDOR;
- cada inversor debe tener el rol INVERSOR;
- una persona con roles explícitos debe estar ACTIVA;
- una persona histórica sin roles sigue siendo aceptada para mantener
  compatibilidad con datos anteriores a K10.

Esta estrategia permite adoptar el modelo de roles gradualmente sin invalidar
automáticamente una base existente.

## Alcance

La validación está en la capa de aplicación y no depende de la UI. Por lo
tanto una llamada programática al alta recibe las mismas garantías que
Streamlit.

No se cambia ningún cálculo financiero ni la persistencia histórica de roles.
