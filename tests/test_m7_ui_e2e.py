"""Aceptación end-to-end de M7 desde Streamlit."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture
def comparador_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "m7-ui.db"

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor_id = personas.crear(
            nombre="Javier",
            apellido="M7",
            documento="99993001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")
        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="M7",
            documento="99993002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        for numero, capital in ((1, "1100.00"), (2, "1200.00")):
            ServicioPrestamos(db).crear_completo(
                deudor_id=deudor_id,
                capital=Decimal(capital),
                plazo_meses=6,
                tasa_anual=Decimal("0.24"),
                modalidad_tasa="TNA",
                sistema="FRANCES",
                convencion_dias="MENSUAL",
                fecha_inicio=date(2026, 1, 1),
                inversores=[
                    {
                        "persona_id": inversor_id,
                        "monto": Decimal(capital),
                    }
                ],
                usuario="m7-ui-test",
                tc_inicial=Decimal("1500.00"),
                destino=f"Alternativa {numero}",
            )

    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    return ruta


def test_comparador_m7_renderiza_y_ofrece_dos_alternativas(
    comparador_database: Path,
):
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception

    at.segmented_control(key="pagina").set_value("comparar")
    at.run()
    assert not at.exception

    assert at.title[0].value == "Comparar"
    assert len(at.multiselect(key="comparador_alternativas").options) == 2
    assert _contiene_texto(at, "Compará dos o más operaciones")
    assert _contiene_texto(at, "Detalle:")
    assert _contiene_texto(at, "Valor real futuro")


def _contiene_texto(at: AppTest, texto: str) -> bool:
    partes = [str(x.value) for x in at.markdown]
    partes.extend(str(x.value) for x in at.caption)
    partes.extend(str(x.value) for x in at.subheader)
    return any(texto in parte for parte in partes)
