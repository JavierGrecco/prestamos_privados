"""
Componentes propios de la interfaz.

Reemplazan a los componentes nativos de Streamlit que no podemos
estilizar completamente. Al crear los nuestros, garantizamos que
se vean bien en los 3 temas.

REGLA DE ORO para renderizar HTML:
  Cualquier string HTML que pasemos a st.markdown DEBE estar
  "limpio" de indentación inicial. Si no, Markdown lo interpreta
  como bloque de código y muestra las etiquetas como texto.

  Para garantizar esto, usar SIEMPRE la función render_html()
  de este módulo, que se encarga de limpiar el string.
"""
import textwrap

import streamlit as st


ICONOS_TIPO = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✕",
}


def render_html(html: str) -> None:
    """
    Renderiza un string HTML de forma segura.

    Hace dos cosas:
      1. Elimina la indentación común del string (textwrap.dedent).
      2. Elimina espacios/saltos al principio y al final (.strip).

    Sin esto, Markdown puede interpretar el HTML como bloque de
    código y mostrarlo como texto plano.

    Uso:
        render_html(f'''
            <div class="mi-clase">
                <span>Contenido</span>
            </div>
        ''')
    """
    limpio = textwrap.dedent(html).strip()
    st.markdown(limpio, unsafe_allow_html=True)


def nota_contextual(mensaje: str, tipo: str = "info") -> None:
    """
    Renderiza una nota pequeña debajo de un botón o control.
    """
    icono = ICONOS_TIPO.get(tipo, "ℹ")
    render_html(f"""
        <div class="nota-contextual nota-{tipo}">
            <span class="nota-icono">{icono}</span>
            <span class="nota-texto">{mensaje}</span>
        </div>
    """)


def disparar_nota(mensaje: str, tipo: str = "info") -> None:
    """Guarda una nota en session_state para mostrarla en el próximo render."""
    st.session_state["_nota_pendiente"] = {
        "mensaje": mensaje,
        "tipo": tipo,
    }


def renderizar_nota_pendiente() -> None:
    """Renderiza la nota pendiente si hay alguna, y la limpia."""
    pendiente = st.session_state.pop("_nota_pendiente", None)
    if pendiente:
        nota_contextual(pendiente["mensaje"], pendiente["tipo"])


def tabla(headers: list[dict], filas: list[list[str]]) -> None:
    """
    Renderiza una tabla HTML estilizada.

    Parámetros:
        headers: lista de dicts con:
            - texto: el texto del encabezado.
            - alineacion: "izq" o "der" (opcional, default "izq").
        filas: lista de filas. Cada fila es una lista de strings
            (pueden incluir HTML como <span class="badge">).
            Si una celda corresponde a una columna alineada a la
            derecha, se renderiza con la clase "num".

    Ejemplo:
        tabla(
            headers=[
                {"texto": "#"},
                {"texto": "Vencimiento"},
                {"texto": "Cuota", "alineacion": "der"},
            ],
            filas=[
                ["1", "01/02/2026", "$ 849.031,53"],
                ["2", "01/03/2026", "$ 849.031,53"],
            ],
        )
    """
    # Encabezados
    celdas_head = []
    for h in headers:
        clase = ' class="num"' if h.get("alineacion") == "der" else ""
        celdas_head.append(f'<th{clase}>{h["texto"]}</th>')

    # Filas
    filas_html = []
    for fila in filas:
        celdas = []
        for i, celda in enumerate(fila):
            alineacion = headers[i].get("alineacion", "izq") if i < len(headers) else "izq"
            clase = ' class="num"' if alineacion == "der" else ""
            celdas.append(f"<td{clase}>{celda}</td>")
        filas_html.append(f"<tr>{''.join(celdas)}</tr>")

    html = f"""
        <div class="tabla-wrapper">
            <table class="tabla-datos">
                <thead>
                    <tr>{''.join(celdas_head)}</tr>
                </thead>
                <tbody>
                    {''.join(filas_html)}
                </tbody>
            </table>
        </div>
    """
    render_html(html)


def badge(texto: str, tipo: str) -> str:
    """
    Devuelve el HTML de un badge de estado.

    tipo: "pendiente", "pagada", "parcial", "vencida", "info".
    """
    return f'<span class="badge estado-{tipo}">{texto}</span>'


def estado_vacio(icono: str, titulo: str, texto: str) -> None:
    """Renderiza un estado vacío consistente."""
    render_html(f"""
        <div class="estado-vacio">
            <div class="estado-vacio-icono">{icono}</div>
            <div class="estado-vacio-titulo">{titulo}</div>
            <div class="estado-vacio-texto">{texto}</div>
        </div>
    """)