"""Formulario controlado para proponer correcciones auditables sin aplicar cambios."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st

from aplicacion.seguridad.identidad import IdentidadSesion
from aplicacion.servicios import ServicioCorreccionesAuditables
from dominio.excepciones import ErrorValidacion
from infraestructura.excepciones import ErrorTransaccion
from infraestructura.repositorios import PlanesReposicionRepo
from . import componentes


_TIPOS_REGISTRO = {
    "APORTE_REPOSICION": "Aporte de reposición",
    "FLUJO_INVERSION_REPOSICION": "Flujo de inversión",
    "VALUACION_INVERSION_REPOSICION": "Valuación de inversión",
}
_ESCALA_IMPORTE = Decimal("0.01")
_ESCALA_COTIZACION = Decimal("0.000001")


def _formatear_decimal(valor: object, decimales: int) -> str:
    """Presenta un decimal con separadores habituales en Argentina."""
    numero = Decimal(str(valor))
    texto = f"{numero:,.{decimales}f}"
    return texto.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def _parsear_decimal(
    texto: str,
    *,
    campo: str,
    escala: Decimal,
    permitir_cero: bool = False,
) -> Decimal:
    """Convierte entrada localizada a Decimal sin pasar por float ni redondear silenciosamente."""
    normalizado = str(texto or "").strip().replace(" ", "").replace("$", "")
    if not normalizado:
        raise ErrorValidacion(f"Completá el campo {campo}.")
    if "," in normalizado and "." in normalizado:
        # El último separador se interpreta como decimal: 1.234,56 o 1,234.56.
        if normalizado.rfind(",") > normalizado.rfind("."):
            normalizado = normalizado.replace(".", "").replace(",", ".")
        else:
            normalizado = normalizado.replace(",", "")
    elif "," in normalizado:
        normalizado = normalizado.replace(",", ".")
    try:
        valor = Decimal(normalizado)
    except (InvalidOperation, ValueError) as exc:
        raise ErrorValidacion(f"El campo {campo} no es un número válido.") from exc
    if not valor.is_finite():
        raise ErrorValidacion(f"El campo {campo} debe ser un número finito.")
    try:
        cuantizado = valor.quantize(escala)
    except InvalidOperation as exc:
        raise ErrorValidacion(f"El campo {campo} está fuera del rango permitido.") from exc
    if valor != cuantizado:
        decimales = max(0, -escala.as_tuple().exponent)
        raise ErrorValidacion(
            f"El campo {campo} admite como máximo {decimales} decimales."
        )
    if valor < 0 or (not permitir_cero and valor == 0):
        regla = "no puede ser negativo" if permitir_cero else "debe ser mayor que cero"
        raise ErrorValidacion(f"El campo {campo} {regla}.")
    return cuantizado


def _sacar_registros(repo: PlanesReposicionRepo, plan_id: int, tipo: str):
    if tipo == "APORTE_REPOSICION":
        return repo.listar_aportes(plan_id, limite=500)
    if tipo == "FLUJO_INVERSION_REPOSICION":
        return repo.listar_flujos_inversion(plan_id, limite=500)
    return repo.listar_valuaciones_inversion(plan_id, limite=500)


def _obtener_registro(repo: PlanesReposicionRepo, tipo: str, registro_id: int):
    if tipo == "APORTE_REPOSICION":
        return repo.obtener_aporte(registro_id), repo.verificar_aporte
    if tipo == "FLUJO_INVERSION_REPOSICION":
        return repo.obtener_flujo_inversion(registro_id), repo.verificar_flujo_inversion
    return repo.obtener_valoracion_inversion(registro_id), repo.verificar_valoracion_inversion


def _fecha_snapshot(snapshot: dict, campo: str) -> date:
    try:
        return date.fromisoformat(str(snapshot[campo]))
    except (KeyError, ValueError) as exc:
        raise ErrorValidacion(
            f"La fecha original '{campo}' no tiene un formato válido; no se habilitó la propuesta."
        ) from exc


def _texto_original(snapshot: dict, campo: str) -> str:
    valor = snapshot.get(campo)
    return "" if valor is None else str(valor)


def _clave_idempotencia(
    *,
    tipo: str,
    registro_id: int,
    hash_original: str,
    snapshot: dict,
    motivo: str,
    correccion_anterior_id: int | None,
) -> str:
    contenido = json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    solicitud = json.dumps(
        {
            "tipo": tipo,
            "registro_id": registro_id,
            "hash_original": hash_original,
            "snapshot": contenido,
            "motivo": motivo.strip(),
            "correccion_anterior_id": correccion_anterior_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "ui-corr-" + hashlib.sha256(solicitud.encode("utf-8")).hexdigest()


def _registrar(
    *,
    servicio: ServicioCorreccionesAuditables,
    tipo: str,
    registro_id: int,
    hash_original: str,
    original: dict,
    corregido: dict,
    motivo: str,
    correccion_anterior_id: int | None,
) -> None:
    if corregido == original:
        st.warning("No cambiaste ningún dato. Ajustá al menos un campo antes de registrar la propuesta.")
        return
    clave = _clave_idempotencia(
        tipo=tipo,
        registro_id=registro_id,
        hash_original=hash_original,
        snapshot=corregido,
        motivo=motivo,
        correccion_anterior_id=correccion_anterior_id,
    )
    propuesta = servicio.registrar_propuesta(
        entidad_tipo=tipo,
        entidad_id=registro_id,
        hash_original=hash_original,
        snapshot_corregido=corregido,
        motivo=motivo,
        clave_idempotencia=clave,
        correccion_anterior_id=correccion_anterior_id,
    )
    st.success(
        f"Propuesta #{propuesta.id} registrada. El dato financiero original no cambió y la propuesta todavía no fue aplicada."
    )


def render(db, identidad: IdentidadSesion) -> None:
    """Permite proponer una corrección con campos guiados, sin editar hechos originales."""
    componentes.render_html(
        '<div class="detalle-titulo">Proponer corrección auditable</div>'
    )
    componentes.render_html(
        '<div class="saludo">Corregí una carga sin reemplazar el dato original</div>'
    )
    st.caption(
        "La propuesta queda registrada para revisión. No cambia por sí sola el aporte, "
        "flujo o valuación efectivos ni modifica rendimientos o reportes."
    )

    try:
        servicio = ServicioCorreccionesAuditables(db, identidad=identidad)
    except (TypeError, ValueError, PermissionError) as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    try:
        repo = PlanesReposicionRepo(db)
        planes = [
            plan for plan in repo.listar_planes(limite=200, solo_activos=True)
            if plan.tipo_plan == "REPOSICION_INTERNA"
        ]
    except Exception as exc:
        componentes.nota_contextual(
            f"No se pudieron cargar los planes internos para corregir: {exc}", "error"
        )
        return

    if not planes:
        componentes.estado_vacio(
            icono="🧾",
            titulo="No hay planes internos activos",
            texto=(
                "Para proponer una corrección debe existir un plan de reposición interno "
                "activo con aportes, flujos o valuaciones registrados."
            ),
        )
        return

    plan_opciones = [None, *[plan.id for plan in planes]]
    plan_por_id = {plan.id: plan for plan in planes}
    plan_id = st.selectbox(
        "Plan de reposición",
        options=plan_opciones,
        format_func=lambda valor: (
            "Seleccioná un plan" if valor is None
            else f"{plan_por_id[valor].nombre} · plan #{valor}"
        ),
        key="proponer_corr_plan",
    )
    if plan_id is None:
        st.info("Elegí un plan para ver sus registros disponibles.")
        return

    tipo = st.selectbox(
        "Qué registro necesitás corregir",
        options=tuple(_TIPOS_REGISTRO),
        format_func=lambda valor: _TIPOS_REGISTRO[valor],
        key=f"proponer_corr_tipo_{plan_id}",
    )

    try:
        registros = _sacar_registros(repo, plan_id, tipo)
    except ErrorValidacion as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    if not registros:
        st.info(
            f"El plan seleccionado todavía no tiene registros de tipo «{_TIPOS_REGISTRO[tipo]}»."
        )
        return

    registro_por_id = {registro.id: registro for registro in registros}
    ids_registro = [None, *registro_por_id.keys()]

    def etiqueta_registro(registro_id):
        if registro_id is None:
            return "Seleccioná un registro"
        registro = registro_por_id[registro_id]
        if tipo == "APORTE_REPOSICION":
            fecha = registro.fecha_aporte.isoformat()
            detalle = f"ARS {_formatear_decimal(registro.monto_ars, 2)}"
        elif tipo == "FLUJO_INVERSION_REPOSICION":
            fecha = registro.fecha_flujo.isoformat()
            detalle = f"{registro.moneda} {_formatear_decimal(registro.monto_original, 2)} · {registro.tipo_flujo}"
        else:
            fecha = registro.fecha_valuacion.isoformat()
            detalle = f"{registro.moneda} {_formatear_decimal(registro.valor_original, 2)}"
        return f"#{registro_id} · {fecha} · {detalle}"

    registro_id = st.selectbox(
        "Registro original",
        options=ids_registro,
        format_func=etiqueta_registro,
        key=f"proponer_corr_registro_{plan_id}_{tipo}",
    )
    if registro_id is None:
        st.info("Seleccioná el registro original antes de editar una propuesta.")
        return

    registro, verificar = _obtener_registro(repo, tipo, registro_id)
    if registro is None:
        st.error("El registro seleccionado ya no existe. Volvé a elegirlo.")
        return
    if registro.plan_id != plan_id:
        st.error("El registro no pertenece al plan seleccionado. No se puede continuar.")
        return
    if registro.snapshot_json is None or not verificar(registro):
        st.error(
            "El snapshot original no supera la verificación de integridad. "
            "La propuesta quedó bloqueada para evitar una corrección sobre datos dudosos."
        )
        return
    try:
        original = json.loads(registro.snapshot_json)
        historial = servicio.listar_historial(entidad_tipo=tipo, entidad_id=registro_id)
    except (json.JSONDecodeError, ErrorValidacion, PermissionError) as exc:
        componentes.nota_contextual(
            f"No se puede abrir el registro con seguridad: {exc}", "error"
        )
        return
    if not isinstance(original, dict):
        st.error("El snapshot original no es un objeto válido. No se puede continuar.")
        return
    correccion_anterior_id = historial[-1].id if historial else None

    st.caption(f"Registro #{registro_id} · plan #{plan_id}")
    with st.expander("Datos originales verificados", expanded=False):
        st.json(original, expanded=False)
    if historial:
        st.info(
            f"Este registro ya tiene {len(historial)} propuesta(s). La nueva propuesta se encadenará con la última: #{correccion_anterior_id}."
        )

    try:
        if tipo == "APORTE_REPOSICION":
            _formulario_aporte(
                servicio, tipo, registro, original, registro_id, correccion_anterior_id
            )
        elif tipo == "FLUJO_INVERSION_REPOSICION":
            _formulario_flujo(
                servicio, tipo, registro, original, registro_id, correccion_anterior_id
            )
        else:
            _formulario_valoracion(
                servicio, tipo, registro, original, registro_id, correccion_anterior_id
            )
    except (ErrorValidacion, ErrorTransaccion, PermissionError) as exc:
        componentes.nota_contextual(
            f"No se pudo registrar la propuesta. El dato original permanece sin cambios. Detalle: {exc}",
            "error",
        )


def _formulario_aporte(
    servicio, tipo, registro, original, registro_id, correccion_anterior_id
) -> None:
    with st.form(f"form_proponer_aporte_{registro_id}"):
        fecha = st.date_input(
            "Fecha del aporte",
            value=_fecha_snapshot(original, "fecha_aporte"),
            key=f"proponer_corr_fecha_aporte_{registro_id}",
        )
        col_importe, col_cotizacion = st.columns(2)
        with col_importe:
            monto_txt = st.text_input(
                "Importe ARS",
                value=_formatear_decimal(original["monto_ars"], 2),
                help="Usá formato local, por ejemplo 1.250,50. Se admiten hasta 2 decimales.",
                key=f"proponer_corr_monto_ars_{registro_id}",
            )
        with col_cotizacion:
            cotizacion_txt = st.text_input(
                "Cotización ARS por USD",
                value=_formatear_decimal(original["cotizacion_ars_por_usd"], 6),
                help="Cotización informativa de la fecha del aporte, con hasta 6 decimales.",
                key=f"proponer_corr_cotizacion_{registro_id}",
            )
        naturaleza = st.selectbox(
            "Naturaleza de la cotización",
            options=("SUPUESTO", "OBSERVADA"),
            index=0 if original["naturaleza_cotizacion"] == "SUPUESTO" else 1,
            key=f"proponer_corr_naturaleza_{registro_id}",
        )
        fuente = st.text_input(
            "Fuente de cotización (requerida si es observada)",
            value=_texto_original(original, "fuente_cotizacion"),
            max_chars=160,
            key=f"proponer_corr_fuente_{registro_id}",
        )
        referencia = st.text_input(
            "Referencia",
            value=_texto_original(original, "referencia"),
            max_chars=240,
            key=f"proponer_corr_referencia_{registro_id}",
        )
        nota = st.text_area(
            "Nota",
            value=_texto_original(original, "nota"),
            max_chars=1000,
            key=f"proponer_corr_nota_{registro_id}",
        )
        motivo = st.text_area(
            "Motivo de la corrección (obligatorio)",
            max_chars=1000,
            key=f"proponer_corr_motivo_{registro_id}",
        )
        enviar = st.form_submit_button(
            "Registrar propuesta auditable",
            type="primary",
            use_container_width=True,
            key=f"proponer_corr_enviar_{registro_id}",
        )

    if not enviar:
        return
    monto = _parsear_decimal(
        monto_txt, campo="importe ARS", escala=_ESCALA_IMPORTE
    )
    cotizacion = _parsear_decimal(
        cotizacion_txt, campo="cotización", escala=_ESCALA_COTIZACION
    )
    equivalente = (monto / cotizacion).quantize(
        _ESCALA_IMPORTE, rounding=ROUND_HALF_UP
    )
    corregido = dict(original)
    corregido.update({
        "fecha_aporte": fecha.isoformat(),
        "monto_ars": format(monto, ".2f"),
        "cotizacion_ars_por_usd": format(cotizacion, ".6f"),
        "equivalente_usd": format(equivalente, ".2f"),
        "naturaleza_cotizacion": naturaleza,
        "fuente_cotizacion": fuente.strip(),
        "referencia": referencia.strip(),
        "nota": nota.strip(),
    })
    _registrar(
        servicio=servicio, tipo=tipo, registro_id=registro_id,
        hash_original=registro.snapshot_sha256, original=original, corregido=corregido,
        motivo=motivo, correccion_anterior_id=correccion_anterior_id,
    )


def _formulario_flujo(
    servicio, tipo, registro, original, registro_id, correccion_anterior_id
) -> None:
    moneda_actual = str(original.get("moneda", "USD"))
    moneda = st.selectbox(
        "Moneda propuesta",
        options=("ARS", "USD"),
        index=0 if moneda_actual == "ARS" else 1,
        key=f"proponer_corr_moneda_flujo_{registro_id}",
        help="Al cambiar la moneda, los campos de cotización se adaptan a la opción elegida.",
    )
    with st.form(f"form_proponer_flujo_{registro_id}"):
        fecha = st.date_input(
            "Fecha del flujo",
            value=_fecha_snapshot(original, "fecha_flujo"),
            key=f"proponer_corr_fecha_flujo_{registro_id}",
        )
        tipo_flujo = st.selectbox(
            "Tipo de movimiento",
            options=(
                "APORTE_INVERSION", "RESCATE", "DISTRIBUCION",
                "COSTO_IMPUESTO_EXTERNO",
            ),
            index=(
                "APORTE_INVERSION", "RESCATE", "DISTRIBUCION",
                "COSTO_IMPUESTO_EXTERNO",
            ).index(original["tipo_flujo"]),
            key=f"proponer_corr_tipo_flujo_{registro_id}",
        )
        monto_txt = st.text_input(
            "Importe",
            value=_formatear_decimal(original["monto_original"], 2),
            help="Usá formato local, por ejemplo 1.250,50. Se admiten hasta 2 decimales.",
            key=f"proponer_corr_monto_flujo_{registro_id}",
        )
        cotizacion_txt = ""
        naturaleza = "NO_APLICA"
        fuente = ""
        if moneda == "ARS":
            cotizacion_txt = st.text_input(
                "Cotización ARS por USD",
                value=_formatear_decimal(
                    original.get("cotizacion_ars_por_usd") or "1.000,000000", 6
                ),
                help="Obligatoria para importes en ARS.",
                key=f"proponer_corr_cotizacion_flujo_{registro_id}",
            )
            naturaleza = st.selectbox(
                "Naturaleza de la cotización",
                options=("SUPUESTO", "OBSERVADA"),
                index=0 if original.get("naturaleza_cotizacion") != "OBSERVADA" else 1,
                key=f"proponer_corr_naturaleza_flujo_{registro_id}",
            )
            fuente = st.text_input(
                "Fuente de cotización (requerida si es observada)",
                value=_texto_original(original, "fuente_cotizacion") if moneda_actual == "ARS" else "",
                max_chars=160,
                key=f"proponer_corr_fuente_flujo_{registro_id}",
            )
        referencia = st.text_input(
            "Referencia", value=_texto_original(original, "referencia"),
            max_chars=240, key=f"proponer_corr_referencia_flujo_{registro_id}",
        )
        nota = st.text_area(
            "Nota", value=_texto_original(original, "nota"),
            max_chars=1000, key=f"proponer_corr_nota_flujo_{registro_id}",
        )
        motivo = st.text_area(
            "Motivo de la corrección (obligatorio)",
            max_chars=1000, key=f"proponer_corr_motivo_{registro_id}",
        )
        enviar = st.form_submit_button(
            "Registrar propuesta auditable", type="primary", use_container_width=True,
            key=f"proponer_corr_enviar_{registro_id}",
        )

    if not enviar:
        return
    monto = _parsear_decimal(
        monto_txt, campo="importe", escala=_ESCALA_IMPORTE
    )
    corregido = dict(original)
    corregido.update({
        "fecha_flujo": fecha.isoformat(),
        "tipo_flujo": tipo_flujo,
        "moneda": moneda,
        "monto_original": format(monto, ".2f"),
        "referencia": referencia.strip(),
        "nota": nota.strip(),
    })
    if moneda == "USD":
        equivalente = monto.quantize(_ESCALA_IMPORTE, rounding=ROUND_HALF_UP)
        corregido.update({
            "cotizacion_ars_por_usd": None,
            "equivalente_usd": format(equivalente, ".2f"),
            "naturaleza_cotizacion": "NO_APLICA",
            "fuente_cotizacion": "",
        })
    else:
        cotizacion = _parsear_decimal(
            cotizacion_txt, campo="cotización", escala=_ESCALA_COTIZACION
        )
        equivalente = (monto / cotizacion).quantize(
            _ESCALA_IMPORTE, rounding=ROUND_HALF_UP
        )
        corregido.update({
            "cotizacion_ars_por_usd": format(cotizacion, ".6f"),
            "equivalente_usd": format(equivalente, ".2f"),
            "naturaleza_cotizacion": naturaleza,
            "fuente_cotizacion": fuente.strip(),
        })
    _registrar(
        servicio=servicio, tipo=tipo, registro_id=registro_id,
        hash_original=registro.snapshot_sha256, original=original, corregido=corregido,
        motivo=motivo, correccion_anterior_id=correccion_anterior_id,
    )


def _formulario_valoracion(
    servicio, tipo, registro, original, registro_id, correccion_anterior_id
) -> None:
    moneda_actual = str(original.get("moneda", "USD"))
    moneda = st.selectbox(
        "Moneda propuesta",
        options=("ARS", "USD"),
        index=0 if moneda_actual == "ARS" else 1,
        key=f"proponer_corr_moneda_valoracion_{registro_id}",
        help="Al cambiar la moneda, los campos de cotización se adaptan a la opción elegida.",
    )
    with st.form(f"form_proponer_valoracion_{registro_id}"):
        fecha = st.date_input(
            "Fecha de valuación",
            value=_fecha_snapshot(original, "fecha_valuacion"),
            key=f"proponer_corr_fecha_valoracion_{registro_id}",
        )
        valor_txt = st.text_input(
            "Valor de mercado",
            value=_formatear_decimal(original["valor_original"], 2),
            help="Usá formato local, por ejemplo 125.000,00. Se admiten hasta 2 decimales.",
            key=f"proponer_corr_valor_valoracion_{registro_id}",
        )
        cotizacion_txt = ""
        naturaleza = "NO_APLICA"
        fuente = ""
        if moneda == "ARS":
            cotizacion_txt = st.text_input(
                "Cotización ARS por USD",
                value=_formatear_decimal(
                    original.get("cotizacion_ars_por_usd") or "1.000,000000", 6
                ),
                help="Obligatoria para valuaciones expresadas en ARS.",
                key=f"proponer_corr_cotizacion_valoracion_{registro_id}",
            )
            naturaleza = st.selectbox(
                "Naturaleza de la cotización",
                options=("SUPUESTO", "OBSERVADA"),
                index=0 if original.get("naturaleza_cotizacion") != "OBSERVADA" else 1,
                key=f"proponer_corr_naturaleza_valoracion_{registro_id}",
            )
            fuente = st.text_input(
                "Fuente de cotización (requerida si es observada)",
                value=_texto_original(original, "fuente_cotizacion") if moneda_actual == "ARS" else "",
                max_chars=160,
                key=f"proponer_corr_fuente_valoracion_{registro_id}",
            )
        referencia = st.text_input(
            "Referencia", value=_texto_original(original, "referencia"),
            max_chars=240, key=f"proponer_corr_referencia_valoracion_{registro_id}",
        )
        nota = st.text_area(
            "Nota", value=_texto_original(original, "nota"),
            max_chars=1000, key=f"proponer_corr_nota_valoracion_{registro_id}",
        )
        motivo = st.text_area(
            "Motivo de la corrección (obligatorio)",
            max_chars=1000, key=f"proponer_corr_motivo_{registro_id}",
        )
        enviar = st.form_submit_button(
            "Registrar propuesta auditable", type="primary", use_container_width=True,
            key=f"proponer_corr_enviar_{registro_id}",
        )

    if not enviar:
        return
    valor = _parsear_decimal(
        valor_txt, campo="valor de mercado", escala=_ESCALA_IMPORTE,
        permitir_cero=True,
    )
    corregido = dict(original)
    corregido.update({
        "fecha_valuacion": fecha.isoformat(),
        "moneda": moneda,
        "valor_original": format(valor, ".2f"),
        "referencia": referencia.strip(),
        "nota": nota.strip(),
    })
    if moneda == "USD":
        equivalente = valor.quantize(_ESCALA_IMPORTE, rounding=ROUND_HALF_UP)
        corregido.update({
            "cotizacion_ars_por_usd": None,
            "equivalente_usd": format(equivalente, ".2f"),
            "naturaleza_cotizacion": "NO_APLICA",
            "fuente_cotizacion": "",
        })
    else:
        cotizacion = _parsear_decimal(
            cotizacion_txt, campo="cotización", escala=_ESCALA_COTIZACION
        )
        equivalente = (
            Decimal("0.00") if valor == 0
            else (valor / cotizacion).quantize(_ESCALA_IMPORTE, rounding=ROUND_HALF_UP)
        )
        corregido.update({
            "cotizacion_ars_por_usd": format(cotizacion, ".6f"),
            "equivalente_usd": format(equivalente, ".2f"),
            "naturaleza_cotizacion": naturaleza,
            "fuente_cotizacion": fuente.strip(),
        })
    _registrar(
        servicio=servicio, tipo=tipo, registro_id=registro_id,
        hash_original=registro.snapshot_sha256, original=original, corregido=corregido,
        motivo=motivo, correccion_anterior_id=correccion_anterior_id,
    )
