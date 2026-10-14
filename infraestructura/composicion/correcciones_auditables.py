"""Punto de composición local para la lectura del formulario de correcciones."""

from __future__ import annotations

from aplicacion.consultas.catalogo_correcciones_auditables import (
    ConsultaCatalogoCorreccionesAuditables,
)
from aplicacion.servicios import ServicioCorreccionesAuditables
from aplicacion.seguridad.capacidades import PoliticaCapacidades
from aplicacion.seguridad.identidad import IdentidadSesion
from infraestructura.consultas.catalogo_correcciones_auditables import (
    CatalogoCorreccionesAuditablesSQLiteQuery,
)
from infraestructura.repositorios.correcciones_auditables import (
    CorreccionesAuditablesSQLiteRepository,
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


def crear_servicio_correcciones_auditables(
    db,
    *,
    identidad: IdentidadSesion,
    politica_capacidades: PoliticaCapacidades | None = None,
) -> ServicioCorreccionesAuditables:
    """Ensambla el servicio de escritura con el repositorio transaccional local."""
    return ServicioCorreccionesAuditables(
        CorreccionesAuditablesSQLiteRepository(db),
        identidad=identidad,
        politica_capacidades=politica_capacidades,
    )


__all__ = [
    "crear_consulta_catalogo_correcciones_auditables",
    "crear_servicio_correcciones_auditables",
]
