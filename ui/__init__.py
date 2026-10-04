"""
Capa de interfaz de usuario (Streamlit).

Esta capa es la responsable de mostrar los datos y capturar las
acciones del usuario. No contiene lógica de negocio ni acceso a
base de datos: eso vive en `dominio`, `infraestructura` y
`aplicacion`.

Reglas de esta capa:
  - Solo habla con la capa de aplicación (servicios).
  - Nunca escribe SQL.
  - Nunca calcula reglas de negocio.
  - Presenta los datos en lenguaje humano, sin jerga técnica.
"""