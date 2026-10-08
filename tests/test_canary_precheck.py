"""Pruebas del precheck operativo de canary V3."""

from pathlib import Path

from aplicacion.servicios.configuracion_motor_pago import ServicioConfiguracionMotorPago
from aplicacion.servicios.puente_motor_pago_v3 import (
    EjecucionSombraMotorPagoV3,
    ResultadoEjecucionSombraV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.ejecuciones_sombra_v3 import EjecucionesSombraV3Repo
from scripts.canary_precheck_motor_pago_v3 import main


def crear_db(path: Path, cantidad: int):
    with BaseDatos(path) as db:
        aplicar_migraciones(db)
        repo = EjecucionesSombraV3Repo(db)
        for i in range(cantidad):
            repo.registrar(
                EjecucionSombraMotorPagoV3(
                    fingerprint=f"fp-{i}",
                    prestamo_id=1,
                    pago_legacy_id=None,
                    resultado=ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
                    revision_snapshot=0,
                    resumen=None,
                )
            )


def test_precheck_no_apto_sin_evidencia(tmp_path, capsys):
    ruta = tmp_path / "canary.db"
    crear_db(ruta, 0)

    codigo = main([str(ruta), "--min-runs", "1"])
    salida = capsys.readouterr().out

    assert codigo == 2
    assert '"listo_para_canary": false' in salida


def test_precheck_apto_con_evidencia_y_sombra_persistida(tmp_path, capsys):
    ruta = tmp_path / "canary.db"
    crear_db(ruta, 100)

    codigo = main([str(ruta), "--min-runs", "100", "--min-match", "1"])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert '"listo_para_canary": true' in salida
    assert '"modo_actual": "SOMBRA"' in salida
    assert '"revision_modo": 1' in salida

    with BaseDatos(ruta) as db:
        antes = db.consultar_uno(
            "SELECT modo, revision FROM configuracion_motor_pago WHERE id = 1"
        )
        ServicioConfiguracionMotorPago(db).obtener()
        despues = db.consultar_uno(
            "SELECT modo, revision FROM configuracion_motor_pago WHERE id = 1"
        )

    assert dict(antes) == dict(despues)


def test_servicio_readiness_reutiliza_la_misma_evaluacion(tmp_path):
    ruta = tmp_path / "canary-service.db"
    crear_db(ruta, 100)

    from decimal import Decimal
    from unittest.mock import patch
    from aplicacion.servicios.precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3

    with BaseDatos(ruta) as db:
        with patch(
            "aplicacion.servicios.preflight_motor_pago_v3.auditar_integridad_v3",
            wraps=__import__("aplicacion.servicios.preflight_motor_pago_v3", fromlist=["auditar_integridad_v3"]).auditar_integridad_v3,
        ) as auditor_integridad:
            from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
            with patch.object(
                ServicioMetricasSombraV3,
                "obtener",
                wraps=ServicioMetricasSombraV3(db).obtener,
            ) as obtener_metricas:
                resultado = ServicioReadinessCanaryV3(
                    db,
                    ejecuciones_minimas=100,
                    tasa_coincidencia_minima=Decimal("1"),
                ).evaluar()

    assert auditor_integridad.call_count == 1
    assert obtener_metricas.call_count == 1

    assert resultado.listo is True
    assert resultado.modo_actual == "SOMBRA"
    assert resultado.integridad_ok is True
    assert resultado.preflight_apto is True
    assert resultado.divergencias == 0
    assert resultado.errores == 0


def test_precheck_puede_guardar_artefacto_json(tmp_path, capsys):
    ruta = tmp_path / "canary.db"
    salida = tmp_path / "evidencia" / "canary-readiness.json"
    crear_db(ruta, 100)

    codigo = main([
        str(ruta),
        "--min-runs", "100",
        "--min-match", "1",
        "--output", str(salida),
    ])

    stdout = capsys.readouterr().out
    assert codigo == 0
    assert salida.exists()

    import json
    contenido = json.loads(salida.read_text(encoding="utf-8"))
    assert contenido["listo_para_canary"] is True
    assert contenido["database"] == str(ruta.resolve())
    assert contenido["evaluated_at"]
    assert stdout == salida.read_text(encoding="utf-8")
