"""
Página de registro de pago.

Flujo:
  1. Cuota del mes (con desglose si hay arrastre).
  2. Monto editable.
  3. Si el monto excede el total: elección explícita RAI o RNI
     con tarjetas grandes. Sin default.
  4. Preview del impacto.
  5. Confirmar.
"""
from datetime import date
from decimal import Decimal

import streamlit as st

from infraestructura.db import BaseDatos
from infraestructura.repositorios import PrestamoRepo
from aplicacion.servicios import ServicioPagos, ErrorServicio, ErrorEstadoInvalido

from . import componentes


def _formatear_pesos(valor: Decimal) -> str:
    negativo = valor < 0
    valor_abs = abs(valor)
    entero, decimales = f"{valor_abs:.2f}".split(".")
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    signo = "-" if negativo else ""
    return f"{signo}$ {entero_con_puntos},{decimales}"


def _formatear_fecha(f) -> str:
    if f is None:
        return "—"
    return f.strftime("%d/%m/%Y")


def _limpiar_estado_pago() -> None:
    claves = [
        k for k in list(st.session_state.keys())
        if k.startswith("pago_") or k.startswith("_pago_")
    ]
    for k in claves:
        st.session_state.pop(k, None)


def _resetear_opcion_adelanto() -> None:
    """Cuando cambia el monto, se resetea la opción de adelanto elegida."""
    st.session_state.pop("pago_opcion_adelanto", None)


def _seleccionar_opcion(opcion: str) -> None:
    """Guarda la opción de adelanto elegida por el usuario."""
    st.session_state["pago_opcion_adelanto"] = opcion


def _guardar_callback() -> None:
    st.session_state["_confirmar_pago"] = True


# ============================================================
# Render principal
# ============================================================
def render(db: BaseDatos, prestamo_id: int) -> None:
    prestamo_repo = PrestamoRepo(db)
    servicio = ServicioPagos(db)

    prestamo = prestamo_repo.obtener(prestamo_id)
    if prestamo is None:
        componentes.render_html("<p>No se encontró el préstamo.</p>")
        return

    if st.button("← Volver al préstamo", key="volver_desde_pago"):
        _limpiar_estado_pago()
        st.session_state.pop("pago_nuevo_step", None)
        st.rerun()

    componentes.render_html("<br>")

    st.markdown(
        '<div class="detalle-titulo">Registrar pago</div>',
        unsafe_allow_html=True,
    )

    componentes.render_html(
        f'<div class="saludo">Préstamo {prestamo.numero} · '
        f'{prestamo.destino or "sin destino"}</div>'
    )

    hoy = date.today()
    deuda = servicio.calcular_deuda_proximo_pago(prestamo_id, hoy)

    if deuda is None:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">ℹ</span>'
            '<span class="nota-texto">'
            'Este préstamo no tiene cuotas pendientes.'
            '</span></div>'
        )
        return

    cuota_obj = deuda["cuota_objetivo"]
    total_a_pagar = deuda["total_a_pagar"]

    # ============================================================
    # Bloque 1: Cuota del mes
    # ============================================================
    componentes.render_html('<div class="seccion-titulo">Cuota del mes</div>')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Cuota #", cuota_obj.numero)
    with col2:
        st.metric("Vence", _formatear_fecha(cuota_obj.fecha_vencimiento))
    with col3:
        st.metric("Total del mes", _formatear_pesos(total_a_pagar))

    tiene_arrastre = (
        deuda["arrastre_capital"] > 0
        or deuda["arrastre_interes"] > 0
        or deuda["arrastre_mora"] > 0
        or deuda["interes_extra"] > 0
        or deuda["mora_nueva"] > 0
    )

    if tiene_arrastre:
        lineas = [
            ("Cuota teórica", deuda["cuota_interes"] + deuda["cuota_capital"]),
        ]
        if deuda["arrastre_capital"] > 0:
            lineas.append(("+ Arrastre de capital", deuda["arrastre_capital"]))
        if deuda["arrastre_interes"] > 0:
            lineas.append(("+ Arrastre de interés", deuda["arrastre_interes"]))
        if deuda["arrastre_mora"] > 0:
            lineas.append(("+ Arrastre de mora", deuda["arrastre_mora"]))
        if deuda["interes_extra"] > 0:
            lineas.append((
                "+ Interés extra por capital pendiente",
                deuda["interes_extra"],
            ))
        if deuda["mora_nueva"] > 0:
            lineas.append(("+ Mora nueva del mes", deuda["mora_nueva"]))

        html_lineas = "".join(
            f'<div class="linea-detalle"><span>{etq}</span>'
            f'<span>{_formatear_pesos(val)}</span></div>'
            for etq, val in lineas
        )
        html_lineas += (
            f'<div class="linea-detalle linea-total">'
            f'<span><strong>= Total del mes</strong></span>'
            f'<span><strong>{_formatear_pesos(total_a_pagar)}</strong></span>'
            f'</div>'
        )

        componentes.render_html(f"""
            <div class="tarjeta-porque tarjeta-grande">
                <div class="icono">↩</div>
                <div class="texto">
                    <div class="titulo">Este mes arrastrás un pendiente</div>
                    <div class="detalle">{html_lineas}</div>
                </div>
            </div>
        """)
    else:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">'
            'Estás al día. Esta cuota no tiene arrastre del mes anterior.'
            '</span></div>'
        )

    # ============================================================
    # Bloque 2: Monto
    # ============================================================
    componentes.render_html('<div class="seccion-titulo">Monto recibido</div>')

    default_monto = float(total_a_pagar)
    if "pago_monto" not in st.session_state:
        st.session_state["pago_monto"] = default_monto

    monto_actual = Decimal(str(st.session_state.get("pago_monto", default_monto)))

    componentes.render_html(f"""
        <div class="aporte-monto-grande">{_formatear_pesos(monto_actual)}</div>
    """)

    col1, col2 = st.columns(2)
    with col1:
        monto = st.number_input(
            "Monto (ARS)",
            min_value=0.01,
            value=default_monto,
            step=1000.0,
            format="%.2f",
            label_visibility="collapsed",
            key="pago_monto",
            on_change=_resetear_opcion_adelanto,
        )
        fecha_real = st.date_input(
            "Fecha en que se recibió",
            value=hoy,
            key="pago_fecha",
        )
    with col2:
        medio = st.selectbox(
            "Medio de pago",
            options=["Efectivo", "Transferencia", "Mercado Pago", "Otro"],
            key="pago_medio",
        )
        nota = st.text_input(
            "Nota (opcional)",
            value="",
            key="pago_nota",
            placeholder="Ej: pago parcial acordado",
        )

    monto_dec = Decimal(str(monto))

    if monto_dec <= 0:
        return

    es_adelanto = monto_dec > total_a_pagar
    opcion_adelanto = st.session_state.get("pago_opcion_adelanto")

    # ============================================================
    # Bloque 3: Preview según el monto
    # ============================================================
    if monto_dec < total_a_pagar:
        _renderizar_preview_parcial(monto_dec, deuda, total_a_pagar)
        puede_confirmar = True

    elif monto_dec == total_a_pagar:
        _renderizar_preview_cuota_completa(deuda, total_a_pagar)
        puede_confirmar = True

    else:
        excedente = monto_dec - total_a_pagar
        puede_confirmar = _renderizar_preview_adelanto(
            monto=monto_dec,
            excedente=excedente,
            deuda=deuda,
            total_a_pagar=total_a_pagar,
            prestamo_id=prestamo_id,
            servicio=servicio,
            hoy=hoy,
            opcion_actual=opcion_adelanto,
        )

    # ============================================================
    # Bloque 4: Botón confirmar
    # ============================================================
    componentes.render_html("<br>")
    _, col_confirmar, _ = st.columns([2, 2, 2])

    with col_confirmar:
        texto_boton = "Confirmar pago"
        if es_adelanto and opcion_adelanto is None:
            texto_boton = "Elegí RAI o RNI arriba"

        st.button(
            texto_boton,
            use_container_width=True,
            key="confirmar_pago",
            on_click=_guardar_callback,
            disabled=not puede_confirmar,
        )

    if puede_confirmar:
        _procesar_guardado(db, prestamo_id)


# ============================================================
# Preview: pago parcial
# ============================================================
def _renderizar_preview_parcial(
    monto: Decimal,
    deuda: dict,
    total_a_pagar: Decimal,
) -> None:
    componentes.render_html(
        '<div class="seccion-titulo">Cómo se aplica este pago</div>'
    )

    d_mora = deuda["arrastre_mora"] + deuda["mora_nueva"]
    d_interes = (
        deuda["arrastre_interes"]
        + deuda["cuota_interes"]
        + deuda["interes_extra"]
    )
    d_capital = deuda["arrastre_capital"] + deuda["cuota_capital"]

    restante = monto
    a_mora = min(restante, d_mora)
    restante -= a_mora
    a_interes = min(restante, d_interes)
    restante -= a_interes
    a_capital = min(restante, d_capital)

    falta = total_a_pagar - (a_mora + a_interes + a_capital)

    filas = []
    if d_mora > 0:
        filas.append([
            "Mora",
            _formatear_pesos(d_mora),
            _formatear_pesos(a_mora),
        ])
    filas.append([
        "Interés",
        _formatear_pesos(d_interes),
        _formatear_pesos(a_interes),
    ])
    filas.append([
        "Capital",
        _formatear_pesos(d_capital),
        _formatear_pesos(a_capital),
    ])

    componentes.tabla(
        [
            {"texto": "Concepto"},
            {"texto": "Deuda del mes", "alineacion": "der"},
            {"texto": "Se aplica", "alineacion": "der"},
        ],
        filas,
    )

    componentes.render_html("<br>")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total del mes", _formatear_pesos(total_a_pagar))
    with col2:
        st.metric("Falta cubrir", _formatear_pesos(falta))

    interes_extra_prox = (falta * Decimal("0.025")).quantize(Decimal("0.01"))
    total_prox = falta + interes_extra_prox

    componentes.render_html(
        f'<div class="nota-contextual nota-warning">'
        f'<span class="nota-icono">⚠</span>'
        f'<span class="nota-texto">'
        f'Al pagar menos del total, quedan '
        f'<strong>{_formatear_pesos(falta)}</strong> sin cubrir. '
        f'El mes que viene vas a deber ese monto más '
        f'{_formatear_pesos(interes_extra_prox)} de interés extra. '
        f'Total adicional: <strong>{_formatear_pesos(total_prox)}</strong>.'
        f'</span></div>'
    )


# ============================================================
# Preview: cuota completa
# ============================================================
def _renderizar_preview_cuota_completa(
    deuda: dict,
    total_a_pagar: Decimal,
) -> None:
    componentes.render_html(
        '<div class="seccion-titulo">Cómo se aplica este pago</div>'
    )
    componentes.render_html(f"""
        <div class="tarjeta-porque tarjeta-grande">
            <div class="icono">✓</div>
            <div class="texto">
                <div class="titulo">Cubrís el total del mes</div>
                <div class="detalle">
                    <div class="linea-detalle">
                        <span>Total a pagar</span>
                        <span>{_formatear_pesos(total_a_pagar)}</span>
                    </div>
                </div>
            </div>
        </div>
    """)
    componentes.render_html(
        '<div class="nota-contextual nota-success">'
        '<span class="nota-icono">✓</span>'
        '<span class="nota-texto">'
        'Con este pago quedás al día. No se arrastra nada al mes siguiente.'
        '</span></div>'
    )


# ============================================================
# Preview: adelanto
# ============================================================
def _renderizar_preview_adelanto(
    monto: Decimal,
    excedente: Decimal,
    deuda: dict,
    total_a_pagar: Decimal,
    prestamo_id: int,
    servicio: ServicioPagos,
    hoy: date,
    opcion_actual: str | None,
) -> bool:
    """
    Renderiza el preview del adelanto.

    Devuelve True si el usuario ya eligió una opción y se puede
    confirmar. False si todavía no eligió.
    """
    componentes.render_html(
        '<div class="seccion-titulo">Adelanto de capital</div>'
    )

    componentes.render_html(
        f'<div class="nota-contextual nota-success">'
        f'<span class="nota-icono">💰</span>'
        f'<span class="nota-texto">'
        f'Cubrís el mes y adelantás '
        f'<strong>{_formatear_pesos(excedente)}</strong> directo a capital.'
        f'</span></div>'
    )

    simulacion = servicio.simular_adelanto(prestamo_id, excedente, hoy)

    if simulacion is None:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            'No se pudo simular el adelanto. Probá con otro monto.'
            '</span></div>'
        )
        return False

    imp_rai = simulacion["rai"]["impacto"]
    imp_rni = simulacion["rni"]["impacto"]

    componentes.render_html(
        '<div class="seccion-titulo">¿Cómo querés que impacte?</div>'
    )

    seleccion_rai = opcion_actual == "RAI"
    seleccion_rni = opcion_actual == "RNI"

    col_rai, col_rni = st.columns(2)

    with col_rai:
        if imp_rai:
            clase = "opcion-card opcion-card-activa" if seleccion_rai else "opcion-card"
            componentes.render_html(f"""
                <div class="{clase}">
                    <div class="opcion-card-icono">📉</div>
                    <div class="opcion-card-titulo">Bajar las cuotas</div>
                    <div class="opcion-card-desc">
                        Las próximas cuotas bajan de monto.
                        El plazo no cambia.
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Cuota actual</span>
                        <span>{_formatear_pesos(imp_rai['cuota_promedio_antes'])}</span>
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Cuota nueva</span>
                        <span class="color-verde">
                            {_formatear_pesos(imp_rai['cuota_promedio_despues'])}
                        </span>
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Plazo</span>
                        <span>{imp_rai['meses_antes']} meses (no cambia)</span>
                    </div>
                    <div class="opcion-card-metrica opcion-card-total">
                        <span>Ahorrás</span>
                        <span class="color-verde">
                            {_formatear_pesos(imp_rai['ahorro'])}
                        </span>
                    </div>
                </div>
            """)
            if not seleccion_rai:
                st.button(
                    "Elegir esta opción",
                    use_container_width=True,
                    key="btn_elegir_rai",
                    on_click=_seleccionar_opcion,
                    args=("RAI",),
                )
            else:
                componentes.render_html(
                    '<div class="opcion-card-elegida">✓ Opción elegida</div>'
                )

    with col_rni:
        if imp_rni:
            clase = "opcion-card opcion-card-activa" if seleccion_rni else "opcion-card"
            componentes.render_html(f"""
                <div class="{clase}">
                    <div class="opcion-card-icono">⏱️</div>
                    <div class="opcion-card-titulo">Acortar el plazo</div>
                    <div class="opcion-card-desc">
                        Las cuotas se mantienen. Terminás antes de pagar.
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Cuotas antes</span>
                        <span>{imp_rni['meses_antes']}</span>
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Cuotas nuevas</span>
                        <span class="color-verde">
                            {imp_rni['meses_despues']}
                            (ahorrás {imp_rni['meses_ahorrados']})
                        </span>
                    </div>
                    <div class="opcion-card-metrica">
                        <span>Cuota</span>
                        <span>Sin cambios</span>
                    </div>
                    <div class="opcion-card-metrica opcion-card-total">
                        <span>Ahorrás</span>
                        <span class="color-verde">
                            {_formatear_pesos(imp_rni['ahorro'])}
                        </span>
                    </div>
                </div>
            """)
            if not seleccion_rni:
                st.button(
                    "Elegir esta opción",
                    use_container_width=True,
                    key="btn_elegir_rni",
                    on_click=_seleccionar_opcion,
                    args=("RNI",),
                )
            else:
                componentes.render_html(
                    '<div class="opcion-card-elegida">✓ Opción elegida</div>'
                )

    if opcion_actual is None:
        componentes.render_html(
            '<div class="nota-contextual nota-warning" '
            'style="margin-top: 1rem;">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            'Tenés que elegir una opción para poder confirmar el pago.'
            '</span></div>'
        )
        return False

    return True


# ============================================================
# Procesar guardado
# ============================================================
def _procesar_guardado(db: BaseDatos, prestamo_id: int) -> None:
    if not st.session_state.pop("_confirmar_pago", False):
        return

    monto_float = st.session_state.get("pago_monto", 0)
    fecha = st.session_state.get("pago_fecha", date.today())
    medio = st.session_state.get("pago_medio", "Efectivo")
    nota = st.session_state.get("pago_nota", "") or None
    opcion_adelanto = st.session_state.get("pago_opcion_adelanto")

    monto = Decimal(str(monto_float))
    if monto <= 0:
        componentes.disparar_nota("El monto debe ser mayor a cero.", "error")
        st.rerun()
        return

    servicio = ServicioPagos(db)

    try:
        pago_id = servicio.registrar_pago(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_real=fecha,
            usuario="admin",
            medio=medio,
            nota=nota,
            opcion_adelanto=opcion_adelanto,
        )
    except (ErrorServicio, ErrorEstadoInvalido) as e:
        componentes.disparar_nota(str(e), "error")
        st.rerun()
        return

    _limpiar_estado_pago()
    st.session_state.pop("pago_nuevo_step", None)

    componentes.disparar_nota(
        f"Pago #{pago_id} registrado correctamente.",
        "success",
    )

    st.rerun()