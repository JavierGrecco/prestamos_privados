"""Integración de los resultados efectivos por operación."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
)
from infraestructura import BaseDatos
from infraestructura.composicion.analisis_financiero import (
    crear_analisis_financiero_query,
    crear_servicio_resultados_operaciones_persona,
)
from infraestructura.composicion.personas import crear_servicio_personas
from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.migraciones import aplicar_migraciones


ROOT = Path(__file__).resolve().parents[1]
CORTE = date(2026, 4, 1)


def _crear_persona(personas, nombre: str, documento: str, rol: str) -> int:
    return personas.crear(
        nombre=nombre,
        apellido="M5",
        documento=documento,
        roles=(rol,),
    )


def _crear_prestamo(db, deudor_id: int, inversor_id: int, *, capital="180000.00") -> int:
    return crear_servicio_prestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal(capital),
        plazo_meses=6,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 8),
        inversores=[{"persona_id": inversor_id, "monto": Decimal(capital)}],
        usuario="test-m5",
        tc_inicial=Decimal("1000.00"),
        destino="Operación M5",
    )


def _insertar_pago_y_cobro(
    db,
    prestamo_id: int,
    inversor_id: int,
    *,
    fecha="2026-03-08",
    monto="40000.00",
    usd="36.36363636",
    tc="1100.00",
):
    monto_usd = "NULL" if usd is None else f"'{usd}'"
    tc_aplicado = "NULL" if tc is None else f"'{tc}'"
    db.ejecutar(
        f"""
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro, moneda_pago,
         monto_moneda_pago, monto_moneda_contractual, monto_usd_ref, tc_aplicado,
         estado, creado_por, tipo_pago)
        VALUES (?, ?, ?, ?, 'ARS', ?, ?, {monto_usd}, {tc_aplicado},
                'VALIDA', 'test-m5', 'CUOTA')
        """,
        (prestamo_id, fecha, fecha, fecha, monto, monto),
    )
    pago_id = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES ('INVERSOR', ?, 'COBRO_PAGO', ?, '0.00', ?,
                ?, ?, ?)
        """,
        (
            inversor_id,
            monto,
            fecha,
            '{"pago_id": ' + str(pago_id) + '}',
            f"m5-{prestamo_id}-{pago_id}",
            fecha,
        ),
    )
    return pago_id


def _base(tmp_path: Path, nombre: str = "m5.db"):
    db = BaseDatos(tmp_path / nombre)
    aplicar_migraciones(db)
    personas = crear_servicio_personas(db)
    return db, personas


def test_inversor_ve_cada_prestamo_por_separado(tmp_path: Path):
    with _base(tmp_path) as (db, personas):
        deudor_1 = _crear_persona(personas, "Deudor uno", "99993101", "DEUDOR")
        deudor_2 = _crear_persona(personas, "Deudor dos", "99993102", "DEUDOR")
        inversor = _crear_persona(personas, "Inversor", "99993103", "INVERSOR")
        prestamo_1 = _crear_prestamo(db, deudor_1, inversor, capital="180000.00")
        prestamo_2 = _crear_prestamo(db, deudor_2, inversor, capital="240000.00")
        _insertar_pago_y_cobro(db, prestamo_1, inversor, monto="40000.00")
        _insertar_pago_y_cobro(db, prestamo_2, inversor, monto="65000.00")

        resultado = crear_servicio_resultados_operaciones_persona(db).obtener(
            inversor,
            fecha_corte=CORTE,
            inflacion_mensual_supuesta=Decimal("0.00"),
        )

        assert len(resultado.operaciones) == 2
        por_id = {operacion.prestamo_id: operacion for operacion in resultado.operaciones}
        assert set(por_id) == {prestamo_1, prestamo_2}
        assert all(operacion.rol == "inversor" for operacion in resultado.operaciones)
        assert all(operacion.evidencia_suficiente for operacion in resultado.operaciones)
        assert all(operacion.cantidad_flujos == 2 for operacion in resultado.operaciones)
        assert all(operacion.xirr_anual is not None for operacion in resultado.operaciones)
        assert por_id[prestamo_1].xirr_anual != por_id[prestamo_2].xirr_anual
        assert por_id[prestamo_1].xirr_usd_anual is not None
        assert por_id[prestamo_2].xirr_usd_anual is not None


def test_deudor_con_prestamo_finalizado_conserva_su_historial(tmp_path: Path):
    with _base(tmp_path, "cerrado.db") as (db, personas):
        deudor = _crear_persona(personas, "Deudor cerrado", "99993104", "DEUDOR")
        inversor = _crear_persona(personas, "Inversor cerrado", "99993105", "INVERSOR")
        prestamo_id = _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(db, prestamo_id, inversor)
        db.ejecutar(
            "UPDATE prestamos SET estado = 'FINALIZADO' WHERE id = ?",
            (prestamo_id,),
        )

        # La vista de posición vigente conserva su filtro de préstamos abiertos.
        posicion = crear_analisis_financiero_query(db).obtener(
            deudor,
            fecha_corte=CORTE,
        )
        assert not any(flujo.prestamo_id == prestamo_id for flujo in posicion.flujos_reales)

        # M5 pide explícitamente los flujos históricos, sin convertirlos en saldo pendiente.
        resultado = crear_servicio_resultados_operaciones_persona(db).obtener(
            deudor,
            fecha_corte=CORTE,
            inflacion_mensual_supuesta=Decimal("0.00"),
        )
        assert len(resultado.operaciones) == 1
        operacion = resultado.operaciones[0]
        assert operacion.prestamo_id == prestamo_id
        assert operacion.rol == "deudor"
        assert operacion.evidencia_suficiente
        assert operacion.xirr_anual is not None

        posicion_con_historia = crear_analisis_financiero_query(db).obtener(
            deudor,
            fecha_corte=CORTE,
            incluir_operaciones_cerradas=True,
        )
        assert posicion_con_historia.resumen.capital_deudor_pendiente == Decimal("0.00")
        assert any(
            flujo.prestamo_id == prestamo_id
            for flujo in posicion_con_historia.flujos_reales
        )


def test_no_muestra_tasa_usd_parcial_si_falta_una_conversion(tmp_path: Path):
    with _base(tmp_path, "usd_incompleto.db") as (db, personas):
        deudor = _crear_persona(personas, "Deudor USD", "99993106", "DEUDOR")
        inversor = _crear_persona(personas, "Inversor USD", "99993107", "INVERSOR")
        prestamo_id = _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(
            db,
            prestamo_id,
            inversor,
            usd=None,
            tc=None,
        )

        resultado = crear_servicio_resultados_operaciones_persona(db).obtener(
            inversor,
            fecha_corte=CORTE,
        )
        operacion = resultado.operaciones[0]

        assert operacion.evidencia_suficiente
        assert operacion.xirr_anual is not None
        assert not operacion.tiene_usd_completo
        assert operacion.xirr_usd_anual is None


def test_fecha_de_corte_no_incluye_movimientos_posteriores(tmp_path: Path):
    with _base(tmp_path, "corte.db") as (db, personas):
        deudor = _crear_persona(personas, "Deudor corte", "99993108", "DEUDOR")
        inversor = _crear_persona(personas, "Inversor corte", "99993109", "INVERSOR")
        prestamo_id = _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(db, prestamo_id, inversor, fecha="2026-03-08")

        resultado = crear_servicio_resultados_operaciones_persona(db).obtener(
            inversor,
            fecha_corte=date(2026, 2, 1),
        )
        operacion = resultado.operaciones[0]

        assert len(operacion.flujos_reales) == 1
        assert not operacion.evidencia_suficiente
        assert operacion.xirr_anual is None
        assert operacion.motivo_no_disponible


def test_rechaza_persona_inexistente_e_inflacion_invalida(tmp_path: Path):
    with _base(tmp_path, "validaciones.db") as (db, personas):
        persona = _crear_persona(personas, "Persona válida", "99993110", "INVERSOR")
        servicio = crear_servicio_resultados_operaciones_persona(db)

        with pytest.raises(ValueError, match="no existe"):
            servicio.obtener(999999, fecha_corte=CORTE)
        with pytest.raises(ValueError, match="mayor a -100%"):
            servicio.obtener(
                persona,
                fecha_corte=CORTE,
                inflacion_mensual_supuesta=Decimal("-1"),
            )
        with pytest.raises(ValueError, match="finita"):
            servicio.obtener(
                persona,
                fecha_corte=CORTE,
                inflacion_mensual_supuesta=Decimal("NaN"),
            )


def test_read_model_por_operacion_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "resultados_operaciones_persona.py"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, "El read model por operación no debe conocer infraestructura: " + "; ".join(problemas)


def test_pantalla_de_rendimiento_no_abre_repositorios_ni_sqlite():
    archivo = ROOT / "ui" / "pagina_rendimiento.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and (
                modulo.startswith("infraestructura.db")
                or modulo.startswith("infraestructura.repositorios")
                or modulo == "sqlite3"
            ):
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, "La UI debe usar el punto de composición: " + "; ".join(problemas)
