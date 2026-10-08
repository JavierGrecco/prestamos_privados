"""Pruebas de escenarios macroeconómicos sobre flujos personales."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.escenarios_persona import ServicioEscenariosPersona
from aplicacion.servicios.prestamos import ServicioPrestamos
from dominio.escenarios import EscenarioMacro
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _persona(personas, nombre, documento, rol):
    persona_id = personas.crear(
        nombre=nombre,
        apellido="Escenario",
        documento=documento,
    )
    personas.agregar_rol(persona_id, rol)
    return persona_id


def _crear_prestamo(
    db,
    deudor_id,
    inversor_id,
    capital=Decimal("180000.00"),
    tc_inicial=Decimal("1000.00"),
):
    ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=capital,
        plazo_meses=6,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 10, 8),
        inversores=[{"persona_id": inversor_id, "monto": capital}],
        usuario="test",
        tc_inicial=tc_inicial,
        destino="Escenario",
    )


def test_escenarios_no_cambian_el_monto_nominal_del_contrato(
    tmp_path: Path,
):
    ruta = tmp_path / "escenarios.db"

    suave = EscenarioMacro(
        nombre="Suave",
        inflacion_mensual=Decimal("0.02"),
        devaluacion_mensual=Decimal("0.02"),
    )
    fuerte = EscenarioMacro(
        nombre="Fuerte",
        inflacion_mensual=Decimal("0.10"),
        devaluacion_mensual=Decimal("0.15"),
    )

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Ana", "99992001", "DEUDOR")
        inversor = _persona(personas, "Pedro", "99992002", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)

        resultado = ServicioEscenariosPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 10, 8),
            horizonte_meses=6,
            tipo_cambio_inicial=Decimal("1000.00"),
            escenarios=(suave, fuerte),
        )

    assert len(resultado.resultados) == 2
    assert resultado.resultados[0].cobros_nominales == resultado.resultados[1].cobros_nominales
    assert resultado.resultados[0].pagos_nominales == resultado.resultados[1].pagos_nominales
    assert resultado.resultados[0].neto_nominal == resultado.resultados[1].neto_nominal
    assert resultado.resultados[0].cobros_reales > resultado.resultados[1].cobros_reales
    assert resultado.resultados[0].cobros_usd > resultado.resultados[1].cobros_usd


def test_escenarios_de_deudor_reducen_valor_real_con_mayor_inflacion(
    tmp_path: Path,
):
    ruta = tmp_path / "escenarios_deuda.db"

    baja = EscenarioMacro(
        nombre="Inflación baja",
        inflacion_mensual=Decimal("0.02"),
        devaluacion_mensual=Decimal("0.02"),
    )
    alta = EscenarioMacro(
        nombre="Inflación alta",
        inflacion_mensual=Decimal("0.10"),
        devaluacion_mensual=Decimal("0.10"),
    )

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Carlos", "99992003", "DEUDOR")
        inversor = _persona(personas, "Lucía", "99992004", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)

        resultado = ServicioEscenariosPersona(db).obtener(
            deudor,
            fecha_corte=date(2026, 10, 8),
            horizonte_meses=6,
            tipo_cambio_inicial=Decimal("1000.00"),
            escenarios=(baja, alta),
        )

    assert resultado.resultados[0].pagos_nominales == resultado.resultados[1].pagos_nominales
    assert resultado.resultados[0].pagos_reales > resultado.resultados[1].pagos_reales


def test_escenarios_sin_tipo_de_cambio_no_inventan_usd(tmp_path: Path):
    ruta = tmp_path / "escenarios_sin_usd.db"

    escenario = EscenarioMacro(
        nombre="Referencia",
        inflacion_mensual=Decimal("0.05"),
        devaluacion_mensual=Decimal("0.07"),
    )

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Mario", "99992005", "DEUDOR")
        inversor = _persona(personas, "Sofía", "99992006", "INVERSOR")
        _crear_prestamo(db, deudor, inversor, tc_inicial=None)

        resultado = ServicioEscenariosPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 10, 8),
            horizonte_meses=6,
            tipo_cambio_inicial=None,
            escenarios=(escenario,),
        )

    assert resultado.resultados[0].cobros_usd is None
    assert resultado.resultados[0].pagos_usd is None


def test_escenarios_rechazan_tipo_de_cambio_invalido(tmp_path: Path):
    ruta = tmp_path / "escenarios_tc.db"

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Nora", "99992007", "DEUDOR")
        inversor = _persona(personas, "Elías", "99992008", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)

        with pytest.raises(ValueError, match="tipo de cambio"):
            ServicioEscenariosPersona(db).obtener(
                inversor,
                fecha_corte=date(2026, 10, 8),
                tipo_cambio_inicial=Decimal("0"),
            )
