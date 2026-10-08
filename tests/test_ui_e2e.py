    assert at.title[0].value == "Mi espacio"
    assert _markdown_contains(at, "Hola, Javier Prueba")
    assert _markdown_contains(at, "Es el dinero original del préstamo.")


def test_mi_espacio_muestra_posicion_financiera_y_evolucion(
    app_database: Path,
):
    at = _go_to(_run_app(), "mi_espacio")
    assert not at.exception
    assert any(x.value == "Tu posición financiera" for x in at.subheader)
    assert any("No representa todo tu patrimonio" in str(x.value) for x in at.caption)
    assert len(at.plotly_chart) == 1