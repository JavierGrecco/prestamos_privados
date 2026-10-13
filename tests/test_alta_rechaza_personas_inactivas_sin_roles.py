"""La compatibilidad con personas legacy sin roles no ignora estado INACTIVO."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios import ErrorDatosInvalidos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def db(tmp_path: Path):
    with BaseDatos(tmp_path / "personas-inactivas.db") as db:
        aplicar_migraciones(db)
        yield db


def _crear_prestamo(servicio, deudor_id: int, inversor_id: int) -> int:
    return servicio.crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("10000.00"),
        plazo_meses=3,
        tasa_anual=Decimal("0.12"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": Decimal("10000.00")}
        ],
        usuario="test-actividad-persona",
    )


def test_deudor_inactivo_sin_roles_explicitos_es_rechazado(db: BaseDatos) -> None:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Legacy")
    inversor_id = personas.crear(nombre="Inversor", apellido="Legacy")
    personas.actualizar(deudor_id, estado="INACTIVO")

    with pytest.raises(ErrorDatosInvalidos, match="deudor está INACTIVO"):
        _crear_prestamo(ServicioPrestamos(db), deudor_id, inversor_id)

    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0


def test_inversor_inactivo_sin_roles_explicitos_es_rechazado(db: BaseDatos) -> None:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Legacy")
    inversor_id = personas.crear(nombre="Inversor", apellido="Legacy")
    personas.actualizar(inversor_id, estado="INACTIVO")

    with pytest.raises(ErrorDatosInvalidos, match="inversor .* está INACTIVO"):
        _crear_prestamo(ServicioPrestamos(db), deudor_id, inversor_id)

    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0


def test_personas_activas_sin_roles_siguen_siendose_aceptadas(db: BaseDatos) -> None:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Legacy")
    inversor_id = personas.crear(nombre="Inversor", apellido="Legacy")

    prestamo_id = _crear_prestamo(ServicioPrestamos(db), deudor_id, inversor_id)

    assert prestamo_id > 0
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 1
