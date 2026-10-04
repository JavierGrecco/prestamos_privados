"""
Repositorio de auditoría.

Registra todos los cambios importantes del sistema: quién hizo qué,
cuándo, sobre qué entidad, con qué datos antes y después.

La auditoría es distinta del ledger:
  - Ledger: registra los efectos ECONÓMICOS de las operaciones.
  - Auditoría: registra los cambios de ESTADO y las decisiones.

Por ejemplo, un cambio de tasa:
  - En auditoría: "admin cambió tasa de 30% a 27%, motivo: refinanciación".
  - En ledger: no genera movimiento (no hay dinero moviéndose).

En cambio, un pago:
  - En auditoría: "se registró un pago de $X".
  - En ledger: varios movimientos que reflejan el movimiento de dinero.
"""
import json
from datetime import datetime

from ..db import BaseDatos
from .base import RepositorioBase
from .modelos import EntradaAuditoria


class AuditoriaRepo(RepositorioBase):
    """Acceso a la tabla `auditoria`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def registrar(
        self,
        usuario: str,
        operacion: str,
        entidad: str,
        entidad_id: int | None,
        correlacion_id: str,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        motivo: str | None = None,
    ) -> int:
        """
        Registra una entrada de auditoría.

        Devuelve el ID de la entrada.
        """
        if not usuario or not usuario.strip():
            raise ValueError("Se requiere un usuario para auditar")
        if not operacion:
            raise ValueError("Se requiere una operación")

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO auditoria
                (fecha, usuario, operacion, entidad, entidad_id,
                 datos_anteriores, datos_nuevos, motivo, correlacion_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    usuario,
                    operacion,
                    entidad,
                    entidad_id,
                    json.dumps(datos_anteriores, default=str) if datos_anteriores else None,
                    json.dumps(datos_nuevos, default=str) if datos_nuevos else None,
                    motivo,
                    correlacion_id,
                ),
            )
            return self.db.ultimo_id_insertado()

    def por_entidad(
        self,
        entidad: str,
        entidad_id: int,
    ) -> list[EntradaAuditoria]:
        """Devuelve las entradas de auditoría de una entidad."""
        filas = self.db.consultar(
            """
            SELECT * FROM auditoria
            WHERE entidad = ? AND entidad_id = ?
            ORDER BY fecha DESC, id DESC
            """,
            (entidad, entidad_id),
        )
        return [self._fila_a_entrada(f) for f in filas]

    def por_correlacion(self, correlacion_id: str) -> list[EntradaAuditoria]:
        """Devuelve las entradas de auditoría de una operación."""
        filas = self.db.consultar(
            """
            SELECT * FROM auditoria
            WHERE correlacion_id = ?
            ORDER BY fecha, id
            """,
            (correlacion_id,),
        )
        return [self._fila_a_entrada(f) for f in filas]

    def _fila_a_entrada(self, fila) -> EntradaAuditoria:
        return EntradaAuditoria(
            id=fila["id"],
            fecha=fila["fecha"],
            usuario=fila["usuario"],
            operacion=fila["operacion"],
            entidad=fila["entidad"],
            entidad_id=fila["entidad_id"],
            datos_anteriores=fila["datos_anteriores"],
            datos_nuevos=fila["datos_nuevos"],
            motivo=fila["motivo"],
            correlacion_id=fila["correlacion_id"],
        )