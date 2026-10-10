"""H3: concurrencia e idempotencia del registro de pagos V3.

Las pruebas usan dos conexiones SQLite independientes y sincronización por
Event, sin sleeps, para demostrar serialización de escritores y reintentos
idempotentes.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
import threading

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from aplicacion.servicios.registro_pago_v3 import RegistrarPagoV3
from dominio.excepciones import ErrorInvariante
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)


class _RepositorioBloqueable:
    """Hace visible el lock de escritura para sincronizar la prueba."""

    def __init__(
        self,
        interno: RepositorioRegistroPagoSQLiteV3,
        adquirido: threading.Event,
        liberar: threading.Event,
    ) -> None:
        self._interno = interno
        self._adquirido = adquirido
        self._liberar = liberar

    def __getattr__(self, nombre):
        return getattr(self._interno, nombre)

    def begin(self) -> None:
        self._interno.begin()
        self._adquirido.set()
        if not self._liberar.wait(timeout=10):
            raise RuntimeError("timeout H3 esperando liberación del lock")


class _RepositorioConIntentoDeInicio:
    """Señala que un segundo hilo intenta comenzar el pago."""

    def __init__(
        self,
        interno: RepositorioRegistroPagoSQLiteV3,
        intentando: threading.Event,
        iniciado: threading.Event,
    ) -> None:
        self._interno = interno
        self._intentando = intentando
        self._iniciado = iniciado

    def __getattr__(self, nombre):
        return getattr(self._interno, nombre)

    def begin(self) -> None:
        self._intentando.set()
        self._interno.begin()
        self._iniciado.set()


def _crear_prestamo(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="H3")
    inversor_id = personas.crear(nombre="Inversor", apellido="H3")

    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="h3",
        destino="Escenario H3",
    )


def _command_para_pago(db: BaseDatos, prestamo_id: int, *, key: str, monto=None):
    if monto is None:
        deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
            prestamo_id=prestamo_id,
            fecha_calculo=date(2026, 2, 1),
        )
        assert deuda is not None
        monto = deuda["total_a_pagar"]

    revision = db.consultar_uno(
        "SELECT revision_prestamo FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )["revision_prestamo"]

    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=monto,
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="h3",
        idempotency_key=key,
        revision_prestamo=int(revision),
    )


def _servicio(db: BaseDatos, adquirido=None, liberar=None):
    repo = RepositorioRegistroPagoSQLiteV3(db)
    if adquirido is not None and liberar is not None:
        repo = _RepositorioBloqueable(repo, adquirido, liberar)
    return RegistrarPagoV3(repo)


def _cantidad_pagos(db: BaseDatos, prestamo_id: int) -> int:
    fila = db.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )
    return int(fila["n"])


@pytest.fixture
def ruta_db(tmp_path: Path):
    ruta = tmp_path / "h3.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        _crear_prestamo(db)
    return ruta


def test_h3_dos_comandos_con_misma_revision_serializan_y_uno_es_rechazado(
    ruta_db,
):
    db_preparacion = BaseDatos(ruta_db)
    db_preparacion.abrir()
    try:
        command_a = _command_para_pago(
            db_preparacion, 1, key="H3-REV-A"
        )
        command_b = _command_para_pago(
            db_preparacion, 1, key="H3-REV-B"
        )
    finally:
        db_preparacion.cerrar()

    db_a = BaseDatos(ruta_db)
    db_b = BaseDatos(ruta_db)
    db_lectura = BaseDatos(ruta_db)
    db_a.abrir()
    db_b.abrir()
    db_lectura.abrir()
    adquirido = threading.Event()
    liberar = threading.Event()

    try:
        servicio_a = _servicio(db_a, adquirido, liberar)
        servicio_b = _servicio(db_b)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(servicio_a.ejecutar, command_a)
            assert adquirido.wait(timeout=10)

            futuro_b = executor.submit(servicio_b.ejecutar, command_b)
            liberar.set()

            resultado_a = futuro_a.result(timeout=10)
            assert resultado_a.es_repeticion_idempotente is False

            with pytest.raises(ErrorInvariante, match="Conflicto de revisión"):
                futuro_b.result(timeout=10)

        assert _cantidad_pagos(db_lectura, 1) == 1
    finally:
        liberar.set()
        db_lectura.cerrar()
        db_b.cerrar()
        db_a.cerrar()


def test_h3_reintento_concurrente_misma_idempotency_key_no_duplica_pago(ruta_db):
    db_preparacion = BaseDatos(ruta_db)
    db_preparacion.abrir()
    try:
        command = _command_para_pago(
            db_preparacion, 1, key="H3-IDEMPOTENTE"
        )
    finally:
        db_preparacion.cerrar()

    db_a = BaseDatos(ruta_db)
    db_b = BaseDatos(ruta_db)
    db_lectura = BaseDatos(ruta_db)
    db_a.abrir()
    db_b.abrir()
    db_lectura.abrir()
    adquirido = threading.Event()
    liberar = threading.Event()

    try:
        servicio_a = _servicio(db_a, adquirido, liberar)
        servicio_b = _servicio(db_b)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(servicio_a.ejecutar, command)
            assert adquirido.wait(timeout=10)

            futuro_b = executor.submit(servicio_b.ejecutar, command)
            liberar.set()

            resultado_a = futuro_a.result(timeout=10)
            resultado_b = futuro_b.result(timeout=10)

        assert resultado_a.es_repeticion_idempotente is False
        assert resultado_b.es_repeticion_idempotente is True
        assert resultado_b.pago_id == resultado_a.pago_id
        assert _cantidad_pagos(db_lectura, 1) == 1
    finally:
        liberar.set()
        db_lectura.cerrar()
        db_b.cerrar()
        db_a.cerrar()


def test_h3_misma_idempotency_key_con_payload_diferente_es_rechazada_sin_mutar(
    ruta_db,
):
    db = BaseDatos(ruta_db)
    db.abrir()
    try:
        command = _command_para_pago(
            db, 1, key="H3-PAYLOAD"
        )
        servicio = _servicio(db)

        primero = servicio.ejecutar(command)
        pagos_antes = _cantidad_pagos(db, 1)

        comando_distinto = _command_para_pago(
            db,
            1,
            key="H3-PAYLOAD",
            monto=command.monto + Decimal("1.00"),
        )

        with pytest.raises(
            ErrorInvariante,
            match="payload diferente",
        ):
            servicio.ejecutar(comando_distinto)

        assert pagos_antes == 1
        assert _cantidad_pagos(db, 1) == 1
        assert primero.pago_id > 0
    finally:
        db.cerrar()

def test_h3_dos_pagos_concurrentes_serializan_una_base_datos_compartida(
    ruta_db,
):
    """La UI puede compartir una instancia de BaseDatos entre dos hilos."""
    db = BaseDatos(ruta_db)
    db.abrir()
    permitir_continuar_a = threading.Event()
    transaccion_a_iniciada = threading.Event()
    intento_inicio_b = threading.Event()
    transaccion_b_iniciada = threading.Event()

    try:
        command_a = _command_para_pago(
            db, 1, key="H3-MISMA-DB-A"
        )
        command_b = _command_para_pago(
            db, 1, key="H3-MISMA-DB-B"
        )
        servicio_a = _servicio(
            db,
            transaccion_a_iniciada,
            permitir_continuar_a,
        )
        repo_b = _RepositorioConIntentoDeInicio(
            RepositorioRegistroPagoSQLiteV3(db),
            intento_inicio_b,
            transaccion_b_iniciada,
        )
        servicio_b = RegistrarPagoV3(repo_b)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(servicio_a.ejecutar, command_a)
            assert transaccion_a_iniciada.wait(timeout=10)

            futuro_b = executor.submit(servicio_b.ejecutar, command_b)
            assert intento_inicio_b.wait(timeout=10)

            # B ya solicitó iniciar su unidad de trabajo, pero el lock de A
            # debe impedirle empezar sobre la misma conexión hasta el COMMIT.
            assert not transaccion_b_iniciada.wait(timeout=0.2)
            permitir_continuar_a.set()

            resultado_a = futuro_a.result(timeout=10)
            assert resultado_a.es_repeticion_idempotente is False

            with pytest.raises(ErrorInvariante, match="Conflicto de revisión"):
                futuro_b.result(timeout=10)

        assert transaccion_b_iniciada.is_set()
        assert _cantidad_pagos(db, 1) == 1
        assert not db.conexion.in_transaction
    finally:
        permitir_continuar_a.set()
        db.cerrar()

