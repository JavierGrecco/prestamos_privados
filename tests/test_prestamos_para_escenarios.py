"""Pruebas de la selección de préstamos que se pueden analizar."""
from datetime import date

from aplicacion.consultas.prestamos_para_escenarios import (
    ParticipacionParaEscenario,
    PrestamoParaEscenario,
    PrestamosParaEscenariosQuery,
)


class _ConsultaDePrueba:
    def __init__(self):
        self.deudor = (
            PrestamoParaEscenario(
                1, "PR-000001", "ACTIVO", date(2026, 1, 1), "Auto"
            ),
            PrestamoParaEscenario(
                2, "PR-000002", "EN_MORA", date(2026, 3, 1), "Reparación"
            ),
            PrestamoParaEscenario(
                3, "PR-000003", "FINALIZADO", date(2026, 5, 1), "Terminado"
            ),
        )
        self.participaciones = (
            ParticipacionParaEscenario(1, "ACTIVA"),
            ParticipacionParaEscenario(4, "ACTIVA"),
            ParticipacionParaEscenario(5, "ACTIVA"),
            ParticipacionParaEscenario(6, "ANULADA"),
            ParticipacionParaEscenario(7, "ACTIVA"),
        )
        self.por_id = {
            4: PrestamoParaEscenario(
                4, "PR-000004", "ACTIVO", date(2026, 4, 1), "Capital de trabajo"
            ),
            5: PrestamoParaEscenario(
                5, "PR-000005", "CANCELADO", date(2026, 6, 1), "Cancelado"
            ),
            7: None,
        }
        self.personas_consultadas = []

    def prestamos_por_deudor(self, persona_id):
        self.personas_consultadas.append(("deudor", persona_id))
        return self.deudor

    def participaciones_por_inversor(self, persona_id):
        self.personas_consultadas.append(("inversor", persona_id))
        return self.participaciones

    def prestamo_por_id(self, prestamo_id):
        self.personas_consultadas.append(("prestamo", prestamo_id))
        return self.por_id.get(prestamo_id)


def test_incluye_deuda_y_inversion_activa_sin_duplicados_y_ordenada():
    consulta = _ConsultaDePrueba()
    servicio = PrestamosParaEscenariosQuery(consulta)

    resultado = servicio.activos_para_persona(42)

    assert [prestamo.id for prestamo in resultado] == [4, 2, 1]
    assert [prestamo.numero for prestamo in resultado] == [
        "PR-000004",
        "PR-000002",
        "PR-000001",
    ]
    assert consulta.personas_consultadas[:2] == [
        ("deudor", 42),
        ("inversor", 42),
    ]


def test_prestamo_activo_sin_fecha_queda_despues_de_los_que_tienen_fecha():
    consulta = _ConsultaDePrueba()
    consulta.por_id[8] = PrestamoParaEscenario(
        8, "PR-000008", "ACTIVO", None, None
    )
    consulta.participaciones = (
        ParticipacionParaEscenario(8, "ACTIVA"),
    )

    consulta.deudor = ()
    resultado = PrestamosParaEscenariosQuery(consulta).activos_para_persona(42)

    assert [prestamo.id for prestamo in resultado] == [8]
