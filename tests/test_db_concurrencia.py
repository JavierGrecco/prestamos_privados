"""Regresiones de concurrencia sobre una misma instancia de BaseDatos.

La UI puede conservar una instancia global mediante st.cache_resource. Estas
pruebas verifican que dos hilos no se incorporen accidentalmente a la misma
transacción ni pierdan cambios por un rollback ajeno.
"""

from threading import Event, Thread
from pathlib import Path

from infraestructura import BaseDatos, ErrorTransaccion


def test_transacciones_de_hilos_distintos_no_se_anidan_en_la_misma_instancia(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "compartida.db"
    db = BaseDatos(ruta)
    db.abrir()
    db.ejecutar(
        "CREATE TABLE movimientos (id INTEGER PRIMARY KEY, referencia TEXT NOT NULL)"
    )

    transaccion_a_iniciada = Event()
    permitir_rollback_a = Event()
    intento_b = Event()
    transaccion_b_iniciada = Event()
    errores_a: list[Exception] = []
    errores_b: list[Exception] = []

    def operacion_a() -> None:
        try:
            with db.transaccion():
                db.ejecutar(
                    "INSERT INTO movimientos (referencia) VALUES (?)", ("A",)
                )
                transaccion_a_iniciada.set()
                if not permitir_rollback_a.wait(timeout=5):
                    raise TimeoutError("el test no liberó la transacción A")
                raise RuntimeError("fallo inyectado en A")
        except ErrorTransaccion as exc:
            errores_a.append(exc)

    def operacion_b() -> None:
        if not transaccion_a_iniciada.wait(timeout=5):
            errores_b.append(TimeoutError("A no inició a tiempo"))
            return
        intento_b.set()
        try:
            with db.transaccion():
                transaccion_b_iniciada.set()
                db.ejecutar(
                    "INSERT INTO movimientos (referencia) VALUES (?)", ("B",)
                )
        except Exception as exc:  # se conserva cualquier error del hilo para el assert
            errores_b.append(exc)

    hilo_a = Thread(target=operacion_a, name="sesion-a")
    hilo_b = Thread(target=operacion_b, name="sesion-b")
    try:
        hilo_a.start()
        assert transaccion_a_iniciada.wait(timeout=5)
        hilo_b.start()
        assert intento_b.wait(timeout=5)

        # Sin un lock que abarque la transacción completa, B entraría como
        # transacción anidada mientras A continúa abierta.
        b_entro_durante_a = transaccion_b_iniciada.wait(timeout=0.2)
        permitir_rollback_a.set()
        hilo_a.join(timeout=5)
        hilo_b.join(timeout=5)

        assert not b_entro_durante_a
        assert not hilo_a.is_alive()
        assert not hilo_b.is_alive()
        assert len(errores_a) == 1
        assert isinstance(errores_a[0], ErrorTransaccion)
        assert errores_b == []

        filas = db.consultar(
            "SELECT referencia FROM movimientos ORDER BY referencia"
        )
        assert [fila["referencia"] for fila in filas] == ["B"]
    finally:
        permitir_rollback_a.set()
        if hilo_a.ident is not None:
            hilo_a.join(timeout=5)
        if hilo_b.ident is not None:
            hilo_b.join(timeout=5)
        db.cerrar()
