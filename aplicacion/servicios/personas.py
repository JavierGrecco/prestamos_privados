"""Casos de uso de administración de personas y roles."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo, PrestamoRepo, ParticipacionRepo

ROLES_VALIDOS = ("DEUDOR", "INVERSOR", "GARANTE", "ADMIN")
ESTADOS_VALIDOS = ("ACTIVO", "INACTIVO")


@dataclass(frozen=True)
class RelacionPrestamoPersona:
    prestamo_id: int
    numero: str
    rol: str
    monto: Decimal
    estado: str
    destino: str | None


class ServicioPersonas:
    def __init__(self, db: BaseDatos):
        self.personas = PersonaRepo(db)
        self.prestamos = PrestamoRepo(db)
        self.participaciones = ParticipacionRepo(db)

    def listar(self, *, estado=None, rol=None):
        if estado is not None and estado not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {estado}")
        if rol is not None and rol not in ROLES_VALIDOS:
            raise ValueError(f"Rol inválido: {rol}")
        return self.personas.listar(estado=estado, rol=rol)

    def obtener(self, persona_id: int):
        persona = self.personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")
        return persona

    def crear(self, *, nombre, apellido="", documento=None, telefono=None,
              email=None, domicilio=None, notas=None, roles=()):
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        roles = tuple(dict.fromkeys(roles))
        self._validar_roles(roles)
        persona_id = self.personas.crear(
            nombre=nombre, apellido=(apellido or "").strip(),
            documento=(documento or "").strip() or None,
            telefono=(telefono or "").strip() or None,
            email=(email or "").strip() or None,
            domicilio=(domicilio or "").strip() or None,
            notas=(notas or "").strip() or None,
        )
        for rol in roles:
            self.personas.agregar_rol(persona_id, rol)
        return persona_id

    def actualizar(self, persona_id: int, *, nombre, apellido="",
                   documento=None, telefono=None, email=None,
                   domicilio=None, notas=None):
        self.obtener(persona_id)
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        self.personas.actualizar(
            persona_id, nombre=nombre, apellido=(apellido or "").strip(),
            documento=(documento or "").strip() or None,
            telefono=(telefono or "").strip() or None,
            email=(email or "").strip() or None,
            domicilio=(domicilio or "").strip() or None,
            notas=(notas or "").strip() or None,
        )

    def cambiar_estado(self, persona_id: int, estado: str):
        if estado not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {estado}")
        self.obtener(persona_id)
        self.personas.actualizar(persona_id, estado=estado)

    def agregar_rol(self, persona_id: int, rol: str):
        self.obtener(persona_id)
        self._validar_roles((rol,))
        self.personas.agregar_rol(persona_id, rol)

    def quitar_rol(self, persona_id: int, rol: str, motivo=""):
        self.obtener(persona_id)
        self._validar_roles((rol,))
        self.personas.quitar_rol(persona_id, rol, motivo=motivo)

    def roles(self, persona_id: int):
        self.obtener(persona_id)
        return self.personas.roles(persona_id)

    def prestamos_de(self, persona_id: int):
        self.obtener(persona_id)
        relaciones = []
        vistos = set()
        for prestamo in self.prestamos.listar(deudor_id=persona_id):
            vistos.add((prestamo.id, "DEUDOR"))
            relaciones.append(RelacionPrestamoPersona(
                prestamo.id, prestamo.numero, "DEUDOR",
                prestamo.capital_original, prestamo.estado, prestamo.destino,
            ))
        for participacion in self.participaciones.por_inversor(persona_id):
            prestamo = self.prestamos.obtener(participacion.prestamo_id)
            if prestamo is None or (prestamo.id, "INVERSOR") in vistos:
                continue
            vistos.add((prestamo.id, "INVERSOR"))
            relaciones.append(RelacionPrestamoPersona(
                prestamo.id, prestamo.numero, "INVERSOR",
                participacion.capital_aportado, prestamo.estado, prestamo.destino,
            ))
        return tuple(sorted(relaciones, key=lambda x: (x.prestamo_id, x.rol)))

    @staticmethod
    def _validar_roles(roles):
        invalidos = [r for r in roles if r not in ROLES_VALIDOS]
        if invalidos:
            raise ValueError(f"Rol(es) inválido(s): {', '.join(invalidos)}")
