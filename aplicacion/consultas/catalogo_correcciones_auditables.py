"""Caso de uso de lectura para seleccionar registros corregibles.

Esta consulta comprueba permisos, limita los resultados y solo permite planes
internos activos. La lectura y la verificación física quedan en infraestructura;
el registro de propuestas conserva su servicio y transacción actuales.
"""
from __future__ import annotations

from dataclasses import dataclass

from aplicacion.puertos.catalogo_correcciones_auditables import (
    CatalogoCorreccionesReposicion,
    RegistroReposicionCorregible,
    TipoRegistroCorreccion,
)
from aplicacion.seguridad.capacidades import (
    CAP_PROPONER_CORRECCIONES_AUDITABLES,
    PoliticaCapacidades,
)
from aplicacion.seguridad.identidad import IdentidadSesion
from dominio.excepciones import ErrorValidacion


@dataclass(frozen=True, slots=True)
class RegistroCorreccionSeleccionado:
    """Registro original más el resultado de su comprobación de integridad."""

    registro: RegistroReposicionCorregible
    integro: bool


class ConsultaCatalogoCorreccionesAuditables:
    """Prepara el catálogo para la pantalla sin depender de SQLite ni repositorios."""

    def __init__(
        self,
        catalogo: CatalogoCorreccionesReposicion,
        *,
        identidad: IdentidadSesion,
        politica_capacidades: PoliticaCapacidades | None = None,
    ) -> None:
        if not isinstance(identidad, IdentidadSesion):
            raise TypeError("La consulta requiere una identidad resuelta por la aplicación")
        if not identidad.disponible or not identidad.proveedor.strip():
            raise ValueError("La identidad debe incluir subject y proveedor")
        self._catalogo = catalogo
        self._identidad = identidad
        self._politica = politica_capacidades or PoliticaCapacidades()

    def _exigir_permiso(self) -> None:
        if not self._identidad.autenticada:
            raise PermissionError(
                "Se requiere una identidad autenticada para consultar registros corregibles"
            )
        self._politica.exigir(
            self._identidad, CAP_PROPONER_CORRECCIONES_AUDITABLES
        )

    def listar_planes(self, *, limite: int = 200):
        """Devuelve solo planes internos activos, ordenados por el repositorio."""
        self._exigir_permiso()
        if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 200:
            raise ErrorValidacion("El límite de planes debe estar entre 1 y 200")
        planes = self._catalogo.listar_planes(limite=limite, solo_activos=True)
        return tuple(
            plan for plan in planes
            if plan.tipo_plan == "REPOSICION_INTERNA" and plan.estado == "ACTIVO"
        )

    def listar_registros(
        self,
        *,
        plan_id: int,
        tipo: TipoRegistroCorreccion,
        limite: int = 500,
    ) -> tuple[RegistroReposicionCorregible, ...]:
        """Lista registros de un tipo permitido para un plan vigente."""
        self._exigir_permiso()
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 500:
            raise ErrorValidacion("El límite de registros debe estar entre 1 y 500")

        plan = self._catalogo.obtener_plan(plan_id)
        if plan is None:
            raise ErrorValidacion("El plan seleccionado ya no existe. Volvé a elegirlo.")
        if plan.tipo_plan != "REPOSICION_INTERNA":
            raise ErrorValidacion(
                "Solo se pueden proponer correcciones para planes de reposición internos"
            )
        if plan.estado != "ACTIVO":
            raise ErrorValidacion(
                "El plan está cerrado; no admite nuevas propuestas"
            )

        if tipo == "APORTE_REPOSICION":
            return tuple(self._catalogo.listar_aportes(plan_id, limite))
        if tipo == "FLUJO_INVERSION_REPOSICION":
            return tuple(self._catalogo.listar_flujos_inversion(plan_id, limite))
        if tipo == "VALUACION_INVERSION_REPOSICION":
            return tuple(self._catalogo.listar_valuaciones_inversion(plan_id, limite))
        raise ErrorValidacion("El tipo de registro no admite correcciones auditables")

    def obtener_registro(
        self, *, tipo: TipoRegistroCorreccion, registro_id: int
    ) -> RegistroCorreccionSeleccionado | None:
        """Recupera el registro y deja explícito si su snapshot supera el control."""
        self._exigir_permiso()
        if (
            not isinstance(registro_id, int)
            or isinstance(registro_id, bool)
            or registro_id <= 0
        ):
            raise ErrorValidacion("El identificador del registro no es válido")

        if tipo == "APORTE_REPOSICION":
            registro = self._catalogo.obtener_aporte(registro_id)
            verificar = self._catalogo.verificar_aporte
        elif tipo == "FLUJO_INVERSION_REPOSICION":
            registro = self._catalogo.obtener_flujo_inversion(registro_id)
            verificar = self._catalogo.verificar_flujo_inversion
        elif tipo == "VALUACION_INVERSION_REPOSICION":
            registro = self._catalogo.obtener_valoracion_inversion(registro_id)
            verificar = self._catalogo.verificar_valoracion_inversion
        else:
            raise ErrorValidacion("El tipo de registro no admite correcciones auditables")

        if registro is None:
            return None
        integro = registro.snapshot_json is not None and bool(verificar(registro))
        return RegistroCorreccionSeleccionado(registro=registro, integro=integro)


__all__ = [
    "RegistroCorreccionSeleccionado",
    "ConsultaCatalogoCorreccionesAuditables",
]
