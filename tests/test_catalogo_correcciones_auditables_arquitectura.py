"""Pruebas del contrato de lectura para el catálogo de correcciones auditables."""

import ast
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from aplicacion.consultas.catalogo_correcciones_auditables import (
    ConsultaCatalogoCorreccionesAuditables,
)
from aplicacion.seguridad.identidad import IdentidadSesion
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.composicion.correcciones_auditables import (
    crear_consulta_catalogo_correcciones_auditables,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class _Plan:
    id: int
    nombre: str
    tipo_plan: str
    estado: str
    fecha_desembolso: date = date(2026, 1, 1)
    capital_original_ars: Decimal = Decimal("1000.00")
    creado_por: str = "admin"
    ultima_version: int = 1


class _CatalogoFalso:
    """Lector de prueba: permite comprobar el caso de uso sin SQLite."""

    def __init__(self):
        self.planes = [
            _Plan(1, "Plan interno", "REPOSICION_INTERNA", "ACTIVO"),
            _Plan(2, "Plan cerrado", "REPOSICION_INTERNA", "CERRADO"),
            _Plan(3, "Préstamo entre personas", "PRESTAMO_ENTRE_PERSONAS", "ACTIVO"),
        ]
        self.registro = SimpleNamespace(
            id=15,
            plan_id=1,
            snapshot_json='{"monto_ars":"1000.00"}',
            snapshot_sha256="a" * 64,
            fecha_aporte=date(2026, 1, 2),
            monto_ars=Decimal("1000.00"),
        )
        self.integro = True
        self.ultima_busqueda = None

    def listar_planes(self, limite, *, solo_activos=False):
        self.ultima_busqueda = ("planes", limite, solo_activos)
        return tuple(self.planes)

    def obtener_plan(self, plan_id):
        return next((p for p in self.planes if p.id == plan_id), None)

    def listar_aportes(self, plan_id, limite):
        self.ultima_busqueda = ("aportes", plan_id, limite)
        return (self.registro,) if self.registro.plan_id == plan_id else ()

    def obtener_aporte(self, aporte_id):
        return self.registro if self.registro.id == aporte_id else None

    def verificar_aporte(self, aporte):
        return self.integro

    def listar_flujos_inversion(self, plan_id, limite):
        self.ultima_busqueda = ("flujos", plan_id, limite)
        return ()

    def obtener_flujo_inversion(self, flujo_id):
        return None

    def verificar_flujo_inversion(self, flujo):
        return self.integro

    def listar_valuaciones_inversion(self, plan_id, limite):
        self.ultima_busqueda = ("valuaciones", plan_id, limite)
        return ()

    def obtener_valoracion_inversion(self, valuacion_id):
        return None

    def verificar_valoracion_inversion(self, valuacion):
        return self.integro


def _identidad_admin():
    return IdentidadSesion(
        subject="local-db:1",
        nombre="admin",
        proveedor="LOCAL_DB",
        autenticada=True,
        roles=frozenset({"ADMIN"}),
    )


def test_lista_solo_planes_internos_y_activos_sin_sqlite():
    lector = _CatalogoFalso()
    consulta = ConsultaCatalogoCorreccionesAuditables(
        lector, identidad=_identidad_admin()
    )

    planes = consulta.listar_planes(limite=20)

    assert [plan.id for plan in planes] == [1]
    assert lector.ultima_busqueda == ("planes", 20, True)


def test_lista_registros_y_rechaza_plan_cerrado_o_de_otro_tipo():
    lector = _CatalogoFalso()
    consulta = ConsultaCatalogoCorreccionesAuditables(
        lector, identidad=_identidad_admin()
    )

    registros = consulta.listar_registros(
        plan_id=1, tipo="APORTE_REPOSICION", limite=25
    )

    assert [registro.id for registro in registros] == [15]
    assert lector.ultima_busqueda == ("aportes", 1, 25)

    with pytest.raises(ErrorValidacion, match="cerrado"):
        consulta.listar_registros(
            plan_id=2, tipo="APORTE_REPOSICION"
        )
    with pytest.raises(ErrorValidacion, match="internos"):
        consulta.listar_registros(
            plan_id=3, tipo="APORTE_REPOSICION"
        )


def test_resultado_de_lectura_expone_si_el_snapshot_supera_la_verificacion():
    lector = _CatalogoFalso()
    consulta = ConsultaCatalogoCorreccionesAuditables(
        lector, identidad=_identidad_admin()
    )

    seleccionado = consulta.obtener_registro(
        tipo="APORTE_REPOSICION", registro_id=15
    )
    assert seleccionado is not None
    assert seleccionado.registro.id == 15
    assert seleccionado.integro is True

    lector.integro = False
    seleccionado = consulta.obtener_registro(
        tipo="APORTE_REPOSICION", registro_id=15
    )
    assert seleccionado is not None
    assert seleccionado.integro is False


def test_no_permite_consultar_catalogo_sin_capacidad_para_proponer():
    lector = _CatalogoFalso()
    identidad_lectura = IdentidadSesion(
        subject="local-db:2",
        nombre="lector",
        proveedor="LOCAL_DB",
        autenticada=True,
        roles=frozenset({"LECTURA"}),
    )
    consulta = ConsultaCatalogoCorreccionesAuditables(
        lector, identidad=identidad_lectura
    )

    with pytest.raises(PermissionError):
        consulta.listar_planes()


def test_consulta_de_aplicacion_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "catalogo_correcciones_auditables.py"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: {modulo}")

    assert not problemas, "El caso de uso no debe depender de infraestructura: " + ", ".join(problemas)


def test_pantalla_no_importa_repositorios_y_usa_la_fabrica_publica():
    archivo = ROOT / "ui" / "pagina_proponer_correccion_auditable.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo == "infraestructura.repositorios" or (
                modulo and modulo.startswith("infraestructura.repositorios.")
            ):
                problemas.append(f"línea {nodo.lineno}: {modulo}")

    assert not problemas, "La UI no debe importar repositorios: " + ", ".join(problemas)
    assert "crear_consulta_catalogo_correcciones_auditables" in fuente
    assert "PlanesReposicionRepo" not in fuente
    assert "_sacar_registros" not in fuente
    assert "_obtener_registro" not in fuente



def test_fabrica_sqlite_entrega_registro_verificado(tmp_path):
    """Verifica el adaptador real sin cambiar los hechos guardados."""
    with BaseDatos(tmp_path / "catalogo-correcciones.db") as db:
        aplicar_migraciones(db)
        repositorio = PlanesReposicionRepo(db)
        plan_id, _ = repositorio.crear_plan_con_snapshot(
            nombre="Plan interno de prueba",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=30),
            capital_original_ars=Decimal("10000.00"),
            datos={"objetivo": "prueba del contrato de lectura"},
            creado_por="admin",
        )
        aporte_id = repositorio.registrar_aporte(
            plan_id,
            fecha_aporte=date.today() - timedelta(days=1),
            monto_ars=Decimal("1000.00"),
            cotizacion_ars_por_usd=Decimal("1000.000000"),
            naturaleza_cotizacion="SUPUESTO",
            fuente_cotizacion="",
            referencia="aporte de prueba",
            nota="",
            creado_por="admin",
        )
        original = repositorio.obtener_aporte(aporte_id)
        assert original is not None

        consulta = crear_consulta_catalogo_correcciones_auditables(
            db, identidad=_identidad_admin()
        )
        planes = consulta.listar_planes()
        registros = consulta.listar_registros(
            plan_id=plan_id, tipo="APORTE_REPOSICION"
        )
        seleccionado = consulta.obtener_registro(
            tipo="APORTE_REPOSICION", registro_id=aporte_id
        )

        assert [plan.id for plan in planes] == [plan_id]
        assert [registro.id for registro in registros] == [aporte_id]
        assert seleccionado is not None and seleccionado.integro
        actual = repositorio.obtener_aporte(aporte_id)
        assert actual is not None
        assert actual.snapshot_json == original.snapshot_json
        assert actual.snapshot_sha256 == original.snapshot_sha256



def test_servicio_de_correcciones_no_importa_infraestructura_ni_sql():
    """Las decisiones de negocio usan el contrato público, no la persistencia."""
    archivo = ROOT / "aplicacion" / "servicios" / "correcciones_auditables.py"
    fuente = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue
        for modulo in modulos:
            if modulo and modulo.split(".", 1)[0] in {
                "infraestructura", "sqlite3"
            }:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "El servicio debe depender del puerto, no de infraestructura: "
        + ", ".join(problemas)
    )
    assert "self._db" not in fuente
    assert "transaccion(" not in fuente
    assert "SELECT " not in fuente
    assert "RepositorioCorreccionesAuditables" in fuente
    assert "NuevaCorreccionAuditable" in fuente
