"""Planes de reposición locales con versiones inmutables y trazables."""
from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from dominio.excepciones import ErrorValidacion

from ..db import BaseDatos
from .base import RepositorioBase, ahora_iso, decimal_a_str
from .modelos import (
    PlanReposicionPersistido,
    SnapshotPlanReposicion,
    VersionPlanReposicion,
)


_TIPOS_PLAN = frozenset({"REPOSICION_INTERNA", "PRESTAMO_ENTRE_PERSONAS"})
_MAXIMO_JSON_BYTES = 4_000_000


def _normalizar_json(valor: Any) -> Any:
    """Serializa importes con Decimal, fechas ISO y estructura determinista."""
    if isinstance(valor, bool) or valor is None or isinstance(valor, (str, int)):
        return valor
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ErrorValidacion("El snapshot no admite importes o tasas no finitos")
        return format(valor, "f")
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Enum):
        return _normalizar_json(valor.value)
    if isinstance(valor, float):
        raise ErrorValidacion(
            "El snapshot no admite float; convertí los valores financieros a Decimal"
        )
    if is_dataclass(valor) and not isinstance(valor, type):
        return {campo.name: _normalizar_json(getattr(valor, campo.name)) for campo in fields(valor)}
    if isinstance(valor, dict):
        normalizado = {}
        for clave, contenido in valor.items():
            if not isinstance(clave, str):
                raise ErrorValidacion("Las claves del snapshot deben ser texto")
            normalizado[clave] = _normalizar_json(contenido)
        return normalizado
    if isinstance(valor, (tuple, list)):
        return [_normalizar_json(elemento) for elemento in valor]
    raise ErrorValidacion(f"El snapshot contiene un tipo no admitido: {type(valor).__name__}")


def _serializar_snapshot(datos: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(datos, dict):
        raise ErrorValidacion("Los datos del snapshot deben ser un objeto")
    contenido = json.dumps(
        _normalizar_json(datos),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(contenido.encode("utf-8")) > _MAXIMO_JSON_BYTES:
        raise ErrorValidacion("El snapshot supera el tamaño máximo de 4 MB")
    return contenido, hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _validar_plan(
    *, nombre: str, tipo_plan: str, fecha_desembolso: date,
    capital_original_ars: Decimal, creado_por: str
) -> tuple[str, str, str]:
    nombre_limpio = str(nombre or "").strip()
    tipo = str(tipo_plan or "").strip().upper()
    usuario = str(creado_por or "").strip()
    if not nombre_limpio or len(nombre_limpio) > 120:
        raise ErrorValidacion("El nombre debe tener entre 1 y 120 caracteres")
    if tipo not in _TIPOS_PLAN:
        raise ErrorValidacion("El tipo de plan no está permitido")
    if not isinstance(fecha_desembolso, date):
        raise ErrorValidacion("La fecha del plan debe ser una fecha válida")
    if (
        not isinstance(capital_original_ars, Decimal)
        or not capital_original_ars.is_finite()
        or capital_original_ars <= 0
    ):
        raise ErrorValidacion("El capital original debe ser un Decimal mayor a cero")
    if not usuario:
        raise ErrorValidacion("Se requiere identificar quién guarda el análisis")
    return nombre_limpio, tipo, usuario


class PlanesReposicionRepo(RepositorioBase):
    """Gestiona planes con identidad estable, versiones inmutables y cierre explícito."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def crear_plan_con_snapshot(
        self, *, nombre: str, tipo_plan: str, fecha_desembolso: date,
        capital_original_ars: Decimal, datos: dict[str, Any], creado_por: str
    ) -> tuple[int, int]:
        nombre_limpio, tipo, usuario = _validar_plan(
            nombre=nombre, tipo_plan=tipo_plan, fecha_desembolso=fecha_desembolso,
            capital_original_ars=capital_original_ars, creado_por=creado_por,
        )
        contenido, digest = _serializar_snapshot(datos)
        ahora = ahora_iso()
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO planes_reposicion (
                    nombre, tipo_plan, fecha_desembolso, capital_original_ars,
                    estado, creado_por, creado_en, actualizado_en
                ) VALUES (?, ?, ?, ?, 'ACTIVO', ?, ?, ?)
                """,
                (nombre_limpio, tipo, fecha_desembolso.isoformat(),
                 decimal_a_str(capital_original_ars), usuario, ahora, ahora),
            )
            plan_id = self.db.ultimo_id_insertado()
            self.db.ejecutar(
                """
                INSERT INTO planes_reposicion_versiones (
                    plan_id, numero_version, snapshot_json, snapshot_sha256,
                    creado_por, creado_en
                ) VALUES (?, 1, ?, ?, ?, ?)
                """,
                (plan_id, contenido, digest, usuario, ahora),
            )
        return plan_id, 1

    def guardar_nueva_version(
        self, plan_id: int, *, datos: dict[str, Any], creado_por: str
    ) -> int:
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        usuario = str(creado_por or "").strip()
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién guarda la versión")
        contenido, digest = _serializar_snapshot(datos)
        ahora = ahora_iso()
        with self.db.transaccion():
            plan = self.db.consultar_uno(
                "SELECT estado FROM planes_reposicion WHERE id = ?", (plan_id,)
            )
            if plan is None:
                raise ErrorValidacion("El plan seleccionado no existe")
            if str(plan["estado"]) != "ACTIVO":
                raise ErrorValidacion("El plan está cerrado; no admite nuevas versiones")
            fila = self.db.consultar_uno(
                """SELECT COALESCE(MAX(numero_version), 0) AS ultima
                   FROM planes_reposicion_versiones WHERE plan_id = ?""",
                (plan_id,),
            )
            numero = int(fila["ultima"]) + 1
            self.db.ejecutar(
                """
                INSERT INTO planes_reposicion_versiones (
                    plan_id, numero_version, snapshot_json, snapshot_sha256,
                    creado_por, creado_en
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (plan_id, numero, contenido, digest, usuario, ahora),
            )
            self.db.ejecutar(
                "UPDATE planes_reposicion SET actualizado_en = ? WHERE id = ?",
                (ahora, plan_id),
            )
        return numero

    def cerrar_plan(self, plan_id: int, *, cerrado_por: str) -> None:
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        usuario = str(cerrado_por or "").strip()
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién cierra el plan")
        ahora = ahora_iso()
        with self.db.transaccion():
            plan = self.db.consultar_uno(
                "SELECT estado FROM planes_reposicion WHERE id = ?", (plan_id,)
            )
            if plan is None:
                raise ErrorValidacion("El plan seleccionado no existe")
            if str(plan["estado"]) != "ACTIVO":
                raise ErrorValidacion("El plan ya está cerrado")
            self.db.ejecutar(
                """UPDATE planes_reposicion
                   SET estado = 'CERRADO', actualizado_en = ?, cerrado_por = ?, cerrado_en = ?
                   WHERE id = ? AND estado = 'ACTIVO'""",
                (ahora, usuario, ahora, plan_id),
            )

    def obtener_plan(self, plan_id: int) -> PlanReposicionPersistido | None:
        fila = self.db.consultar_uno(
            """
            SELECT p.*,
                COALESCE((SELECT MAX(v.numero_version) FROM planes_reposicion_versiones v
                          WHERE v.plan_id = p.id), 0) AS ultima_version,
                (SELECT v.snapshot_sha256 FROM planes_reposicion_versiones v
                 WHERE v.plan_id = p.id ORDER BY v.numero_version DESC LIMIT 1)
                 AS ultima_version_sha256
            FROM planes_reposicion p WHERE p.id = ?
            """,
            (plan_id,),
        )
        return self._fila_a_plan(fila) if fila else None

    def listar_planes(self, limite: int = 30, *, solo_activos: bool = False) -> list[PlanReposicionPersistido]:
        limite_seguro = self._validar_limite(limite)
        where = "WHERE p.estado = 'ACTIVO'" if solo_activos else ""
        filas = self.db.consultar(
            f"""
            SELECT p.*,
                COALESCE((SELECT MAX(v.numero_version) FROM planes_reposicion_versiones v
                          WHERE v.plan_id = p.id), 0) AS ultima_version,
                (SELECT v.snapshot_sha256 FROM planes_reposicion_versiones v
                 WHERE v.plan_id = p.id ORDER BY v.numero_version DESC LIMIT 1)
                 AS ultima_version_sha256
            FROM planes_reposicion p {where}
            ORDER BY p.actualizado_en DESC, p.id DESC LIMIT ?
            """,
            (limite_seguro,),
        )
        return [self._fila_a_plan(fila) for fila in filas]

    def listar_versiones(self, plan_id: int) -> list[VersionPlanReposicion]:
        if self.obtener_plan(plan_id) is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        filas = self.db.consultar(
            """
            SELECT v.*, p.nombre, p.tipo_plan, p.fecha_desembolso, p.capital_original_ars
            FROM planes_reposicion_versiones v
            JOIN planes_reposicion p ON p.id = v.plan_id
            WHERE v.plan_id = ? ORDER BY v.numero_version DESC
            """,
            (plan_id,),
        )
        return [self._fila_a_version(fila, incluir_json=False) for fila in filas]

    def obtener_version(self, plan_id: int, numero_version: int) -> VersionPlanReposicion | None:
        fila = self.db.consultar_uno(
            """
            SELECT v.*, p.nombre, p.tipo_plan, p.fecha_desembolso, p.capital_original_ars
            FROM planes_reposicion_versiones v
            JOIN planes_reposicion p ON p.id = v.plan_id
            WHERE v.plan_id = ? AND v.numero_version = ?
            """,
            (plan_id, numero_version),
        )
        return self._fila_a_version(fila, incluir_json=True) if fila else None

    def verificar_version(self, version: VersionPlanReposicion) -> bool:
        if version.snapshot_json is None:
            return False
        if hashlib.sha256(version.snapshot_json.encode("utf-8")).hexdigest() != version.snapshot_sha256:
            return False
        try:
            return isinstance(json.loads(version.snapshot_json), dict)
        except (TypeError, json.JSONDecodeError):
            return False

    # Compatibilidad para código v022 y tests existentes: un snapshot nuevo
    # equivale a crear un plan con la primera versión, nunca un movimiento real.
    def guardar_snapshot(
        self, *, nombre: str, tipo_plan: str, fecha_desembolso: date,
        capital_original_ars: Decimal, datos: dict[str, Any], creado_por: str
    ) -> int:
        plan_id, _ = self.crear_plan_con_snapshot(
            nombre=nombre, tipo_plan=tipo_plan, fecha_desembolso=fecha_desembolso,
            capital_original_ars=capital_original_ars, datos=datos, creado_por=creado_por,
        )
        return plan_id

    def listar_resumenes(self, limite: int = 30) -> list[SnapshotPlanReposicion]:
        return [
            SnapshotPlanReposicion(
                id=plan.id, nombre=plan.nombre, tipo_plan=plan.tipo_plan,
                fecha_desembolso=plan.fecha_desembolso,
                capital_original_ars=plan.capital_original_ars,
                snapshot_sha256=plan.ultima_version_sha256 or "",
                creado_por=plan.creado_por, creado_en=plan.creado_en,
            )
            for plan in self.listar_planes(limite)
        ]

    def obtener_snapshot(self, snapshot_id: int) -> SnapshotPlanReposicion | None:
        plan = self.obtener_plan(snapshot_id)
        if plan is None or plan.ultima_version < 1:
            return None
        version = self.obtener_version(plan.id, plan.ultima_version)
        if version is None:
            return None
        return SnapshotPlanReposicion(
            id=plan.id, nombre=plan.nombre, tipo_plan=plan.tipo_plan,
            fecha_desembolso=plan.fecha_desembolso,
            capital_original_ars=plan.capital_original_ars,
            snapshot_sha256=version.snapshot_sha256,
            creado_por=version.creado_por, creado_en=version.creado_en,
            snapshot_json=version.snapshot_json,
        )

    def verificar_snapshot(self, snapshot: SnapshotPlanReposicion) -> bool:
        if snapshot.snapshot_json is None:
            return False
        if hashlib.sha256(snapshot.snapshot_json.encode("utf-8")).hexdigest() != snapshot.snapshot_sha256:
            return False
        try:
            return isinstance(json.loads(snapshot.snapshot_json), dict)
        except (TypeError, json.JSONDecodeError):
            return False

    @staticmethod
    def _validar_limite(limite: int) -> int:
        if not isinstance(limite, int) or isinstance(limite, bool):
            raise ErrorValidacion("El límite de planes debe ser un entero")
        return max(1, min(limite, 100))

    @staticmethod
    def _fila_a_plan(fila) -> PlanReposicionPersistido:
        return PlanReposicionPersistido(
            id=int(fila["id"]), nombre=str(fila["nombre"]), tipo_plan=str(fila["tipo_plan"]),
            fecha_desembolso=date.fromisoformat(str(fila["fecha_desembolso"])),
            capital_original_ars=Decimal(str(fila["capital_original_ars"])),
            estado=str(fila["estado"]), creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]), actualizado_en=str(fila["actualizado_en"]),
            cerrado_por=str(fila["cerrado_por"]) if fila["cerrado_por"] is not None else None,
            cerrado_en=str(fila["cerrado_en"]) if fila["cerrado_en"] is not None else None,
            ultima_version=int(fila["ultima_version"]),
            ultima_version_sha256=str(fila["ultima_version_sha256"])
            if fila["ultima_version_sha256"] is not None else None,
        )

    @staticmethod
    def _fila_a_version(fila, *, incluir_json: bool) -> VersionPlanReposicion:
        return VersionPlanReposicion(
            id=int(fila["id"]), plan_id=int(fila["plan_id"]),
            numero_version=int(fila["numero_version"]), nombre=str(fila["nombre"]),
            tipo_plan=str(fila["tipo_plan"]),
            fecha_desembolso=date.fromisoformat(str(fila["fecha_desembolso"])),
            capital_original_ars=Decimal(str(fila["capital_original_ars"])),
            snapshot_sha256=str(fila["snapshot_sha256"]), creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            snapshot_json=str(fila["snapshot_json"]) if incluir_json else None,
        )
