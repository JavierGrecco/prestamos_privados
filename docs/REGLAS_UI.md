# Reglas de la capa de UI

## Regla 1 - Renderizado seguro de HTML

Nunca pasar un string HTML multilinea a `st.markdown()` directamente.
Siempre usar `componentes.render_html()` o `componentes.tabla()`.

Razon: Markdown interpreta strings con indentacion de 4+ espacios
como bloques de codigo.

## Regla 2 - Estilos de componentes HTML crudos

Todo componente HTML que no sea un widget nativo (tabla, badge,
tarjeta, div, span) debe tener `!important` en background, color,
border y border-radius.

## Regla 3 - Testing de los 3 temas

Antes de dar por terminado cualquier componente, verificarlo en
claro, intermedio y oscuro.

## Regla 4 - Mensajeria propia

Nunca usar `st.toast`, `st.info`, `st.warning`, `st.error`,
`st.success`, `help=`. Usar los componentes de `componentes.py`.

## Regla 5 - Variantes semánticas de controles

Las variantes visuales deben ser consistentes. Se permite destacar una acción
o la ruta activa con una variante semántica (por ejemplo, `type="primary"`
para la página activa de la navegación). No se deben crear botones falsos con
HTML ni usar el color como única forma de comunicar un estado.

## Regla 6 - `!important` en widgets nativos

Los widgets nativos tienen CSS interno que depende del modo del SO.
Todos los selectores en los CSS deben llevar `!important`.

## Regla 7 - `-webkit-text-fill-color` en inputs

Chrome y Safari aplican `-webkit-text-fill-color` que sobrescribe
`color` en inputs. Siempre configurar color, -webkit-text-fill-color
y caret-color.

## Regla 8 - Los desplegables son portales

Los selectbox/multiselect de BaseWeb se renderizan en un portal
fuera del arbol principal. Hay que estilizar:
- `div[data-baseweb="popover"]`
- `ul[role="listbox"]` y `div[role="listbox"]`
- `li[role="option"]` y `div[role="option"]`
- `li[aria-selected="true"]`
- `li:hover`

## Regla 9 - Esquema nativo coherente con el tema

Los controles del navegador deben seguir el tema seleccionado. La aplicación
usa oscuro como valor predeterminado, pero no debe aplicar `color-scheme: dark`
a temas claros. `ui/estilos.py` sustituye el token `__COLOR_SCHEME__` al
inyectar los estilos: `dark` para oscuro y `light` para claro/intermedio.

## Regla 10 - Auditar widgets nuevos ANTES de usarlos

Antes de usar un widget que no hayamos usado antes:
1. Agregarlo solo.
2. Probarlo en los 3 temas.
3. Interactuar con el (clic, escribir, desplegar).
4. Agregar CSS si hace falta.
5. Recien entonces usarlo en el codigo real.

Widgets auditados:
- st.button, st.form_submit_button
- st.popover: cobertura funcional AppTest añadida en D4; revisión visual manual pendiente
- st.selectbox, st.multiselect
- st.text_input, st.number_input, st.text_area, st.date_input
- st.segmented_control
- st.metric
- st.columns

Widgets pendientes de auditar:
- st.checkbox, st.radio, st.slider
- st.file_uploader, st.expander, st.tabs
- st.form

## Estructura de archivos CSS

- `ui/estilos_base.css`        -> reset, layout, inputs basicos
- `ui/estilos_controles.css`   -> botones, selectbox, date, calendario
- `ui/estilos_componentes.css` -> notas, tarjetas, tablas, badges, metricas
- `ui/estilos.py`              -> lee los 3 CSS y los inyecta