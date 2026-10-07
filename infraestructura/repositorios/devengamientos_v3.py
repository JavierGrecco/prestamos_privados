"""Repositorio SQLite de eventos de devengamiento V3-G1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json

from infraestructura.db import BaseDatos
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.motor_pagos_v3 import Devengamiento
from dominio.tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa, ZERO, money, rate

MOTOR_VERSION_DEVENGAMIENTO = "V3-G1"


@dataclass(frozen=True)
class DevengamientoPersistidoV3:
    id: int
    prestamo_id: int
    cuota_id: int | None
    devengamiento: Devengamiento
    huella: str
    motor_version: str
    creado_en: str


class RepositorioDevengamientosSQLiteV3:
    """CRUD append-only para eventos de devengamiento.

    No actualiza ni elimina eventos. La corrección futura debe producir otro
    evento compensatorio, no sobrescribir este registro histórico.
    """

    def __init__(self, db: BaseDatos) -> None:
        self.db = db

    def registrar(
        self,
        *,
        prestamo_id: int,
        cuota_id: int | None,
        devengamiento: Devengamiento,
        motor_version: str = MOTOR_VERSION_DEVENGAMIENTO,
    ) -> DevengamientoPersistidoV3:
        if prestamo_id <= 0:
            raise ErrorValidacion("prestamo_id debe ser positivo")
        if cuota_id is not None and cuota_id <= 0:
            raise ErrorValidacion("cuota_id debe ser positivo")
        if devengamiento.monto <= ZERO:
            raise ErrorValidacion("No se persisten devengamientos de monto cero")
        if devengamiento.fecha_hasta <= devengamiento.fecha_desde:
            raise ErrorValidacion("El evento de devengamiento debe tener un período positivo")
        if not motor_version.strip():
            raise ErrorValidacion("motor_version no puede ser vacío")

        prestamo = self.db.consultar_uno(
            "SELECT id FROM prestamos WHERE id = ?", (prestamo_id,)
        )
        if prestamo is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no existe")

        if cuota_id is not None:
            cuota = self.db.consultar_uno(
                """
                SELECT c.id
                FROM cuotas c
                JOIN versiones_tasa v ON v.id = c.version_id
                WHERE c.id = ? AND v.prestamo_id = ?
                """,
                (cuota_id, prestamo_id),
            )
            if cuota is None:
                raise ErrorValidacion(
                    f"La cuota {cuota_id} no pertenece al préstamo {prestamo_id}"
                )

        huella = _huella(
            prestamo_id=prestamo_id,
            cuota_id=cuota_id,
            devengamiento=devengamiento,
            motor_version=motor_version,
        )
        creado_en = datetime.now().isoformat(timespec="seconds")
        self.db.ejecutar(
            """
            INSERT INTO devengamientos
            (prestamo_id, cuota_id, concepto, monto, fecha_desde, fecha_hasta,
             origen, referencia, base, tasa_anual, modalidad_tasa,
             convencion_dias, dias, fraccion_anual, huella, motor_version, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prestamo_id,
                cuota_id,
                devengamiento.concepto.value,
                str(money(devengamiento.monto)),
                devengamiento.fecha_desde.isoformat(),
                devengamiento.fecha_hasta.isoformat(),
                devengamiento.origen,
                devengamiento.referencia,
                str(money(devengamiento.base)),
                str(rate(devengamiento.tasa_anual)),
                _enum_value(devengamiento.modalidad_tasa),
                _enum_value(devengamiento.convencion_dias),
                int(devengamiento.dias),
                str(devengamiento.fraccion_anual),
                huella,
                motor_version,
                creado_en,
            ),
        )
        dev_id = int(self.db.ultimo_id_insertado())
        return DevengamientoPersistidoV3(
            id=dev_id,
            prestamo_id=prestamo_id,
            cuota_id=cuota_id,
            devengamiento=devengamiento,
            huella=huella,
            motor_version=motor_version,
            creado_en=creado_en,
        )

    def por_cuota(self, cuota_id: int) -> list[DevengamientoPersistidoV3]:
        filas = self.db.consultar(
            "SELECT * FROM devengamientos WHERE cuota_id = ? ORDER BY fecha_desde, fecha_hasta, id",
            (cuota_id,),
        )
        return [_fila(f) for f in filas]

    def por_prestamo_hasta(
        self, prestamo_id: int, hasta: date | None = None
    ) -> list[DevengamientoPersistidoV3]:
        if hasta is None:
            filas = self.db.consultar(
                "SELECT * FROM devengamientos WHERE prestamo_id = ? ORDER BY fecha_hasta, id",
                (prestamo_id,),
            )
        else:
            filas = self.db.consultar(
                """
                SELECT * FROM devengamientos
                WHERE prestamo_id = ? AND fecha_hasta <= ?
                ORDER BY fecha_hasta, id
                """,
                (prestamo_id, hasta.isoformat()),
            )
        return [_fila(f) for f in filas]

    def ultimo_hasta(
        self,
        *,
        cuota_id: int,
        concepto: ConceptoImputacion | None = None,
        origen: str | None = None,
    ) -> date | None:
        condiciones = ["cuota_id = ?"]
        params: list[object] = [cuota_id]
        if concepto is not None:
            condiciones.append("concepto = ?")
            params.append(concepto.value)
        if origen is not None:
            condiciones.append("origen = ?")
            params.append(origen)
        fila = self.db.consultar_uno(
            f"SELECT MAX(fecha_hasta) AS fecha FROM devengamientos WHERE {' AND '.join(condiciones)}",
            tuple(params),
        )
        if fila is None or fila["fecha"] is None:
            return None
        return date.fromisoformat(fila["fecha"])

    def por_huella(self, huella: str) -> DevengamientoPersistidoV3 | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM devengamientos WHERE huella = ?", (huella,)
        )
        return None if fila is None else _fila(fila)


def _huella(*, prestamo_id: int, cuota_id: int | None, devengamiento: Devengamiento, motor_version: str) -> str:
    payload = {
        "prestamo_id": prestamo_id,
        "cuota_id": cuota_id,
        "concepto": devengamiento.concepto.value,
        "monto": str(money(devengamiento.monto)),
        "fecha_desde": devengamiento.fecha_desde.isoformat(),
        "fecha_hasta": devengamiento.fecha_hasta.isoformat(),
        "origen": devengamiento.origen,
        "referencia": devengamiento.referencia,
        "base": str(money(devengamiento.base)),
        "tasa_anual": str(rate(devengamiento.tasa_anual)),
        "modalidad_tasa": _enum_value(devengamiento.modalidad_tasa),
        "convencion_dias": _enum_value(devengamiento.convencion_dias),
        "dias": devengamiento.dias,
        "fraccion_anual": str(devengamiento.fraccion_anual),
        "motor_version": motor_version,
    }
    serializado = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _enum_value(valor: Enum | None) -> str | None:
    return None if valor is None else valor.value


def _fila(fila) -> DevengamientoPersistidoV3:
    modalidad = fila["modalidad_tasa"]
    convencion = fila["convencion_dias"]
    d = Devengamiento(
        concepto=ConceptoImputacion(fila["concepto"]),
        monto=Decimal(str(fila["monto"])),
        fecha_desde=date.fromisoformat(fila["fecha_desde"]),
        fecha_hasta=date.fromisoformat(fila["fecha_hasta"]),
        origen=str(fila["origen"]),
        referencia=fila["referencia"],
        base=Decimal(str(fila["base"])),
        tasa_anual=Decimal(str(fila["tasa_anual"])),
        modalidad_tasa=None if modalidad is None else ModalidadTasa(modalidad),
        convencion_dias=None if convencion is None else ConvencionDias(convencion),
        dias=int(fila["dias"]),
        fraccion_anual=Decimal(str(fila["fraccion_anual"])),
    )
    return DevengamientoPersistidoV3(
        id=int(fila["id"]),
        prestamo_id=int(fila["prestamo_id"]),
        cuota_id=None if fila["cuota_id"] is None else int(fila["cuota_id"]),
        devengamiento=d,
        huella=str(fila["huella"]),
        motor_version=str(fila["motor_version"]),
        creado_en=str(fila["creado_en"]),
    )
