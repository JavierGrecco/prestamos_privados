"""Pruebas de la frontera de pagos consumida por la UI."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.preflight_motor_pago_v3 import (
    CriterioPreflightV3,
    ResultadoPreflightV3,
)
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from dominio.excepciones import ErrorValidacion


class _ConfiguracionStub:
    def obtener(self):
        return SimpleNamespace(modo=ModoMotorPagoV3.LEGACY)

    def cambiar(self, **kwargs):
        return SimpleNamespace(modo=kwargs.get("nuevo_modo"))


class _PreflightStub:
    def evaluar(self):
        return _preflight(True)


def _servicio(*, registrar_legacy=None) -> ServicioRegistroPagoUI:
    """Construye el caso de uso con colaboradores falsos, sin SQLite."""
    if registrar_legacy is None:
        registrar_legacy = lambda **kwargs: 1
    return ServicioRegistroPagoUI(
        configuracion=_ConfiguracionStub(),
        preflight=_PreflightStub(),
        registrar_legacy=registrar_legacy,
        crear_puente_sombra=lambda: None,
        prestamos=object(),
        politicas_pago=object(),
        crear_registrador_v3=lambda **kwargs: None,
    )


def _preflight(apto: bool) -> ResultadoPreflightV3:
    return ResultadoPreflightV3(
        apto=apto,
        criterios=(
            CriterioPreflightV3(
                nombre="test",
                cumplido=apto,
                detalle="prueba",
            ),
        ),
    )


def test_resolver_modo_sin_configuracion_conserva_legacy():
    servicio = _servicio()

    estado = servicio.resolver_modo(None)

    assert estado.decision.modo is ModoMotorPagoV3.LEGACY
    assert estado.preflight is None


def test_resolver_modo_sombra_no_requiere_preflight():
    servicio = _servicio()

    estado = servicio.resolver_modo(ModoMotorPagoV3.SOMBRA)

    assert estado.decision.modo is ModoMotorPagoV3.SOMBRA
    assert estado.preflight is None


def test_v3_exige_preflight_aprobado():
    servicio = _servicio()
    servicio.modo_actual = lambda: ModoMotorPagoV3.V3

    with pytest.raises(ErrorValidacion, match="preflight"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.V3,
            preflight=_preflight(False),
        )


def test_v3_sin_preflight_tambien_es_rechazado():
    servicio = _servicio()
    servicio.modo_actual = lambda: ModoMotorPagoV3.V3

    with pytest.raises(ErrorValidacion, match="preflight"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.V3,
            preflight=None,
        )


def test_crear_command_normaliza_dinero_y_fecha_valor():
    servicio = _servicio()

    command = servicio.crear_command(
        prestamo_id=7,
        monto=Decimal("100.005"),
        fecha_real=date(2026, 10, 8),
        usuario=" admin ",
        medio="Transferencia",
        referencia="ref-1",
        nota=" pago ",
        opcion_adelanto="RAI",
        idempotency_key=" key-1 ",
    )

    assert command.monto == Decimal("100.01")
    assert command.fecha_valor == date(2026, 10, 8)
    assert command.usuario == "admin"
    assert command.idempotency_key == "key-1"


def test_pago_rechaza_modo_obsoleto():
    servicio = _servicio()
    servicio.modo_actual = lambda: ModoMotorPagoV3.SOMBRA

    with pytest.raises(ErrorValidacion, match="cambió desde la pantalla"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.LEGACY,
            preflight=None,
        )


def test_crear_command_conserva_fecha_valor_distinta():
    servicio = _servicio()

    command = servicio.crear_command(
        prestamo_id=7,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 8),
        fecha_valor=date(2026, 10, 9),
        usuario="admin",
        medio="Transferencia",
        referencia="ref-2",
        nota=None,
        opcion_adelanto=None,
        idempotency_key="key-2",
    )

    assert command.fecha_real == date(2026, 10, 8)
    assert command.fecha_valor == date(2026, 10, 9)

def test_legacy_forwarda_clave_y_huella_de_idempotencia():
    from aplicacion.servicios.registro_pago_v3 import fingerprint_command

    capturado = {}

    def registrar_legacy(**kwargs):
        capturado.update(kwargs)
        return 41

    servicio = _servicio(registrar_legacy=registrar_legacy)
    servicio.modo_actual = lambda: ModoMotorPagoV3.LEGACY
    command = servicio.crear_command(
        prestamo_id=7,
        monto=Decimal("250.00"),
        fecha_real=date(2026, 10, 8),
        fecha_valor=date(2026, 10, 9),
        usuario="admin",
        medio="Transferencia",
        referencia="op-42",
        nota="reintento",
        opcion_adelanto=None,
        idempotency_key="intento-pago-42",
    )

    resultado = servicio.registrar(
        command=command,
        modo=ModoMotorPagoV3.LEGACY,
    )

    assert resultado.pago_id == 41
    assert capturado["fecha_real"] == command.fecha_real
    assert capturado["fecha_valor"] == command.fecha_valor
    assert capturado["idempotency_key"] == command.idempotency_key
    assert capturado["idempotency_fingerprint"] == fingerprint_command(command)

def test_error_transaccion_preserva_clave_para_reintento_idempotente(monkeypatch):
    from types import SimpleNamespace
    import ui.pagina_registrar_pago as modulo_pagina
    from infraestructura.excepciones import ErrorTransaccion

    estado = {
        "_confirmar_pago": True,
        "pago_monto": 250.00,
        "pago_fecha": date(2026, 10, 8),
        "pago_fecha_valor": date(2026, 10, 8),
        "pago_medio": "Transferencia",
        "pago_nota": "pago de prueba",
        "pago_idempotency_key": "intento-pago-estable",
    }
    notas = []

    class StreamlitFalso:
        session_state = estado

        @staticmethod
        def rerun():
            return None

    class RegistroPagoFalso:
        def modo_actual(self):
            return ModoMotorPagoV3.LEGACY

        def crear_command(self, **kwargs):
            return SimpleNamespace(**kwargs)

        def registrar(self, **kwargs):
            raise ErrorTransaccion("fallo de persistencia/confirmación")

    monkeypatch.setattr(modulo_pagina, "st", StreamlitFalso())
    monkeypatch.setattr(
        modulo_pagina.componentes,
        "disparar_nota",
        lambda mensaje, tipo="info": notas.append((mensaje, tipo)),
    )
    monkeypatch.setattr(modulo_pagina, "operador_actual", lambda: "admin")

    modulo_pagina._procesar_guardado(
        db=None,
        prestamo_id=7,
        servicio_ui=RegistroPagoFalso(),
    )

    assert estado["pago_idempotency_key"] == "intento-pago-estable"
    assert estado.get("_confirmar_pago") is None
    assert len(notas) == 1
    assert notas[0][1] == "warning"
    assert "no cambies los datos" in notas[0][0]
    assert "clave" in notas[0][0]

def test_conflicto_idempotencia_preserva_clave_y_muestra_pago_anterior(monkeypatch):
    from types import SimpleNamespace
    import ui.pagina_registrar_pago as modulo_pagina
    from aplicacion.servicios import ErrorConflictoIdempotencia

    estado = {
        "_confirmar_pago": True,
        "pago_monto": 250.00,
        "pago_fecha": date(2026, 10, 8),
        "pago_fecha_valor": date(2026, 10, 8),
        "pago_medio": "Transferencia",
        "pago_nota": "pago modificado",
        "pago_idempotency_key": "intento-pago-estable",
    }
    notas = []

    class StreamlitFalso:
        session_state = estado

        @staticmethod
        def rerun():
            return None

    class RegistroPagoFalso:
        def modo_actual(self):
            return ModoMotorPagoV3.LEGACY

        def crear_command(self, **kwargs):
            return SimpleNamespace(**kwargs)

        def registrar(self, **kwargs):
            raise ErrorConflictoIdempotencia(
                "La clave ya está asociada a otro contenido",
                pago_existente_id=41,
            )

    monkeypatch.setattr(modulo_pagina, "st", StreamlitFalso())
    monkeypatch.setattr(
        modulo_pagina.componentes,
        "disparar_nota",
        lambda mensaje, tipo="info": notas.append((mensaje, tipo)),
    )
    monkeypatch.setattr(modulo_pagina, "operador_actual", lambda: "admin")

    modulo_pagina._procesar_guardado(
        db=None,
        prestamo_id=7,
        servicio_ui=RegistroPagoFalso(),
    )

    assert estado["pago_idempotency_key"] == "intento-pago-estable"
    assert len(notas) == 1
    assert notas[0][1] == "warning"
    assert "pago existente #41" in notas[0][0]
    assert "Revisá el historial" in notas[0][0]

