"""Pruebas de la simulación de adelanto Legacy sin usar SQLite."""
import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from aplicacion.consultas.simulacion_adelanto_legacy import (
    ConsultaSimulacionAdelantoLegacy,
)

ROOT = Path(__file__).resolve().parents[1]


def _cuota(
    cuota_id: int,
    estado: str,
    vencimiento: date,
    saldo: str,
    importe_cuota: str,
    interes: str,
):
    return SimpleNamespace(
        id=cuota_id,
        estado=estado,
        fecha_vencimiento=vencimiento,
        saldo=Decimal(saldo),
        cuota=Decimal(importe_cuota),
        interes=Decimal(interes),
    )


class _PrestamosFalsos:
    def __init__(self, cuotas, info_tasa=None):
        self._cuotas = tuple(cuotas)
        self._info_tasa = info_tasa or {
            "tasa_anual": Decimal("0.24"),
            "modalidad": "TNA",
        }
        self.versiones_consultadas = []
        self.tasas_consultadas = []
        self.cuotas_consultadas = []

    def version_activa(self, prestamo_id):
        self.versiones_consultadas.append(prestamo_id)
        return 7

    def info_tasa_activa(self, prestamo_id):
        self.tasas_consultadas.append(prestamo_id)
        return self._info_tasa

    def cuotas(self, version_id):
        self.cuotas_consultadas.append(version_id)
        return self._cuotas


def _escenario():
    objetivo = _cuota(
        10, "PENDIENTE", date(2026, 2, 1), "1000.00", "200.00", "50.00"
    )
    siguientes = (
        _cuota(11, "PENDIENTE", date(2026, 3, 1), "800.00", "200.00", "45.00"),
        _cuota(12, "PENDIENTE", date(2026, 4, 1), "600.00", "200.00", "40.00"),
    )
    prestamos = _PrestamosFalsos((objetivo, *siguientes))
    llamadas = []

    def calcular_deuda(prestamo_id, fecha_calculo):
        llamadas.append((prestamo_id, fecha_calculo))
        return {"cuota_objetivo": objetivo}

    return objetivo, siguientes, prestamos, llamadas, calcular_deuda


def test_simula_rai_y_rni_y_conserva_la_forma_de_salida():
    objetivo, siguientes, prestamos, llamadas, calcular_deuda = _escenario()
    consulta = ConsultaSimulacionAdelantoLegacy(prestamos, calcular_deuda)

    resultado = consulta.simular(42, Decimal("250.00"), date(2026, 2, 10))

    assert resultado is not None
    assert resultado["capital_pendiente_actual"] == Decimal("1000.00")
    assert resultado["capital_despues_adelanto"] == Decimal("750.00")
    assert resultado["monto_adelanto"] == Decimal("250.00")
    assert resultado["cuotas_restantes_antes"] == 2
    assert resultado["fecha_ultimo_vencimiento"] == date(2026, 4, 1)
    assert resultado["rai"]["tabla"] is not None
    assert resultado["rai"]["impacto"] is not None
    assert resultado["rni"]["tabla"] is not None
    assert resultado["rni"]["cuotas_nuevas"] is not None
    assert resultado["rni"]["impacto"] is not None
    assert llamadas == [(42, date(2026, 2, 10))]
    assert prestamos.versiones_consultadas == [42]
    assert prestamos.tasas_consultadas == [42]
    assert prestamos.cuotas_consultadas == [7]
    # La simulación consulta los objetos: no altera el cronograma original.
    assert tuple(siguientes) == prestamos._cuotas
    assert objetivo.saldo == Decimal("1000.00")


def test_sin_deuda_no_consulta_el_repositorio():
    prestamos = _PrestamosFalsos(())
    consulta = ConsultaSimulacionAdelantoLegacy(prestamos, lambda *_: None)

    assert consulta.simular(42, Decimal("100.00"), date(2026, 2, 10)) is None
    assert prestamos.versiones_consultadas == []
    assert prestamos.tasas_consultadas == []
    assert prestamos.cuotas_consultadas == []


def test_sin_tasa_activa_devuelve_none():
    objetivo = _cuota(
        10, "PENDIENTE", date(2026, 2, 1), "1000.00", "200.00", "50.00"
    )
    prestamos = _PrestamosFalsos((objetivo,))
    prestamos._info_tasa = None
    consulta = ConsultaSimulacionAdelantoLegacy(
        prestamos, lambda *_: {"cuota_objetivo": objetivo}
    )

    assert consulta.simular(42, Decimal("100.00"), date(2026, 2, 10)) is None
    assert prestamos.cuotas_consultadas == []


def test_sin_cuotas_futuras_devuelve_none():
    objetivo = _cuota(
        10, "PENDIENTE", date(2026, 2, 1), "1000.00", "200.00", "50.00"
    )
    prestamos = _PrestamosFalsos((objetivo,))
    consulta = ConsultaSimulacionAdelantoLegacy(
        prestamos, lambda *_: {"cuota_objetivo": objetivo}
    )

    assert consulta.simular(42, Decimal("100.00"), date(2026, 2, 10)) is None


def test_adelanto_mayor_al_saldo_no_deja_capital_negativo():
    objetivo, _, prestamos, _, calcular_deuda = _escenario()
    consulta = ConsultaSimulacionAdelantoLegacy(prestamos, calcular_deuda)

    resultado = consulta.simular(42, Decimal("1500.00"), date(2026, 2, 10))

    assert resultado is not None
    assert resultado["capital_despues_adelanto"] == Decimal("0.00")


def test_consulta_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "simulacion_adelanto_legacy.py"
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

    assert problemas == [], "\\n".join(problemas)


def test_fachada_publica_delega_simulacion_a_la_consulta():
    archivo = ROOT / "aplicacion" / "servicios" / "pagos.py"
    fuente = archivo.read_text(encoding="utf-8")
    assert "self._consulta_simulacion_adelanto_legacy = ConsultaSimulacionAdelantoLegacy(" in fuente
    assert "return self._consulta_simulacion_adelanto_legacy.simular(" in fuente
