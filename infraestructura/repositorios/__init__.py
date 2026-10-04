"""
Repositorios: capa que abstrae el acceso a la base de datos.
"""
from .base import RepositorioBase
from .personas import PersonaRepo
from .prestamos import PrestamoRepo
from .participaciones import ParticipacionRepo
from .pagos import PagoRepo
from .recalculos import RecalculoRepo
from .ledger import LedgerRepo
from .tipos_cambio import TipoCambioRepo
from .auditoria import AuditoriaRepo
from .modelos import (
    Persona,
    Prestamo,
    Cuota,
    Participacion,
    Pago,
    Imputacion,
    HistorialRecalculo,
    MovimientoLedger,
    TipoCambio,
    EntradaAuditoria,
)

__all__ = [
    "RepositorioBase",
    "PersonaRepo",
    "PrestamoRepo",
    "ParticipacionRepo",
    "PagoRepo",
    "RecalculoRepo",
    "LedgerRepo",
    "TipoCambioRepo",
    "AuditoriaRepo",
    "Persona",
    "Prestamo",
    "Cuota",
    "Participacion",
    "Pago",
    "Imputacion",
    "HistorialRecalculo",
    "MovimientoLedger",
    "TipoCambio",
    "EntradaAuditoria",
]