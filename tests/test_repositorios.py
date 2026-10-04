"""
Tests de integración de los repositorios.

Validan que:
  - Crear, obtener, listar y actualizar funcionan.
  - Los roles de persona funcionan y se preservan al dar de baja.
  - El préstamo se crea en BORRADOR.
  - Las versiones de tasa se numeran y se cierran correctamente.
  - La tabla de amortización se persiste con precisión decimal.
  - La suma de porcentajes de participaciones es correcta.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from dominio import generar_tabla, SistemaAmortizacion, ModalidadTasa
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import (
    PersonaRepo,
    PrestamoRepo,
    ParticipacionRepo,
)


@pytest.fixture
def db(tmp_path: Path):
    """Base temporal con migraciones aplicadas."""
    ruta = tmp_path / "test.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.fixture
def persona_repo(db):
    return PersonaRepo(db)


@pytest.fixture
def prestamo_repo(db):
    return PrestamoRepo(db)


@pytest.fixture
def participacion_repo(db):
    return ParticipacionRepo(db)


# ================================================================
# Personas
# ================================================================

class TestPersonaRepo:

    def test_crear_y_obtener(self, persona_repo):
        """Crea una persona y la recupera por ID."""
        pid = persona_repo.crear(nombre="Juan", apellido="Pérez",
                                 documento="12345678")
        persona = persona_repo.obtener(pid)
        assert persona is not None
        assert persona.nombre == "Juan"
        assert persona.apellido == "Pérez"
        assert persona.documento == "12345678"
        assert persona.estado == "ACTIVO"
        assert persona.nombre_completo == "Juan Pérez"

    def test_nombre_obligatorio(self, persona_repo):
        """No se puede crear una persona sin nombre."""
        with pytest.raises(ValueError):
            persona_repo.crear(nombre="")

    def test_documento_unico(self, persona_repo):
        """No se puede repetir el documento."""
        persona_repo.crear(nombre="Juan", documento="123")
        with pytest.raises(Exception):
            persona_repo.crear(nombre="Otro", documento="123")

    def test_obtener_por_documento(self, persona_repo):
        """Busca por documento."""
        persona_repo.crear(nombre="Juan", documento="999")
        p = persona_repo.obtener_por_documento("999")
        assert p is not None
        assert p.nombre == "Juan"

    def test_listar(self, persona_repo):
        """Lista todas las personas."""
        persona_repo.crear(nombre="A")
        persona_repo.crear(nombre="B")
        persona_repo.crear(nombre="C")
        assert len(persona_repo.listar()) == 3

    def test_actualizar(self, persona_repo):
        """Actualiza campos permitidos."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.actualizar(pid, telefono="11-1234-5678",
                                email="juan@ejemplo.com")
        p = persona_repo.obtener(pid)
        assert p.telefono == "11-1234-5678"
        assert p.email == "juan@ejemplo.com"

    def test_actualizar_ignora_campos_no_permitidos(self, persona_repo):
        """No se pueden cambiar campos como `id` o `creado_en`."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.actualizar(pid, id=999, creado_en="otra")
        p = persona_repo.obtener(pid)
        assert p.id == pid


class TestRoles:

    def test_agregar_rol(self, persona_repo):
        """Agrega roles a una persona."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.agregar_rol(pid, "INVERSOR")
        persona_repo.agregar_rol(pid, "DEUDOR")
        assert persona_repo.tiene_rol(pid, "INVERSOR")
        assert persona_repo.tiene_rol(pid, "DEUDOR")
        assert not persona_repo.tiene_rol(pid, "ADMIN")
        assert set(persona_repo.roles(pid)) == {"INVERSOR", "DEUDOR"}

    def test_agregar_rol_duplicado_es_idempotente(self, persona_repo):
        """Agregar un rol ya activo no falla."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.agregar_rol(pid, "INVERSOR")
        persona_repo.agregar_rol(pid, "INVERSOR")  # no debe fallar
        assert persona_repo.roles(pid) == ["INVERSOR"]

    def test_rol_invalido_rechazado(self, persona_repo):
        """Roles desconocidos son rechazados por el repo."""
        pid = persona_repo.crear(nombre="Juan")
        with pytest.raises(ValueError):
            persona_repo.agregar_rol(pid, "ROL_INVENTADO")

    def test_quitar_rol_preserva_historial(self, persona_repo):
        """Quitar un rol no lo elimina, lo da de baja."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.agregar_rol(pid, "INVERSOR")
        persona_repo.quitar_rol(pid, "INVERSOR", motivo="Baja por cierre")
        assert not persona_repo.tiene_rol(pid, "INVERSOR")

    def test_reactivar_rol_dado_de_baja(self, persona_repo):
        """Se puede reactivar un rol previamente dado de baja."""
        pid = persona_repo.crear(nombre="Juan")
        persona_repo.agregar_rol(pid, "INVERSOR")
        persona_repo.quitar_rol(pid, "INVERSOR")
        persona_repo.agregar_rol(pid, "INVERSOR")
        assert persona_repo.tiene_rol(pid, "INVERSOR")

    def test_listar_por_rol(self, persona_repo):
        """Filtra personas por rol activo."""
        p1 = persona_repo.crear(nombre="A")
        p2 = persona_repo.crear(nombre="B")
        persona_repo.agregar_rol(p1, "INVERSOR")
        persona_repo.agregar_rol(p2, "DEUDOR")
        inversores = persona_repo.listar(rol="INVERSOR")
        assert len(inversores) == 1
        assert inversores[0].id == p1


# ================================================================
# Préstamos
# ================================================================

class TestPrestamoRepo:

    def test_crear_prestamo(self, persona_repo, prestamo_repo):
        """Crea un préstamo en BORRADOR."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id=deudor_id,
            capital_original=Decimal("20000000"),
            plazo_meses=36,
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            destino="Cambio de auto",
        )
        prestamo = prestamo_repo.obtener(pid)
        assert prestamo is not None
        assert prestamo.numero == "PR-000001"
        assert prestamo.estado == "BORRADOR"
        assert prestamo.capital_original == Decimal("20000000")
        assert prestamo.destino == "Cambio de auto"

    def test_numeracion_secuencial(self, persona_repo, prestamo_repo):
        """Los préstamos se numeran PR-000001, PR-000002, ..."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid1 = prestamo_repo.crear(
            deudor_id, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        pid2 = prestamo_repo.crear(
            deudor_id, Decimal("2000"), 12, "FRANCES", "MENSUAL",
            date(2026, 2, 1),
        )
        assert prestamo_repo.obtener(pid1).numero == "PR-000001"
        assert prestamo_repo.obtener(pid2).numero == "PR-000002"

    def test_capital_positivo(self, persona_repo, prestamo_repo):
        """Rechaza capital <= 0."""
        deudor_id = persona_repo.crear(nombre="Juan")
        with pytest.raises(ValueError):
            prestamo_repo.crear(
                deudor_id, Decimal("0"), 12, "FRANCES", "MENSUAL",
                date(2026, 1, 1),
            )

    def test_actualizar_estado(self, persona_repo, prestamo_repo):
        """Cambia el estado del préstamo."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        prestamo_repo.actualizar_estado(pid, "ACTIVO")
        assert prestamo_repo.obtener(pid).estado == "ACTIVO"

    def test_listar_por_estado(self, persona_repo, prestamo_repo):
        """Filtra préstamos por estado."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid1 = prestamo_repo.crear(
            deudor_id, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        prestamo_repo.crear(
            deudor_id, Decimal("2000"), 12, "FRANCES", "MENSUAL",
            date(2026, 2, 1),
        )
        prestamo_repo.actualizar_estado(pid1, "ACTIVO")
        activos = prestamo_repo.listar(estado="ACTIVO")
        assert len(activos) == 1


class TestVersionesTasa:

    def test_crear_primera_version(self, persona_repo, prestamo_repo):
        """La primera versión es la número 1."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        vid = prestamo_repo.crear_version_tasa(
            prestamo_id=pid,
            tasa_anual=Decimal("0.30"),
            modalidad_tasa="TNA",
            fecha_desde=date(2026, 1, 1),
        )
        assert vid > 0
        assert prestamo_repo.version_activa(pid) == vid

    def test_segunda_version_cierra_la_primera(self, persona_repo, prestamo_repo):
        """Crear una nueva versión cierra la anterior."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        vid1 = prestamo_repo.crear_version_tasa(
            pid, Decimal("0.30"), "TNA", date(2026, 1, 1),
        )
        vid2 = prestamo_repo.crear_version_tasa(
            pid, Decimal("0.27"), "TNA", date(2027, 1, 1),
            motivo="Reducción de tasa",
        )
        assert vid2 != vid1
        assert prestamo_repo.version_activa(pid) == vid2
        # Verificar que la primera tiene fecha_hasta
        fila = prestamo_repo.db.consultar_uno(
            "SELECT fecha_hasta FROM versiones_tasa WHERE id = ?",
            (vid1,),
        )
        assert fila["fecha_hasta"] == "2027-01-01"


class TestTablaAmortizacion:

    def test_guardar_tabla_completa(self, persona_repo, prestamo_repo):
        """Persiste la tabla generada por el motor financiero."""
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id, Decimal("1000000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        vid = prestamo_repo.crear_version_tasa(
            pid, Decimal("0.30"), "TNA", date(2026, 1, 1),
        )

        tabla = generar_tabla(
            capital=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=12,
            fecha_inicio=date(2026, 1, 1),
            sistema=SistemaAmortizacion.FRANCES,
        )

        cantidad = prestamo_repo.guardar_tabla_amortizacion(vid, tabla)
        assert cantidad == 12

        cuotas = prestamo_repo.cuotas(vid)
        assert len(cuotas) == 12
        assert cuotas[0].numero == 1
        # Verificar precisión decimal
        assert cuotas[0].cuota == tabla[0]["cuota"]
        assert cuotas[-1].saldo == Decimal("0.00")
        assert cuotas[-1].estado == "PENDIENTE"


# ================================================================
# Participaciones
# ================================================================

class TestParticipacionRepo:

    def test_crear_participacion(self, persona_repo, prestamo_repo,
                                 participacion_repo):
        """Crea una participación y la recupera."""
        inversor_id = persona_repo.crear(nombre="María")
        deudor_id = persona_repo.crear(nombre="Juan")
        pid = prestamo_repo.crear(
            deudor_id, Decimal("10000000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )

        part_id = participacion_repo.crear(
            prestamo_id=pid,
            inversor_id=inversor_id,
            capital_aportado=Decimal("10000000"),
            porcentaje=Decimal("1.0"),
            fecha_aporte=date(2026, 1, 1),
            tc_aporte=Decimal("1500"),
            capital_usd_ref=Decimal("6666.67"),
        )

        part = participacion_repo.obtener(part_id)
        assert part is not None
        assert part.capital_aportado == Decimal("10000000")
        assert part.porcentaje == Decimal("1.0")
        assert part.tc_aporte == Decimal("1500")

    def test_suma_porcentajes(self, persona_repo, prestamo_repo,
                              participacion_repo):
        """La suma de porcentajes debe dar el total esperado."""
        inv1 = persona_repo.crear(nombre="A")
        inv2 = persona_repo.crear(nombre="B")
        inv3 = persona_repo.crear(nombre="C")
        deudor = persona_repo.crear(nombre="Deudor")
        pid = prestamo_repo.crear(
            deudor, Decimal("20000000"), 36, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )

        participacion_repo.crear(pid, inv1, Decimal("10000000"),
                                 Decimal("0.5"), date(2026, 1, 1))
        participacion_repo.crear(pid, inv2, Decimal("6000000"),
                                 Decimal("0.3"), date(2026, 1, 1))
        participacion_repo.crear(pid, inv3, Decimal("4000000"),
                                 Decimal("0.2"), date(2026, 1, 1))

        assert participacion_repo.suma_porcentajes(pid) == Decimal("1.0")

    def test_porcentaje_invalido(self, persona_repo, prestamo_repo,
                                 participacion_repo):
        """Rechaza porcentajes fuera de (0, 1]."""
        inv = persona_repo.crear(nombre="A")
        deudor = persona_repo.crear(nombre="Deudor")
        pid = prestamo_repo.crear(
            deudor, Decimal("1000000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        with pytest.raises(ValueError):
            participacion_repo.crear(pid, inv, Decimal("1000"),
                                     Decimal("1.5"), date(2026, 1, 1))
        with pytest.raises(ValueError):
            participacion_repo.crear(pid, inv, Decimal("1000"),
                                     Decimal("0"), date(2026, 1, 1))

    def test_listar_por_inversor(self, persona_repo, prestamo_repo,
                                 participacion_repo):
        """Lista las participaciones de un inversor."""
        inv = persona_repo.crear(nombre="A")
        deudor = persona_repo.crear(nombre="Deudor")

        pid1 = prestamo_repo.crear(
            deudor, Decimal("1000"), 12, "FRANCES", "MENSUAL",
            date(2026, 1, 1),
        )
        pid2 = prestamo_repo.crear(
            deudor, Decimal("2000"), 12, "FRANCES", "MENSUAL",
            date(2026, 2, 1),
        )

        participacion_repo.crear(pid1, inv, Decimal("1000"),
                                 Decimal("1.0"), date(2026, 1, 1))
        participacion_repo.crear(pid2, inv, Decimal("2000"),
                                 Decimal("1.0"), date(2026, 2, 1))

        parts = participacion_repo.por_inversor(inv)
        assert len(parts) == 2