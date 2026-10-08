"""
Página de alta de préstamo.

Flujo en dos fases:
  1. Formulario: el usuario carga los datos y puede simular.
  2. Confirmación: se muestra la tabla y se guarda.

Sobre simular vs guardar:
  - SIMULAR: solo necesita capital, plazo y tasa.
  - GUARDAR: requiere al menos un inversor asignado.

Después de guardar:
  - Se limpia el estado del alta.
  - Se hace rerun.
  - La página actual (Préstamos) se re-renderiza mostrando la
    lista con la nota de éxito.

NOTA IMPORTANTE:
No se modifica `st.session_state["pagina"]` después de que el
widget de navegación fue instanciado. Streamlit no lo permite.
Como `_procesar_guardado` corre dentro de la página Préstamos,
basta con limpiar el estado y hacer rerun: la página sigue
siendo Préstamos, ahora sin el formulario de alta.
"""
from datetime import date
from decimal import Decimal

import streamlit as st

from dominio import (
    SistemaAmortizacion,
    ModalidadTasa,
    ConvencionDias,
)
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo
from aplicacion.servicios import ServicioPrestamos, ErrorServicio
from aplicacion.servicios.simulacion_prestamo import ServicioSimulacionPrestamo

from . import componentes


# ============================================================
# Helpers de formato
# ============================================================
def _formatear_pesos(valor: Decimal) -> str:
    entero, decimales = f"{valor:.2f}".split(".")
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    return f"$ {entero_con_puntos},{decimales}"


def _formatear_fecha(f) -> str:
    if f is None:
        return "—"
    return f.strftime("%d/%m/%Y")


def _calcular_cuota_segura(
    simulador: ServicioSimulacionPrestamo,
    capital: Decimal,
    plazo: int,
    tasa_pct: float,
    modalidad: str,
    sistema: str = "FRANCES",
    fecha_inicio: date | None = None,
) -> Decimal | None:
    try:
        return simulador.cuota_inicial(
            capital=capital,
            tasa_anual=Decimal(str(tasa_pct)) / Decimal("100"),
            plazo_meses=int(plazo),
            modalidad_tasa=ModalidadTasa(modalidad),
            sistema=SistemaAmortizacion(sistema.lower()),
            fecha_inicio=fecha_inicio or date.today(),
        )
    except Exception:
        return None


def _interes_primer_mes_por_convencion(
    simulador: ServicioSimulacionPrestamo,
    capital: Decimal,
    tasa_pct: float,
    modalidad: str,
    fecha_inicio: date,
) -> dict[str, Decimal]:
    resultado = simulador.comparar_convenciones_primer_periodo(
        capital=capital,
        tasa_anual=Decimal(str(tasa_pct)) / Decimal("100"),
        modalidad_tasa=ModalidadTasa(modalidad),
        fecha_inicio=fecha_inicio,
    )
    return {
        "Mensual": resultado[ConvencionDias.MENSUAL],
        "Actual/365": resultado[ConvencionDias.ACTUAL_365],
        "Actual/360": resultado[ConvencionDias.ACTUAL_360],
        "30/360": resultado[ConvencionDias.TREINTA_360],
    }


# ============================================================
# Modal de ayuda
# ============================================================
@st.dialog("Ayuda", width="large")
def _dialog_ayuda(titulo: str, cuerpo_md: str) -> None:
    st.markdown(f"### {titulo}")
    st.markdown(cuerpo_md)
    st.markdown("")
    if st.button("Entendido", use_container_width=True, key="cerrar_dialog_ayuda"):
        st.rerun()


# ============================================================
# Estado de aportes
# ============================================================
def _clave_estado(capital: Decimal, ids: list[int]) -> str:
    ids_str = "-".join(str(i) for i in sorted(ids))
    return f"aportes_{int(capital)}_{ids_str}"


def _clave_fijos(capital: Decimal, ids: list[int]) -> str:
    return f"fijos_{_clave_estado(capital, ids)}"


def _repartir_iguales(capital: Decimal, ids: list[int]) -> dict[int, Decimal]:
    if not ids:
        return {}
    parte = (capital / Decimal(len(ids))).quantize(Decimal("0.01"))
    montos = {pid: parte for pid in ids}
    dif = capital - sum(montos.values())
    if dif != 0:
        montos[ids[-1]] += dif
    return montos


def _redistribuir(
    montos: dict[int, Decimal],
    pid_movido: int,
    capital: Decimal,
    fijos: set[int],
) -> dict[int, Decimal]:
    fijos_actuales = set(fijos)
    fijos_actuales.add(pid_movido)

    ajustables = [pid for pid in montos if pid not in fijos_actuales]
    suma_fijos = sum(montos[pid] for pid in fijos_actuales if pid in montos)
    restante = capital - suma_fijos

    if not ajustables:
        return montos

    if restante < 0:
        exceso = -restante
        montos[pid_movido] -= exceso
        if montos[pid_movido] < 0:
            montos[pid_movido] = Decimal("0.00")
        return _redistribuir(
            montos, pid_movido, capital, fijos_actuales - {pid_movido}
        )

    suma_ajustables = sum(montos[pid] for pid in ajustables)

    if suma_ajustables == 0:
        parte = (restante / Decimal(len(ajustables))).quantize(Decimal("0.01"))
        for pid in ajustables:
            montos[pid] = parte
    else:
        for pid in ajustables:
            proporcion = montos[pid] / suma_ajustables
            montos[pid] = (restante * proporcion).quantize(Decimal("0.01"))

    dif = capital - sum(montos.values())
    if dif != 0 and ajustables:
        montos[ajustables[-1]] += dif

    return montos


# ============================================================
# Callbacks
# ============================================================
def _cancelar() -> None:
    st.session_state.pop("prestamo_nuevo_datos", None)
    st.session_state.pop("prestamo_nuevo_step", None)


def _repartir_iguales_callback() -> None:
    ctx = st.session_state.get("_aportes_ctx")
    if not ctx:
        return
    st.session_state[ctx["clave"]] = _repartir_iguales(ctx["capital"], ctx["ids"])
    st.session_state[ctx["fijos_clave"]] = set()


def _on_cambio_aporte(pid: int, clave: str, fijos_clave: str,
                      capital: Decimal) -> None:
    input_key = f"aporte_input_{pid}_{clave}"
    try:
        valor = Decimal(str(st.session_state.get(input_key, 0)))
    except Exception:
        return

    montos = st.session_state.get(clave, {})
    if pid not in montos:
        return

    montos[pid] = valor
    fijos = st.session_state.get(fijos_clave, set())
    fijos.add(pid)
    st.session_state[fijos_clave] = fijos

    montos = _redistribuir(montos, pid, capital, fijos)
    st.session_state[clave] = montos


def _boton_ayuda(key: str, titulo: str, cuerpo_md: str) -> None:
    if st.button("Ver explicación", key=key):
        _dialog_ayuda(titulo, cuerpo_md)


def _guardar_callback() -> None:
    st.session_state["_confirmar_guardado"] = True


# ============================================================
# Fase 1: Formulario
# ============================================================
def _renderizar_formulario(
    db: BaseDatos, simulador: ServicioSimulacionPrestamo
) -> None:
    st.markdown(
        '<div class="detalle-titulo">Nuevo préstamo</div>',
        unsafe_allow_html=True,
    )

    _, col_cancelar = st.columns([4, 1])
    with col_cancelar:
        if st.button("Cancelar", use_container_width=True, key="cancelar_alta"):
            _cancelar()
            st.rerun()

    componentes.render_html("<br>")

    personas_repo = PersonaRepo(db)
    personas = personas_repo.listar()

    # ---- Deudor ----
    componentes.render_html('<div class="seccion-titulo">Deudor</div>')

    opciones_deudores = {p.id: f"{p.nombre} {p.apellido}".strip() for p in personas}
    deudor_id = st.selectbox(
        "Deudor",
        options=list(opciones_deudores.keys()),
        format_func=lambda x: opciones_deudores[x],
        key="alta_deudor",
    )

    # ---- Datos del préstamo ----
    componentes.render_html('<div class="seccion-titulo">Datos del préstamo</div>')

    capital_actual = Decimal(str(st.session_state.get("alta_capital", 1000000.0)))

    componentes.render_html(f"""
        <div class="aporte-header">
            <div class="aporte-nombre">Capital (ARS)</div>
        </div>
        <div class="aporte-monto-grande">{_formatear_pesos(capital_actual)}</div>
    """)

    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input(
            "Capital (ARS)",
            min_value=1000.0,
            value=1000000.0,
            step=10000.0,
            format="%.2f",
            label_visibility="collapsed",
            key="alta_capital",
        )

        plazo = st.number_input(
            "Plazo (meses)",
            min_value=1, max_value=360, value=12, step=1,
            key="alta_plazo",
        )
        componentes.render_html(
            '<div class="caption-ayuda">Cantidad de cuotas mensuales. '
            'Podés poner cualquier número: 12, 36, 84, 120.</div>'
        )

        fecha_inicio = st.date_input(
            "Fecha de inicio", value=date.today(), key="alta_fecha",
        )

    with col2:
        tasa = st.number_input(
            "Tasa anual (%)",
            min_value=0.0, max_value=500.0, value=30.0, step=1.0,
            format="%.2f", key="alta_tasa",
        )
        componentes.render_html(
            '<div class="caption-ayuda">Tasa de interés anual, '
            'sin incluir inflación ni gastos.</div>'
        )

        modalidad = st.selectbox(
            "Modalidad de tasa",
            options=["TNA", "TEA"],
            format_func=lambda x: {
                "TNA": "Tasa simple (TNA)",
                "TEA": "Tasa compuesta (TEA)",
            }[x],
            key="alta_modalidad",
        )

        capital_dec = Decimal(str(capital))
        cuota_tna = _calcular_cuota_segura(
            simulador, capital_dec, int(plazo), tasa, "TNA",
            fecha_inicio=fecha_inicio,
        )
        cuota_tea = _calcular_cuota_segura(
            simulador, capital_dec, int(plazo), tasa, "TEA",
            fecha_inicio=fecha_inicio,
        )
        tna_txt = _formatear_pesos(cuota_tna) if cuota_tna else "—"
        tea_txt = _formatear_pesos(cuota_tea) if cuota_tea else "—"

        _boton_ayuda(
            key="ayuda_modalidad",
            titulo="Modalidad de tasa",
            cuerpo_md=f"""
**¿Qué es?** Define cómo se convierte la tasa anual que pusiste
en una tasa mensual para calcular cada cuota.

---

**Tasa simple (TNA)**

La tasa anual se divide por 12.

**Tasa compuesta (TEA)**

La tasa se aplica con interés compuesto mes a mes.

---

**Impacto en tu préstamo** (a {int(plazo)} meses, con tus datos actuales):

| Modalidad | Cuota mensual |
|---|---|
| Tasa simple | {tna_txt} |
| Tasa compuesta | {tea_txt} |

**Recomendación:** si no estás seguro, usá **tasa simple**.
""",
        )

        sistema = st.selectbox(
            "Sistema de amortización",
            options=["FRANCES", "ALEMAN"],
            format_func=lambda x: {
                "FRANCES": "Cuota fija",
                "ALEMAN": "Cuota que va bajando",
            }[x],
            key="alta_sistema",
        )

        cuota_ini_fr = _calcular_cuota_segura(
            simulador, capital_dec, int(plazo), tasa, "TNA", "FRANCES",
            fecha_inicio=fecha_inicio,
        )
        try:
            tabla_al = simulador.generar_tabla(
                capital=capital_dec,
                tasa_anual=Decimal(str(tasa)) / Decimal("100"),
                plazo_meses=int(plazo),
                modalidad_tasa=ModalidadTasa("TNA"),
                sistema=SistemaAmortizacion.ALEMAN,
                fecha_inicio=fecha_inicio,
            )
            al_ini_txt = _formatear_pesos(tabla_al[0]["cuota"])
            al_fin_txt = _formatear_pesos(tabla_al[-1]["cuota"])
        except Exception:
            al_ini_txt = "—"
            al_fin_txt = "—"
        fr_txt = _formatear_pesos(cuota_ini_fr) if cuota_ini_fr else "—"

        _boton_ayuda(
            key="ayuda_sistema",
            titulo="Sistema de amortización",
            cuerpo_md=f"""
**¿Qué es?** Define cómo se reparte cada pago entre interés y
capital a lo largo del préstamo.

---

**Cuota fija** *(también conocido como Sistema Francés)*

Pagás el mismo monto todos los meses.

**Cuota que va bajando** *(también conocido como Sistema Alemán)*

Empezás pagando más y terminás pagando menos.

---

**Impacto en tu préstamo**:

| Sistema | Cuota |
|---|---|
| Cuota fija | {int(plazo)} cuotas de {fr_txt} |
| Cuota que va bajando | Empieza en {al_ini_txt} y termina en {al_fin_txt} |

**Recomendación:** si querés previsibilidad, usá **cuota fija**.
""",
        )

    convencion = st.selectbox(
        "Cómo se cuenta cada mes",
        options=["MENSUAL", "ACTUAL_365", "ACTUAL_360", "TREINTA_360"],
        format_func=lambda x: {
            "MENSUAL": "Mensual",
            "ACTUAL_365": "Días reales, año de 365",
            "ACTUAL_360": "Días reales, año de 360",
            "TREINTA_360": "Mes de 30 días",
        }[x],
        index=0,
        key="alta_convencion",
    )

    impacto = _interes_primer_mes_por_convencion(
        simulador, capital_dec, tasa, modalidad, fecha_inicio
    )

    _boton_ayuda(
        key="ayuda_convencion",
        titulo="Cómo se cuenta cada mes",
        cuerpo_md=f"""
**¿Qué es?** Define cómo se mide el tiempo para calcular el
interés de cada cuota. **No cambia la cantidad de cuotas ni el
plazo total del préstamo.**

---

**Mensual** *(también conocido como 1/12 del año)*

Todos los meses cuestan lo mismo. **Recomendado.**

**Días reales, año de 365** *(también conocido como Actual/365)*

Se cobra según los días que tuvo el mes.

**Días reales, año de 360** *(también conocido como Actual/360)*

Igual que el anterior, pero con un año "más corto".

**Mes de 30 días** *(también conocido como 30/360)*

Todos los meses se cuentan como de 30 días.

---

**Impacto real en tu primer mes**:

| Forma de contar | Interés del primer mes |
|---|---|
| Mensual | {_formatear_pesos(impacto['Mensual'])} |
| Días reales, año de 365 | {_formatear_pesos(impacto['Actual/365'])} |
| Días reales, año de 360 | {_formatear_pesos(impacto['Actual/360'])} |
| Mes de 30 días | {_formatear_pesos(impacto['30/360'])} |

**Recomendación:** para un préstamo personal, elegí **Mensual**.
""",
    )

    # ---- Destino ----
    componentes.render_html('<div class="seccion-titulo">Destino y descripción</div>')

    destino = st.text_input(
        "Destino (ej: Cambio de auto)", value="", key="alta_destino"
    )
    descripcion = st.text_area(
        "Descripción (opcional)", value="", key="alta_descripcion"
    )

    tc_inicial = st.number_input(
        "Tipo de cambio inicial ARS/USD (opcional, para medición)",
        min_value=0.0, value=1500.0, step=10.0, format="%.2f",
        key="alta_tc",
    )
    componentes.render_html(
        '<div class="caption-ayuda">Se usa solo para medir el rendimiento '
        'en dólares. No afecta la deuda que se pacta en pesos.</div>'
    )

    # ---- Inversores ----
    componentes.render_html('<div class="seccion-titulo">Inversores</div>')
    componentes.render_html(
        '<div class="caption-ayuda" style="margin-top: -0.5rem; margin-bottom: 1rem;">'
        'Podés simular el préstamo sin asignar inversores. Los vas a poder '
        'asignar antes de confirmar y guardar.'
        '</div>'
    )

    opciones_inversores = {
        p.id: f"{p.nombre} {p.apellido}".strip()
        for p in personas if p.id != deudor_id
    }

    ids_seleccionados = st.multiselect(
        "Elegí quiénes aportan capital (opcional)",
        options=list(opciones_inversores.keys()),
        format_func=lambda x: opciones_inversores[x],
        key="alta_inversores",
    )

    capital_dec = Decimal(str(capital))

    if ids_seleccionados:
        clave = _clave_estado(capital_dec, ids_seleccionados)
        fijos_clave = _clave_fijos(capital_dec, ids_seleccionados)

        if clave not in st.session_state:
            st.session_state[clave] = _repartir_iguales(capital_dec, ids_seleccionados)
            st.session_state[fijos_clave] = set()

        montos = st.session_state[clave]
        fijos = st.session_state.get(fijos_clave, set())

        st.session_state["_aportes_ctx"] = {
            "capital": capital_dec,
            "ids": ids_seleccionados,
            "clave": clave,
            "fijos_clave": fijos_clave,
        }

        for pid in ids_seleccionados:
            monto = montos.get(pid, Decimal("0"))
            porcentaje = (monto / capital_dec * 100) if capital_dec > 0 else Decimal("0")
            esta_fijo = pid in fijos
            candado = "🔒" if esta_fijo else ""

            componentes.render_html(f"""
                <div class="aporte-header">
                    <div class="aporte-nombre">
                        {opciones_inversores[pid]} {candado}
                    </div>
                    <div class="aporte-porcentaje-grande">
                        {float(porcentaje):.1f}%
                    </div>
                </div>
                <div class="aporte-monto-grande">
                    {_formatear_pesos(monto)}
                </div>
            """)

            st.number_input(
                f"Monto de {opciones_inversores[pid]}",
                min_value=0.0,
                max_value=float(capital_dec),
                value=float(monto),
                step=10000.0,
                format="%.2f",
                label_visibility="collapsed",
                key=f"aporte_input_{pid}_{clave}",
                on_change=_on_cambio_aporte,
                args=(pid, clave, fijos_clave, capital_dec),
            )

            componentes.render_html(f"""
                <div class="aporte-barra-wrapper">
                    <div class="aporte-barra">
                        <div class="aporte-barra-fill" style="width: {float(porcentaje):.2f}%;"></div>
                    </div>
                </div>
            """)

        if len(ids_seleccionados) >= 2:
            componentes.render_html("<br>")
            _, col_repartir, _ = st.columns([2, 2, 2])
            with col_repartir:
                st.button(
                    "Repartir en partes iguales",
                    use_container_width=True,
                    on_click=_repartir_iguales_callback,
                    key="repartir_iguales",
                )

        total = sum(montos.values())
        if total == capital_dec:
            componentes.render_html(
                f'<div class="nota-contextual nota-success">'
                f'<span class="nota-icono">✓</span>'
                f'<span class="nota-texto">'
                f'Asignación completa: {_formatear_pesos(total)}'
                f'</span></div>'
            )
        else:
            componentes.render_html(
                f'<div class="nota-contextual nota-warning">'
                f'<span class="nota-icono">⚠</span>'
                f'<span class="nota-texto">'
                f'Diferencia: {_formatear_pesos(capital_dec - total)}'
                f'</span></div>'
            )

    componentes.render_html("<br>")
    _, col_btn, _ = st.columns([2, 2, 2])
    with col_btn:
        puede_simular = capital_dec > 0

        if st.button(
            "Ver simulación",
            use_container_width=True,
            key="alta_simular",
            disabled=not puede_simular,
        ):
            inversores_dict = {}
            if ids_seleccionados:
                clave = _clave_estado(capital_dec, ids_seleccionados)
                inversores_dict = dict(st.session_state.get(clave, {}))

            st.session_state["prestamo_nuevo_datos"] = {
                "deudor_id": deudor_id,
                "capital": capital,
                "plazo": plazo,
                "tasa": tasa,
                "modalidad": modalidad,
                "sistema": sistema,
                "convencion": convencion,
                "fecha_inicio": fecha_inicio,
                "destino": destino,
                "descripcion": descripcion,
                "tc_inicial": tc_inicial,
                "inversores": inversores_dict,
            }
            st.session_state["prestamo_nuevo_step"] = "preview"
            st.rerun()

    if not ids_seleccionados:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">ℹ</span>'
            '<span class="nota-texto">'
            'Podés simular ahora. Al confirmar vas a necesitar asignar '
            'al menos un inversor.'
            '</span></div>'
        )


# ============================================================
# Fase 2: Preview
# ============================================================
def _renderizar_preview(simulador: ServicioSimulacionPrestamo) -> None:
    datos = st.session_state.get("prestamo_nuevo_datos")
    if not datos:
        st.session_state.pop("prestamo_nuevo_step", None)
        st.rerun()
        return

    st.markdown(
        '<div class="detalle-titulo">Confirmar préstamo</div>',
        unsafe_allow_html=True,
    )

    componentes.render_html(
        '<div class="nota-contextual nota-info">'
        '<span class="nota-icono">ℹ</span>'
        '<span class="nota-texto">'
        'Revisá la simulación antes de confirmar.'
        '</span></div>'
    )

    try:
        tabla = simulador.generar_tabla(
            capital=Decimal(str(datos["capital"])),
            tasa_anual=Decimal(str(datos["tasa"])) / Decimal("100"),
            plazo_meses=int(datos["plazo"]),
            modalidad_tasa=ModalidadTasa(datos["modalidad"]),
            sistema=SistemaAmortizacion(datos["sistema"].lower()),
            fecha_inicio=datos["fecha_inicio"],
        )
    except Exception as e:
        componentes.render_html(
            f'<div class="nota-contextual nota-error">'
            f'<span class="nota-icono">✕</span>'
            f'<span class="nota-texto">Error al calcular: {e}</span></div>'
        )
        return

    capital_dec = Decimal(str(datos["capital"]))
    total_intereses = sum(f["interes"] for f in tabla)
    total_pagado = sum(f["cuota"] for f in tabla)

    componentes.render_html('<div class="seccion-titulo">Resumen</div>')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Capital", _formatear_pesos(capital_dec))
    with col2:
        st.metric("Total intereses", _formatear_pesos(total_intereses))
    with col3:
        st.metric("Total a pagar", _formatear_pesos(total_pagado))

    componentes.render_html('<div class="seccion-titulo">Tabla de amortización</div>')

    headers = [
        {"texto": "#"},
        {"texto": "Vencimiento"},
        {"texto": "Cuota", "alineacion": "der"},
        {"texto": "Interés", "alineacion": "der"},
        {"texto": "Capital", "alineacion": "der"},
        {"texto": "Saldo", "alineacion": "der"},
    ]

    filas = []
    for f in tabla:
        filas.append([
            str(f["numero"]),
            _formatear_fecha(f["vencimiento"]),
            _formatear_pesos(f["cuota"]),
            _formatear_pesos(f["interes"]),
            _formatear_pesos(f["capital"]),
            _formatear_pesos(f["saldo"]),
        ])

    componentes.tabla(headers, filas)

    hay_inversores = bool(datos.get("inversores"))

    if not hay_inversores:
        componentes.render_html("<br>")
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            'Para guardar el préstamo, primero tenés que asignar '
            'al menos un inversor que aporte el capital. '
            'Volvé al formulario y agregalos en la sección "Inversores".'
            '</span></div>'
        )

    componentes.render_html("<br>")

    col_volver, col_confirmar, _ = st.columns([2, 2, 2])
    with col_volver:
        if st.button("Volver al formulario", use_container_width=True, key="volver_form"):
            st.session_state["prestamo_nuevo_step"] = "form"
            st.rerun()

    with col_confirmar:
        st.button(
            "Confirmar y guardar",
            use_container_width=True,
            key="confirmar_alta",
            disabled=not hay_inversores,
            on_click=_guardar_callback,
        )


# ============================================================
# Procesar guardado
# ============================================================
def _procesar_guardado(db: BaseDatos) -> None:
    """
    Si el usuario confirmó el guardado, crea el préstamo, limpia
    el estado del alta y hace rerun.

    IMPORTANTE: no se modifica `st.session_state["pagina"]`. Como
    este código corre dentro de la página Préstamos, después del
    rerun la página sigue siendo Préstamos y muestra la lista.
    """
    if not st.session_state.pop("_confirmar_guardado", False):
        return

    datos = st.session_state.get("prestamo_nuevo_datos")
    if not datos:
        return

    servicio = ServicioPrestamos(db)

    inversores = [
        {"persona_id": pid, "monto": Decimal(str(monto))}
        for pid, monto in datos["inversores"].items()
        if monto > 0
    ]

    try:
        prestamo_id = servicio.crear_completo(
            deudor_id=datos["deudor_id"],
            capital=Decimal(str(datos["capital"])),
            plazo_meses=int(datos["plazo"]),
            tasa_anual=Decimal(str(datos["tasa"])) / Decimal("100"),
            modalidad_tasa=datos["modalidad"],
            sistema=datos["sistema"],
            convencion_dias=datos["convencion"],
            fecha_inicio=datos["fecha_inicio"],
            inversores=inversores,
            usuario="admin",
            tc_inicial=(
                Decimal(str(datos["tc_inicial"]))
                if datos["tc_inicial"] > 0 else None
            ),
            destino=datos["destino"] or None,
            descripcion=datos["descripcion"] or None,
        )
    except ErrorServicio as e:
        componentes.disparar_nota(str(e), "error")
        st.rerun()
        return

    # Limpiar TODO el estado del alta
    claves_a_borrar = [
        k for k in list(st.session_state.keys())
        if k.startswith("aportes_")
        or k.startswith("fijos_")
        or k.startswith("aporte_input_")
        or k == "_aportes_ctx"
        or k == "_confirmar_guardado"
        or k == "prestamo_nuevo_datos"
        or k == "prestamo_nuevo_step"
        or k == "prestamo_seleccionado"
    ]
    for k in claves_a_borrar:
        st.session_state.pop(k, None)

    # Disparar la nota de éxito (aparece en la lista)
    componentes.disparar_nota(
        f"Préstamo #{prestamo_id} creado correctamente.",
        "success",
    )

    # Forzar rerun limpio
    st.rerun()


# ============================================================
# Render principal
# ============================================================
def render(db: BaseDatos) -> None:
    # Procesar guardado pendiente ANTES de renderizar nada
    _procesar_guardado(db)

    step = st.session_state.get("prestamo_nuevo_step", "form")
    if step == "preview":
        _renderizar_preview(db)
    else:
        _renderizar_formulario(db)