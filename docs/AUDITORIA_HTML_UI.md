# Auditoría de HTML dinámico en la interfaz

**Última revisión:** 27 de noviembre de 2026  
**Estado:** componentes compartidos protegidos, guarda estática ampliada y regresión AppTest sobre datos hostiles persistidos; aceptación manual en navegador y revisión de helpers/atributos indirectos todavía pendientes.  
**Seguimiento:** [Issue #158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158).

## Para qué sirve esta guía

La aplicación usa HTML propio para mantener un diseño claro y consistente. Ese HTML permite mostrar tarjetas, avisos y tablas con el aspecto previsto, pero también exige cuidado: **la función `componentes.render_html()` no limpia los datos que se insertan dentro de una plantilla**.

Por eso no alcanza con enviar cualquier texto a `render_html()`. Si el texto viene de una persona, de la base de datos o de una nota histórica, hay que escaparlo antes de incorporarlo a la plantilla.

## Qué protegen los componentes compartidos

En `ui/componentes.py` quedaron estas reglas:

- **Tablas:** encabezados y celdas se escapan por defecto. El único marcado permitido debe proceder de un componente compartido que lo construya de forma controlada.
- **Notas contextuales:** el mensaje se muestra como texto y el tipo visual se limita a opciones conocidas.
- **Badges:** el texto se escapa y la clase visual se valida contra una lista permitida.
- **Estados vacíos:** icono, título y descripción se escapan.
- **Texto dinámico:** `escapar_texto_html()` es la función compartida para convertir un valor en texto seguro dentro de una plantilla HTML.

La frontera de HTML confiable se endureció para reducir errores de desarrollo: se eliminó la función pública que permitía etiquetar cualquier string como confiable, el constructor de `FragmentoHTMLConfiable` rechaza el uso directo y la comprobación estática impide que las pantallas importen o invoquen ese constructor privado. Actualmente, los badges validan la variante CSS y escapan su texto; las notas inline también escapan su texto y la función de composición solo acepta fragmentos de tipo confiable creados por esos componentes.

Este control evita usos accidentales de la API; no es una sandbox frente a código Python malicioso ni sustituye el escape de cada valor. `render_html()` continúa aceptando plantillas HTML y exige que sus valores dinámicos se escapen explícitamente. La guarda automática identifica extracciones directas de campos textuales y sigue alias, contenedores simples (listas, tuplas, conjuntos y diccionarios), f-strings, concatenaciones, `.format()`, `.join()` y algunas transformaciones de cadena que conservan el contenido. Los valores que pasan por `escape()` o `escapar_texto_html()` dejan de marcarse como texto crudo. No es un análisis formal de taint: no sigue helpers arbitrarios, serializaciones, transformaciones desconocidas, acceso dinámico a atributos ni todo valor que termine en clases, estilos, URLs o atributos HTML. Esos casos requieren revisión específica y validación manual.

## Qué se revisó en las pantallas

La revisión manual y los cambios integrados cubren estas superficies principales:

| Pantalla o módulo | Protección aplicada |
|---|---|
| `ui/pagina_principal.py` | Nombre de la persona y explicaciones financieras escapados antes de mostrarse en tarjetas. |
| `ui/pagina_prestamos.py` | Título y número del préstamo, estado/vencimiento visible y textos del historial de decisiones escapados. Los badges de pago usan fragmentos controlados. |
| `ui/pagina_pagos.py` | Nota, motivo de anulación, medio, referencia, creador, correlación, datos de auditoría y resumen de observaciones SOMBRA escapados. Las tablas pasan por el componente común. |
| `ui/pagina_registrar_pago.py` | Destino del préstamo, etiquetas de desglose y errores mostrados dentro de HTML escapados. |
| `ui/pagina_alta_prestamo.py` | Nombre del inversor y error de cálculo escapados en las plantillas personalizadas. Los bloques HTML habilitados directamente usan rótulos estáticos. |
| `ui/pagina_analisis.py` | Nombres y descripciones de escenarios y advertencias escapados. |
| `ui/pagina_detalle_financiero.py` | Tipo de recálculo, error de detalle y número de préstamo escapados; las tablas usan el componente común. |
| `ui/pagina_motor_v3.py` | Observaciones, motivos de readiness y detalles mostrados en tablas protegidos antes de llegar a HTML. |
| `ui/pagina_operacion.py` | Errores de integridad y motivos de bloqueo escapados. |
| `ui/personas_view.py`, `ui/pagina_auditoria.py` y `ui/pagina_mi_espacio.py` | Las tablas de texto pasan por el componente seguro; los textos colocados directamente en tarjetas se escapan. |
| `ui/ss.py` | El renderer principal heredado también escapa el nombre y las descripciones. El punto de entrada actual usa `ui/pagina_principal.py`; esta protección evita reintroducir el fallo si el módulo antiguo se reutiliza. |
| `ui/estilos.py` | El HTML permitido se limita al CSS generado por la propia aplicación a partir de temas definidos en el código. No debe incorporarse texto del usuario a esa plantilla. |

El contenido de reportes se presenta con `st.markdown()` sin habilitar HTML explícitamente. Si esa configuración cambiara, el reporte deberá revisarse de nuevo antes de permitir HTML.

La guarda estática reconoce f-strings, concatenaciones con `+`, llamadas a `.format()` y uniones mediante `.join()`. Sigue texto sensible por alias locales, listas, tuplas, conjuntos, diccionarios, comprensiones y transformaciones de cadena acotadas como `.strip()`. Los valores que se escapan antes de incorporarse a la plantilla dejan de marcarse como texto crudo. Las regresiones cubren rutas inseguras y seguras, así como texto insertado en atributos `class` y `style`. No es un análisis formal de taint de Python: no sigue helpers arbitrarios, serializaciones, acceso dinámico a atributos ni todos los valores calculados que terminan en URLs, clases, estilos u otros atributos; esos límites requieren revisión específica.

## Pruebas que respaldan la primera capa

- `tests/test_componentes_html.py`: prueba texto malicioso en tablas, notas, badges y estados vacíos; también verifica que la construcción pública de fragmentos confiables falle.
- `tests/test_prestamos_html.py`: prueba etiquetas e atributos maliciosos en el historial de decisiones.
- `tests/test_ss_html.py`: prueba el renderer principal heredado.
- `tests/test_ui_html_escape_contract.py`: revisa f-strings, concatenaciones, `.format()` y `.join()` con marcado HTML literal; sigue datos por alias y contenedores; comprueba escape anidado, valores dinámicos en `class`/`style` y bloquea la creación/importación de fragmentos confiables desde las pantallas.
- `tests/test_ui_e2e.py::test_ui_escapa_nombre_y_destino_maliciosos_leidos_desde_sqlite` (PR #414): ejecuta el entrypoint real con AppTest y SQLite sintético, inyecta un nombre con `<img onerror>` y un destino con `<script>`, y comprueba que Resumen y Mi espacio entregan texto escapado al renderizador. No inspecciona el DOM final ni sustituye la aceptación manual en navegador.

La ampliación estática se integró mediante PR #413; sus checks post-merge aprobaron **1.432 pruebas por Python 3.11–3.14**, CodeQL, `pip-audit` y housekeeping ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035822) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035784) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035796)). La prueba AppTest descrita arriba se incorpora mediante PR #414 y queda sujeta a su propio CI.

Estas pruebas verifican que las plantillas generadas contengan texto escapado y que los flujos existentes no fallen. No son, por sí solas, una garantía universal frente a toda posible inyección en el navegador.

## Qué falta antes de cerrar el issue

1. **Ampliar la frontera de datos:** mantener actualizado el catálogo de campos editables y revisar helpers indirectos, acceso dinámico a atributos y cualquier valor que se incorpore a `class`, `style`, `href`, `src` u otros atributos. Cuando el valor sea una clase/estilo calculado, usar una lista permitida específica, no solo escape HTML.
2. **Completar la revisión de extremo a extremo:** abrir la aplicación en navegador con datos sintéticos que incluyan etiquetas, comillas, ampersands y cierres de etiqueta en nombres, destinos, notas, motivos y referencias; confirmar que aparecen literalmente, sin alterar el DOM ni ejecutar eventos.
3. **Mantener la regla visible:** cualquier plantilla nueva debe documentar qué partes son HTML fijo y qué partes son texto dinámico, y agregar una prueba si la pantalla muestra datos editables.
4. **Revisar de nuevo los módulos heredados:** si se confirma que una pantalla vieja no se usa ni tiene consumidores externos, decidir si conviene retirarla en vez de mantener dos implementaciones.

PR #413 integró la ampliación de la guarda estática. PR #414 añade un recorrido AppTest del entrypoint real con datos hostiles provenientes de SQLite. El issue #158 permanece abierto hasta completar la revisión de atributos/helpers indirectos y la aceptación manual en navegador. AppTest no inspecciona el DOM final ni prueba la ejecución JavaScript; la CI verde no acredita una auditoría universal de toda la superficie.

## Regla simple para quien desarrolle después

- Para texto normal, preferir los componentes nativos de Streamlit.
- Para tablas, notas, badges y estados vacíos, usar los componentes compartidos.
- Si una plantilla necesita HTML propio, escapar cada valor dinámico con `escapar_texto_html()`.
- Usar `fragmento_html_confiable()` solo para marcado estático escrito en el código, nunca para nombres, notas, referencias ni otros datos externos.
