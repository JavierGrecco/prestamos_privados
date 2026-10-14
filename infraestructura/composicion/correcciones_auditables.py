"""Punto de composición local para la lectura del formulario de correcciones."""

from __future__ import annotations

from aplicacion.consultas.catalogo_correcciones_auditables import (
    ConsultaCatalogoCorreccionesAuditables,
)
from aplicacion.seguridad.capacidades import PoliticaCapacidades
from aplicacion.seguridad.identidad import IdentidadSesion
from infraestructura.consultas.catalogo_correcciones_auditables import (
    CatalogoCorreccionesAuditablesSQLiteQuery,
)


def crear_consulta_catalogo_correcciones_auditables(
    db,
    *,
    identidad: IdentidadSesion,
    politica_capacidades: PoliticaCapacidades | None = None,
) -> ConsultaCatalogoCorreccionesAuditables:
    """Ensambla el caso de uso con el lector local; no realiza escrituras."""
    return ConsultaCatalogoCorreccionesAuditables(
        CatalogoCorreccionesAuditablesSQLiteQuery(db),
        identidad=identidad,
        politica_capacidades=politica_capacidades,
    )


__all__ = ["crear_consulta_catalogo_correcciones_auditables"]
