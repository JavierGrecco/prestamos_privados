"""Idempotencia y concurrencia del camino Legacy de registro de pagos."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios import ErrorDatosInvalidos, ServicioPagos, ServicioPrestamos
from aplicacion.servicios.registro_pago_v3 import fingerprint_command
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import LedgerRepo, PagoRepo, PersonaRepo, PrestamoRepo


FECHA_PAGO = date(2026, 2, 1)
CLAVE = "legacy-pago-intento-1"


def _crear_prestamo(db: BaseDatos) -> int:
    aplicar_migraciones(db)
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="Idempotencia")
    inversor_id = personas.crear(nombre="Inversor", apellido="Idempotencia")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000.00"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000.00")}],
        usuario="test-idempotencia",
    )


def _fingerprint(
    prestamo_id: int,
    monto: Decimal,
    *,
    nota: str | None = None,
) -> str:
    command = RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=monto,
        fecha_real=FECHA_PAGO,
        fecha_valor=FECHA_PAGO,
        usuario="test-idempotencia",
        medio="Transferencia",
        referencia=None,
        nota=nota,
        opcion_adelanto=None,
        idempotency_key=CLAVE,
    )
    return fingerprint_command(command)


def _registrar(db: BaseDatos, prestamo_id: int, monto: Decimal, huella: str,
               *, nota: str | None = None) -> int:
    return ServicioPagos(db).registrar_pago(
        prestamo_id=prestamo_id,
        monto=monto,
        fecha_real=FECHA_PAGO,
        usuario="test-idempotencia",
        medio="Transferencia",
        nota=nota,
        idempotency_key=CLAVE,
        idempotency_fingerprint=huella,
    )


def test_reintento_con_misma_clave_y_misma_huella_devuelve_el_pago_original(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "pago-idempotente.db") as db:
        prestamo_id = _crear_prestamo(db)
        deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
            prestamo_id, FECHA_PAGO
        )
        assert deuda is not None
        monto = deuda["total_a_pagar"]
        huella = _fingerprint(prestamo_id, monto)

        primero = _registrar(db, prestamo_id, monto, huella)
        pagos_antes = db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"]
        ledger_antes = db.consultar_uno("SELECT COUNT(*) AS n FROM ledger")["n"]
        cuotas_antes = tuple(
            tuple(fila)
            for fila in db.consultar(
                """
                SELECT id, estado, interes_pendiente, capital_pendiente,
                       mora_pendiente
                FROM cuotas ORDER BY id
                """
            )
        )

        repetido = _registrar(db, prestamo_id, monto, huella)

        assert repetido == primero
        assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == pagos_antes == 1
        assert db.consultar_uno("SELECT COUNT(*) AS n FROM ledger")["n"] == ledger_antes
        assert tuple(
            tuple(fila)
            for fila in db.consultar(
                """
                SELECT id, estado, interes_pendiente, capital_pendiente,
                       mora_pendiente
                FROM cuotas ORDER BY id
                """
            )
        ) == cuotas_antes
        assert LedgerRepo(db).verificar_cuadre() is True


def test_reutilizar_clave_con_otro_contenido_se_rechaza_sin_nuevo_pago(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "pago-clave-conflicto.db") as db:
        prestamo_id = _crear_prestamo(db)
        deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
            prestamo_id, FECHA_PAGO
        )
        assert deuda is not None
        monto = deuda["total_a_pagar"]
        huella = _fingerprint(prestamo_id, monto)

        primero = _registrar(db, prestamo_id, monto, huella)
        conteo_antes = db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"]

        from aplicacion.servicios import ErrorConflictoIdempotencia

        with pytest.raises(
            ErrorConflictoIdempotencia, match="datos diferentes"
        ) as conflicto:
            _registrar(
                db,
                prestamo_id,
                monto,
                _fingerprint(prestamo_id, monto, nota="payload diferente"),
                nota="payload diferente",
            )
        assert conflicto.value.pago_existente_id == primero

        assert PagoRepo(db).por_prestamo(prestamo_id)[0].id == primero
        assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == conteo_antes
        assert LedgerRepo(db).verificar_cuadre() is True


def test_dos_conexiones_reintentando_la_misma_operacion_crean_un_solo_pago(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "pago-idempotente-concurrente.db"
    db1 = BaseDatos(ruta)
    db1.abrir()
    db2 = None
    try:
        prestamo_id = _crear_prestamo(db1)
        deuda = ServicioPagos(db1).calcular_deuda_proximo_pago(
            prestamo_id, FECHA_PAGO
        )
        assert deuda is not None
        monto = deuda["total_a_pagar"]
        huella = _fingerprint(prestamo_id, monto)

        db2 = BaseDatos(ruta)
        db2.abrir()
        inicio = Barrier(2, timeout=5)
        pagos: list[int] = []
        errores: list[Exception] = []

        def enviar(db: BaseDatos) -> None:
            try:
                inicio.wait()
                pagos.append(_registrar(db, prestamo_id, monto, huella))
            except Exception as exc:
                errores.append(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(enviar, db1)
            f2 = pool.submit(enviar, db2)
            f1.result(timeout=15)
            f2.result(timeout=15)

        assert errores == []
        assert len(pagos) == 2
        assert pagos[0] == pagos[1]
        assert db1.consultar_uno(
            "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
            (prestamo_id,),
        )["n"] == 1
        assert db1.consultar_uno(
            "SELECT COUNT(*) AS n FROM auditoria WHERE entidad = 'PAGO'"
        )["n"] == 1
        assert LedgerRepo(db1).verificar_cuadre() is True
    finally:
        if db2 is not None:
            db2.cerrar()
        db1.cerrar()
