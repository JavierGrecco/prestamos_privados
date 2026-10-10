"""Persistencia local e inmutable de análisis de reposición en USD."""
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
from .modelos import SnapshotPlanReposicion


_TIPOS_PLAN = frozenset({"REPOSICION_INTERNA", "PRESTAMO_ENTRE_PERSONAS"})
_MAXIMO_JSON_BYTES = 4_000_000


def _normalizar_json(valor: Any) -> Any:
    """Convierte tipos financieros a JSON sin perder Decimal ni aceptar float."""
    if isinstance(valor, bool) or valor is None or isinstance(valor, (str, int)):
        return valor
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ErrorValidacion("El snapshot no admite importes o tasas no finitos")
        return format(valor, "f")
    # datetime hereda de date; comprobarlo antes para no perder la hora.
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
        return {
            campo.name: _normalizar_json(getattr(valor, campo.name))
            for campo in fields(valor)
        }
    if isinstance(valor, dict):
        normalizado = {}
        for clave, contenido in valor.items():
            if not isinstance(clave, str):
                raise ErrorValidacion("Las claves del snapshot deben ser texto")
            normalizado[clave] = _normalizar_json(contenido)
        return normalizado
    if isinstance(valor, (tuple, list)):
        return [_normalizar_json(elemento) for elemento in valor]
    raise ErrorValidacion(
        f"El snapshot contiene un tipo no admitido: {type(valor).__name__}"
    )


class PlanesReposicionRepo(RepositorioBase):
    """Guarda y consulta snapshots de análisis; nunca los trata como contratos."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def guardar_snapshot(
        self,
        *,
        nombre: str,
        tipo_plan: str,
        fecha_desembolso: date,
        capital_original_ars: Decimal,
        datos: dict[str, Any],
        creado_por: str,
    ) -> int:
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
            raise ErrorValidacion("Se requiere identificar quién guardó el análisis")
        if not isinstance(datos, dict):
            raise ErrorValidacion("Los datos del snapshot deben ser un objeto")

        normalizado = _normalizar_json(datos)
        snapshot_json = json.dumps(
            normalizado,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        if len(snapshot_json.encode("utf-8")) > _MAXIMO_JSON_BYTES:
            raise ErrorValidacion("El snapshot supera el tamaño máximo de 4 MB")
        snapshot_sha256 = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO planes_reposicion_snapshots (
                    nombre, tipo_plan, fecha_desembolso, capital_original_ars,
                    snapshot_json, snapshot_sha256, creado_por, creado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nombre_limpio,
                    tipo,
                    fecha_desembolso.isoformat(),
                    decimal_a_str(capital_original_ars),
                    snapshot_json,
                    snapshot_sha256,
                    usuario,
                    ahora_iso(),
                ),
            )
            return self.db.ultimo_id_insertado()

    def listar_resumenes(self, limite: int = 30) -> list[SnapshotPlanReposicion]:
        """Devuelve metadatos recientes sin cargar los JSON completos."""
        if not isinstance(limite, int) or isinstance(limite, bool):
            raise ErrorValidacion("El límite de snapshots debe ser un entero")
        limite_seguro = max(1, min(limite, 100))
        filas = self.db.consultar(
            """
            SELECT id, nombre, tipo_plan, fecha_desembolso,
                   capital_original_ars, snapshot_sha256, creado_por, creado_en
            FROM planes_reposicion_snapshots
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite_seguro,),
        )
        return [self._fila_a_snapshot(fila, incluir_json=False) for fila in filas]

    def obtener_snapshot(self, snapshot_id: int) -> SnapshotPlanReposicion | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM planes_reposicion_snapshots WHERE id = ?",
            (snapshot_id,),
        )
        return self._fila_a_snapshot(fila, incluir_json=True) if fila else None

    def verificar_snapshot(self, snapshot: SnapshotPlanReposicion) -> bool:
        """Comprueba el hash del JSON guardado antes de mostrar el contenido."""
        if snapshot.snapshot_json is None:
            return False
        digest = hashlib.sha256(snapshot.snapshot_json.encode("utf-8")).hexdigest()
        if digest != snapshot.snapshot_sha256:
            return False
        try:
            contenido = json.loads(snapshot.snapshot_json)
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(contenido, dict)

    def _fila_a_snapshot(self, fila, *, incluir_json: bool) -> SnapshotPlanReposicion:
        return SnapshotPlanReposicion(
            id=int(fila["id"]),
            nombre=str(fila["nombre"]),
            tipo_plan=str(fila["tipo_plan"]),
            fecha_desembolso=date.fromisoformat(str(fila["fecha_desembolso"])),
            capital_original_ars=Decimal(str(fila["capital_original_ars"])),
            snapshot_sha256=str(fila["snapshot_sha256"]),
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            snapshot_json=(
                str(fila["snapshot_json"]) if incluir_json else None
            ),
        )
