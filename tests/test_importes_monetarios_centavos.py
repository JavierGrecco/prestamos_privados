"""Los servicios financieros rechazan importes que no pueden registrarse en centavos."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.composicion.servicio_pagos_legacy import crear_servicio_pagos_legacy
from aplicacion.servicios import ErrorDatosInvalidos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def escenario(tmp_path: Path):
    with BaseDatos(tmp_path / "importes-centavos.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor_id = personas.crear(nombre="Deudor", apellido="Centavos")
        inversor_id = personas.crear(nombre="Inversor", apellido="Centavos")
        yield db, deudor_id, inversor_id


def _alta(servicio: ServicioPrestamos, deudor_id: int, inversor_id: int,
          capital: Decimal, aporte: Decimal) -> int:
    return servicio.crear_completo(
        deudor_id=deudor_id,
        capital=capital,
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": aporte}],
        usuario="test-centavos",
    )


@pytest.mark.parametrize("valor", [Decimal("10000.005"), Decimal("NaN"), Decimal("Infinity")])
def test_alta_rechaza_capital_con_fraccion_de_centavo_o_no_finito(
    escenario, valor: Decimal
) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos):
        _alta(crear_servicio_prestamos(db), deudor_id, inversor_id, valor, valor)
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0


def test_alta_rechaza_aporte_con_fraccion_de_centavo(escenario) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos, match="fracciones de centavo"):
        _alta(
            crear_servicio_prestamos(db),
            deudor_id,
            inversor_id,
            Decimal("10000.00"),
            Decimal("10000.005"),
        )
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"] == 0


def test_pago_rechaza_fraccion_de_centavo_antes_de_persistir(escenario) -> None:
    db, deudor_id, inversor_id = escenario
    prestamo_id = _alta(
        crear_servicio_prestamos(db),
        deudor_id,
        inversor_id,
        Decimal("1000000.00"),
        Decimal("1000000.00"),
    )

    with pytest.raises(ErrorDatosInvalidos, match="fracciones de centavo"):
        crear_servicio_pagos_legacy(db).registrar_pago(
            prestamo_id=prestamo_id,
            monto=Decimal("97487.135"),
            fecha_real=date(2026, 2, 1),
            usuario="test-centavos",
            opcion_adelanto="RAI",
        )

    assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == 0


def test_pago_rechaza_decimal_no_finito_con_error_de_dominio(escenario) -> None:
    db, deudor_id, inversor_id = escenario
    with pytest.raises(ErrorDatosInvalidos, match="finito"):
        crear_servicio_pagos_legacy(db).registrar_pago(
            prestamo_id=999,
            monto=Decimal("NaN"),
            fecha_real=date(2026, 2, 1),
            usuario="test-centavos",
        )
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == 0
