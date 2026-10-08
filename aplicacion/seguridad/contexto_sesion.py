"""Contexto de seguridad de una sesión.

Mantiene separados identidad, actor declarado y persona seleccionada.
"""

from __future__ import annotations

from dataclasses import dataclass

from aplicacion.seguridad.acceso_personas import (
    AccesoPersonaDenegado,
    ContextoAcceso,
    PoliticaAccesoPersonas,
)
from aplicacion.seguridad.identidad import (
    IdentidadSesion,
    ProveedorIdentidad,
    identidad_desde_proveedor,
)


@dataclass(frozen=True)
class ContextoSesionSeguridad:
    """Contexto completo para una vista o caso de uso."""

    identidad: IdentidadSesion
    actor_declarado: str
    persona_id: int | None
    acceso: ContextoAcceso | None

    @property
    def autenticada(self) -> bool:
        return self.identidad.autenticada


class ServicioContextoSesionSeguridad:
    """Construye el contexto de seguridad sin conocer Streamlit."""

    def __init__(
        self,
        proveedor_identidad: ProveedorIdentidad,
        politica_personas: PoliticaAccesoPersonas,
    ) -> None:
        self._proveedor = proveedor_identidad
        self._politica = politica_personas

    def construir(
        self,
        *,
        actor_declarado: str,
        persona_id: int | None,
    ) -> ContextoSesionSeguridad:
        identidad = identidad_desde_proveedor(self._proveedor)
        acceso = None

        if persona_id is not None:
            try:
                acceso = self._politica.autorizar(
                    persona_id,
                    actor_declarado=actor_declarado,
                )
            except AccesoPersonaDenegado:
                raise

        return ContextoSesionSeguridad(
            identidad=identidad,
            actor_declarado=actor_declarado.strip() or "sin declarar",
            persona_id=persona_id,
            acceso=acceso,
        )
