"""Regresiones del modelo de garantías personales por préstamo."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios.garantias_prestamo import ServicioGarantiasPrestamo
from aplicacion.servicios.personas import ServicioPersonas
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


CAPITAL = Decimal("100000.00")


@pytest.fixture
def db(tmp_path: Path):
    with BaseDatos(tmp_path / "garantias.db") as db:
        aplicar_migraciones(db)
        yield db


def _persona(servicio: ServicioPersonas, nombre: str, *roles: str) -> int:
    return servicio.crear(nombre=nombre, roles=roles)


def _prestamo(
    db: BaseDatos,
    deudor_id: int,
    inversor_id: int,
    destino: str,
) -> int:
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=CAPITAL,
        plazo_meses=3,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": CAPITAL},
        ],
        usuario="admin-test",
        destino=destino,
    )


def test_garantia_es_auditable_y_no_modifica_hechos_financieros(db: BaseDatos):
    personas = ServicioPersonas(db)
    deudor = _persona(personas, "Deudor", "DEUDOR")
    inversor = _persona(personas, "Inversor", "INVERSOR")
    garante = _persona(personas, "Garante")
    prestamo_id = _prestamo(db, deudor, inversor, "Préstamo con garantía")

    ledger_antes = db.consultar(
        """
        SELECT id, entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
               correlacion_id
        FROM ledger WHERE entidad = 'PRESTAMO' AND entidad_id = ?
        ORDER BY id
        """,
        (prestamo_id,),
    )
    pagos_antes = db.consultar(
        "SELECT id, prestamo_id, monto_moneda_pago, estado FROM pagos "
        "WHERE prestamo_id = ? ORDER BY id",
        (prestamo_id,),
    )
    deuda_antes = db.consultar_uno(
        "SELECT capital_original, estado FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )

    servicio = ServicioGarantiasPrestamo(db)
    garantia = servicio.crear(
        prestamo_id=prestamo_id,
        garante_id=garante,
        alcance="Cubre la obligación de acuerdo con el documento firmado.",
        monto_maximo=Decimal("75000.00"),
        fecha_constitucion=date(2026, 2, 1),
        usuario="admin-test",
    )

    assert garantia.prestamo_id == prestamo_id
    assert garantia.garante_id == garante
    assert garantia.estado == "ACTIVA"
    assert garantia.monto_maximo == Decimal("75000.00")
    assert "GARANTE" in personas.roles(garante)

    ledger_despues = db.consultar(
        """
        SELECT id, entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
               correlacion_id
        FROM ledger WHERE entidad = 'PRESTAMO' AND entidad_id = ?
        ORDER BY id
        """,
        (prestamo_id,),
    )
    pagos_despues = db.consultar(
        "SELECT id, prestamo_id, monto_moneda_pago, estado FROM pagos "
        "WHERE prestamo_id = ? ORDER BY id",
        (prestamo_id,),
    )
    deuda_despues = db.consultar_uno(
        "SELECT capital_original, estado FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )
    assert ledger_despues == ledger_antes
    assert pagos_despues == pagos_antes
    assert deuda_despues == deuda_antes

    eventos = db.consultar(
        """
        SELECT operacion, usuario
        FROM auditoria
        WHERE entidad = 'GARANTIA_PRESTAMO' AND entidad_id = ?
        """,
        (garantia.id,),
    )
    assert any(
        fila["operacion"] == "GARANTIA_PERSONAL_CONSTITUIDA"
        and fila["usuario"] == "admin-test"
        for fila in eventos
    )
    assert servicio.por_prestamo(prestamo_id) == (garantia,)
    assert servicio.por_garante(garante) == (garantia,)


def test_garantia_unica_activa_se_libera_con_historial_y_puede_reconstituirse(
    db: BaseDatos,
):
    personas = ServicioPersonas(db)
    deudor = _persona(personas, "Deudor", "DEUDOR")
    inversor = _persona(personas, "Inversor", "INVERSOR")
    garante = _persona(personas, "Garante")
    prestamo_id = _prestamo(db, deudor, inversor, "Garantía repetible")
    servicio = ServicioGarantiasPrestamo(db)

    primera = servicio.crear(
        prestamo_id=prestamo_id,
        garante_id=garante,
        alcance="Garantía inicial.",
        usuario="admin-test",
    )
    assert primera.monto_maximo is None

    with pytest.raises(ValueError, match="garantía activa"):
        servicio.crear(
            prestamo_id=prestamo_id,
            garante_id=garante,
            alcance="Intento duplicado.",
            usuario="admin-test",
        )

    with pytest.raises(ValueError, match="motivo"):
        servicio.finalizar(
            garantia_id=primera.id,
            usuario="admin-test",
            motivo=" ",
        )

    liberada = servicio.finalizar(
        garantia_id=primera.id,
        usuario="admin-test",
        motivo="La obligación garantizada fue reemplazada por otro acuerdo.",
    )
    assert liberada is not None
    assert liberada.estado == "LIBERADA"
    assert liberada.fecha_fin == date.today()
    assert liberada.motivo_fin

    segunda = servicio.crear(
        prestamo_id=prestamo_id,
        garante_id=garante,
        alcance="Nueva constitución posterior.",
        usuario="admin-test",
    )
    assert segunda.id != primera.id
    historia = servicio.por_prestamo(prestamo_id)
    assert {g.id for g in historia} == {primera.id, segunda.id}
    assert next(g for g in historia if g.id == primera.id).estado == "LIBERADA"
    assert next(g for g in historia if g.id == segunda.id).estado == "ACTIVA"

    with pytest.raises(ValueError, match="garantías activas"):
        personas.quitar_rol(garante, "GARANTE", motivo="No corresponde retirarlo aún.")


def test_no_se_puede_garantizar_propio_prestamo_ni_usar_personas_inactivas(
    db: BaseDatos,
):
    personas = ServicioPersonas(db)
    deudor = _persona(personas, "Deudor", "DEUDOR")
    inversor = _persona(personas, "Inversor", "INVERSOR")
    garante = _persona(personas, "Garante")
    prestamo_id = _prestamo(db, deudor, inversor, "Validación de garantías")
    servicio = ServicioGarantiasPrestamo(db)

    with pytest.raises(ValueError, match="propio préstamo"):
        servicio.crear(
            prestamo_id=prestamo_id,
            garante_id=deudor,
            alcance="No válido.",
            usuario="admin-test",
        )

    personas.cambiar_estado(garante, "INACTIVO")
    with pytest.raises(ValueError, match="inactiva"):
        servicio.crear(
            prestamo_id=prestamo_id,
            garante_id=garante,
            alcance="No válido para persona inactiva.",
            usuario="admin-test",
        )

    with db.transaccion():
        db.ejecutar(
            "UPDATE prestamos SET estado = 'CANCELADO' WHERE id = ?",
            (prestamo_id,),
        )
    persona_activa = _persona(personas, "Otra garante", "GARANTE")
    with pytest.raises(ValueError, match="préstamo cancelado"):
        servicio.crear(
            prestamo_id=prestamo_id,
            garante_id=persona_activa,
            alcance="No válido en préstamo cerrado.",
            usuario="admin-test",
        )


def test_una_persona_puede_ser_deudora_inversora_y_garante_en_distintas_operaciones(
    db: BaseDatos,
):
    personas = ServicioPersonas(db)
    polifuncional = _persona(
        personas,
        "Persona Polifuncional",
        "DEUDOR",
        "INVERSOR",
        "GARANTE",
    )
    inversor_a = _persona(personas, "Inversor A", "INVERSOR")
    deudor_b = _persona(personas, "Deudor B", "DEUDOR")
    deudor_c = _persona(personas, "Deudor C", "DEUDOR")
    inversor_c = _persona(personas, "Inversor C", "INVERSOR")

    prestamo_deuda = _prestamo(db, polifuncional, inversor_a, "Deuda")
    prestamo_inversion = _prestamo(db, deudor_b, polifuncional, "Inversión")
    prestamo_garantia = _prestamo(db, deudor_c, inversor_c, "Garantía")

    garantia = ServicioGarantiasPrestamo(db).crear(
        prestamo_id=prestamo_garantia,
        garante_id=polifuncional,
        alcance="Garantía asociada a la tercera operación.",
        usuario="admin-test",
    )

    assert set(personas.roles(polifuncional)) == {"DEUDOR", "INVERSOR", "GARANTE"}
    relaciones = personas.prestamos_de(polifuncional)
    por_rol = {relacion.rol: relacion for relacion in relaciones}
    assert set(por_rol) == {"DEUDOR", "INVERSOR", "GARANTE"}
    assert por_rol["DEUDOR"].prestamo_id == prestamo_deuda
    assert por_rol["INVERSOR"].prestamo_id == prestamo_inversion
    assert por_rol["GARANTE"].prestamo_id == prestamo_garantia
    assert por_rol["GARANTE"].monto is None
    assert garantia.estado == "ACTIVA"


def test_no_se_puede_asignar_admin_como_rol_financiero_nuevo(db: BaseDatos):
    personas = ServicioPersonas(db)
    with pytest.raises(ValueError, match="ADMIN es un rol histórico"):
        personas.crear(nombre="Prueba", roles=("ADMIN",))

    persona_id = personas.crear(nombre="Persona actual", roles=("DEUDOR",))
    # Simula una fila heredada creada con la regla histórica de la v001.
    db.ejecutar(
        """
        INSERT INTO roles_persona (persona_id, rol, fecha_alta)
        VALUES (?, 'ADMIN', '2026-01-01')
        """,
        (persona_id,),
    )
    assert "ADMIN" in personas.roles(persona_id)
    with pytest.raises(ValueError, match="motivo"):
        personas.quitar_rol(persona_id, "ADMIN")
    personas.quitar_rol(persona_id, "ADMIN", motivo="Limpieza explícita del rol legado.")
    assert "ADMIN" not in personas.roles(persona_id)
