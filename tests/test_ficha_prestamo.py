"""Pruebas de la consulta de lectura para la ficha del préstamo."""
from datetime import date
from decimal import Decimal

from aplicacion.consultas.ficha_prestamo import (
    PagoFicha,
    PrestamoFicha,
    TasaActivaFicha,
    ConsultaFichaPrestamo,
)
from infraestructura import BaseDatos
from infraestructura.composicion.ficha_prestamo import (
    crear_consulta_ficha_prestamo,
)
from infraestructura.composicion.personas import crear_servicio_personas
from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PagoRepo


def _prestamo() -> PrestamoFicha:
    return PrestamoFicha(
        id=12,
        numero="PR-000012",
        deudor_id=4,
        capital_original=Decimal("120000.00"),
        plazo_meses=12,
        sistema="FRANCES",
        fecha_inicio=date(2026, 1, 15),
        estado="ACTIVO",
        destino="Auto",
    )


class _FuenteFichaPrueba:
    def __init__(self):
        self.prestamo = _prestamo()
        self.tasa = TasaActivaFicha(Decimal("0.24"), "TNA")
        self.pagos = (
            PagoFicha("VALIDA", date(2026, 1, 31), Decimal("100.00"), "CUOTA", "Transferencia", "Pago 1"),
            PagoFicha("ANULADA", date(2026, 2, 28), Decimal("200.00"), "CUOTA", "Efectivo", "Anulado"),
            PagoFicha("VALIDA", date(2026, 3, 31), Decimal("300.00"), "ADELANTO_RAI", None, None),
        )
        self.consultas = []

    def obtener_prestamo(self, prestamo_id):
        self.consultas.append(("prestamo", prestamo_id))
        return self.prestamo if prestamo_id == self.prestamo.id else None

    def obtener_tasa_activa(self, prestamo_id):
        self.consultas.append(("tasa", prestamo_id))
        return self.tasa

    def listar_pagos(self, prestamo_id):
        self.consultas.append(("pagos", prestamo_id))
        return self.pagos


def test_ficha_filtra_solo_pagos_validos_y_conserva_el_orden():
    fuente = _FuenteFichaPrueba()

    ficha = ConsultaFichaPrestamo(fuente).obtener(12)

    assert ficha is not None
    assert ficha.prestamo == _prestamo()
    assert ficha.tasa_activa == TasaActivaFicha(Decimal("0.24"), "TNA")
    assert [p.nota for p in ficha.pagos_validos] == ["Pago 1", None]
    assert [p.estado for p in ficha.pagos_validos] == ["VALIDA", "VALIDA"]
    assert [p.fecha_real for p in ficha.pagos_validos] == [
        date(2026, 1, 31),
        date(2026, 3, 31),
    ]
    assert fuente.consultas == [
        ("prestamo", 12),
        ("tasa", 12),
        ("pagos", 12),
    ]


def test_ficha_inexistente_no_consulta_tasa_ni_pagos():
    fuente = _FuenteFichaPrueba()

    assert ConsultaFichaPrestamo(fuente).obtener(999) is None
    assert fuente.consultas == [("prestamo", 999)]


def test_fabrica_sqlite_devuelve_tasa_y_solo_pagos_validos(tmp_path):
    """Verifica contrato, repositorios y orden contra una base SQLite aislada."""
    with BaseDatos(tmp_path / "ficha_prestamo.db") as db:
        aplicar_migraciones(db)
        personas = crear_servicio_personas(db)
        deudor = personas.crear(
            nombre="Deudor ficha",
            roles=("DEUDOR", "INVERSOR"),
        )
        inversor = personas.crear(
            nombre="Inversor ficha",
            roles=("INVERSOR",),
        )
        prestamos = crear_servicio_prestamos(db)
        prestamo_id = prestamos.crear_completo(
            deudor_id=deudor,
            capital=Decimal("120000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 15),
            inversores=[
                {"persona_id": inversor, "monto": Decimal("120000.00")}
            ],
            usuario="test",
            destino="Auto",
        )
        pagos = PagoRepo(db)
        temprano = pagos.registrar(
            prestamo_id,
            date(2026, 1, 31),
            Decimal("100.00"),
            [{"cuota_id": None, "concepto": "INTERES", "monto": Decimal("100.00")}],
            medio="Transferencia",
            nota="Temprano",
        )
        pagos.registrar(
            prestamo_id,
            date(2026, 2, 28),
            Decimal("200.00"),
            [{"cuota_id": None, "concepto": "INTERES", "monto": Decimal("200.00")}],
            medio="Efectivo",
            nota="Anulado",
        )
        pagos.anular(pagos.por_prestamo(prestamo_id)[-1].id, "Prueba de lectura")

        ficha = crear_consulta_ficha_prestamo(db).obtener(prestamo_id)

        assert ficha is not None
        assert ficha.prestamo.id == prestamo_id
        assert ficha.prestamo.deudor_id == deudor
        assert ficha.prestamo.destino == "Auto"
        assert ficha.tasa_activa is not None
        assert ficha.tasa_activa.tasa_anual == Decimal("0.24")
        assert ficha.tasa_activa.modalidad_tasa == "TNA"
        assert [p.nota for p in ficha.pagos_validos] == ["Temprano"]
