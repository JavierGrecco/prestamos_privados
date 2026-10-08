"""Pruebas del resultado efectivo por operación."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.resultados_operaciones_persona import (
    ServicioResultadosOperacionesPersona,
)
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _persona(personas, nombre, documento, rol):
    persona_id = personas.crear(
        nombre=nombre,
        apellido="Resultado",
        documento=documento,
    )
    personas.agregar_rol(persona_id, rol)
    return persona_id


def _crear_prestamo(db, deudor_id, inversor_id):
    ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("180000.00"),
        plazo_meses=6,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 8),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("180000.00")}],
        usuario="test",
        tc_inicial=Decimal("1000.00"),
        destino="Resultado",
    )


def _insertar_pago_y_cobro(db, prestamo_id: int):
    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro,
         monto_moneda_pago, monto_moneda_contractual, estado,
         creado_por, tipo_pago, tc_aplicado, monto_usd_ref)
        VALUES (?, '2026-03-08', '2026-03-08', '2026-03-08',
                '40000.00', '40000.00', 'VALIDA', 'test', 'CUOTA',
                '1100.00', '36.36363636')
        """,
        (prestamo_id,),
    )
    pago_id = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES ('INVERSOR', ?, 'COBRO_PAGO', '40000.00', '0.00',
                '2026-03-08', ?, 'test-correlacion', '2026-03-08')
        """,
        (1, '{"pago_id": %d}' % pago_id),
    )


def test_inversor_obtiene_tasa_real_y_usd(tmp_path: Path):
    with BaseDatos(tmp_path / "resultados.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Ana", "99993001", "DEUDOR")
        inversor = _persona(personas, "Pedro", "99993002", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(db, 1)

        resultado = ServicioResultadosOperacionesPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 3, 9),
            inflacion_mensual_supuesta=Decimal("0.05"),
        )

    assert len(resultado.operaciones) == 1
    op = resultado.operaciones[0]
    assert op.evidencia_suficiente
    assert op.xirr_anual is not None
    assert op.rendimiento_real_anual is not None
    assert op.xirr_usd_anual is not None
    assert op.cantidad_flujos == 2


def test_deudor_obtiene_costo_efectivo(tmp_path: Path):
    with BaseDatos(tmp_path / "costo.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Carlos", "99993003", "DEUDOR")
        inversor = _persona(personas, "Lucía", "99993004", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(db, 1)

        resultado = ServicioResultadosOperacionesPersona(db).obtener(
            deudor,
            fecha_corte=date(2026, 3, 9),
        )

    assert len(resultado.operaciones) == 1
    op = resultado.operaciones[0]
    assert op.metrica_nombre == "Costo efectivo"
    assert op.evidencia_suficiente
    assert op.xirr_anual is not None


def test_sin_movimientos_no_inventa_tasa(tmp_path: Path):
    with BaseDatos(tmp_path / "sin_datos.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = _persona(personas, "Nora", "99993005", "DEUDOR")
        inversor = _persona(personas, "Elías", "99993006", "INVERSOR")
        _crear_prestamo(db, deudor, inversor)

        resultado = ServicioResultadosOperacionesPersona(db).obtener(
            deudor,
            fecha_corte=date(2026, 1, 1),
        )

    # El desembolso contractual cuenta como movimiento real del deudor,
    # por lo que hay un único flujo: todavía no alcanza para XIRR.
    op = resultado.operaciones[0]
    assert not op.evidencia_suficiente
    assert op.xirr_anual is None
    assert op.motivo_no_disponible


def test_rechaza_inflacion_invalida(tmp_path: Path):
    with BaseDatos(tmp_path / "invalida.db") as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        persona = _persona(personas, "Eva", "99993007", "DEUDOR")

        servicio = ServicioResultadosOperacionesPersona(db)
        try:
            servicio.obtener(
                persona,
                inflacion_mensual_supuesta=Decimal("-1"),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Se esperaba ValueError")
