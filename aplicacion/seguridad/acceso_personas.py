"""Frontera de autorización para personas consultables.

La selección de una persona y la autorización para verla son conceptos
distintos. En modo local la aplicación mantiene compatibilidad, pero lo
identifica como un entorno sin autenticación real. En entornos multiusuario se
puede configurar una allowlist de personas mediante PRESTAMOS_PERSONAS_PERMITIDAS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class AccesoPersonaDenegado(PermissionError):
    """La sesión no está autorizada a consultar la persona solicitada."""


@dataclass(frozen=True)
class ContextoAcceso:
    """Contexto explícito de una operación de lectura."""

    actor_declarado: str
    persona_id: int
    modo: str
    autenticacion_real: bool
    autorizado: bool


class PoliticaAccesoPersonas:
    """Decide si la sesión actual puede consultar una persona."""

    VARIABLE_ALLOWLIST = "PRESTAMOS_PERSONAS_PERMITIDAS"

    def __init__(self, personas_permitidas: set[int] | None = None) -> None:
        if personas_permitidas is None:
            personas_permitidas = self._leer_allowlist_entorno()
        invalidas = [x for x in personas_permitidas if x <= 0]
        if invalidas:
            raise ValueError("La allowlist solo puede contener IDs positivos")
        self._personas_permitidas = frozenset(personas_permitidas)

    @classmethod
    def desde_entorno(cls) -> "PoliticaAccesoPersonas":
        return cls()

    @property
    def modo(self) -> str:
        return (
            "ALLOWLIST"
            if self._personas_permitidas
            else "LOCAL_SIN_AUTENTICACION"
        )

    @property
    def autenticacion_real(self) -> bool:
        return False

    @property
    def personas_permitidas(self) -> frozenset[int]:
        return self._personas_permitidas

    def puede_consultar(self, persona_id: int) -> bool:
        if persona_id <= 0:
            return False
        if not self._personas_permitidas:
            return True
        return persona_id in self._personas_permitidas

    def autorizar(
        self,
        persona_id: int,
        *,
        actor_declarado: str,
    ) -> ContextoAcceso:
        autorizado = self.puede_consultar(persona_id)
        if not autorizado:
            raise AccesoPersonaDenegado(
                "La sesión no está autorizada a consultar esta persona."
            )
        return ContextoAcceso(
            actor_declarado=actor_declarado.strip() or "sin declarar",
            persona_id=persona_id,
            modo=self.modo,
            autenticacion_real=self.autenticacion_real,
            autorizado=True,
        )

    @classmethod
    def _leer_allowlist_entorno(cls) -> set[int]:
        raw = os.environ.get(cls.VARIABLE_ALLOWLIST, "").strip()
        if not raw:
            return set()

        resultado: set[int] = set()
        for parte in raw.split(","):
            valor = parte.strip()
            if not valor:
                continue
            try:
                resultado.add(int(valor))
            except ValueError as exc:
                raise ValueError(
                    f"{cls.VARIABLE_ALLOWLIST} debe contener IDs separados por comas"
                ) from exc
        return resultado


def estado_ux_acceso(politica: PoliticaAccesoPersonas) -> tuple[str, str]:
    """Devuelve una etiqueta simple para mostrar el estado al operador."""
    if politica.modo == "ALLOWLIST":
        return (
            "Acceso limitado",
            "La sesión solo puede consultar las personas incluidas en la lista autorizada.",
        )
    return (
        "Modo local sin autenticación",
        "Elegir una persona no otorga permisos. En este modo no existe una identidad autenticada real.",
    )
