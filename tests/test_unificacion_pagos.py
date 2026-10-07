"""Regresión: simulación y registro deben consumir el mismo plan puro."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PagoRepo, PersonaRepo


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "test.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.fixture
def prestamo_activo(db):
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Juan", apellido="Pérez")
    inversor_id = personas.crear(nombre="María", apellido="García")

    prestamo_id = ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="admin",
    )
    return prestamo_id


def _cuotas_dict(db, prestamo_id):
    servicio = ServicioPrestamos(db)
    version_id = servicio.prestamos.version_activa(prestamo_id)
    return {
        cuota.id: cuota
        for cuota in servicio.prestamos.cuotas(version_id)
    }


class TestPlanPagoIntegrado:
    def test_registro_aplica_el_mismo_plan_que_mostro_simulacion(
        self, db, prestamo_activo
    ):
        servicio = ServicioPagos(db)
        monto = Decimal("50000.00")
        fecha = date(2026, 2, 1)

        simulacion = servicio.simular_pago(
            prestamo_id=prestamo_activo,
            monto=monto,
            fecha_calculo=fecha,
        )
        plan = simulacion["plan"]

        pago_id = servicio.registrar_pago(
            prestamo_id=prestamo_activo,
            monto=monto,
            fecha_real=fecha,
            usuario="admin",
        )

        pago = PagoRepo(db).obtener(pago_id)
        assert pago is not None
        assert pago.interes_extra_generado == plan.interes_extra_generado_por_pago

        cuotas = _cuotas_dict(db, prestamo_activo)
        for actualizacion in plan.actualizaciones:
            cuota = cuotas[actualizacion.cuota_id]
            assert cuota.estado == actualizacion.estado
            assert cuota.interes_pendiente == actualizacion.interes_pendiente
            assert cuota.capital_pendiente == actualizacion.capital_pendiente
            assert cuota.mora_pendiente == actualizacion.mora_pendiente

    def test_arrastre_tambien_se_aplica_con_el_mismo_plan(self, db, prestamo_activo):
        servicio = ServicioPagos(db)
        servicio.registrar_pago(
            prestamo_id=prestamo_activo,
            monto=Decimal("50000.00"),
            fecha_real=date(2026, 2, 1),
            usuario="admin",
        )

        simulacion = servicio.simular_pago(
            prestamo_id=prestamo_activo,
            monto=Decimal("50000.00"),
            fecha_calculo=date(2026, 3, 1),
        )
        plan = simulacion["plan"]

        pago_id = servicio.registrar_pago(
            prestamo_id=prestamo_activo,
            monto=Decimal("50000.00"),
            fecha_real=date(2026, 3, 1),
            usuario="admin",
        )
        pago = PagoRepo(db).obtener(pago_id)
        assert pago is not None
        assert pago.interes_extra_generado == plan.interes_extra_generado_por_pago
        assert (
            plan.resultado.interes_extra_estimado_proximo_periodo
            >= plan.interes_extra_generado_por_pago
        )
