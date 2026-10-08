"""Pruebas del servicio de personas y relaciones."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios.personas import ServicioPersonas
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


def test_criar_persona_con_roles_y_administrarlos(tmp_path: Path):
    ruta = tmp_path / "personas.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        servicio = ServicioPersonas(db)

        persona_id = servicio.crear(
            nombre="Ana",
            apellido="García",
            documento="90000001",
            roles=("DEUDOR",),
        )

        assert servicio.obtener(persona_id).nombre_completo == "Ana García"
        assert servicio.roles(persona_id) == ["DEUDOR"]

        servicio.agregar_rol(persona_id, "INVERSOR")
        assert set(servicio.roles(persona_id)) == {"DEUDOR", "INVERSOR"}

        servicio.quitar_rol(persona_id, "DEUDOR", motivo="Cambio de rol")
        assert servicio.roles(persona_id) == ["INVERSOR"]

        servicio.actualizar(
            persona_id,
            nombre="Ana María",
            apellido="García",
            email="ana@example.com",
        )
        servicio.cambiar_estado(persona_id, "INACTIVO")

        persona = servicio.obtener(persona_id)
        assert persona.nombre_completo == "Ana María García"
        assert persona.email == "ana@example.com"
        assert persona.estado == "INACTIVO"


def test_persona_expone_prestamos_como_deudora_e_inversora(tmp_path: Path):
    ruta = tmp_path / "relaciones.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        servicio_personas = ServicioPersonas(db)

        deudor = servicio_personas.crear(
            nombre="Deudor", roles=("DEUDOR",)
        )
        inversor = servicio_personas.crear(
            nombre="Inversor", roles=("INVERSOR",)
        )

        ServicioPrestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("100000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": inversor, "monto": Decimal("100000.00")}
            ],
            usuario="test",
        )

        relaciones_deudor = servicio_personas.prestamos_de(deudor)
        relaciones_inversor = servicio_personas.prestamos_de(inversor)

        assert len(relaciones_deudor) == 1
        assert relaciones_deudor[0].rol == "DEUDOR"
        assert relaciones_deudor[0].monto == Decimal("100000.00")

        assert len(relaciones_inversor) == 1
        assert relaciones_inversor[0].rol == "INVERSOR"
        assert relaciones_inversor[0].monto == Decimal("100000.00")


def test_servicio_rechaza_roles_invalidos(tmp_path: Path):
    ruta = tmp_path / "roles.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        servicio = ServicioPersonas(db)

        try:
            servicio.crear(nombre="X", roles=("NO_EXISTE",))
        except ValueError as exc:
            assert "inválido" in str(exc)
        else:
            raise AssertionError("Se esperaba ValueError")
