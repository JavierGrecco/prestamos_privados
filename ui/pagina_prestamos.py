"""
Página de préstamos.
"""
from datetime import date
from decimal import Decimal

import streamlit as st

from infraestructura.db import BaseDatos
from infraestructura.repositorios import (
    PrestamoRepo,
    ParticipacionRepo,
    PagoRepo,
)
from aplicacion.servicios import ServicioPagos
from . import componentes
from . import pagina_alta_prestamo
from . import pagina_registrar_pago


def _formatear_pesos(valor: Decimal) -> str:
    negativo = valor < 0
    valor_abs = abs(valor)
    entero, decimales = f"{valor_abs:.2f}".split(".")
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    signo = "-" if negativo else ""
    return f"{signo}$ {entero_con_puntos},{decimales}"


def _formatear_fecha(fecha) -> str:
    if fecha is None:
        return "—"
    return fecha.strftime("%d/%m/%Y")


def _icono_destino(destino: str) -> str:
    if not destino:
        return "📋"
    d = destino.lower()
    if "auto" in d or "vehiculo" in d or "vehículo" in d:
        return "🚗"
    if "viaje" in d or "vacacion" in d:
        return "✈️"
    if "casa" in d or "hogar" in d or "reforma" in d:
        return "🏠"
    if "inversion" in d or "inversión" in d:
        return "📈"
    if "estudio" in d or "curso" in d:
        return "🎓"
    return "📋"


def _badge_tipo_pago(tipo: str) -> str:
    if tipo == "PARCIAL":
        return '<span class="badge estado-parcial">↩ parcial</span>'
    if tipo == "COMPLEMENTO":
        return '<span class="badge estado-complemento">✓ completó</span>'
    if tipo == "ADELANTO_RAI":
        return '<span class="badge estado-adelanto">💰 adelanto RAI</span>'
    if tipo == "ADELANTO_RNI":
        return '<span class="badge estado-adelanto">💰 adelanto RNI</span>'
    return '<span class="badge estado-pendiente">✓ cuota</span>'


def _celda_estado_cuota(cuota: dict) -> str:
    """
    HTML de la celda Estado de una cuota.

    Muestra el badge del estado actual + notas inline que
    indican si la cuota tuvo pago parcial o fue recalculada.
    """
    estado_lower = cuota["estado"].lower()

    if estado_lower == "pagada":
        badge = '<span class="badge estado-pagada">✓ pagada</span>'
    elif estado_lower == "parcial":
        badge = '<span class="badge estado-parcial">◐ parcial</span>'
    elif estado_lower == "vencida":
        badge = '<span class="badge estado-vencida">⚠ vencida</span>'
    else:
        badge = '<span class="badge estado-pendiente">○ pendiente</span>'

    notas = []
    if cuota.get("fue_recalculada"):
        notas.append('<span class="nota-cuota">💰 recalculada</span>')
    if cuota.get("tuvo_pago_parcial"):
        notas.append('<span class="nota-cuota">↩ pagada en partes</span>')

    if notas:
        return badge + " " + " ".join(notas)
    return badge


def _prestamos_de_persona(db: BaseDatos, persona_id: int) -> list[dict]:
    prestamo_repo = PrestamoRepo(db)
    participacion_repo = ParticipacionRepo(db)

    resultados = []
    vistos = set()

    for prestamo in prestamo_repo.listar(deudor_id=persona_id):
        if prestamo.estado not in ("ACTIVO", "EN_MORA"):
            continue
        vistos.add(prestamo.id)
        proxima = _proxima_cuota(prestamo_repo, prestamo.id)
        resultados.append({
            "prestamo": prestamo,
            "rol": "deudor",
            "monto": prestamo.capital_original,
            "proxima_cuota": proxima,
        })

    for participacion in participacion_repo.por_inversor(persona_id):
        if participacion.estado != "ACTIVA":
            continue
        if participacion.prestamo_id in vistos:
            continue
        prestamo = prestamo_repo.obtener(participacion.prestamo_id)
        if prestamo is None or prestamo.estado not in ("ACTIVO", "EN_MORA"):
            continue
        vistos.add(prestamo.id)
        proxima = _proxima_cuota(prestamo_repo, prestamo.id)
        resultados.append({
            "prestamo": prestamo,
            "rol": "inversor",
            "monto": participacion.capital_aportado,
            "proxima_cuota": proxima,
        })

    return resultados


def _proxima_cuota(prestamo_repo: PrestamoRepo, prestamo_id: int):
    version_id = prestamo_repo.version_activa(prestamo_id)
    if version_id is None:
        return None
    for cuota in prestamo_repo.cuotas(version_id):
        if cuota.estado == "PENDIENTE":
            return cuota
    return None


def _renderizar_lista(db: BaseDatos, persona_id: int) -> None:
    componentes.renderizar_nota_pendiente()

    _, col_nuevo = st.columns([3, 1])
    with col_nuevo:
        if st.button("+ Nuevo préstamo", use_container_width=True, key="nuevo_prestamo"):
            st.session_state["prestamo_nuevo_step"] = "form"
            st.rerun()

    prestamos = _prestamos_de_persona(db, persona_id)

    if not prestamos:
        componentes.estado_vacio(
            icono="📋",
            titulo="No tenés préstamos activos",
            texto=(
                "Cuando participes en un préstamo como deudor o "
                "inversor, va a aparecer acá."
            ),
        )
        return

    plural = "s" if len(prestamos) != 1 else ""
    componentes.render_html(
        f'<div class="seccion-titulo">Tenés {len(prestamos)} préstamo{plural} activo{plural}</div>'
    )

    for item in prestamos:
        prestamo = item["prestamo"]
        rol = item["rol"]
        monto = item["monto"]
        proxima = item["proxima_cuota"]

        icono = _icono_destino(prestamo.destino)
        titulo = prestamo.destino or f"Préstamo {prestamo.numero}"

        if rol == "deudor":
            linea_rol = f"Debés {_formatear_pesos(monto)}"
        else:
            linea_rol = f"Prestaste {_formatear_pesos(monto)}"

        if proxima:
            linea_prox = f"Próximo vencimiento: {_formatear_fecha(proxima.fecha_vencimiento)}"
        else:
            linea_prox = "Sin cuotas pendientes"

        componentes.render_html(f"""
            <div class="tarjeta-prestamo">
                <div class="tarjeta-prestamo-icono">{icono}</div>
                <div class="tarjeta-prestamo-cuerpo">
                    <div class="tarjeta-prestamo-titulo">{titulo}</div>
                    <div class="tarjeta-prestamo-rol">{linea_rol}</div>
                    <div class="tarjeta-prestamo-prox">{linea_prox}</div>
                </div>
                <div class="tarjeta-prestamo-accion">{prestamo.numero}</div>
            </div>
        """)

        _, col_btn = st.columns([4, 1])
        with col_btn:
            if st.button(
                "Ver detalle",
                key=f"ver_prestamo_{prestamo.id}",
                use_container_width=True,
            ):
                st.session_state["prestamo_seleccionado"] = prestamo.id
                st.rerun()

        componentes.render_html("<div style='margin-bottom: 0.75rem;'></div>")


# ============================================================
# Balance
# ============================================================
def _renderizar_balance(impacto: dict) -> None:
    if not impacto["hubo_decisiones"]:
        return

    componentes.render_html(
        '<div class="seccion-titulo">Balance de decisiones del deudor</div>'
    )

    balance = impacto["sobrecosto_total"]

    if balance > 0:
        color = "color-rojo"
        emoji = "🔴"
        veredicto = "Este préstamo te costó más por las decisiones tomadas"
        monto_str = f"+ {_formatear_pesos(balance)}"
    elif balance < 0:
        color = "color-verde"
        emoji = "🟢"
        veredicto = "Este préstamo te costó menos gracias a los adelantos"
        monto_str = f"- {_formatear_pesos(abs(balance))}"
    else:
        color = "color-neutro"
        emoji = "⚪"
        veredicto = "Las decisiones no cambiaron el costo del préstamo"
        monto_str = _formatear_pesos(abs(balance))

    componentes.render_html(f"""
        <div class="bloque-impacto">
            <div class="bloque-impacto-icono">{emoji}</div>
            <div class="bloque-impacto-cuerpo">
                <div class="bloque-impacto-veredicto {color}">
                    {veredicto}
                </div>
                <div class="bloque-impacto-monto {color}">
                    {monto_str}
                </div>
            </div>
        </div>
    """)

    col1, col2 = st.columns(2)

    with col1:
        componentes.render_html('<div class="etiqueta-control">SUMÓ COSTOS</div>')
        componentes.render_html(f"""
            <div class="detalle-item">
                <span>Interés extra por pagos parciales</span>
                <strong class="color-rojo">
                    {_formatear_pesos(impacto['interes_extra_acumulado'])}
                </strong>
            </div>
            <div class="detalle-item">
                <span>Mora acumulada</span>
                <strong class="color-rojo">
                    {_formatear_pesos(impacto['mora_pendiente'])}
                </strong>
            </div>
            <div class="detalle-item">
                <span>Cuotas con atraso</span>
                <strong>{impacto['cuotas_con_atraso']} de {impacto['cuotas_totales']}</strong>
            </div>
        """)
        if impacto["numeros_con_atraso"]:
            numeros = ", ".join(f"#{n}" for n in impacto["numeros_con_atraso"])
            componentes.render_html(
                f'<div class="detalle-item-sub">Cuotas afectadas: {numeros}</div>'
            )

    with col2:
        componentes.render_html('<div class="etiqueta-control">AHORRÓ COSTOS</div>')
        componentes.render_html(f"""
            <div class="detalle-item">
                <span>Capital adelantado</span>
                <strong class="color-verde">
                    {_formatear_pesos(impacto['capital_adelantado'])}
                </strong>
            </div>
            <div class="detalle-item">
                <span>Intereses ahorrados</span>
                <strong class="color-verde">
                    {_formatear_pesos(impacto['intereses_ahorrados'])}
                </strong>
            </div>
        """)


# ============================================================
# Historial
# ============================================================
def _renderizar_historial(historial: list[dict]) -> None:
    if not historial:
        return

    componentes.render_html(
        '<div class="seccion-titulo">Historial de decisiones</div>'
    )

    for evento in historial:
        color = "color-rojo" if evento["monto_impacto"] > 0 else "color-verde"
        signo = "+" if evento["monto_impacto"] > 0 else "-"
        monto_fmt = _formatear_pesos(abs(evento["monto_impacto"]))

        componentes.render_html(f"""
            <div class="tarjeta-porque">
                <div class="icono">{evento['icono']}</div>
                <div class="texto">
                    <div class="titulo">
                        {_formatear_fecha(evento['fecha'])} · {evento['titulo']}
                    </div>
                    <div class="detalle">
                        {evento['descripcion']}
                        <br>
                        <span class="{color}">{evento['impacto']}</span>
                    </div>
                </div>
                <div class="{color} tarjeta-impacto-monto">
                    {signo} {monto_fmt}
                </div>
            </div>
        """)


# ============================================================
# Detalle
# ============================================================
def _renderizar_detalle(db: BaseDatos, prestamo_id: int) -> None:
    prestamo_repo = PrestamoRepo(db)
    pago_repo = PagoRepo(db)
    servicio_pagos = ServicioPagos(db)

    prestamo = prestamo_repo.obtener(prestamo_id)
    if prestamo is None:
        componentes.render_html("<p>No se encontró el préstamo.</p>")
        return

    componentes.renderizar_nota_pendiente()

    col_volver, col_pago = st.columns([3, 2])

    with col_volver:
        if st.button("← Volver a la lista", key="volver_lista"):
            st.session_state.pop("prestamo_seleccionado", None)
            st.rerun()

    with col_pago:
        if st.button("Registrar pago", use_container_width=True, key="ir_registrar_pago"):
            st.session_state["pago_nuevo_step"] = "form"
            st.rerun()

    componentes.render_html("<br>")

    icono = _icono_destino(prestamo.destino)
    titulo = prestamo.destino or f"Préstamo {prestamo.numero}"

    componentes.render_html(f"""
        <div class="detalle-cabecera">
            <div class="detalle-icono">{icono}</div>
            <div class="detalle-titulo-grupo">
                <div class="detalle-titulo">{titulo}</div>
                <div class="detalle-numero">{prestamo.numero}</div>
            </div>
        </div>
    """)

    componentes.render_html('<div class="seccion-titulo">Datos del préstamo</div>')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Capital", _formatear_pesos(prestamo.capital_original))
    with col2:
        st.metric("Plazo", f"{prestamo.plazo_meses} meses")
    with col3:
        st.metric("Sistema", prestamo.sistema.capitalize())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Inicio", _formatear_fecha(prestamo.fecha_inicio))
    with col2:
        st.metric("Estado", prestamo.estado.replace("_", " ").capitalize())
    with col3:
        version_id = prestamo_repo.version_activa(prestamo.id)
        if version_id:
            fila = db.consultar_uno(
                "SELECT tasa_anual, modalidad_tasa FROM versiones_tasa WHERE id = ?",
                (version_id,),
            )
            if fila:
                tasa = Decimal(fila["tasa_anual"])
                st.metric(
                    "Tasa",
                    f"{float(tasa)*100:.2f}% {fila['modalidad_tasa']}",
                )

    impacto = servicio_pagos.resumen_impacto_financiero(prestamo_id)
    _renderizar_balance(impacto)

    historial = servicio_pagos.historial_decisiones(prestamo_id)
    _renderizar_historial(historial)

    hoy = date.today()
    estado_cuotas = servicio_pagos.estado_cuotas_con_arrastre(prestamo_id, hoy)

    if estado_cuotas:
        proxima = next((c for c in estado_cuotas if c["es_proxima"]), None)
        if proxima and proxima["desglose"]:
            d = proxima["desglose"]
            componentes.render_html(
                '<div class="seccion-titulo">Estado de la próxima cuota</div>'
            )
            componentes.render_html(f"""
                <div class="tarjeta-porque tarjeta-grande">
                    <div class="icono">⭐</div>
                    <div class="texto">
                        <div class="titulo">Cuota #{proxima['numero']} ·
                            vence {_formatear_fecha(proxima['vencimiento'])}</div>
                        <div class="detalle">
                            <div class="linea-detalle">
                                <span>Cuota teórica:</span>
                                <span>{_formatear_pesos(d['cuota_teorica'])}</span>
                            </div>
                            <div class="linea-detalle">
                                <span>+ Arrastre de capital:</span>
                                <span>{_formatear_pesos(d['arrastre_capital'])}</span>
                            </div>
                            <div class="linea-detalle">
                                <span>+ Arrastre de interés:</span>
                                <span>{_formatear_pesos(d['arrastre_interes'])}</span>
                            </div>
                            <div class="linea-detalle">
                                <span>+ Arrastre de mora:</span>
                                <span>{_formatear_pesos(d['arrastre_mora'])}</span>
                            </div>
                            <div class="linea-detalle">
                                <span>+ Interés extra por capital pendiente:</span>
                                <span>{_formatear_pesos(d['interes_extra'])}</span>
                            </div>
                            <div class="linea-detalle">
                                <span>+ Mora nueva del mes:</span>
                                <span>{_formatear_pesos(d['mora_nueva'])}</span>
                            </div>
                            <div class="linea-detalle linea-total">
                                <span><strong>= Monto actual</strong></span>
                                <span><strong>{_formatear_pesos(proxima['monto_real'])}</strong></span>
                            </div>
                        </div>
                    </div>
                </div>
            """)

    componentes.render_html('<div class="seccion-titulo">Cuotas</div>')

    if estado_cuotas:
        headers = [
            {"texto": "#"},
            {"texto": "Vencimiento"},
            {"texto": "Cuota teórica", "alineacion": "der"},
            {"texto": "Monto actual", "alineacion": "der"},
            {"texto": "Interés", "alineacion": "der"},
            {"texto": "Capital", "alineacion": "der"},
            {"texto": "Saldo", "alineacion": "der"},
            {"texto": "Estado"},
        ]

        filas = []
        for c in estado_cuotas:
            monto_actual_str = _formatear_pesos(c["monto_real"])
            if c["es_proxima"] and c["desglose"]:
                monto_actual_str = f"★ {monto_actual_str}"

            filas.append([
                str(c["numero"]),
                _formatear_fecha(c["vencimiento"]),
                _formatear_pesos(c["cuota_teorica"]),
                monto_actual_str,
                _formatear_pesos(c["interes_teorico"]),
                _formatear_pesos(c["capital_teorico"]),
                _formatear_pesos(c["saldo_teorico"]),
                _celda_estado_cuota(c),
            ])

        componentes.tabla(headers, filas)

    componentes.render_html('<div class="seccion-titulo">Pagos registrados</div>')

    pagos = pago_repo.por_prestamo(prestamo.id)
    pagos_validos = [p for p in pagos if p.estado == "VALIDA"]

    if not pagos_validos:
        componentes.render_html("""
            <div class="estado-vacio-chico">
                Todavía no hay pagos registrados.
            </div>
        """)
    else:
        headers = [
            {"texto": "Fecha"},
            {"texto": "Monto", "alineacion": "der"},
            {"texto": "Tipo"},
            {"texto": "Medio"},
            {"texto": "Nota"},
        ]

        filas = []
        for pago in pagos_validos:
            tipo = getattr(pago, "tipo_pago", "CUOTA") or "CUOTA"
            filas.append([
                _formatear_fecha(pago.fecha_real),
                _formatear_pesos(pago.monto_moneda_pago),
                _badge_tipo_pago(tipo),
                pago.medio or "—",
                pago.nota or "—",
            ])

        componentes.tabla(headers, filas)


def render(db: BaseDatos, persona_id: int) -> None:
    if st.session_state.get("prestamo_nuevo_step"):
        pagina_alta_prestamo.render(db)
        return

    if st.session_state.get("pago_nuevo_step"):
        prestamo_id = st.session_state.get("prestamo_seleccionado")
        if prestamo_id:
            pagina_registrar_pago.render(db, prestamo_id)
            return

    prestamo_id = st.session_state.get("prestamo_seleccionado")
    if prestamo_id:
        _renderizar_detalle(db, prestamo_id)
        return

    _renderizar_lista(db, persona_id)