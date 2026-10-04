"""
Repositorio de tipos de cambio.

Guarda las cotizaciones del dólar (u otra moneda) en distintas
fechas y fuentes. Se usa para convertir montos a la moneda de
referencia en el análisis de paridad cambiaria.

Fuentes posibles:
  - BCRA_A3500: tipo de cambio mayorista de referencia.
  - BNA_VENDEDOR: Banco Nación, punta vendedora.
  - MEP: dólar MEP.
  - MANUAL: ingresado a mano por el usuario.
"""
from datetime import date

from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    fecha_a_iso,
    iso_a_fecha,
    decimal_a_str,
    str_a_decimal,
)
from .modelos import TipoCambio


class TipoCambioRepo(RepositorioBase):
    """Acceso a la tabla `tipos_cambio`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def registrar(
        self,
        fecha: date,
        fuente: str,
        valor,
        es_manual: bool = False,
        creado_por: str | None = None,
    ) -> int:
        """
        Registra o actualiza un tipo de cambio.

        Si ya existe una cotización para esa fecha y fuente, la
        actualiza. Esto permite corregir valores sin duplicar filas.
        """
        from decimal import Decimal

        valor_d = Decimal(str(valor))
        if valor_d <= 0:
            raise ValueError("El tipo de cambio debe ser mayor a cero")

        with self.db.transaccion():
            # Intentar update primero
            existente = self.db.consultar_uno(
                "SELECT id FROM tipos_cambio WHERE fecha = ? AND fuente = ?",
                (fecha_a_iso(fecha), fuente),
            )
            if existente:
                self.db.ejecutar(
                    """
                    UPDATE tipos_cambio
                    SET valor = ?, es_manual = ?, creado_por = ?, creado_en = ?
                    WHERE id = ?
                    """,
                    (
                        decimal_a_str(valor_d),
                        1 if es_manual else 0,
                        creado_por,
                        ahora_iso(),
                        existente["id"],
                    ),
                )
                return existente["id"]
            else:
                self.db.ejecutar(
                    """
                    INSERT INTO tipos_cambio
                    (fecha, fuente, valor, es_manual, creado_por, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fecha_a_iso(fecha),
                        fuente,
                        decimal_a_str(valor_d),
                        1 if es_manual else 0,
                        creado_por,
                        ahora_iso(),
                    ),
                )
                return self.db.ultimo_id_insertado()

    def obtener(self, fecha: date, fuente: str) -> TipoCambio | None:
        """Devuelve la cotización de una fecha y fuente."""
        fila = self.db.consultar_uno(
            "SELECT * FROM tipos_cambio WHERE fecha = ? AND fuente = ?",
            (fecha_a_iso(fecha), fuente),
        )
        return self._fila_a_tc(fila) if fila else None

    def ultimo(self, fuente: str) -> TipoCambio | None:
        """Devuelve la cotización más reciente de una fuente."""
        fila = self.db.consultar_uno(
            """
            SELECT * FROM tipos_cambio
            WHERE fuente = ?
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (fuente,),
        )
        return self._fila_a_tc(fila) if fila else None

    def por_rango(
        self,
        fuente: str,
        desde: date,
        hasta: date,
    ) -> list[TipoCambio]:
        """Devuelve las cotizaciones de un rango de fechas."""
        filas = self.db.consultar(
            """
            SELECT * FROM tipos_cambio
            WHERE fuente = ? AND fecha BETWEEN ? AND ?
            ORDER BY fecha
            """,
            (fuente, fecha_a_iso(desde), fecha_a_iso(hasta)),
        )
        return [self._fila_a_tc(f) for f in filas]

    def _fila_a_tc(self, fila) -> TipoCambio:
        return TipoCambio(
            id=fila["id"],
            fecha=iso_a_fecha(fila["fecha"]),
            fuente=fila["fuente"],
            valor=str_a_decimal(fila["valor"]),
            es_manual=bool(fila["es_manual"]),
            creado_por=fila["creado_por"],
            creado_en=fila["creado_en"],
        )