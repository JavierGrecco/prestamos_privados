"""Registro transaccional de propuestas de corrección, sin editar hechos originales.

El servicio deja una nueva evidencia auditable. No aplica todavía el snapshot
corregido a los cálculos ni a los reportes; esos consumidores deben integrarse
por separado para evitar cambios financieros implícitos.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any

from aplicacion.seguridad.capacidades import (
    CAP_PROPONER_CORRECCIONES_AUDITABLES,
    CAP_VER_CORRECCIONES_AUDITABLES,
    PoliticaCapacidades,
)
from aplicacion.seguridad.identidad import IdentidadSesion
from aplicacion.puertos.correcciones_auditables import (
    CorreccionAuditable,
    NuevaCorreccionAuditable,
    RepositorioCorreccionesAuditables,
)
from dominio.excepciones import ErrorValidacion


_MAXIMO_JSON_BYTES = 4_000_000
_HASH_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TIPOS_REGISTRO = {
    "APORTE_REPOSICION": "APORTE_REPOSICION",
    "FLUJO_INVERSION_REPOSICION": "FLUJO_INVERSION",
    "VALUACION_INVERSION_REPOSICION": "VALORACION_INVERSION",
}
_CAMPOS_INMUTABLES = (
    "esquema",
    "tipo_registro",
    "plan_id",
    "creado_por",
    "creado_en",
)
_CENTAVO = Decimal("0.01")
_SEISMIL = Decimal("0.000001")
_MAXIMO_IMPORTE = Decimal("999999999999999.99")
_MAXIMA_COTIZACION = Decimal("999999999999.999999")




def _normalizar_valor(valor: Any) -> Any:
    """Normaliza valores determinísticamente y prohíbe float en snapshots."""
    if valor is None or isinstance(valor, (str, int, bool)):
        return valor
    if isinstance(valor, datetime):
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ErrorValidacion("Las fechas y horas del snapshot deben incluir zona horaria")
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ErrorValidacion("El snapshot no admite valores Decimal no finitos")
        return format(valor, "f")
    if isinstance(valor, Enum):
        return _normalizar_valor(valor.value)
    if isinstance(valor, float):
        raise ErrorValidacion("El snapshot no admite float; usá Decimal para importes")
    if isinstance(valor, dict):
        normalizado: dict[str, Any] = {}
        for clave, contenido in valor.items():
            if not isinstance(clave, str):
                raise ErrorValidacion("Las claves del snapshot deben ser texto")
            normalizado[clave] = _normalizar_valor(contenido)
        return normalizado
    if isinstance(valor, (tuple, list)):
        return [_normalizar_valor(elemento) for elemento in valor]
    raise ErrorValidacion(
        f"El snapshot contiene un tipo no admitido: {type(valor).__name__}"
    )


def _serializar_snapshot(datos: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    if not isinstance(datos, dict):
        raise ErrorValidacion("El snapshot corregido debe ser un objeto")
    normalizado = _normalizar_valor(datos)
    contenido = json.dumps(
        normalizado,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(contenido.encode("utf-8")) > _MAXIMO_JSON_BYTES:
        raise ErrorValidacion("El snapshot supera el tamaño máximo de 4 MB")
    digest = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    return contenido, normalizado, digest


def _decimal_snapshot(datos: dict[str, Any], campo: str) -> Decimal:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorValidacion(f"El campo financiero '{campo}' debe ser un decimal serializado como texto")
    try:
        resultado = Decimal(valor)
    except (InvalidOperation, ValueError) as exc:
        raise ErrorValidacion(f"El campo financiero '{campo}' no es un decimal válido") from exc
    if not resultado.is_finite():
        raise ErrorValidacion(f"El campo financiero '{campo}' debe ser finito")
    return resultado


def _validar_importe(valor: Decimal, campo: str, *, permitir_cero: bool = False) -> None:
    minimo = Decimal("0") if permitir_cero else _CENTAVO
    if valor < minimo or valor > _MAXIMO_IMPORTE or valor != valor.quantize(_CENTAVO):
        regla = "no negativo" if permitir_cero else "positivo"
        raise ErrorValidacion(
            f"El campo '{campo}' debe ser {regla}, tener hasta 2 decimales "
            "y no superar 999.999.999.999.999,99"
        )


def _validar_cotizacion(valor: Decimal) -> None:
    if valor < _SEISMIL or valor > _MAXIMA_COTIZACION or valor != valor.quantize(_SEISMIL):
        raise ErrorValidacion(
            "La cotización debe estar entre 0,000001 y 999.999.999.999,999999, "
            "con hasta 6 decimales"
        )


def _validar_fecha(datos: dict[str, Any], campo: str) -> None:
    valor = datos.get(campo)
    if not isinstance(valor, str):
        raise ErrorValidacion(f"La fecha '{campo}' debe estar en formato ISO")
    try:
        fecha = date.fromisoformat(valor)
    except ValueError as exc:
        raise ErrorValidacion(f"La fecha '{campo}' no es válida") from exc
    if fecha > date.today():
        raise ErrorValidacion(f"La fecha '{campo}' no puede estar en el futuro")


def _validar_equivalente(observado: Decimal, esperado: Decimal, *, puede_ser_cero: bool) -> None:
    if observado != esperado:
        raise ErrorValidacion(
            "El equivalente USD no coincide con el importe y la cotización del snapshot corregido"
        )
    if observado < 0 or (not puede_ser_cero and observado <= 0):
        raise ErrorValidacion("El equivalente USD corregido queda fuera del rango permitido")


def _validar_snapshot_corregido(
    entidad_tipo: str,
    original_json: str,
    corregido: dict[str, Any],
) -> None:
    try:
        original = json.loads(original_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ErrorValidacion("El snapshot original no contiene JSON válido") from exc
    if not isinstance(original, dict):
        raise ErrorValidacion("El snapshot original no es un objeto")

    if set(original) != set(corregido):
        raise ErrorValidacion(
            "La corrección debe conservar todos los campos del snapshot original"
        )
    for campo in _CAMPOS_INMUTABLES:
        if campo in original and corregido[campo] != original[campo]:
            raise ErrorValidacion(
                f"La corrección no puede modificar el campo de trazabilidad '{campo}'"
            )

    tipo_registro = _TIPOS_REGISTRO[entidad_tipo]
    if corregido.get("tipo_registro") != tipo_registro:
        raise ErrorValidacion("El tipo de registro del snapshot no corresponde a la entidad")

    if entidad_tipo == "APORTE_REPOSICION":
        _validar_fecha(corregido, "fecha_aporte")
        monto = _decimal_snapshot(corregido, "monto_ars")
        cotizacion = _decimal_snapshot(corregido, "cotizacion_ars_por_usd")
        equivalente = _decimal_snapshot(corregido, "equivalente_usd")
        _validar_importe(monto, "monto_ars")
        _validar_cotizacion(cotizacion)
        _validar_importe(equivalente, "equivalente_usd", permitir_cero=True)
        naturaleza = corregido.get("naturaleza_cotizacion")
        fuente = str(corregido.get("fuente_cotizacion") or "").strip()
        if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
            raise ErrorValidacion("La naturaleza de la cotización del aporte no es válida")
        if naturaleza == "OBSERVADA" and not fuente:
            raise ErrorValidacion("Un aporte con cotización observada requiere una fuente")
        _validar_equivalente(
            equivalente,
            (monto / cotizacion).quantize(_CENTAVO, rounding=ROUND_HALF_UP),
            puede_ser_cero=True,
        )
        return

    if entidad_tipo == "FLUJO_INVERSION_REPOSICION":
        _validar_fecha(corregido, "fecha_flujo")
        monto = _decimal_snapshot(corregido, "monto_original")
        equivalente = _decimal_snapshot(corregido, "equivalente_usd")
        _validar_importe(monto, "monto_original")
        _validar_importe(equivalente, "equivalente_usd", permitir_cero=True)
        if corregido.get("tipo_flujo") not in {
            "APORTE_INVERSION", "RESCATE", "DISTRIBUCION", "COSTO_IMPUESTO_EXTERNO"
        }:
            raise ErrorValidacion("El tipo de flujo de inversión corregido no es válido")
        moneda = corregido.get("moneda")
        naturaleza = corregido.get("naturaleza_cotizacion")
        fuente = str(corregido.get("fuente_cotizacion") or "").strip()
        cotizacion_raw = corregido.get("cotizacion_ars_por_usd")
        if moneda == "USD":
            if cotizacion_raw is not None or naturaleza != "NO_APLICA" or fuente:
                raise ErrorValidacion("Un flujo USD debe usar NO_APLICA y no llevar cotización ni fuente")
            esperado = monto.quantize(_CENTAVO, rounding=ROUND_HALF_UP)
        elif moneda == "ARS":
            cotizacion = _decimal_snapshot(corregido, "cotizacion_ars_por_usd")
            _validar_cotizacion(cotizacion)
            if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
                raise ErrorValidacion("La naturaleza de la cotización del flujo no es válida")
            if naturaleza == "OBSERVADA" and not fuente:
                raise ErrorValidacion("Un flujo con cotización observada requiere una fuente")
            esperado = (monto / cotizacion).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
        else:
            raise ErrorValidacion("La moneda del flujo corregido debe ser ARS o USD")
        _validar_equivalente(equivalente, esperado, puede_ser_cero=False)
        return

    _validar_fecha(corregido, "fecha_valuacion")
    valor = _decimal_snapshot(corregido, "valor_original")
    equivalente = _decimal_snapshot(corregido, "equivalente_usd")
    _validar_importe(valor, "valor_original", permitir_cero=True)
    _validar_importe(equivalente, "equivalente_usd", permitir_cero=True)
    moneda = corregido.get("moneda")
    naturaleza = corregido.get("naturaleza_cotizacion")
    fuente = str(corregido.get("fuente_cotizacion") or "").strip()
    cotizacion_raw = corregido.get("cotizacion_ars_por_usd")
    if moneda == "USD":
        if cotizacion_raw is not None or naturaleza != "NO_APLICA" or fuente:
            raise ErrorValidacion("Una valuación USD debe usar NO_APLICA y no llevar cotización ni fuente")
        esperado = valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)
    elif moneda == "ARS":
        cotizacion = _decimal_snapshot(corregido, "cotizacion_ars_por_usd")
        _validar_cotizacion(cotizacion)
        if naturaleza not in {"OBSERVADA", "SUPUESTO"}:
            raise ErrorValidacion("La naturaleza de la cotización de la valuación no es válida")
        if naturaleza == "OBSERVADA" and not fuente:
            raise ErrorValidacion("Una valuación con cotización observada requiere una fuente")
        esperado = (
            Decimal("0.00")
            if valor == 0
            else (valor / cotizacion).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
        )
    else:
        raise ErrorValidacion("La moneda de la valuación corregida debe ser ARS o USD")
    _validar_equivalente(equivalente, esperado, puede_ser_cero=True)


class ServicioCorreccionesAuditables:
    """Registra y consulta propuestas de corrección con integridad e idempotencia."""

    def __init__(
        self,
        repositorio: RepositorioCorreccionesAuditables,
        *,
        identidad: IdentidadSesion,
        politica_capacidades: PoliticaCapacidades | None = None,
    ) -> None:
        if repositorio is None:
            raise TypeError("El servicio requiere un repositorio de correcciones")
        if not isinstance(identidad, IdentidadSesion):
            raise TypeError("El servicio requiere una IdentidadSesion resuelta por la aplicación")
        if not identidad.disponible or not identidad.proveedor.strip():
            raise ValueError("La identidad debe incluir subject y proveedor")
        self._repositorio = repositorio
        self._identidad = identidad
        self._politica_capacidades = politica_capacidades or PoliticaCapacidades()

    def _exigir_capacidad(self, capacidad: str) -> None:
        if not self._identidad.autenticada:
            raise PermissionError(
                "Se requiere una identidad autenticada para consultar o proponer correcciones"
            )
        self._politica_capacidades.exigir(self._identidad, capacidad)

    def _actor_auditado(self) -> str:
        actor = f"{self._identidad.proveedor.strip()}:{self._identidad.subject.strip()}"
        if not 1 <= len(actor) <= 120:
            raise ErrorValidacion(
                "La identidad autenticada supera el tamaño permitido para la auditoría"
            )
        return actor

    def registrar_propuesta(
        self,
        *,
        entidad_tipo: str,
        entidad_id: int,
        hash_original: str,
        snapshot_corregido: dict[str, Any],
        motivo: str,
        clave_idempotencia: str,
        correccion_anterior_id: int | None = None,
    ) -> CorreccionAuditable:
        self._exigir_capacidad(CAP_PROPONER_CORRECCIONES_AUDITABLES)
        actor = self._actor_auditado()
        tipo = str(entidad_tipo or "").strip().upper()
        if tipo not in _TIPOS_REGISTRO:
            raise ErrorValidacion("El tipo de entidad no admite correcciones auditables")
        if not isinstance(entidad_id, int) or isinstance(entidad_id, bool) or entidad_id <= 0:
            raise ErrorValidacion("El identificador del registro original no es válido")
        if not isinstance(hash_original, str) or not _HASH_SHA256.fullmatch(hash_original):
            raise ErrorValidacion("El hash original debe ser un SHA-256 hexadecimal en minúsculas")
        motivo_limpio = str(motivo or "").strip()
        if not 3 <= len(motivo_limpio) <= 1000:
            raise ErrorValidacion("El motivo debe tener entre 3 y 1000 caracteres")
        clave = str(clave_idempotencia or "").strip()
        if not 8 <= len(clave) <= 160:
            raise ErrorValidacion("La clave de idempotencia debe tener entre 8 y 160 caracteres")
        if correccion_anterior_id is not None and (
            not isinstance(correccion_anterior_id, int)
            or isinstance(correccion_anterior_id, bool)
            or correccion_anterior_id <= 0
        ):
            raise ErrorValidacion("El identificador de la corrección anterior no es válido")

        snapshot_json, snapshot_normalizado, digest_corregido = _serializar_snapshot(
            snapshot_corregido
        )
        with self._repositorio.transaccion() as unidad:
            existente = unidad.obtener_por_clave(clave)
            if existente is not None:
                coincide = (
                    existente.entidad_tipo == tipo
                    and existente.entidad_id == entidad_id
                    and existente.hash_original == hash_original
                    and existente.snapshot_corregido_json == snapshot_json
                    and existente.hash_corregido == digest_corregido
                    and existente.motivo == motivo_limpio
                    and existente.corregido_por == actor
                    and existente.correccion_anterior_id == correccion_anterior_id
                )
                if not coincide:
                    raise ErrorValidacion(
                        "La clave de idempotencia ya se usó con una solicitud diferente"
                    )
                return existente

            original = unidad.obtener_snapshot_original(tipo, entidad_id)
            if original is None:
                raise ErrorValidacion("El registro original no existe")
            json_original = original.snapshot_json
            hash_guardado = original.snapshot_sha256
            hash_calculado = hashlib.sha256(json_original.encode("utf-8")).hexdigest()
            if hash_calculado != hash_guardado:
                raise ErrorValidacion(
                    "El snapshot original no supera la verificación de integridad; no se registró la corrección"
                )
            if hash_original != hash_guardado:
                raise ErrorValidacion(
                    "El hash original está desactualizado; volvé a consultar el registro antes de corregirlo"
                )
            _validar_snapshot_corregido(
                tipo, json_original, snapshot_normalizado
            )

            ultima = unidad.obtener_ultima_correccion(tipo, entidad_id)
            if ultima is None:
                if correccion_anterior_id is not None:
                    raise ErrorValidacion(
                        "No existe una corrección previa para el registro indicado"
                    )
            else:
                if ultima.hash_original != hash_original:
                    raise ErrorValidacion(
                        "La cadena de correcciones tiene una huella original inconsistente"
                    )
                if correccion_anterior_id != ultima.id:
                    raise ErrorValidacion(
                        "El registro ya tiene una corrección; indicá su identificador como corrección anterior"
                    )

            propuesta_nueva = NuevaCorreccionAuditable(
                entidad_tipo=tipo,
                entidad_id=entidad_id,
                hash_original=hash_original,
                snapshot_corregido_json=snapshot_json,
                hash_corregido=digest_corregido,
                motivo=motivo_limpio,
                corregido_por=actor,
                corregido_en_utc=datetime.now(timezone.utc).isoformat(),
                clave_idempotencia=clave,
                correccion_anterior_id=correccion_anterior_id,
            )
            return unidad.insertar(propuesta_nueva)

    def listar_recientes(
        self, *, limite: int = 200
    ) -> tuple[CorreccionAuditable, ...]:
        """Lista propuestas recientes y verifica la cadena completa de cada registro."""
        self._exigir_capacidad(CAP_VER_CORRECCIONES_AUDITABLES)
        if (
            not isinstance(limite, int)
            or isinstance(limite, bool)
            or limite < 1
            or limite > 500
        ):
            raise ErrorValidacion("El límite de propuestas debe estar entre 1 y 500")

        referencias = self._repositorio.listar_referencias_recientes(limite)
        if not referencias:
            return ()

        # Verificamos la cadena completa por entidad aunque la lista visible sea
        # una ventana reciente. El límite no debe ocultar una ruptura anterior.
        entidades = tuple(
            dict.fromkeys(
                (referencia.entidad_tipo, referencia.entidad_id)
                for referencia in referencias
            )
        )
        por_id: dict[int, CorreccionAuditable] = {}
        for entidad_tipo, entidad_id in entidades:
            for propuesta in self.listar_historial(
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
            ):
                por_id[propuesta.id] = propuesta

        recientes: list[CorreccionAuditable] = []
        for referencia in referencias:
            propuesta = por_id.get(referencia.id)
            if propuesta is None:
                raise ErrorValidacion(
                    f"No se pudo verificar la propuesta reciente #{referencia.id}"
                )
            recientes.append(propuesta)
        return tuple(recientes)

    def obtener_snapshot_original(
        self, propuesta: CorreccionAuditable
    ) -> dict[str, Any]:
        """Obtiene el snapshot original solo si sigue íntegro y corresponde a la propuesta."""
        self._exigir_capacidad(CAP_VER_CORRECCIONES_AUDITABLES)
        if not isinstance(propuesta, CorreccionAuditable):
            raise TypeError("Se requiere una propuesta auditable obtenida del servicio")

        existente = self._repositorio.obtener(propuesta.id)
        if existente is None or existente != propuesta:
            raise ErrorValidacion(
                "La propuesta ya no coincide con la evidencia persistida"
            )

        historial = self.listar_historial(
            entidad_tipo=propuesta.entidad_tipo,
            entidad_id=propuesta.entidad_id,
        )
        if not any(item.id == propuesta.id for item in historial):
            raise ErrorValidacion("La propuesta no pertenece al historial verificado")

        tipo = propuesta.entidad_tipo
        if tipo not in _TIPOS_REGISTRO:
            raise ErrorValidacion("El tipo de entidad no admite correcciones auditables")
        original = self._repositorio.obtener_snapshot_original(
            tipo, propuesta.entidad_id
        )
        if original is None:
            raise ErrorValidacion("El registro financiero original ya no existe")

        contenido_original = original.snapshot_json
        hash_calculado = hashlib.sha256(contenido_original.encode("utf-8")).hexdigest()
        if (
            hash_calculado != original.snapshot_sha256
            or hash_calculado != propuesta.hash_original
        ):
            raise ErrorValidacion(
                "El snapshot original cambió o perdió integridad; no se puede mostrar una comparación confiable"
            )
        try:
            snapshot = json.loads(contenido_original)
        except json.JSONDecodeError as exc:
            raise ErrorValidacion("El snapshot original no contiene JSON válido") from exc
        if not isinstance(snapshot, dict):
            raise ErrorValidacion("El snapshot original no es un objeto")
        return snapshot

    def listar_historial(
        self, *, entidad_tipo: str, entidad_id: int
    ) -> tuple[CorreccionAuditable, ...]:
        """Devuelve el historial solo después de verificar hashes y encadenamiento."""
        self._exigir_capacidad(CAP_VER_CORRECCIONES_AUDITABLES)
        tipo = str(entidad_tipo or "").strip().upper()
        if tipo not in _TIPOS_REGISTRO:
            raise ErrorValidacion("El tipo de entidad no admite correcciones auditables")
        if not isinstance(entidad_id, int) or isinstance(entidad_id, bool) or entidad_id <= 0:
            raise ErrorValidacion("El identificador del registro original no es válido")

        filas = self._repositorio.listar_historial(tipo, entidad_id)
        historial: list[CorreccionAuditable] = []
        hash_original_base: str | None = None
        correccion_anterior_esperada: int | None = None
        for registro in filas:
            contenido = registro.snapshot_corregido_json.encode("utf-8")
            hash_calculado = hashlib.sha256(contenido).hexdigest()
            if hash_calculado != registro.hash_corregido:
                raise ErrorValidacion(
                    f"La corrección #{registro.id} no supera la verificación de su hash"
                )
            try:
                snapshot = json.loads(registro.snapshot_corregido_json)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ErrorValidacion(
                    f"El snapshot de la corrección #{registro.id} no es JSON válido"
                ) from exc
            if not isinstance(snapshot, dict):
                raise ErrorValidacion(
                    f"El snapshot de la corrección #{registro.id} no es un objeto"
                )
            if registro.correccion_anterior_id != correccion_anterior_esperada:
                raise ErrorValidacion(
                    f"La cadena de correcciones está rota en el registro #{registro.id}"
                )
            if hash_original_base is None:
                hash_original_base = registro.hash_original
            elif registro.hash_original != hash_original_base:
                raise ErrorValidacion(
                    f"La huella original cambia dentro de la cadena de correcciones #{registro.id}"
                )
            historial.append(registro)
            correccion_anterior_esperada = registro.id
        return tuple(historial)
