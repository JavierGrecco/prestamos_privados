"""Pruebas de las proyecciones de impacto de pagos sin usar SQLite."""

import ast
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.impacto_pagos import ConsultaImpactoPagos


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class _Cuota:
    numero: int
    mora_pendiente: Decimal
    fue_mora: bool


@dataclass(frozen=True)
class _Pago:
    estado: str
    tipo_pago: str | None
    fecha_real: date | None
    interes_extra_generado: Decimal
    intereses_ahorrados: Decimal
    monto_a_capital: Decimal


class _LecturaCuotas:
    def __init__(self, version_id=3, cuotas=()):
        self.version_id = version_id
        self.items = tuple(cuotas)
        self.versiones_consultadas = []
        self.versiones_cuotas_consultadas = []

    def version_activa(self, prestamo_id):
        self.versiones_consultadas.append(prestamo_id)
        return self.version_id

    def cuotas(self, version_id):
        self.versiones_cuotas_consultadas.append(version_id)
        return self.items


class _LecturaPagos:
    def __init__(self, pagos=()):
        self.items = tuple(pagos)
        self.prestamos_consultados = []

    def por_prestamo(self, prestamo_id):
        self.prestamos_consultados.append(prestamo_id)
        return self.items


def test_resumen_usa_decimal_y_calcula_costos_ahorros_y_atrasos():
    cuotas = _LecturaCuotas(cuotas=(
        _Cuota(1, Decimal("9.25"), True),
        _Cuota(2, Decimal("0.00"), False),
    ))
    pagos = _LecturaPagos((
        _Pago(
            "VALIDA", "PARCIAL", date(2026, 2, 3),
            Decimal("12.50"), Decimal("0.00"), Decimal("0.00"),
        ),
        _Pago(
            "VALIDA", "ADELANTO_RAI", date(2026, 2, 1),
            Decimal("0.00"), Decimal("8.25"), Decimal("30.00"),
        ),
        # Los pagos anulados no participan en el resumen.
        _Pago(
            "ANULADA", "PARCIAL", date(2026, 2, 4),
            Decimal("999.00"), Decimal("999.00"), Decimal("999.00"),
        ),
    ))
    consulta = ConsultaImpactoPagos(cuotas, pagos)

    resumen = consulta.resumen_impacto_financiero(7)

    assert resumen == {
        "mora_pendiente": Decimal("9.25"),
        "interes_extra_acumulado": Decimal("12.50"),
        "intereses_ahorrados": Decimal("8.25"),
        "capital_adelantado": Decimal("30.00"),
        "cuotas_con_atraso": 1,
        "cuotas_totales": 2,
        "numeros_con_atraso": [1],
        "costos_totales": Decimal("21.75"),
        "ahorros_totales": Decimal("8.25"),
        "sobrecosto_total": Decimal("13.50"),
        "hubo_decisiones": True,
    }
    assert cuotas.versiones_consultadas == [7]
    assert cuotas.versiones_cuotas_consultadas == [3]
    assert pagos.prestamos_consultados == [7]


def test_resumen_vacio_no_consulta_pagos_si_no_hay_version_activa():
    cuotas = _LecturaCuotas(version_id=None)
    pagos = _LecturaPagos()
    consulta = ConsultaImpactoPagos(cuotas, pagos)

    resumen = consulta.resumen_impacto_financiero(12)

    assert resumen["mora_pendiente"] == Decimal("0.00")
    assert resumen["interes_extra_acumulado"] == Decimal("0.00")
    assert resumen["intereses_ahorrados"] == Decimal("0.00")
    assert resumen["capital_adelantado"] == Decimal("0.00")
    assert resumen["cuotas_totales"] == 0
    assert resumen["numeros_con_atraso"] == []
    assert resumen["hubo_decisiones"] is False
    assert pagos.prestamos_consultados == []


def test_historial_filtra_decisiones_sin_impacto_y_ordena_por_fecha():
    cuotas = _LecturaCuotas()
    pagos = _LecturaPagos((
        _Pago(
            "VALIDA", "PARCIAL", date(2026, 2, 3),
            Decimal("12.50"), Decimal("0.00"), Decimal("0.00"),
        ),
        _Pago(
            "VALIDA", "ADELANTO_RAI", date(2026, 2, 1),
            Decimal("0.00"), Decimal("8.25"), Decimal("30.00"),
        ),
        _Pago(
            "VALIDA", "PARCIAL", date(2026, 2, 5),
            Decimal("0.00"), Decimal("0.00"), Decimal("0.00"),
        ),
        _Pago(
            "ANULADA", "ADELANTO_RNI", date(2026, 2, 6),
            Decimal("0.00"), Decimal("999.00"), Decimal("999.00"),
        ),
    ))
    consulta = ConsultaImpactoPagos(cuotas, pagos)

    eventos = consulta.historial_decisiones(7)

    assert [evento["tipo"] for evento in eventos] == [
        "ADELANTO_RAI", "PAGO_PARCIAL"
    ]
    assert eventos[0]["fecha"] == date(2026, 2, 1)
    assert eventos[0]["monto_impacto"] == Decimal("-8.25")
    assert eventos[0]["descripcion"] == "Adelantaste $ 30,00 a capital"
    assert eventos[0]["impacto"] == "Ahorraste $ 8,25 en intereses"
    assert eventos[1]["fecha"] == date(2026, 2, 3)
    assert eventos[1]["monto_impacto"] == Decimal("12.50")
    assert eventos[1]["impacto"] == (
        "Ese monto generó $ 12,50 de interés extra al mes siguiente"
    )


def test_formateador_conserva_notacion_local():
    assert ConsultaImpactoPagos._fmt(Decimal("1234567.8")) == "$ 1.234.567,80"


def test_consulta_de_impacto_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "impacto_pagos.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: {modulo}")

    assert not problemas, (
        "La consulta debe depender de contratos de aplicación, no de infraestructura: "
        + ", ".join(problemas)
    )
    assert "SELECT " not in fuente
    assert "INSERT " not in fuente


def test_servicio_de_pagos_mantiene_fachadas_publicas_para_estas_lecturas():
    archivo = ROOT / "aplicacion" / "servicios" / "pagos.py"
    fuente = archivo.read_text(encoding="utf-8")

    assert "self._consulta_impacto.resumen_impacto_financiero(prestamo_id)" in fuente
    assert "self._consulta_impacto.historial_decisiones(prestamo_id)" in fuente
    assert "self._consulta_impacto = ConsultaImpactoPagos(self.prestamos, self.pagos)" in fuente
