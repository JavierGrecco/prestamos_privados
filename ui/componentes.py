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
from html import escape

import streamlit as st


ICONOS_TIPO = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✕",
}


_TOKEN_FRAGMENTO_HTML = object()


class FragmentoHTMLConfiable(str):
    """Fragmento HTML construido solo por componentes compartidos controlados."""

    def __new__(cls, markup: str, *, _token: object | None = None):
        if _token is not _TOKEN_FRAGMENTO_HTML:
            raise TypeError(
                "Los fragmentos HTML confiables solo se crean desde componentes seguros"
            )
        if not isinstance(markup, str):
            raise TypeError("El fragmento HTML debe ser texto")
        return super().__new__(cls, markup)


def escapar_texto_html(valor: object) -> str:
    """Escapa un valor para mostrarlo como texto dentro de HTML."""
    return escape(str(valor), quote=True)


def _crear_fragmento_html_confiable(markup: str) -> FragmentoHTMLConfiable:
    """Construye marcado interno después de escapar los datos variables."""
    return FragmentoHTMLConfiable(markup, _token=_TOKEN_FRAGMENTO_HTML)


def render_html(html: str) -> None:
    """
    Renderiza una plantilla HTML construida por la aplicación.

    Limpia indentación y espacios exteriores, pero NO sanea el HTML ni
    escapa valores dinámicos. Todo texto variable debe pasar por
    escapar_texto_html() antes de incorporarse a una plantilla. Para mostrar
    texto libre, preferir los componentes específicos de este módulo.
    """
    limpio = textwrap.dedent(html).strip()
    st.markdown(limpio, unsafe_allow_html=True)


def nota_contextual(mensaje: str, tipo: str = "info") -> None:
    """
    Renderiza una nota pequeña debajo de un botón o control.
    """
    tipo_css = tipo if tipo in ICONOS_TIPO else "info"
    icono = ICONOS_TIPO[tipo_css]
    mensaje_html = escapar_texto_html(mensaje)
    render_html(f"""
        <div class="nota-contextual nota-{tipo_css}">
            <span class="nota-icono">{icono}</span>
            <span class="nota-texto">{mensaje_html}</span>
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

    Los encabezados y las celdas se tratan como texto y se escapan
    automáticamente. Solo se permite HTML en una celda si se entrega un
    FragmentoHTMLConfiable creado desde markup estático de la aplicación.

    Parámetros:
        headers: lista de dicts con texto y alineación opcional.
        filas: lista de filas con texto o fragmentos HTML controlados.

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
        texto = escapar_texto_html(h.get("texto", ""))
        celdas_head.append(f'<th{clase}>{texto}</th>')

    # Filas
    filas_html = []
    for fila in filas:
        celdas = []
        for i, celda in enumerate(fila):
            alineacion = headers[i].get("alineacion", "izq") if i < len(headers) else "izq"
            clase = ' class="num"' if alineacion == "der" else ""
            contenido = (
                str(celda)
                if isinstance(celda, FragmentoHTMLConfiable)
                else escapar_texto_html(celda)
            )
            celdas.append(f"<td{clase}>{contenido}</td>")
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
    tipos_permitidos = {
        "pendiente", "pagada", "parcial", "vencida", "info",
        "complemento", "adelanto", "success", "warning", "error",
    }
    tipo_css = tipo if tipo in tipos_permitidos else "info"
    texto_html = escapar_texto_html(texto)
    return _crear_fragmento_html_confiable(
        f'<span class="badge estado-{tipo_css}">{texto_html}</span>'
    )


def estado_vacio(icono: str, titulo: str, texto: str) -> None:
    """Renderiza un estado vacío consistente."""
    icono_html = escapar_texto_html(icono)
    titulo_html = escapar_texto_html(titulo)
    texto_html = escapar_texto_html(texto)
    render_html(f"""
        <div class="estado-vacio">
            <div class="estado-vacio-icono">{icono_html}</div>
            <div class="estado-vacio-titulo">{titulo_html}</div>
            <div class="estado-vacio-texto">{texto_html}</div>
        </div>
    """)