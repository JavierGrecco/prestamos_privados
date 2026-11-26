"""Pruebas de cobros futuros fechados y escenarios de demora."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion.consultas.analisis_financiero import FlujoCajaFinanciero
from aplicacion.consultas.cobros_futuros_persona import (
    CobrosFuturosPersonaQuery,
    EstadoCobroEnEscenario,
)
from infraestructura import BaseDatos
from infraestructura.composicion.analisis_financiero import (
    crear_servicio_cobros_futuros_persona,
)
from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


CORTE = date(2026, 10, 8)


class _Personas:
    def __init__(self, existentes=(7,)) -> None:
        self._existentes = set(existentes)

    def existe(self, persona_id: int) -> bool:
        return persona_id in self._existentes


class _Analisis:
    def __init__(self, flujos) -> None:
        self._flujos = tuple(flujos)
        self.ultima_fecha_corte = None

    def obtener(self, persona_id, *, fecha_corte=None):
        self.ultima_fecha_corte = fecha_corte
        return SimpleNamespace(flujos_proyectados=self._flujos)


def _flujo(
    fecha: date,
    monto: str,
    *,
    rol: str = "inversor",
    real: bool = False,
    prestamo_id: int = 1,
    numero: str = "PP-0001",
) -> FlujoCajaFinanciero:
    return FlujoCajaFinanciero(
        fecha=fecha,
        monto_ars=Decimal(monto),
        tipo="COBRO_PROYECTADO" if not real else "COBRO",
        origen="PROYECCION_CONTRACTUAL" if not real else "REAL",
        rol=rol,
        prestamo_id=prestamo_id,
        prestamo_numero=numero,
        real=real,
    )


def test_usa_flujos_del_inversor_por_fecha_y_excluye_otros_movimientos():
    flujos = (
        _flujo(date(2026, 11, 8), "125000.00"),
        _flujo(date(2026, 12, 8), "130000.00", prestamo_id=2, numero="PP-0002"),
        _flujo(date(2026, 11, 8), "-50000.00", rol="deudor"),
        _flujo(date(2026, 11, 8), "90000.00", real=True),
        _flujo(date(2026, 10, 1), "70000.00"),
        _flujo(date(2028, 1, 1), "80000.00"),
    )
    analisis = _Analisis(flujos)
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=analisis,
    )

    resultado = consulta.obtener(7, fecha_corte=CORTE)

    assert analisis.ultima_fecha_corte == CORTE
    assert [c.fecha_prevista for c in resultado.cobros] == [
        date(2026, 11, 8),
        date(2026, 12, 8),
    ]
    assert resultado.total_previsto_ars == Decimal("255000.00")
    assert resultado.total_en_escenario_ars == Decimal("255000.00")
    assert resultado.cantidad_cobros == 2
    assert resultado.cantidad_en_escenario == 2


def test_simula_demora_de_30_dias_sin_mover_el_vencimiento_original():
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=_Analisis(
            (
                _flujo(date(2026, 11, 8), "100000.00"),
                _flujo(date(2026, 12, 8), "50000.00", prestamo_id=2),
            )
        ),
    )

    resultado = consulta.obtener(
        7,
        fecha_corte=CORTE,
        demora_dias=30,
    )

    assert resultado.cobros[0].fecha_prevista == date(2026, 11, 8)
    assert resultado.cobros[0].fecha_escenario == date(2026, 12, 8)
    assert resultado.cobros[0].estado_escenario is EstadoCobroEnEscenario.EN_HORIZONTE
    assert resultado.total_previsto_ars == Decimal("150000.00")
    assert resultado.total_en_escenario_ars == Decimal("150000.00")


def test_cobro_que_se_mueve_mas_alla_del_horizonte_no_se_cuenta_como_disponible():
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=_Analisis(
            (_flujo(date(2027, 10, 1), "80000.00"),)
        ),
    )

    resultado = consulta.obtener(
        7,
        fecha_corte=CORTE,
        horizonte_dias=365,
        demora_dias=60,
    )

    assert resultado.cantidad_cobros == 1
    assert resultado.cobros[0].estado_escenario is (
        EstadoCobroEnEscenario.FUERA_DEL_HORIZONTE
    )
    assert resultado.total_previsto_ars == Decimal("80000.00")
    assert resultado.total_en_escenario_ars == Decimal("0.00")
    assert resultado.total_fuera_del_horizonte_ars == Decimal("80000.00")


def test_escenario_sin_cobros_no_suma_entradas_proyectadas():
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=_Analisis(
            (
                _flujo(date(2026, 11, 8), "100000.00"),
                _flujo(date(2026, 12, 8), "50000.00", prestamo_id=2),
            )
        ),
    )

    resultado = consulta.obtener(
        7,
        fecha_corte=CORTE,
        demora_dias=None,
    )

    assert resultado.total_previsto_ars == Decimal("150000.00")
    assert resultado.total_en_escenario_ars == Decimal("0.00")
    assert resultado.total_no_recibido_ars == Decimal("150000.00")
    assert all(
        cobro.estado_escenario is EstadoCobroEnEscenario.NO_RECIBIDO
        and cobro.fecha_escenario is None
        for cobro in resultado.cobros
    )


def test_no_existe_una_segunda_fuente_de_calculo_de_cuotas_en_el_read_model():
    class AnalisisConUnaSolaLectura(_Analisis):
        def __init__(self, flujos):
            super().__init__(flujos)
            self.llamadas = 0

        def obtener(self, persona_id, *, fecha_corte=None):
            self.llamadas += 1
            return super().obtener(persona_id, fecha_corte=fecha_corte)

    analisis = AnalisisConUnaSolaLectura(
        (_flujo(date(2026, 11, 8), "100000.00"),)
    )
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=analisis,
    )

    consulta.obtener(7, fecha_corte=CORTE)

    assert analisis.llamadas == 1


@pytest.mark.parametrize("horizonte", [0, -1, 1096, True, 1.5])
def test_rechaza_horizonte_invalido(horizonte):
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=_Analisis(()),
    )

    with pytest.raises(ValueError, match="horizonte_dias"):
        consulta.obtener(7, fecha_corte=CORTE, horizonte_dias=horizonte)


@pytest.mark.parametrize("demora", [-1, 366, True, 1.5])
def test_rechaza_demora_invalida(demora):
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(),
        analisis=_Analisis(()),
    )

    with pytest.raises(ValueError, match="demora_dias"):
        consulta.obtener(7, fecha_corte=CORTE, demora_dias=demora)


def test_rechaza_persona_inexistente():
    consulta = CobrosFuturosPersonaQuery(
        personas=_Personas(existentes=()),
        analisis=_Analisis(()),
    )

    with pytest.raises(ValueError, match="no existe"):
        consulta.obtener(8, fecha_corte=CORTE)


def test_composicion_sqlite_reutiliza_cobros_proyectados_del_inversor(
    tmp_path,
):
    ruta = tmp_path / "cobros_futuros.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor = personas.crear(
            nombre="Deudor",
            apellido="Cobro",
            documento="99110001",
        )
        personas.agregar_rol(deudor, "DEUDOR")
        inversor = personas.crear(
            nombre="Inversor",
            apellido="Cobro",
            documento="99110002",
        )
        personas.agregar_rol(inversor, "INVERSOR")

        crear_servicio_prestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("300000.00"),
            plazo_meses=6,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=CORTE,
            inversores=[{"persona_id": inversor, "monto": Decimal("300000.00")}],
            usuario="test",
            destino="Cobros futuros fechados",
        )

        proyeccion = crear_servicio_cobros_futuros_persona(db).obtener(
            inversor,
            fecha_corte=CORTE,
            horizonte_dias=365,
        )

    assert proyeccion.persona_id == inversor
    assert proyeccion.cantidad_cobros == 6
    assert proyeccion.total_previsto_ars > Decimal("300000.00")
    assert all(
        cobro.origen == "PROYECCION_CONTRACTUAL"
        and cobro.fecha_prevista > CORTE
        for cobro in proyeccion.cobros
    )
