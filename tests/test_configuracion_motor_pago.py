"""Pruebas de la configuración persistente del Motor de Pagos."""

from pathlib import Path

import pytest

from aplicacion.servicios.configuracion_motor_pago import (
    ServicioConfiguracionMotorPago,
)
from aplicacion.servicios.puente_motor_pago_v3 import (
    EjecucionSombraMotorPagoV3,
    ModoMotorPagoV3,
    ResultadoEjecucionSombraV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.configuracion_motor_pago import ConfiguracionMotorPagoRepo
from infraestructura.repositorios.ejecuciones_sombra_v3 import (
    EjecucionesSombraV3Repo,
)


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "motor_mode.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def _sembrar_evidencia_sombra(db, cantidad: int = 100):
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


def test_modo_inicial_es_sombra(db):
    estado = ServicioConfiguracionMotorPago(db).obtener()

    assert estado.modo is ModoMotorPagoV3.SOMBRA
    assert estado.revision == 1


def test_cambio_a_legacy_queda_persistido_y_auditado(db):
    servicio = ServicioConfiguracionMotorPago(db)

    estado = servicio.cambiar(
        nuevo_modo=ModoMotorPagoV3.LEGACY,
        usuario="operador",
        motivo="Rollback operativo",
    )

    assert estado.modo is ModoMotorPagoV3.LEGACY
    assert estado.revision == 2

    fila = AuditoriaRepo(db).por_entidad(
        "CONFIGURACION_MOTOR_PAGO",
        1,
    )[0]
    assert fila.operacion == "MOTOR_PAGO_MODO_CAMBIADO"
    assert fila.motivo == "Rollback operativo"
    assert "SOMBRA" in (fila.datos_anteriores or "")
    assert "LEGACY" in (fila.datos_nuevos or "")


def test_activar_v3_exige_preflight_aprobado(db):
    servicio = ServicioConfiguracionMotorPago(db)

    with pytest.raises(Exception, match="preflight"):
        servicio.cambiar(
            nuevo_modo="V3",
            usuario="operador",
            motivo="Canary",
        )


def test_activar_v3_con_evidencia_suficiente(db):
    _sembrar_evidencia_sombra(db)

    servicio = ServicioConfiguracionMotorPago(db)
    estado = servicio.cambiar(
        nuevo_modo="V3",
        usuario="operador",
        motivo="Canary V3 aprobado",
    )

    assert estado.modo is ModoMotorPagoV3.V3
    assert estado.revision == 2


def test_motivo_obligatorio_y_cambio_concurrente_rechazado(db):
    servicio = ServicioConfiguracionMotorPago(db)

    with pytest.raises(Exception, match="motivo"):
        servicio.cambiar(
            nuevo_modo="LEGACY",
            usuario="operador",
            motivo="",
        )

    fila = ConfiguracionMotorPagoRepo(db).obtener()
    with pytest.raises(Exception, match="concurrentemente"):
        ConfiguracionMotorPagoRepo(db).actualizar(
            modo="LEGACY",
            usuario="operador",
            revision_esperada=fila["revision"] + 100,
        )
