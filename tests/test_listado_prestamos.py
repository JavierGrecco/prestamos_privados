"""Pruebas del listado de préstamos y su adaptación SQLite."""
from datetime import date
from decimal import Decimal

from aplicacion.consultas.listado_prestamos import (
    CuotaProximaListado,
    ParticipacionListado,
    PrestamoListado,
    ConsultaListadoPrestamos,
)
from infraestructura import BaseDatos
from infraestructura.composicion.listado_prestamos import (
    crear_consulta_listado_prestamos,
)
from infraestructura.composicion.personas import crear_servicio_personas
from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.migraciones import aplicar_migraciones


def _prestamo(
    prestamo_id: int,
    estado: str,
    *,
    destino: str | None = None,
) -> PrestamoListado:
    return PrestamoListado(
        id=prestamo_id,
        numero=f"PR-{prestamo_id:06d}",
        estado=estado,
        fecha_inicio=date(2026, 1, min(prestamo_id, 28)),
        destino=destino,
        capital_original=Decimal(f"{prestamo_id * 1000}.00"),
    )


class _FuenteDePrueba:
    def __init__(self):
        self.deudor = (
            _prestamo(1, "ACTIVO", destino="Auto"),
            _prestamo(2, "EN_MORA"),
            _prestamo(3, "FINALIZADO"),
            _prestamo(4, "CANCELADO"),
            _prestamo(5, "REFINANCIADO"),
        )
        self.participaciones = (
            ParticipacionListado(1, "ACTIVA", Decimal("500.00")),
            ParticipacionListado(6, "ACTIVA", Decimal("600.00")),
            ParticipacionListado(7, "ACTIVA", Decimal("700.00")),
            ParticipacionListado(8, "ACTIVA", Decimal("800.00")),
            ParticipacionListado(9, "LIBERADA", Decimal("900.00")),
        )
        self.por_id = {
            6: _prestamo(6, "ACTIVO", destino="Vivienda"),
            7: _prestamo(7, "CANCELADO"),
        }
        self.proximas = {
            prestamo_id: CuotaProximaListado(
                "PENDIENTE", date(2026, 11, 1)
            )
            for prestamo_id in (1, 2, 6, 7)
        }
        self.llamadas_cuotas = []

    def prestamos_por_deudor(self, persona_id):
        return self.deudor

    def participaciones_por_inversor(self, persona_id):
        return self.participaciones

    def prestamo_por_id(self, prestamo_id):
        return self.por_id.get(prestamo_id)

    def proxima_cuota(self, prestamo_id):
        self.llamadas_cuotas.append(prestamo_id)
        return self.proximas.get(prestamo_id)


def test_filtro_activos_incluye_mora_y_omite_roles_duplicados():
    fuente = _FuenteDePrueba()

    resultado = ConsultaListadoPrestamos(fuente).por_persona(42, "ACTIVOS")

    assert [item.prestamo.id for item in resultado] == [1, 2, 6]
    assert [item.rol for item in resultado] == ["deudor", "deudor", "inversor"]
    assert [item.monto for item in resultado] == [
        Decimal("1000.00"),
        Decimal("2000.00"),
        Decimal("600.00"),
    ]
    assert [item.proxima_cuota.fecha_vencimiento for item in resultado] == [
        date(2026, 11, 1),
        date(2026, 11, 1),
        date(2026, 11, 1),
    ]
    assert fuente.llamadas_cuotas == [1, 2, 6]


def test_filtros_terminales_y_todos_conservan_los_estados_esperados():
    servicio = ConsultaListadoPrestamos(_FuenteDePrueba())

    assert [i.prestamo.id for i in servicio.por_persona(42, "FINALIZADOS")] == [3]
    assert [i.prestamo.id for i in servicio.por_persona(42, "CANCELADOS")] == [4, 7]
    assert [i.prestamo.id for i in servicio.por_persona(42, "REFINANCIADOS")] == [5]
    assert [i.prestamo.id for i in servicio.por_persona(42, "TODOS")] == [
        1, 2, 3, 4, 5, 6, 7
    ]


def test_fabrica_sqlite_conserva_rol_importe_y_proxima_cuota(tmp_path):
    """Comprueba la composición real contra una base de datos aislada."""
    with BaseDatos(tmp_path / "listado_prestamos.db") as db:
        aplicar_migraciones(db)
        personas = crear_servicio_personas(db)
        persona = personas.crear(
            nombre="Persona con doble rol",
            roles=("DEUDOR", "INVERSOR"),
        )
        otro_inversor = personas.crear(
            nombre="Otro inversor",
            roles=("INVERSOR",),
        )
        otro_deudor = personas.crear(
            nombre="Otro deudor",
            roles=("DEUDOR",),
        )
        prestamos = crear_servicio_prestamos(db)

        como_deudor = prestamos.crear_completo(
            deudor_id=persona,
            capital=Decimal("100000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": otro_inversor, "monto": Decimal("100000.00")}
            ],
            usuario="test",
            destino="Auto",
        )
        como_inversor = prestamos.crear_completo(
            deudor_id=otro_deudor,
            capital=Decimal("90000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 2, 1),
            inversores=[
                {"persona_id": persona, "monto": Decimal("90000.00")}
            ],
            usuario="test",
            destino="Vivienda",
        )

        resultado = crear_consulta_listado_prestamos(db).por_persona(
            persona, "ACTIVOS"
        )

        assert [item.prestamo.id for item in resultado] == [
            como_deudor, como_inversor
        ]
        assert [item.rol for item in resultado] == ["deudor", "inversor"]
        assert [item.monto for item in resultado] == [
            Decimal("100000.00"), Decimal("90000.00")
        ]
        assert all(item.proxima_cuota is not None for item in resultado)
        assert all(
            item.proxima_cuota.estado == "PENDIENTE" for item in resultado
        )
