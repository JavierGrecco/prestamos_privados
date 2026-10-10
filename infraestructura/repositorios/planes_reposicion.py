"""Planes de reposición locales con versiones inmutables y trazables."""
from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from dominio import xirr
from dominio.excepciones import ErrorCalculo, ErrorValidacion

from ..db import BaseDatos
from ..excepciones import ErrorTransaccion
from .base import RepositorioBase, ahora_iso, decimal_a_str
from .modelos import (
    AporteReposicion,
    FlujoInversionReposicion,
    ValoracionInversionReposicion,
    ResumenRendimientoInversion,
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
        try:
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
        except ErrorTransaccion as exc:
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise
        return numero

    def cerrar_plan(self, plan_id: int, *, cerrado_por: str) -> None:
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        usuario = str(cerrado_por or "").strip()
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién cierra el plan")
        ahora = ahora_iso()
        try:
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
        except ErrorTransaccion as exc:
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise

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

    def registrar_aporte(
        self,
        plan_id: int,
        *,
        fecha_aporte: date,
        monto_ars: Decimal,
        cotizacion_ars_por_usd: Decimal,
        naturaleza_cotizacion: str,
        fuente_cotizacion: str,
        referencia: str,
        nota: str,
        creado_por: str,
    ) -> int:
        """Registra un aporte propio observado; nunca lo convierte en un pago."""
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        if not isinstance(fecha_aporte, date) or isinstance(fecha_aporte, datetime):
            raise ErrorValidacion("La fecha del aporte no es válida")
        if fecha_aporte > date.today():
            raise ErrorValidacion("Un aporte realizado no puede tener fecha futura")
        if (
            not isinstance(monto_ars, Decimal)
            or not monto_ars.is_finite()
            or monto_ars <= 0
            or monto_ars > Decimal("999999999999999.99")
            or monto_ars != monto_ars.quantize(Decimal("0.01"))
        ):
            raise ErrorValidacion(
                "El aporte en ARS debe ser positivo, no superar 999.999.999.999.999,99 "
                "y tener hasta 2 decimales"
            )
        if (
            not isinstance(cotizacion_ars_por_usd, Decimal)
            or not cotizacion_ars_por_usd.is_finite()
            or cotizacion_ars_por_usd < Decimal("0.000001")
            or cotizacion_ars_por_usd > Decimal("999999999999.999999")
            or cotizacion_ars_por_usd != cotizacion_ars_por_usd.quantize(Decimal("0.000001"))
        ):
            raise ErrorValidacion(
                "La cotización ARS/USD debe estar entre 0,000001 y "
                "999.999.999.999,999999, con hasta 6 decimales"
            )
        naturaleza = str(naturaleza_cotizacion or "").strip().upper()
        if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
            raise ErrorValidacion("La naturaleza de la cotización debe ser OBSERVADA o SUPUESTO")
        fuente = str(fuente_cotizacion or "").strip()
        ref = str(referencia or "").strip()
        observacion = str(nota or "").strip()
        usuario = str(creado_por or "").strip()
        if naturaleza == "OBSERVADA" and not fuente:
            raise ErrorValidacion("Indicá la fuente de la cotización observada")
        if len(fuente) > 160 or len(ref) > 240 or len(observacion) > 1000:
            raise ErrorValidacion("La fuente, referencia o nota supera la longitud permitida")
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién registra el aporte")

        equivalente_usd = (monto_ars / cotizacion_ars_por_usd).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        creado_en = ahora_iso()
        payload = {
            "esquema": 1,
            "tipo_registro": "APORTE_REPOSICION",
            "plan_id": plan_id,
            "fecha_aporte": fecha_aporte,
            "monto_ars": monto_ars,
            "cotizacion_ars_por_usd": cotizacion_ars_por_usd,
            "equivalente_usd": equivalente_usd,
            "naturaleza_cotizacion": naturaleza,
            "fuente_cotizacion": fuente,
            "referencia": ref,
            "nota": observacion,
            "creado_por": usuario,
            "creado_en": creado_en,
        }
        contenido, digest = _serializar_snapshot(payload)
        try:
            with self.db.transaccion():
                plan = self.db.consultar_uno(
                    "SELECT estado, tipo_plan FROM planes_reposicion WHERE id = ?",
                    (plan_id,),
                )
                if plan is None:
                    raise ErrorValidacion("El plan seleccionado no existe")
                if str(plan["tipo_plan"]) != "REPOSICION_INTERNA":
                    raise ErrorValidacion(
                        "Los aportes de reposición solo corresponden a un plan interno"
                    )
                if str(plan["estado"]) != "ACTIVO":
                    raise ErrorValidacion("El plan está cerrado; no admite nuevos aportes")
                self.db.ejecutar(
                    """
                    INSERT INTO aportes_reposicion (
                        plan_id, fecha_aporte, monto_ars, cotizacion_ars_por_usd,
                        equivalente_usd, naturaleza_cotizacion, fuente_cotizacion,
                        referencia, nota, snapshot_json, snapshot_sha256,
                        creado_por, creado_en
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id, fecha_aporte.isoformat(), decimal_a_str(monto_ars),
                        decimal_a_str(cotizacion_ars_por_usd), decimal_a_str(equivalente_usd),
                        naturaleza, fuente or None, ref or None, observacion or None,
                        contenido, digest, usuario, creado_en,
                    ),
                )
                return self.db.ultimo_id_insertado()
        except ErrorTransaccion as exc:
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise

    def listar_aportes(
        self, plan_id: int, limite: int = 200
    ) -> list[AporteReposicion]:
        if self.obtener_plan(plan_id) is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        limite_seguro = self._validar_limite(limite)
        filas = self.db.consultar(
            """
            SELECT * FROM aportes_reposicion
            WHERE plan_id = ?
            ORDER BY fecha_aporte DESC, id DESC
            LIMIT ?
            """,
            (plan_id, limite_seguro),
        )
        return [self._fila_a_aporte(fila, incluir_json=False) for fila in filas]

    def obtener_aporte(self, aporte_id: int) -> AporteReposicion | None:
        if not isinstance(aporte_id, int) or isinstance(aporte_id, bool) or aporte_id <= 0:
            raise ErrorValidacion("El identificador del aporte no es válido")
        fila = self.db.consultar_uno(
            "SELECT * FROM aportes_reposicion WHERE id = ?", (aporte_id,)
        )
        return self._fila_a_aporte(fila, incluir_json=True) if fila else None

    def verificar_aporte(self, aporte: AporteReposicion) -> bool:
        if aporte.snapshot_json is None:
            return False
        if hashlib.sha256(aporte.snapshot_json.encode("utf-8")).hexdigest() != aporte.snapshot_sha256:
            return False
        try:
            return isinstance(json.loads(aporte.snapshot_json), dict)
        except (TypeError, json.JSONDecodeError):
            return False

    @staticmethod
    def _fila_a_aporte(fila, *, incluir_json: bool) -> AporteReposicion:
        return AporteReposicion(
            id=int(fila["id"]),
            plan_id=int(fila["plan_id"]),
            fecha_aporte=date.fromisoformat(str(fila["fecha_aporte"])),
            monto_ars=Decimal(str(fila["monto_ars"])),
            cotizacion_ars_por_usd=Decimal(str(fila["cotizacion_ars_por_usd"])),
            equivalente_usd=Decimal(str(fila["equivalente_usd"])),
            naturaleza_cotizacion=str(fila["naturaleza_cotizacion"]),
            fuente_cotizacion=(
                str(fila["fuente_cotizacion"]) if fila["fuente_cotizacion"] is not None else None
            ),
            referencia=str(fila["referencia"]) if fila["referencia"] is not None else None,
            nota=str(fila["nota"]) if fila["nota"] is not None else None,
            snapshot_sha256=str(fila["snapshot_sha256"]),
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            snapshot_json=str(fila["snapshot_json"]) if incluir_json else None,
        )

    @staticmethod
    def _validar_importe_inversion(
        importe: Decimal,
        *,
        etiqueta: str,
        permitir_cero: bool = False,
    ) -> None:
        minimo = Decimal("0") if permitir_cero else Decimal("0.01")
        if (
            not isinstance(importe, Decimal)
            or not importe.is_finite()
            or importe < minimo
            or importe > Decimal("999999999999999.99")
            or importe != importe.quantize(Decimal("0.01"))
        ):
            comparador = "no negativo" if permitir_cero else "positivo"
            raise ErrorValidacion(
                f"{etiqueta.capitalize()} debe ser {comparador}, no superar "
                "999.999.999.999.999,99 y tener hasta 2 decimales"
            )

    @staticmethod
    def _validar_cotizacion_inversion(cotizacion: Decimal) -> None:
        if (
            not isinstance(cotizacion, Decimal)
            or not cotizacion.is_finite()
            or cotizacion < Decimal("0.000001")
            or cotizacion > Decimal("999999999999.999999")
            or cotizacion != cotizacion.quantize(Decimal("0.000001"))
        ):
            raise ErrorValidacion(
                "La cotización ARS/USD debe estar entre 0,000001 y "
                "999.999.999.999,999999, con hasta 6 decimales"
            )

    @staticmethod
    def _equivalente_a_usd_ref(
        *, moneda: str, monto: Decimal, cotizacion: Decimal | None
    ) -> Decimal:
        if moneda == "USD":
            return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if moneda != "ARS" or cotizacion is None:
            raise ErrorValidacion("La moneda y su cotización de referencia no son compatibles")
        equivalente = (monto / cotizacion).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if equivalente <= 0:
            raise ErrorValidacion(
                "El equivalente USD queda en cero con esa cotización; revise el importe o el tipo de cambio"
            )
        return equivalente

    def registrar_flujo_inversion(
        self,
        plan_id: int,
        *,
        fecha_flujo: date,
        tipo_flujo: str,
        moneda: str,
        monto_original: Decimal,
        cotizacion_ars_por_usd: Decimal | None = None,
        naturaleza_cotizacion: str | None = None,
        fuente_cotizacion: str = "",
        referencia: str = "",
        nota: str = "",
        creado_por: str,
    ) -> int:
        """Registra un flujo externo de inversión sin mezclarlo con aportes de reposición."""
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        if not isinstance(fecha_flujo, date) or isinstance(fecha_flujo, datetime):
            raise ErrorValidacion("La fecha del flujo no es válida")
        if fecha_flujo > date.today():
            raise ErrorValidacion("Un movimiento realizado no puede tener fecha futura")
        tipo = str(tipo_flujo or "").strip().upper()
        if tipo not in {
            "APORTE_INVERSION", "RESCATE", "DISTRIBUCION", "COSTO_IMPUESTO_EXTERNO"
        }:
            raise ErrorValidacion("El tipo de flujo de inversión no está permitido")
        moneda_limpia = str(moneda or "").strip().upper()
        if moneda_limpia not in {"ARS", "USD"}:
            raise ErrorValidacion("La moneda del flujo debe ser ARS o USD")
        self._validar_importe_inversion(monto_original, etiqueta="El importe del flujo")

        naturaleza = str(naturaleza_cotizacion or "").strip().upper()
        fuente = str(fuente_cotizacion or "").strip()
        ref = str(referencia or "").strip()
        observacion = str(nota or "").strip()
        usuario = str(creado_por or "").strip()
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién registra el flujo")
        if len(fuente) > 160 or len(ref) > 240 or len(observacion) > 1000:
            raise ErrorValidacion("La fuente, referencia o nota supera la longitud permitida")

        if moneda_limpia == "USD":
            if cotizacion_ars_por_usd is not None:
                raise ErrorValidacion("Los flujos en USD no llevan cotización ARS/USD")
            if naturaleza not in {"", "NO_APLICA"}:
                raise ErrorValidacion("Los flujos en USD deben usar naturaleza NO_APLICA")
            if fuente:
                raise ErrorValidacion("Los flujos en USD no necesitan fuente de conversión")
            naturaleza = "NO_APLICA"
            fuente = ""
            equivalente_usd = self._equivalente_a_usd_ref(
                moneda="USD", monto=monto_original, cotizacion=None
            )
            cotizacion_db = None
        else:
            if cotizacion_ars_por_usd is None:
                raise ErrorValidacion("Para convertir un flujo en ARS, ingrese la cotización")
            self._validar_cotizacion_inversion(cotizacion_ars_por_usd)
            if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
                raise ErrorValidacion("La cotización de ARS debe ser OBSERVADA o SUPUESTO")
            if naturaleza == "OBSERVADA" and not fuente:
                raise ErrorValidacion("Indicá la fuente de la cotización observada")
            equivalente_usd = self._equivalente_a_usd_ref(
                moneda="ARS", monto=monto_original, cotizacion=cotizacion_ars_por_usd
            )
            cotizacion_db = decimal_a_str(cotizacion_ars_por_usd)

        creado_en = ahora_iso()
        payload = {
            "esquema": 1,
            "tipo_registro": "FLUJO_INVERSION",
            "plan_id": plan_id,
            "fecha_flujo": fecha_flujo,
            "tipo_flujo": tipo,
            "moneda": moneda_limpia,
            "monto_original": monto_original,
            "cotizacion_ars_por_usd": cotizacion_ars_por_usd,
            "equivalente_usd": equivalente_usd,
            "naturaleza_cotizacion": naturaleza,
            "fuente_cotizacion": fuente,
            "referencia": ref,
            "nota": observacion,
            "creado_por": usuario,
            "creado_en": creado_en,
        }
        contenido, digest = _serializar_snapshot(payload)
        try:
            with self.db.transaccion():
                plan = self.db.consultar_uno(
                    "SELECT estado, tipo_plan FROM planes_reposicion WHERE id = ?",
                    (plan_id,),
                )
                if plan is None:
                    raise ErrorValidacion("El plan seleccionado no existe")
                if str(plan["tipo_plan"]) != "REPOSICION_INTERNA":
                    raise ErrorValidacion("Los flujos de inversión solo corresponden a un plan interno")
                if str(plan["estado"]) != "ACTIVO":
                    raise ErrorValidacion("El plan está cerrado; no admite nuevos flujos de inversión")
                self.db.ejecutar(
                    """
                    INSERT INTO flujos_inversion_reposicion (
                        plan_id, fecha_flujo, tipo_flujo, moneda, monto_original,
                        cotizacion_ars_por_usd, equivalente_usd, naturaleza_cotizacion,
                        fuente_cotizacion, referencia, nota, snapshot_json,
                        snapshot_sha256, creado_por, creado_en
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id, fecha_flujo.isoformat(), tipo, moneda_limpia,
                        decimal_a_str(monto_original), cotizacion_db,
                        decimal_a_str(equivalente_usd), naturaleza, fuente or None,
                        ref or None, observacion or None, contenido, digest, usuario, creado_en,
                    ),
                )
                return self.db.ultimo_id_insertado()
        except ErrorTransaccion as exc:
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise

    def listar_flujos_inversion(
        self, plan_id: int, limite: int = 500
    ) -> list[FlujoInversionReposicion]:
        if self.obtener_plan(plan_id) is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        limite_seguro = self._validar_limite(limite)
        filas = self.db.consultar(
            """
            SELECT * FROM flujos_inversion_reposicion
            WHERE plan_id = ?
            ORDER BY fecha_flujo, id
            LIMIT ?
            """,
            (plan_id, limite_seguro),
        )
        return [self._fila_a_flujo_inversion(fila, incluir_json=False) for fila in filas]

    def obtener_flujo_inversion(self, flujo_id: int) -> FlujoInversionReposicion | None:
        if not isinstance(flujo_id, int) or isinstance(flujo_id, bool) or flujo_id <= 0:
            raise ErrorValidacion("El identificador del flujo no es válido")
        fila = self.db.consultar_uno(
            "SELECT * FROM flujos_inversion_reposicion WHERE id = ?",
            (flujo_id,),
        )
        return self._fila_a_flujo_inversion(fila, incluir_json=True) if fila else None

    def verificar_flujo_inversion(self, flujo: FlujoInversionReposicion) -> bool:
        if flujo.snapshot_json is None:
            return False
        if hashlib.sha256(flujo.snapshot_json.encode("utf-8")).hexdigest() != flujo.snapshot_sha256:
            return False
        try:
            return isinstance(json.loads(flujo.snapshot_json), dict)
        except (TypeError, json.JSONDecodeError):
            return False

    def registrar_valoracion_inversion(
        self,
        plan_id: int,
        *,
        fecha_valuacion: date,
        moneda: str,
        valor_original: Decimal,
        cotizacion_ars_por_usd: Decimal | None = None,
        naturaleza_cotizacion: str | None = None,
        fuente_cotizacion: str = "",
        referencia: str = "",
        nota: str = "",
        creado_por: str,
    ) -> int:
        """Registra el valor de mercado declarado del saldo de inversión que aún permanece."""
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        if not isinstance(fecha_valuacion, date) or isinstance(fecha_valuacion, datetime):
            raise ErrorValidacion("La fecha de valuación no es válida")
        if fecha_valuacion > date.today():
            raise ErrorValidacion("Una valuación declarada no puede tener fecha futura")
        moneda_limpia = str(moneda or "").strip().upper()
        if moneda_limpia not in {"ARS", "USD"}:
            raise ErrorValidacion("La moneda de valuación debe ser ARS o USD")
        self._validar_importe_inversion(
            valor_original, etiqueta="El valor de la inversión", permitir_cero=True
        )
        naturaleza = str(naturaleza_cotizacion or "").strip().upper()
        fuente = str(fuente_cotizacion or "").strip()
        ref = str(referencia or "").strip()
        observacion = str(nota or "").strip()
        usuario = str(creado_por or "").strip()
        if not usuario:
            raise ErrorValidacion("Se requiere identificar quién registra la valuación")
        if len(fuente) > 160 or len(ref) > 240 or len(observacion) > 1000:
            raise ErrorValidacion("La fuente, referencia o nota supera la longitud permitida")

        if moneda_limpia == "USD":
            if cotizacion_ars_por_usd is not None:
                raise ErrorValidacion("Una valuación en USD no lleva cotización ARS/USD")
            if naturaleza not in {"", "NO_APLICA"}:
                raise ErrorValidacion("Una valuación en USD debe usar naturaleza NO_APLICA")
            if fuente:
                raise ErrorValidacion("Una valuación en USD no necesita fuente de conversión")
            naturaleza = "NO_APLICA"
            fuente = ""
            equivalente_usd = self._equivalente_a_usd_ref(
                moneda="USD", monto=valor_original, cotizacion=None
            ) if valor_original > 0 else Decimal("0.00")
            cotizacion_db = None
        else:
            if cotizacion_ars_por_usd is None:
                raise ErrorValidacion("Para convertir una valuación en ARS, ingrese la cotización")
            self._validar_cotizacion_inversion(cotizacion_ars_por_usd)
            if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
                raise ErrorValidacion("La cotización de ARS debe ser OBSERVADA o SUPUESTO")
            if naturaleza == "OBSERVADA" and not fuente:
                raise ErrorValidacion("Indicá la fuente de la cotización observada")
            equivalente_usd = (
                self._equivalente_a_usd_ref(
                    moneda="ARS", monto=valor_original, cotizacion=cotizacion_ars_por_usd
                )
                if valor_original > 0
                else Decimal("0.00")
            )
            cotizacion_db = decimal_a_str(cotizacion_ars_por_usd)

        creado_en = ahora_iso()
        payload = {
            "esquema": 1,
            "tipo_registro": "VALORACION_INVERSION",
            "plan_id": plan_id,
            "fecha_valuacion": fecha_valuacion,
            "moneda": moneda_limpia,
            "valor_original": valor_original,
            "cotizacion_ars_por_usd": cotizacion_ars_por_usd,
            "equivalente_usd": equivalente_usd,
            "naturaleza_cotizacion": naturaleza,
            "fuente_cotizacion": fuente,
            "referencia": ref,
            "nota": observacion,
            "creado_por": usuario,
            "creado_en": creado_en,
        }
        contenido, digest = _serializar_snapshot(payload)
        try:
            with self.db.transaccion():
                plan = self.db.consultar_uno(
                    "SELECT estado, tipo_plan FROM planes_reposicion WHERE id = ?",
                    (plan_id,),
                )
                if plan is None:
                    raise ErrorValidacion("El plan seleccionado no existe")
                if str(plan["tipo_plan"]) != "REPOSICION_INTERNA":
                    raise ErrorValidacion("Las valuaciones solo corresponden a un plan interno")
                if str(plan["estado"]) != "ACTIVO":
                    raise ErrorValidacion("El plan está cerrado; no admite nuevas valuaciones")
                self.db.ejecutar(
                    """
                    INSERT INTO valuaciones_inversion_reposicion (
                        plan_id, fecha_valuacion, moneda, valor_original,
                        cotizacion_ars_por_usd, equivalente_usd, naturaleza_cotizacion,
                        fuente_cotizacion, referencia, nota, snapshot_json,
                        snapshot_sha256, creado_por, creado_en
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id, fecha_valuacion.isoformat(), moneda_limpia,
                        decimal_a_str(valor_original), cotizacion_db,
                        decimal_a_str(equivalente_usd), naturaleza, fuente or None,
                        ref or None, observacion or None, contenido, digest, usuario, creado_en,
                    ),
                )
                return self.db.ultimo_id_insertado()
        except ErrorTransaccion as exc:
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int = 200
    ) -> list[ValoracionInversionReposicion]:
        if self.obtener_plan(plan_id) is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        limite_seguro = self._validar_limite(limite)
        filas = self.db.consultar(
            """
            SELECT * FROM valuaciones_inversion_reposicion
            WHERE plan_id = ?
            ORDER BY fecha_valuacion DESC, id DESC
            LIMIT ?
            """,
            (plan_id, limite_seguro),
        )
        return [self._fila_a_valoracion_inversion(fila, incluir_json=False) for fila in filas]

    def obtener_valoracion_inversion(
        self, valoracion_id: int
    ) -> ValoracionInversionReposicion | None:
        if not isinstance(valoracion_id, int) or isinstance(valoracion_id, bool) or valoracion_id <= 0:
            raise ErrorValidacion("El identificador de la valuación no es válido")
        fila = self.db.consultar_uno(
            "SELECT * FROM valuaciones_inversion_reposicion WHERE id = ?",
            (valoracion_id,),
        )
        return (
            self._fila_a_valoracion_inversion(fila, incluir_json=True)
            if fila else None
        )

    def verificar_valoracion_inversion(
        self, valoracion: ValoracionInversionReposicion
    ) -> bool:
        if valoracion.snapshot_json is None:
            return False
        if hashlib.sha256(valoracion.snapshot_json.encode("utf-8")).hexdigest() != valoracion.snapshot_sha256:
            return False
        try:
            return isinstance(json.loads(valoracion.snapshot_json), dict)
        except (TypeError, json.JSONDecodeError):
            return False

    def resumen_rendimiento_inversion(
        self, plan_id: int
    ) -> ResumenRendimientoInversion:
        plan = self.obtener_plan(plan_id)
        if plan is None:
            raise ErrorValidacion("El plan seleccionado no existe")
        if plan.tipo_plan != "REPOSICION_INTERNA":
            raise ErrorValidacion("El rendimiento de inversión solo corresponde a un plan interno")

        cuenta_flujos = self.db.consultar_uno(
            "SELECT COUNT(*) AS n FROM flujos_inversion_reposicion WHERE plan_id = ?",
            (plan_id,),
        )
        cuenta_valuaciones = self.db.consultar_uno(
            "SELECT COUNT(*) AS n FROM valuaciones_inversion_reposicion WHERE plan_id = ?",
            (plan_id,),
        )
        if int(cuenta_flujos["n"]) > 100 or int(cuenta_valuaciones["n"]) > 100:
            raise ErrorValidacion(
                "El plan tiene más de 100 flujos o valuaciones; revise el historial antes del resumen automático"
            )
        flujos = self.listar_flujos_inversion(plan_id, limite=100)
        valuaciones = self.listar_valuaciones_inversion(plan_id, limite=100)
        for flujo in flujos:
            completo = self.obtener_flujo_inversion(flujo.id)
            if completo is None or not self.verificar_flujo_inversion(completo):
                raise ErrorValidacion(f"No se pudo verificar la integridad del flujo #{flujo.id}")
        for valoracion in valuaciones:
            completo = self.obtener_valoracion_inversion(valoracion.id)
            if completo is None or not self.verificar_valoracion_inversion(completo):
                raise ErrorValidacion(
                    f"No se pudo verificar la integridad de la valuación #{valoracion.id}"
                )

        aportes = sum(
            (f.equivalente_usd for f in flujos if f.tipo_flujo == "APORTE_INVERSION"),
            Decimal("0"),
        )
        cobros = sum(
            (f.equivalente_usd for f in flujos if f.tipo_flujo in {"RESCATE", "DISTRIBUCION"}),
            Decimal("0"),
        )
        costos = sum(
            (f.equivalente_usd for f in flujos if f.tipo_flujo == "COSTO_IMPUESTO_EXTERNO"),
            Decimal("0"),
        )
        fechas = [f.fecha_flujo for f in flujos]
        ultima = valuaciones[0] if valuaciones else None
        fecha_inicio = min(fechas) if fechas else None
        valor_final = ultima.equivalente_usd if ultima is not None else None
        resultado_total = None
        tasa = None
        mensaje = "Registrá una valuación de la inversión para calcular el rendimiento reportado."
        if ultima is not None:
            if flujos and ultima.fecha_valuacion < max(f.fecha_flujo for f in flujos):
                mensaje = (
                    "La última valuación es anterior al último movimiento. "
                    "Registrá una valuación igual o posterior para calcular el resultado."
                )
            else:
                if not any(f.tipo_flujo == "APORTE_INVERSION" for f in flujos):
                    mensaje = (
                        "Registrá al menos un aporte efectivamente destinado a la inversión "
                        "antes de interpretar su rendimiento."
                    )
                else:
                    resultado_total = cobros + (valor_final or Decimal("0")) - aportes - costos
                    salidas = [
                        (f.fecha_flujo, -f.equivalente_usd)
                        if f.tipo_flujo in {"APORTE_INVERSION", "COSTO_IMPUESTO_EXTERNO"}
                        else (f.fecha_flujo, f.equivalente_usd)
                        for f in flujos
                    ]
                    salidas.append((ultima.fecha_valuacion, valor_final or Decimal("0")))
                    try:
                        tasa = xirr(salidas)
                        mensaje = "XIRR anualizada calculada con los flujos y la última valuación declarados."
                    except (ErrorValidacion, ErrorCalculo, ArithmeticError, ValueError) as exc:
                        tasa = None
                        mensaje = f"No se pudo calcular una XIRR fiable con estos datos: {exc}"
        return ResumenRendimientoInversion(
            cantidad_flujos=len(flujos),
            cantidad_valuaciones=len(valuaciones),
            fecha_inicio=fecha_inicio,
            fecha_valuacion=ultima.fecha_valuacion if ultima is not None else None,
            aportes_inversion_usd_ref=aportes,
            cobros_y_rescates_usd_ref=cobros,
            costos_externos_usd_ref=costos,
            valor_mercado_final_usd_ref=valor_final,
            resultado_total_usd_ref=resultado_total,
            xirr_anual=tasa,
            mensaje_xirr=mensaje,
        )

    @staticmethod
    def _fila_a_flujo_inversion(
        fila, *, incluir_json: bool
    ) -> FlujoInversionReposicion:
        return FlujoInversionReposicion(
            id=int(fila["id"]),
            plan_id=int(fila["plan_id"]),
            fecha_flujo=date.fromisoformat(str(fila["fecha_flujo"])),
            tipo_flujo=str(fila["tipo_flujo"]),
            moneda=str(fila["moneda"]),
            monto_original=Decimal(str(fila["monto_original"])),
            cotizacion_ars_por_usd=(
                Decimal(str(fila["cotizacion_ars_por_usd"]))
                if fila["cotizacion_ars_por_usd"] is not None else None
            ),
            equivalente_usd=Decimal(str(fila["equivalente_usd"])),
            naturaleza_cotizacion=str(fila["naturaleza_cotizacion"]),
            fuente_cotizacion=str(fila["fuente_cotizacion"]) if fila["fuente_cotizacion"] is not None else None,
            referencia=str(fila["referencia"]) if fila["referencia"] is not None else None,
            nota=str(fila["nota"]) if fila["nota"] is not None else None,
            snapshot_sha256=str(fila["snapshot_sha256"]),
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            snapshot_json=str(fila["snapshot_json"]) if incluir_json else None,
        )

    @staticmethod
    def _fila_a_valoracion_inversion(
        fila, *, incluir_json: bool
    ) -> ValoracionInversionReposicion:
        return ValoracionInversionReposicion(
            id=int(fila["id"]),
            plan_id=int(fila["plan_id"]),
            fecha_valuacion=date.fromisoformat(str(fila["fecha_valuacion"])),
            moneda=str(fila["moneda"]),
            valor_original=Decimal(str(fila["valor_original"])),
            cotizacion_ars_por_usd=(
                Decimal(str(fila["cotizacion_ars_por_usd"]))
                if fila["cotizacion_ars_por_usd"] is not None else None
            ),
            equivalente_usd=Decimal(str(fila["equivalente_usd"])),
            naturaleza_cotizacion=str(fila["naturaleza_cotizacion"]),
            fuente_cotizacion=str(fila["fuente_cotizacion"]) if fila["fuente_cotizacion"] is not None else None,
            referencia=str(fila["referencia"]) if fila["referencia"] is not None else None,
            nota=str(fila["nota"]) if fila["nota"] is not None else None,
            snapshot_sha256=str(fila["snapshot_sha256"]),
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            snapshot_json=str(fila["snapshot_json"]) if incluir_json else None,
        )

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
