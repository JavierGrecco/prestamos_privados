"""
Clase base para todos los repositorios.

Concentra helpers que se repiten: conversión de fechas y Decimals,
generación de IDs de correlación, manejo de timestamps ISO.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from ..db import BaseDatos


def ahora_iso() -> str:
    """Timestamp actual en formato ISO 8601, para guardar en la base."""
    return datetime.now().isoformat(timespec="seconds")


def fecha_a_iso(fecha: date | None) -> str | None:
    """Convierte date a string ISO, o None si la fecha es None."""
    return fecha.isoformat() if fecha else None


def iso_a_fecha(valor: str | None) -> date | None:
    """Convierte string ISO a date, o None si el string es None."""
    if not valor:
        return None
    return date.fromisoformat(valor)


def decimal_a_str(valor: Decimal | None) -> str | None:
    """
    Convierte Decimal a string preservando la precisión.

    Decimal("100.50") se guarda como "100.50", no como "100.5".
    Al leerlo, Decimal("100.50") es idéntico.
    """
    return str(valor) if valor is not None else None


def str_a_decimal(valor: str | None, default: Decimal = Decimal("0.00")) -> Decimal:
    """Convierte string a Decimal, con valor por defecto si es None."""
    if valor is None or valor == "":
        return default
    return Decimal(valor)


def nuevo_correlacion_id() -> str:
    """
    Genera un ID único para correlacionar operaciones.

    Se usa para vincular una operación del usuario con todos sus
    efectos: ledger, auditoría, logs. Si algo sale mal, buscando
    por correlacion_id se reconstruye todo lo que pasó.
    """
    return str(uuid.uuid4())


class RepositorioBase:
    """
    Clase base de todos los repositorios.

    Cada repositorio recibe la conexión a la base en el constructor
    y usa los helpers heredados.
    """

    def __init__(self, db: BaseDatos):
        self.db = db

    def _existe_tabla(self, nombre: str) -> bool:
        """Verifica si una tabla existe en el schema."""
        fila = self.db.consultar_uno(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,),
        )
        return fila is not None

    def contar(self, tabla: str, where: str = "", params: tuple = ()) -> int:
        """
        Cuenta filas de una tabla, con filtro opcional.

        Ejemplo:
            repo.contar("personas")
            repo.contar("prestamos", "estado = ?", ("ACTIVO",))
        """
        sql = f"SELECT COUNT(*) AS n FROM {tabla}"
        if where:
            sql += f" WHERE {where}"
        fila = self.db.consultar_uno(sql, params)
        return fila["n"] if fila else 0