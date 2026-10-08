"""Historial y detalle auditable de pagos para Streamlit."""

from __future__ import annotations

from decimal import Decimal
import json

import streamlit as st

from aplicacion.consultas.historial_pagos import (
    EvidenciaPagoAuditable,
    HistorialPagosQuery,
)
from . import componentes


def _pesos(valor) -> str:
    valor = Decimal(str(valor))
    negativo = valor < 0
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _fecha(valor) -> str:
    return valor.strftime("%d/%m/%Y")


def _render_lista(db, persona_id: int) -> None:
    query = HistorialPagosQuery(db)
    limite = st.selectbox(
        "Cantidad máxima",
        options=[25, 50, 100, 250],
        index=1,
        key="historial_pagos_limite",
    )
    pagos = query.por_persona(persona_id, limite=limite)

    if not pagos:
        componentes.estado_vacio(
            icono="🧾",
            titulo="Todavía no hay pagos",
            texto="Cuando registres pagos, su evidencia aparecerá acá.",
        )
        return

    componentes.render_html(
        f'<div class="seccion-titulo">Últimos {len(pagos)} pagos visibles</div>'
    )

    for pago in pagos:
        estado = pago.estado.capitalize()
        motor = pago.motor_version or "LEGACY"
        tipo = pago.tipo_pago or "CUOTA"
        linea = (
            f"{_fecha(pago.fecha_real)} · {pago.prestamo_numero} · "
            f"{tipo} · {motor} · {estado}"
        )

        col1, col2 = st.columns([5, 1])
        with col1:
            componentes.render_html(
                f'<div class="tarjeta-prestamo">'
                f'<div class="tarjeta-prestamo-icono">🧾</div>'
                f'<div class="tarjeta-prestamo-cuerpo">'
                f'<div class="tarjeta-prestamo-titulo">Pago #{pago.id}</div>'
                f'<div class="tarjeta-prestamo-rol">{linea}</div>'
                f'<div class="tarjeta-prestamo-prox">{_pesos(pago.monto)} '
                f'{pago.moneda}</div>'
                f'</div></div>'
            )
        with col2:
            if st.button(
                "Detalle",
                key=f"detalle_pago_{pago.id}",
                use_container_width=True,
            ):
                st.session_state["pago_auditable_id"] = pago.id
                st.rerun()


def _render_metadatos(evidencia: EvidenciaPagoAuditable) -> None:
    p = evidencia.pago
    componentes.render_html('<div class="seccion-titulo">Identidad y resultado</div>')

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pago", f"#{p.id}")
    with c2:
        st.metric("Monto", _pesos(p.monto))
    with c3:
        st.metric("Tipo", p.tipo_pago)
    with c4:
        st.metric("Motor", p.motor_version)

    c1, c2, c3 = st.columns(3)
    with c1:
        componentes.render_html(
            f'<div class="detalle-item"><span>Fecha real</span>'
            f'<strong>{_fecha(p.fecha_real)}</strong></div>'
        )
    with c2:
        componentes.render_html(
            f'<div class="detalle-item"><span>Fecha valor</span>'
            f'<strong>{_fecha(p.fecha_valor)}</strong></div>'
        )
    with c3:
        componentes.render_html(
            f'<div class="detalle-item"><span>Registro</span>'
            f'<strong>{p.fecha_registro}</strong></div>'
        )

    c1, c2 = st.columns(2)
    with c1:
        componentes.render_html(
            f'<div class="detalle-item"><span>Monto a capital</span>'
            f'<strong>{_pesos(p.monto_a_capital)}</strong></div>'
            f'<div class="detalle-item"><span>Intereses ahorrados</span>'
            f'<strong>{_pesos(p.intereses_ahorrados)}</strong></div>'
            f'<div class="detalle-item"><span>Cuotas restantes</span>'
            f'<strong>{p.cuotas_restantes_antes} → {p.cuotas_restantes_despues}</strong></div>'
        )
    with c2:
        componentes.render_html(
            f'<div class="detalle-item"><span>Medio</span>'
            f'<strong>{p.medio or "—"}</strong></div>'
            f'<div class="detalle-item"><span>Referencia</span>'
            f'<strong>{p.referencia or "—"}</strong></div>'
            f'<div class="detalle-item"><span>Creado por</span>'
            f'<strong>{p.creado_por or "—"}</strong></div>'
        )

    if p.nota:
        componentes.render_html(
            f'<div class="nota-contextual nota-info">'
            f'<span class="nota-icono">ℹ</span>'
            f'<span class="nota-texto">{p.nota}</span>'
            f'</div>'
        )
    if p.motivo_anulacion:
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">Anulado: {p.motivo_anulacion}</span>'
            f'</div>'
        )


def _render_imputaciones(evidencia: EvidenciaPagoAuditable) -> None:
    componentes.render_html('<div class="seccion-titulo">Imputaciones</div>')
    if not evidencia.imputaciones:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay imputaciones persistidas.</div>'
        )
        return

    filas = [
        [
            str(x.get("id", "")),
            "—" if x.get("cuota_id") is None else str(x["cuota_id"]),
            str(x.get("concepto", "")),
            str(x.get("origen", "")),
            _pesos(x.get("monto", "0")),
        ]
        for x in evidencia.imputaciones
    ]
    componentes.tabla(
        [
            {"texto": "ID"},
            {"texto": "Cuota"},
            {"texto": "Concepto"},
            {"texto": "Origen"},
            {"texto": "Monto", "alineacion": "der"},
        ],
        filas,
    )


def _render_devengamientos(evidencia: EvidenciaPagoAuditable) -> None:
    if not evidencia.devengamientos:
        return

    componentes.render_html('<div class="seccion-titulo">Devengamientos asociados</div>')
    filas = [
        [
            str(x.get("id", "")),
            str(x.get("cuota_id") or "—"),
            str(x.get("concepto", "")),
            _pesos(x.get("monto", "0")),
            str(x.get("fecha_desde", "")),
            str(x.get("fecha_hasta", "")),
            str(x.get("origen", "")),
        ]
        for x in evidencia.devengamientos
    ]
    componentes.tabla(
        [
            {"texto": "ID"},
            {"texto": "Cuota"},
            {"texto": "Concepto"},
            {"texto": "Monto", "alineacion": "der"},
            {"texto": "Desde"},
            {"texto": "Hasta"},
            {"texto": "Origen"},
        ],
        filas,
    )


def _render_ledger(evidencia: EvidenciaPagoAuditable) -> None:
    componentes.render_html('<div class="seccion-titulo">Ledger y correlación</div>')
    correlacion = evidencia.correlacion_id or "—"
    componentes.render_html(
        f'<div class="detalle-item"><span>Correlación</span>'
        f'<strong>{correlacion}</strong></div>'
    )

    if not evidencia.ledger:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay movimientos de ledger para este pago.</div>'
        )
        return

    filas = [
        [
            str(x.get("id", "")),
            str(x.get("entidad", "")),
            str(x.get("entidad_id", "")),
            str(x.get("tipo_movimiento", "")),
            _pesos(x.get("debe", "0")),
            _pesos(x.get("haber", "0")),
        ]
        for x in evidencia.ledger
    ]
    componentes.tabla(
        [
            {"texto": "ID"},
            {"texto": "Entidad"},
            {"texto": "Entidad ID"},
            {"texto": "Movimiento"},
            {"texto": "Debe", "alineacion": "der"},
            {"texto": "Haber", "alineacion": "der"},
        ],
        filas,
    )


def _render_auditoria(evidencia: EvidenciaPagoAuditable) -> None:
    componentes.render_html('<div class="seccion-titulo">Auditoría</div>')
    if not evidencia.auditoria:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay eventos de auditoría asociados.</div>'
        )
        return

    for evento in evidencia.auditoria:
        componentes.render_html(
            f'<div class="tarjeta-porque">'
            f'<div class="icono">🔎</div>'
            f'<div class="texto">'
            f'<div class="titulo">{evento["operacion"]} · {evento["fecha"]}</div>'
            f'<div class="detalle">{evento["motivo"] or "—"} · usuario: '
            f'{evento["usuario"]}</div>'
            f'</div></div>'
        )


def _render_sombra(evidencia: EvidenciaPagoAuditable) -> None:
    componentes.render_html('<div class="seccion-titulo">SOMBRA V3</div>')
    if not evidencia.observaciones_sombra:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay observación SOMBRA vinculada a este pago.</div>'
        )
        return

    for obs in evidencia.observaciones_sombra:
        tipo = str(obs["tipo"])
        clase = "nota-success" if tipo == "SIN_DIVERGENCIA" else "nota-warning"
        componentes.render_html(
            f'<div class="nota-contextual {clase}">'
            f'<span class="nota-icono">{"✓" if tipo == "SIN_DIVERGENCIA" else "⚠"}</span>'
            f'<span class="nota-texto"><strong>{tipo}</strong> · '
            f'{obs["resumen"]}</span>'
            f'</div>'
        )


def _render_plan(evidencia: EvidenciaPagoAuditable) -> None:
    if not evidencia.plan:
        return

    componentes.render_html('<div class="seccion-titulo">Plan V3 persistido</div>')
    plan = evidencia.plan

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Recibido", _pesos(plan.get("monto_pago_recibido", "0")))
    with c2:
        st.metric("Aplicado", _pesos(
            sum(
                (Decimal(str(x.get("monto", "0"))) for x in plan.get("aplicaciones", [])),
                Decimal("0"),
            )
        ))
    with c3:
        st.metric("Tipo", str(plan.get("tipo", "—")))

    with st.expander("Ver JSON persistido del plan"):
        st.code(
            json.dumps(plan, ensure_ascii=False, indent=2),
            language="json",
        )


def _render_detalle(db, pago_id: int) -> None:
    evidencia = HistorialPagosQuery(db).detalle(pago_id)
    if evidencia is None:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">No se encontró el pago seleccionado.</span>'
            '</div>'
        )
        return

    if st.button("← Volver al historial", key="volver_historial_pagos"):
        st.session_state.pop("pago_auditable_id", None)
        st.rerun()

    componentes.render_html(
        f'<div class="detalle-titulo">Pago #{evidencia.pago.id}</div>'
        f'<div class="saludo">{evidencia.pago.prestamo_numero}</div>'
    )

    _render_metadatos(evidencia)
    _render_imputaciones(evidencia)
    _render_devengamientos(evidencia)
    _render_plan(evidencia)
    _render_ledger(evidencia)
    _render_auditoria(evidencia)
    _render_sombra(evidencia)


def render(db, persona_id: int, prestamo_id: int | None = None) -> None:
    componentes.render_html('<div class="detalle-titulo">Historial de pagos</div>')
    componentes.render_html(
        '<div class="saludo">Pagos, evidencia, trazabilidad y SOMBRA</div>'
    )

    pago_id = st.session_state.get("pago_auditable_id")
    if pago_id:
        _render_detalle(db, int(pago_id))
        return

    if prestamo_id is not None:
        pagos = HistorialPagosQuery(db).por_prestamo(prestamo_id)
        if pagos:
            componentes.render_html(
                f'<div class="nota-contextual nota-info"><span class="nota-icono">ℹ</span>'
                f'<span class="nota-texto">Mostrando pagos del préstamo seleccionado.</span></div>'
            )
            _render_lista(db, persona_id)
        else:
            _render_lista(db, persona_id)
    else:
        _render_lista(db, persona_id)
