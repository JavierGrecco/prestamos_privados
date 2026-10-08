"""Consola operativa segura para Streamlit."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from aplicacion.servicios.operacion_ui import (
    ServicioOperacionUI,
)
from infraestructura.excepciones import ErrorBaseDatos
from . import componentes


def _render_integridad(servicio: ServicioOperacionUI) -> None:
    componentes.render_html('<div class="seccion-titulo">Salud de la base</div>')
    try:
        resultado = servicio.verificar_integridad()
    except ErrorBaseDatos as exc:
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">No se pudo verificar la base: {componentes.escapar_texto_html(exc)}</span>'
            f'</div>'
        )
        return

    componentes.render_html(
        '<div class="nota-contextual nota-success">'
        '<span class="nota-icono">✓</span>'
        '<span class="nota-texto">La base activa supera quick_check, '
        'integrity_check y foreign_key_check.</span>'
        '</div>'
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("quick_check", "OK")
    with c2:
        st.metric("integrity_check", "OK")
    with c3:
        st.metric("foreign_key_check", str(len(resultado.foreign_key_errores)))


def _render_backups(servicio: ServicioOperacionUI) -> None:
    componentes.render_html('<div class="seccion-titulo">Backups</div>')

    backups = servicio.listar_backups()
    if not backups:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">Todavía no hay backups locales verificados.</span>'
            '</div>'
        )
    else:
        filas = []
        for path in backups:
            try:
                evidencia = servicio.verificar_backup(path)
                estado = "✓ Verificado"
                detalle = evidencia.sha256[:16] + "…"
            except (ErrorBaseDatos, OSError, ValueError) as exc:
                estado = "✗ Inválido"
                detalle = str(exc)
            filas.append([
                path.name,
                estado,
                detalle,
            ])
        componentes.tabla(
            [
                {"texto": "Archivo"},
                {"texto": "Estado"},
                {"texto": "Evidencia"},
            ],
            filas,
        )

    confirmar = st.checkbox(
        "Confirmo que quiero crear un nuevo backup local sin sobrescribir otro",
        key="operacion_confirmar_backup",
    )
    if st.button(
        "Crear backup verificable",
        use_container_width=True,
        key="operacion_crear_backup",
        disabled=not confirmar,
    ):
        try:
            resultado = servicio.crear_backup(confirmar=True)
            componentes.disparar_nota(
                f"Backup creado y verificado: {resultado.ruta_backup.name}",
                "success",
            )
        except (ErrorBaseDatos, OSError, ValueError) as exc:
            componentes.disparar_nota(
                f"No se pudo crear el backup: {exc}",
                "error",
            )
        st.rerun()

    backups = servicio.listar_backups()
    if not backups:
        return

    opciones = {str(path): path for path in backups}
    seleccionado = st.selectbox(
        "Backup a verificar / probar restore",
        options=list(opciones),
        format_func=lambda x: Path(x).name,
        key="operacion_backup_seleccionado",
    )
    path = opciones[seleccionado]

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "Verificar backup",
            use_container_width=True,
            key="operacion_verificar_backup",
        ):
            try:
                resultado = servicio.verificar_backup(path)
                componentes.disparar_nota(
                    (
                        f"Backup válido · {resultado.bytes} bytes · "
                        f"SHA-256 {resultado.sha256}"
                    ),
                    "success",
                )
            except (ErrorBaseDatos, OSError, ValueError) as exc:
                componentes.disparar_nota(
                    f"Backup inválido: {exc}",
                    "error",
                )
    with c2:
        if st.button(
            "Ejecutar restore drill seguro",
            use_container_width=True,
            key="operacion_restore_drill",
        ):
            try:
                resultado = servicio.ejecutar_restore_drill(path)
                componentes.disparar_nota(
                    (
                        f"Restore drill OK · {resultado.bytes} bytes · "
                        f"SHA-256 {resultado.sha256}. "
                        "La restauración temporal fue eliminada al finalizar."
                    ),
                    "success",
                )
            except (ErrorBaseDatos, OSError, ValueError) as exc:
                componentes.disparar_nota(
                    f"Restore drill falló: {exc}",
                    "error",
                )


def _render_preflight(servicio: ServicioOperacionUI) -> None:
    estado = servicio.estado()
    preflight = estado.preflight
    metricas = estado.metricas_sombra

    componentes.render_html('<div class="seccion-titulo">Preparación de V3</div>')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("SOMBRA", str(metricas.ejecuciones_sombra))
    with c2:
        valor = metricas.tasa_coincidencia
        st.metric(
            "Coincidencia",
            "—" if valor is None else f"{valor * 100:.2f}%",
        )
    with c3:
        st.metric("Divergencias", str(metricas.ejecuciones_con_divergencia))
    with c4:
        st.metric("Errores", str(metricas.ejecuciones_con_error))

    if preflight.apto:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">Preflight V3 aprobado.</span>'
            '</div>'
        )
    else:
        motivos = " · ".join(preflight.motivos_rechazo[:3]) or "Sin ejecución suficiente"
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">V3 sigue bloqueado. {componentes.escapar_texto_html(motivos)}</span>'
            f'</div>'
        )


def render(db) -> None:
    componentes.render_html('<div class="detalle-titulo">Operación</div>')
    componentes.render_html(
        '<div class="saludo">Integridad, backups, restore y preparación de V3</div>'
    )

    servicio = ServicioOperacionUI(db)
    _render_integridad(servicio)
    _render_backups(servicio)
    _render_preflight(servicio)
