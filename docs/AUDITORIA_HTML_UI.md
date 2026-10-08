# Auditoría de HTML dinámico en la interfaz

**Última revisión:** 8 de octubre de 2026  
**Estado:** primera capa integrada; revisión y prevención automática todavía pendientes.  
**Seguimiento:** [Issue #158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158).

## Para qué sirve esta guía

La aplicación usa HTML propio para mantener un diseño claro y consistente. Ese HTML permite mostrar tarjetas, avisos y tablas con el aspecto previsto, pero también exige cuidado: **la función `componentes.render_html()` no limpia los datos que se insertan dentro de una plantilla**.

Por eso no alcanza con enviar cualquier texto a `render_html()`. Si el texto viene de una persona, de la base de datos o de una nota histórica, hay que escaparlo antes de incorporarlo a la plantilla.

## Qué protegen los componentes compartidos

En `ui/componentes.py` quedaron estas reglas:

- **Tablas:** encabezados y celdas se escapan por defecto. Solo se interpreta HTML cuando la celda se marca expresamente como `FragmentoHTMLConfiable`.
- **Notas contextuales:** el mensaje se muestra como texto y el tipo visual se limita a opciones conocidas.
- **Badges:** el texto se escapa y la clase visual se valida contra una lista permitida.
- **Estados vacíos:** icono, título y descripción se escapan.
- **Texto dinámico:** `escapar_texto_html()` es la función compartida para convertir un valor en texto seguro dentro de una plantilla HTML.

La marca de HTML confiable sirve para que el código deje claro cuándo espera mostrar marcado. No es una barrera que pueda sanear HTML arbitrario: debe usarse solo con fragmentos escritos y controlados por la aplicación.

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

## Pruebas que respaldan la primera capa

- `tests/test_componentes_html.py`: prueba texto malicioso en tablas, notas, badges y estados vacíos.
- `tests/test_prestamos_html.py`: prueba etiquetas e atributos maliciosos en el historial de decisiones.
- `tests/test_ss_html.py`: prueba el renderer principal heredado.
- `tests/test_ui_html_escape_contract.py`: revisa las plantillas HTML de la interfaz y alerta si encuentra interpolaciones directas de una lista conocida de campos sensibles sin escape explícito.

Los PR [#162](https://github.com/JavierGrecco/prestamos_privados/pull/162), [#164](https://github.com/JavierGrecco/prestamos_privados/pull/164), [#165](https://github.com/JavierGrecco/prestamos_privados/pull/165) y [#167](https://github.com/JavierGrecco/prestamos_privados/pull/167) integraron estas capas y sus regresiones. Antes de integrarlos, los checks pasaron en Python 3.11, 3.12, 3.13 y 3.14, además de la auditoría de dependencias y CodeQL.

Estas pruebas verifican que las plantillas generadas contengan texto escapado y que los flujos existentes no fallen. No son, por sí solas, una garantía universal frente a toda posible inyección en el navegador.

## Qué falta antes de cerrar el issue

1. **Ampliar la regla automática:** ya existe una comprobación estática, pero solo reconoce campos y patrones conocidos. Extenderla para detectar más atributos, aliases y valores usados en clases o estilos; considerar una API de plantillas tipadas a medida que se refactoricen las pantallas.
2. **Completar la revisión de extremo a extremo:** probar las superficies relevantes con datos de ejemplo que incluyan etiquetas, comillas, ampersands y cierres de etiqueta.
3. **Mantener la regla visible:** cualquier plantilla nueva debe documentar qué partes son HTML fijo y qué partes son texto dinámico, y agregar una prueba si la pantalla muestra datos editables.
4. **Revisar de nuevo los módulos heredados:** si se confirma que una pantalla vieja no se usa ni tiene consumidores externos, decidir si conviene retirarla en vez de mantener dos implementaciones.

El issue #158 permanece abierto hasta ampliar la prevención automática y validar los flujos de interfaz. No debe darse por cerrada toda la superficie solo porque las pruebas actuales estén verdes.

## Regla simple para quien desarrolle después

- Para texto normal, preferir los componentes nativos de Streamlit.
- Para tablas, notas, badges y estados vacíos, usar los componentes compartidos.
- Si una plantilla necesita HTML propio, escapar cada valor dinámico con `escapar_texto_html()`.
- Usar `fragmento_html_confiable()` solo para marcado estático escrito en el código, nunca para nombres, notas, referencias ni otros datos externos.
