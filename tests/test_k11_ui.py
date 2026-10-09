"""Aceptación de las capacidades de ciclo de vida en la UI."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from streamlit.testing.v1 import AppTest

from aplicacion.servicios import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from tests.ui_auth_helpers import iniciar_apptest_autenticado


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def crear_base(tmp_path):
    ruta = tmp_path / "k11_ui.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = personas.crear(nombre="Deudor", apellido="UI")
        personas.agregar_rol(deudor, "DEUDOR")
        inversor = personas.crear(nombre="Inversor", apellido="UI")
        personas.agregar_rol(inversor, "INVERSOR")
        ServicioPrestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("100000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[{"persona_id": inversor, "monto": Decimal("100000.00")}],
            usuario="test",
        )
    return ruta


def _run(ruta, monkeypatch):
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    at = AppTest.from_file(APP, default_timeout=10)
    return iniciar_apptest_autenticado(at, ruta)


def test_lista_expone_filtro_de_ciclo_de_vida(tmp_path, monkeypatch):
    at = _run(crear_base(tmp_path), monkeypatch)
    at.segmented_control(key="pagina").set_value("prestamos")
    at.run()
    assert not at.exception
    assert at.segmented_control(key="prestamos_estado_filtro").value == "ACTIVOS"

    at.segmented_control(key="prestamos_estado_filtro").set_value("TODOS")
    at.run()
    assert not at.exception


def test_detalle_expone_transiciones_controladas(tmp_path, monkeypatch):
    at = _run(crear_base(tmp_path), monkeypatch)
    at.segmented_control(key="pagina").set_value("prestamos")
    at.run()
    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception

    valores = at.selectbox(key="estado_destino_1").options
    assert "Marcar en mora" in valores
    assert "Finalizar préstamo" in valores
    assert "Cancelar préstamo" in valores
    assert any("Ciclo de vida" in str(m.value) for m in at.markdown)
