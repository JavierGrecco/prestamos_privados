"""Pruebas de la vista humana por persona."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.vista_humana_persona import VistaHumanaPersonaQuery
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def test_vista_humana_reune_deudor_e_inversor_y_separa_estimado_de_real(
    tmp_path: Path,
):
    ruta = tmp_path / "humana.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        persona = personas.crear(
            nombre="María",
            apellido="Ejemplo",
            documento="99999999",
        )
        personas.agregar_rol(persona, "DEUDOR")
        personas.agregar_rol(persona, "INVERSOR")

        ServicioPrestamos(db).crear_completo(
            deudor_id=persona,
            capital=Decimal("1200000.00"),
            plazo_meses=6,
            tasa_anual=Decimal("0.30"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2027, 1, 1),
            inversores=[
                {"persona_id": persona, "monto": Decimal("1200000.00")}
            ],
            usuario="test",
            destino="Compra de herramienta",
        )

        vista = VistaHumanaPersonaQuery(db).obtener(
            persona,
            fecha_corte=date(2026, 10, 8),
        )

    assert set(vista.roles) == {"DEUDOR", "INVERSOR"}
    assert vista.capital_invertido == Decimal("1200000.00")
    assert vista.capital_pendiente_deuda > Decimal("0")
    assert vista.proximo_pago is not None
    assert vista.proximo_cobro is not None

    inversiones = [p for p in vista.posiciones if p.rol == "INVERSOR"]
    deudas = [p for p in vista.posiciones if p.rol == "DEUDOR"]

    assert len(inversiones) == 1
    assert len(deudas) == 1
    assert inversiones[0].monto_principal == Decimal("1200000.00")
    assert inversiones[0].cobrado_real == Decimal("0.00")
    assert inversiones[0].proximo_monto is not None
    assert deudas[0].capital_pendiente == vista.capital_pendiente_deuda
    assert deudas[0].proximo_monto is not None
