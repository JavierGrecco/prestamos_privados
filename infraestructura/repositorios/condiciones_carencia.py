"""Repositorio de snapshots contractuales de carencia, append-only."""
from __future__ import annotations

import json
from decimal import Decimal

from dominio import CondicionesCarencia, hash_snapshot, json_canonico, verificar_hash_snapshot
from dominio.excepciones import ErrorValidacion
from dominio.tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion

from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    fecha_a_iso,
    iso_a_fecha,
    decimal_a_str,
    str_a_decimal,
)
from .modelos import CondicionesCarenciaPersistidas


class CondicionesCarenciaRepo(RepositorioBase):
    """Lee y agrega versiones contractuales sin mutar las existentes."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def guardar_snapshot(
        self,
        *,
        prestamo_id: int,
        version_tasa_id: int,
        condiciones: CondicionesCarencia,
        creado_por: str,
    ) -> int:
        """Guarda un snapshot solo si coincide con el préstamo y la versión de tasa.

        El método se puede invocar dentro de la transacción del alta completa.
        Si se invoca de forma aislada, su INSERT también es atómico. Una nueva
        condición obtiene la siguiente versión; nunca se actualiza un snapshot.
        """
        if not creado_por or not creado_por.strip():
            raise ErrorValidacion("Se requiere identificar quién acordó el contrato")

        prestamo = self.db.consultar_uno(
            """
            SELECT id, capital_original, plazo_meses, sistema,
                   convencion_dias, fecha_inicio
            FROM prestamos WHERE id = ?
            """,
            (prestamo_id,),
        )
        if prestamo is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no existe")

        version_tasa = self.db.consultar_uno(
            """
            SELECT id, prestamo_id, tasa_anual, modalidad_tasa, fecha_desde
            FROM versiones_tasa WHERE id = ?
            """,
            (version_tasa_id,),
        )
        if version_tasa is None or int(version_tasa["prestamo_id"]) != prestamo_id:
            raise ErrorValidacion(
                "La versión de tasa no pertenece al préstamo indicado"
            )

        if str_a_decimal(prestamo["capital_original"]) != condiciones.capital_original:
            raise ErrorValidacion("El capital del snapshot no coincide con el préstamo")
        if int(prestamo["plazo_meses"]) != condiciones.plazo_amortizacion_meses:
            raise ErrorValidacion("El plazo del snapshot no coincide con el préstamo")
        if iso_a_fecha(prestamo["fecha_inicio"]) != condiciones.fecha_desembolso:
            raise ErrorValidacion(
                "La fecha de desembolso del snapshot no coincide con la del préstamo"
            )
        if str(prestamo["sistema"]).upper() != condiciones.sistema.name:
            raise ErrorValidacion("El sistema de amortización no coincide con el préstamo")

        convencion_db = str(prestamo["convencion_dias"]).strip().upper()
        if convencion_db in {"30_360", "30/360"}:
            convencion_db = ConvencionDias.TREINTA_360.name
        if convencion_db != condiciones.convencion_dias.name:
            raise ErrorValidacion("La convención de días no coincide con el préstamo")
        if str(version_tasa["modalidad_tasa"]).upper() != condiciones.modalidad_tasa.name:
            raise ErrorValidacion("La modalidad de tasa no coincide con su versión")
        if str_a_decimal(version_tasa["tasa_anual"]) != condiciones.tasa_anual:
            raise ErrorValidacion("La tasa anual no coincide con su versión")
        if iso_a_fecha(version_tasa["fecha_desde"]) != condiciones.fecha_desembolso:
            raise ErrorValidacion(
                "La versión de tasa inicial debe comenzar en la fecha de desembolso"
            )

        fila_version = self.db.consultar_uno(
            """
            SELECT COALESCE(MAX(version_contrato), 0) AS ultima
            FROM condiciones_carencia WHERE prestamo_id = ?
            """,
            (prestamo_id,),
        )
        version_contrato = int(fila_version["ultima"] or 0) + 1
        creado_en = ahora_iso()
        payload = {
            **condiciones.payload(),
            "prestamo_id": prestamo_id,
            "version_tasa_id": version_tasa_id,
            "version_contrato": version_contrato,
            "creado_por": creado_por.strip(),
            "creado_en": creado_en,
        }
        snapshot_json = json_canonico(payload)
        snapshot_sha256 = hash_snapshot(snapshot_json)

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO condiciones_carencia (
                    prestamo_id, version_tasa_id, version_contrato,
                    version_snapshot, tratamiento, capital_original, tasa_anual,
                    modalidad_tasa, convencion_dias, sistema, meses_carencia,
                    fecha_desembolso, fecha_fin_carencia, fecha_primer_vencimiento,
                    plazo_amortizacion_meses, interes_simple_referencia,
                    interes_carencia_debido, interes_carencia_no_cobrado,
                    snapshot_json, snapshot_sha256, creado_por, creado_en
                )
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prestamo_id,
                    version_tasa_id,
                    version_contrato,
                    condiciones.tratamiento,
                    decimal_a_str(condiciones.capital_original),
                    decimal_a_str(condiciones.tasa_anual),
                    condiciones.modalidad_tasa.name,
                    condiciones.convencion_dias.name,
                    condiciones.sistema.name,
                    condiciones.meses_carencia,
                    fecha_a_iso(condiciones.fecha_desembolso),
                    fecha_a_iso(condiciones.fecha_fin_carencia),
                    fecha_a_iso(condiciones.fecha_primer_vencimiento),
                    condiciones.plazo_amortizacion_meses,
                    decimal_a_str(condiciones.interes_simple_referencia),
                    decimal_a_str(condiciones.interes_carencia_debido),
                    decimal_a_str(condiciones.interes_carencia_no_cobrado),
                    snapshot_json,
                    snapshot_sha256,
                    creado_por.strip(),
                    creado_en,
                ),
            )
            return self.db.ultimo_id_insertado()

    def listar_versiones(
        self, prestamo_id: int
    ) -> list[CondicionesCarenciaPersistidas]:
        filas = self.db.consultar(
            """
            SELECT * FROM condiciones_carencia
            WHERE prestamo_id = ?
            ORDER BY version_contrato
            """,
            (prestamo_id,),
        )
        return [self._fila_a_snapshot(fila) for fila in filas]

    def obtener_actual(
        self, prestamo_id: int
    ) -> CondicionesCarenciaPersistidas | None:
        fila = self.db.consultar_uno(
            """
            SELECT * FROM condiciones_carencia
            WHERE prestamo_id = ?
            ORDER BY version_contrato DESC
            LIMIT 1
            """,
            (prestamo_id,),
        )
        return self._fila_a_snapshot(fila) if fila else None

    def verificar_snapshot(self, snapshot: CondicionesCarenciaPersistidas) -> bool:
        """Verifica JSON canónico y digest antes de interpretar los términos."""
        return verificar_hash_snapshot(
            snapshot.snapshot_json,
            snapshot.snapshot_sha256,
        )

    def _fila_a_snapshot(self, fila) -> CondicionesCarenciaPersistidas:
        return CondicionesCarenciaPersistidas(
            id=int(fila["id"]),
            prestamo_id=int(fila["prestamo_id"]),
            version_tasa_id=int(fila["version_tasa_id"]),
            version_contrato=int(fila["version_contrato"]),
            tratamiento=str(fila["tratamiento"]),
            capital_original=str_a_decimal(fila["capital_original"]),
            tasa_anual=str_a_decimal(fila["tasa_anual"]),
            modalidad_tasa=str(fila["modalidad_tasa"]),
            convencion_dias=str(fila["convencion_dias"]),
            sistema=str(fila["sistema"]),
            meses_carencia=int(fila["meses_carencia"]),
            fecha_desembolso=iso_a_fecha(fila["fecha_desembolso"]),
            fecha_fin_carencia=iso_a_fecha(fila["fecha_fin_carencia"]),
            fecha_primer_vencimiento=iso_a_fecha(fila["fecha_primer_vencimiento"]),
            plazo_amortizacion_meses=int(fila["plazo_amortizacion_meses"]),
            interes_simple_referencia=str_a_decimal(fila["interes_simple_referencia"]),
            interes_carencia_debido=str_a_decimal(fila["interes_carencia_debido"]),
            interes_carencia_no_cobrado=str_a_decimal(fila["interes_carencia_no_cobrado"]),
            snapshot_json=str(fila["snapshot_json"]),
            snapshot_sha256=str(fila["snapshot_sha256"]),
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
        )
