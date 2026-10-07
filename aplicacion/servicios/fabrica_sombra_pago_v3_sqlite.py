"""Factory for the real SQLite SOMBRA flow."""

from __future__ import annotations

from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from aplicacion.servicios.sombra_pago_v3_sqlite import crear_sombra_pago_v3_sqlite
from aplicacion.servicios.pagos import ServicioPagos
from infraestructura.consultas.comparador_sombra_pago_v3 import (
    ComparadorSombraPagoSQLite,
)
from infraestructura.repositorios.observaciones_sombra_v3 import (
    ObservacionesSombraV3Repo,
)


def crear_puente_sombra_pago_v3_sqlite(db):
    """Builds the non-blocking Legacy + V3 shadow flow over one SQLite DB."""
    sombra = crear_sombra_pago_v3_sqlite(db)
    comparador = ComparadorSombraPagoSQLite(db)
    observaciones = ObservacionesSombraV3Repo(db)
    legacy = ServicioPagos(db)

    def registrar_legacy(command):
        return legacy.registrar_pago(
            prestamo_id=command.prestamo_id,
            monto=command.monto,
            fecha_real=command.fecha_real,
            usuario=command.usuario,
            medio=command.medio,
            referencia=command.referencia,
            nota=command.nota,
            opcion_adelanto=command.opcion_adelanto,
        )

    return PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=registrar_legacy,
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=comparador.comparar,
        observar_divergencia=observaciones.registrar,
    )
