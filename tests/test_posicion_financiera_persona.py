"""Pruebas de la posición financiera consolidada."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.posicion_financiera_persona import (
    ServicioPosicionFinancieraPersona,
)
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _crear_persona(personas, nombre, documento, *roles):
    persona_id = personas.crear(
        nombre=nombre,
        apellido="Ejemplo",
        documento=documento,
    )
    for rol in roles:
        personas.agregar_rol(persona_id, rol)
    return persona_id


def test_posicion_neta_separa_inversion_de_deuda(
    tmp_path: Path,
):
    ruta = tmp_path / "posicion.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        persona = _crear_persona(
            personas,
            "María",
            "99990001",
            "DEUDOR",
            "INVERSOR",
        )
        inversor_externo = _crear_persona(
            personas,
            "Pedro",
            "99990002",
            "INVERSOR",
        )
        deudor_externo = _crear_persona(
            personas,
            "Lucía",
            "99990003",
            "DEUDOR",
        )

        servicio = ServicioPrestamos(db)

        prestamo_deuda_id = servicio.crear_completo(
            deudor_id=persona,
            capital=Decimal("200000.00"),
            plazo_meses=4,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": inversor_externo, "monto": Decimal("200000.00")}
            ],
            usuario="test",
            destino="Deuda de prueba",
        )

        servicio.crear_completo(
            deudor_id=deudor_externo,
            capital=Decimal("300000.00"),
            plazo_meses=4,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": persona, "monto": Decimal("300000.00")}
            ],
            usuario="test",
            destino="Inversión de prueba",
        )

        db.ejecutar(
            """
            INSERT INTO pagos
            (prestamo_id, fecha_real, fecha_valor, fecha_registro,
             monto_moneda_pago, monto_moneda_contractual, estado,
             creado_por, tipo_pago)
            VALUES (?, '2026-02-15', '2026-02-15', '2026-02-15',
                    '10000.00', '10000.00', 'VALIDA', 'test', 'CUOTA')
            """,
            (prestamo_deuda_id,),
        )

        posicion = ServicioPosicionFinancieraPersona(db).obtener(
            persona,
            fecha_corte=date(2026, 2, 20),
        )

    assert posicion.capital_invertido == Decimal("300000.00")
    assert posicion.capital_deuda_pendiente == Decimal("200000.00")
    assert posicion.posicion_neta_capital == Decimal("100000.00")
    assert posicion.cobros_reales == Decimal("0.00")
    assert posicion.pagos_reales == Decimal("10000.00")
    assert posicion.flujo_neto_real == Decimal("-10000.00")
    assert posicion.cobros_futuros_estimados > Decimal("300000.00")
    assert posicion.pagos_futuros_estimados > Decimal("200000.00")
    assert len(posicion.movimientos_mensuales) == 12
    enero = next(m for m in posicion.movimientos_mensuales if m.periodo == date(2026, 1, 1))
    febrero = next(m for m in posicion.movimientos_mensuales if m.periodo == date(2026, 2, 1))
    assert enero.entradas == Decimal("200000.00")
    assert enero.salidas == Decimal("300000.00")
    assert enero.neto == Decimal("-100000.00")
    assert febrero.entradas == Decimal("0.00")
    assert febrero.salidas == Decimal("10000.00")
    assert febrero.neto == Decimal("-10000.00")
    assert febrero.acumulado == Decimal("-110000.00")


def test_posicion_sin_operaciones_no_inventa_patrimonio(tmp_path: Path):
    ruta = tmp_path / "vacia.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        persona = _crear_persona(
            personas,
            "Ana",
            "99990010",
            "DEUDOR",
        )

        posicion = ServicioPosicionFinancieraPersona(db).obtener(
            persona,
            fecha_corte=date(2026, 10, 8),
        )

    assert posicion.capital_invertido == Decimal("0.00")
    assert posicion.capital_deuda_pendiente == Decimal("0.00")
    assert posicion.posicion_neta_capital == Decimal("0.00")
    assert posicion.cobros_futuros_estimados == Decimal("0.00")
    assert posicion.pagos_futuros_estimados == Decimal("0.00")
    assert posicion.movimientos_mensuales
    assert all(m.neto == Decimal("0.00") for m in posicion.movimientos_mensuales)
