"""Pruebas de la consulta de estado de cuotas con arrastre."""
import ast
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from aplicacion.consultas.estado_cuotas_con_arrastre import (
    ConsultaEstadoCuotasConArrastre,
)
from dominio import PoliticaImputacionPago

ROOT = Path(__file__).resolve().parents[1]


def _cuota(
    numero: int,
    *,
    estado: str,
    vencimiento: date,
    cuota: str,
    interes: str,
    capital: str,
    saldo: str,
    capital_pendiente: str = "0.00",
    interes_pendiente: str = "0.00",
    mora_pendiente: str = "0.00",
    tuvo_pago_parcial: bool = False,
    fue_recalculada: bool = False,
):
    return SimpleNamespace(
        numero=numero,
        fecha_vencimiento=vencimiento,
        estado=estado,
        cuota=Decimal(cuota),
        interes=Decimal(interes),
        capital=Decimal(capital),
        saldo=Decimal(saldo),
        capital_pendiente=Decimal(capital_pendiente),
        interes_pendiente=Decimal(interes_pendiente),
        mora_pendiente=Decimal(mora_pendiente),
        tuvo_pago_parcial=tuvo_pago_parcial,
        fue_recalculada=fue_recalculada,
    )


class _PrestamosLecturaFalsos:
    def __init__(self, *, version_id=1, info_tasa=None, cuotas=()):
        self.version_id = version_id
        self.info_tasa = info_tasa or {
            "tasa_anual": Decimal("0.24"),
            "modalidad": "TNA",
        }
        self.items = tuple(cuotas)
        self.versiones_consultadas = []
        self.tasas_consultadas = []
        self.cuotas_consultadas = []

    def version_activa(self, prestamo_id):
        self.versiones_consultadas.append(prestamo_id)
        return self.version_id

    def info_tasa_activa(self, prestamo_id):
        self.tasas_consultadas.append(prestamo_id)
        return self.info_tasa

    def cuotas(self, version_id):
        self.cuotas_consultadas.append(version_id)
        return self.items


class _PoliticasLecturaFalsas:
    def __init__(self, politica):
        self.politica = politica
        self.consultas = []

    def obtener_vigente(self, prestamo_id, fecha=None):
        self.consultas.append((prestamo_id, fecha))
        return self.politica


def test_sin_version_activa_no_consulta_tasa_ni_politica():
    prestamos = _PrestamosLecturaFalsos(version_id=None)
    politicas = _PoliticasLecturaFalsas(PoliticaImputacionPago.canonica())

    resultado = ConsultaEstadoCuotasConArrastre(prestamos, politicas).obtener(
        12, date(2026, 2, 1)
    )

    assert resultado == []
    assert prestamos.tasas_consultadas == []
    assert politicas.consultas == []


def test_sin_tasa_activa_no_consulta_politica():
    prestamos = _PrestamosLecturaFalsos()
    prestamos.info_tasa = None
    politicas = _PoliticasLecturaFalsas(PoliticaImputacionPago.canonica())

    resultado = ConsultaEstadoCuotasConArrastre(prestamos, politicas).obtener(
        12, date(2026, 2, 1)
    )

    assert resultado == []
    assert politicas.consultas == []


def test_conserva_formato_y_calcula_arrastre_de_la_proxima_cuota():
    cuotas = (
        _cuota(
            1,
            estado="PARCIAL",
            vencimiento=date(2026, 1, 1),
            cuota="100.00",
            interes="20.00",
            capital="80.00",
            saldo="920.00",
            capital_pendiente="30.00",
            interes_pendiente="5.00",
            mora_pendiente="2.00",
            tuvo_pago_parcial=True,
        ),
        _cuota(
            2,
            estado="PENDIENTE",
            vencimiento=date(2026, 3, 1),
            cuota="120.00",
            interes="20.00",
            capital="100.00",
            saldo="800.00",
        ),
        _cuota(
            3,
            estado="PENDIENTE",
            vencimiento=date(2026, 4, 1),
            cuota="115.00",
            interes="15.00",
            capital="100.00",
            saldo="700.00",
            fue_recalculada=True,
        ),
    )
    politica = replace(
        PoliticaImputacionPago.canonica(),
        mora_habilitada=False,
    )
    prestamos = _PrestamosLecturaFalsos(cuotas=cuotas)
    politicas = _PoliticasLecturaFalsas(politica)

    resultado = ConsultaEstadoCuotasConArrastre(prestamos, politicas).obtener(
        12, date(2026, 2, 15)
    )

    assert len(resultado) == 3
    assert resultado[0]["monto_real"] == Decimal("100.00")
    assert resultado[0]["desglose"] is None
    assert resultado[0]["tuvo_pago_parcial"] is True

    proxima = resultado[1]
    assert proxima["es_proxima"] is True
    assert proxima["monto_real"] == Decimal("157.60")
    assert proxima["desglose"] == {
        "cuota_teorica": Decimal("120.00"),
        "arrastre_capital": Decimal("30.00"),
        "arrastre_interes": Decimal("5.00"),
        "arrastre_mora": Decimal("2.00"),
        "interes_extra": Decimal("0.60"),
        "mora_nueva": Decimal("0.00"),
    }
    assert resultado[2]["es_proxima"] is False
    assert resultado[2]["fue_recalculada"] is True
    assert politicas.consultas == [(12, date(2026, 2, 15))]


def test_calcula_mora_solo_si_la_proxima_cuota_esta_vencida():
    cuota = _cuota(
        1,
        estado="PENDIENTE",
        vencimiento=date(2026, 1, 1),
        cuota="100.00",
        interes="20.00",
        capital="80.00",
        saldo="920.00",
    )
    prestamos = _PrestamosLecturaFalsos(cuotas=(cuota,))
    politicas = _PoliticasLecturaFalsas(PoliticaImputacionPago.canonica())

    resultado = ConsultaEstadoCuotasConArrastre(prestamos, politicas).obtener(
        12, date(2026, 2, 1)
    )

    desglose = resultado[0]["desglose"]
    assert desglose is not None
    assert desglose["mora_nueva"] > 0
    assert resultado[0]["monto_real"] == (
        cuota.cuota
        + desglose["arrastre_capital"]
        + desglose["arrastre_interes"]
        + desglose["arrastre_mora"]
        + desglose["interes_extra"]
        + desglose["mora_nueva"]
    )


def test_sin_cuotas_pendientes_no_marca_una_proxima():
    cuotas = (
        _cuota(
            1,
            estado="PAGADA",
            vencimiento=date(2026, 1, 1),
            cuota="100.00",
            interes="20.00",
            capital="80.00",
            saldo="0.00",
        ),
    )
    consulta = ConsultaEstadoCuotasConArrastre(
        _PrestamosLecturaFalsos(cuotas=cuotas),
        _PoliticasLecturaFalsas(PoliticaImputacionPago.canonica()),
    )

    resultado = consulta.obtener(12, date(2026, 2, 1))

    assert len(resultado) == 1
    assert resultado[0]["es_proxima"] is False
    assert resultado[0]["monto_real"] == Decimal("100.00")


def test_consulta_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "estado_cuotas_con_arrastre.py"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", maxsplit=1)[0] in {
                "infraestructura",
                "sqlite3",
            }:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert problemas == [], "\n".join(problemas)


def test_fachada_legacy_delega_su_api_publica_a_la_consulta():
    archivo = ROOT / "aplicacion" / "servicios" / "pagos.py"
    fuente = archivo.read_text(encoding="utf-8")
    assert "self._consulta_estado_cuotas_con_arrastre = ConsultaEstadoCuotasConArrastre(" in fuente
    assert "return self._consulta_estado_cuotas_con_arrastre.obtener(" in fuente
