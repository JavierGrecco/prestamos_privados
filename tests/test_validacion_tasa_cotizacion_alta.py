"""La frontera de alta rechaza tasas y cotizaciones inválidas antes de persistir."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from aplicacion.servicios import ErrorDatosInvalidos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def escenario(tmp_path: Path):
    with BaseDatos(tmp_path / "validacion-tasa-cotizacion.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor_id = personas.crear(nombre="Deudor", apellido="Validación")
        inversor_id = personas.crear(nombre="Inversor", apellido="Validación")
        yield db, deudor_id, inversor_id


def _crear(
    db: BaseDatos,
    deudor_id: int,
    inversor_id: int,
    *,
    tasa: Decimal = Decimal("0.30"),
    modalidad: str = "TNA",
    tc: Decimal | None = None,
) -> int:
    return crear_servicio_prestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("10000.00"),
        plazo_meses=3,
        tasa_anual=tasa,
        modalidad_tasa=modalidad,
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": Decimal("10000.00")}
        ],
        usuario="test-validacion-tasa",
        tc_inicial=tc,
    )


@pytest.mark.parametrize(
    ("tasa", "mensaje"),
    [
        (Decimal("-0.01"), "no puede ser negativa"),
        (Decimal("NaN"), "Decimal finito"),
        (Decimal("Infinity"), "Decimal finito"),
        (Decimal("-Infinity"), "Decimal finito"),
    ],
)
def test_alta_rechaza_tasa_negativa_o_no_finita(escenario, tasa, mensaje) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos, match=mensaje):
        _crear(db, deudor_id, inversor_id, tasa=tasa)
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM versiones_tasa")["n"] == 0


def test_alta_rechaza_modalidad_tasa_desconocida(escenario) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos, match="TNA o TEA"):
        _crear(db, deudor_id, inversor_id, modalidad="TASA_DESCONOCIDA")
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0


@pytest.mark.parametrize(
    ("tc", "mensaje"),
    [
        (Decimal("0"), "mayor a cero"),
        (Decimal("-1500"), "mayor a cero"),
        (Decimal("NaN"), "Decimal finito"),
        (Decimal("Infinity"), "Decimal finito"),
    ],
)
def test_alta_rechaza_cotizacion_inicial_invalida(
    escenario, tc, mensaje
) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos, match=mensaje):
        _crear(db, deudor_id, inversor_id, tc=tc)
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM participaciones")["n"] == 0


def test_alta_permite_tasa_cero_y_cotizacion_omitida(escenario) -> None:
    db, deudor_id, inversor_id = escenario
    prestamo_id = _crear(
        db,
        deudor_id,
        inversor_id,
        tasa=Decimal("0"),
        tc=None,
    )
    assert prestamo_id > 0
