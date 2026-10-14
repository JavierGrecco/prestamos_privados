"""Composición local de cuentas de acceso y autenticación."""

from __future__ import annotations

from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales
from infraestructura.adaptadores.unidad_trabajo_usuarios_locales import (
    UnidadTrabajoUsuariosLocalesSQLite,
)
from infraestructura.consultas.usuarios_locales import (
    ConsultaPersonasUsuariosLocalesSQLite,
)
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.usuarios_app import UsuarioAppRepo


def crear_servicio_usuarios_locales(db) -> ServicioUsuariosLocales:
    """Ensamble el servicio con repositorios y transacción SQLite locales."""
    return ServicioUsuariosLocales(
        usuarios=UsuarioAppRepo(db),
        personas=ConsultaPersonasUsuariosLocalesSQLite(db),
        auditoria=AuditoriaRepo(db),
        unidad_trabajo=UnidadTrabajoUsuariosLocalesSQLite(db),
    )


def crear_consulta_personas_usuarios_locales(
    db,
) -> ConsultaPersonasUsuariosLocalesSQLite:
    """Entrega la lectura de personas que necesita el vínculo opcional de cuentas."""
    return ConsultaPersonasUsuariosLocalesSQLite(db)


__all__ = [
    "crear_servicio_usuarios_locales",
    "crear_consulta_personas_usuarios_locales",
]
