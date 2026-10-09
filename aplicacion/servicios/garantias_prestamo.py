"""Casos de uso para garantías personales vinculadas a préstamos.

Registrar una garantía no genera pagos ni cambia obligaciones financieras.
Cada alta/finalización es una relación auditable y conserva su historial.
"""
from datetime import date
from decimal import Decimal
import sqlite3

from infraestructura.db import BaseDatos
from infraestructura.excepciones import ErrorTransaccion
from infraestructura.repositorios import (
    AuditoriaRepo,
    GarantiaPrestamoRepo,
    PersonaRepo,
    PrestamoRepo,
)
from infraestructura.repositorios.base import nuevo_correlacion_id


ESTADOS_TERMINALES_PRESTAMO = {"CANCELADO", "FINALIZADO", "ANULADO"}


class ServicioGarantiasPrestamo:
    """Orquesta alta y finalización de garantías personales."""

    def __init__(self, db: BaseDatos):
        self.db = db
        self.garantias = GarantiaPrestamoRepo(db)
        self.personas = PersonaRepo(db)
        self.prestamos = PrestamoRepo(db)
        self.auditoria = AuditoriaRepo(db)

    def por_prestamo(self, prestamo_id: int):
        """Devuelve todas las garantías del préstamo, incluidas las históricas."""
        return self.garantias.por_prestamo(prestamo_id)

    def por_garante(self, persona_id: int):
        """Devuelve la historia de garantías de una persona."""
        return self.garantias.por_garante(persona_id)

    def crear(
        self,
        *,
        prestamo_id: int,
        garante_id: int,
        alcance: str,
        monto_maximo: Decimal | None = None,
        fecha_constitucion: date | None = None,
        usuario: str,
    ):
        """Constituye una relación personal, sin inferir cobertura jurídica."""
        alcance = self._validar_alcance(alcance)
        usuario = self._validar_usuario(usuario)
        monto_maximo = self._validar_monto(monto_maximo)
        fecha_constitucion = fecha_constitucion or date.today()
        if not isinstance(fecha_constitucion, date):
            raise ValueError("La fecha de constitución no es válida.")

        try:
            with self.db.transaccion():
                prestamo = self.prestamos.obtener(prestamo_id)
                if prestamo is None:
                    raise ValueError("El préstamo que elegiste no existe.")
                if prestamo.estado in ESTADOS_TERMINALES_PRESTAMO:
                    raise ValueError(
                        "No se puede constituir una garantía para un préstamo "
                        "cancelado, finalizado o anulado."
                    )

                persona = self.personas.obtener(garante_id)
                if persona is None:
                    raise ValueError("La persona garante no existe.")
                if persona.estado != "ACTIVO":
                    raise ValueError(
                        "La persona garante está inactiva y no puede asumir una "
                        "garantía nueva."
                    )
                if prestamo.deudor_id == garante_id:
                    raise ValueError(
                        "El deudor no puede garantizar su propio préstamo."
                    )
                if self.garantias.activa_para_par(prestamo_id, garante_id):
                    raise ValueError(
                        "Esa persona ya tiene una garantía activa para este préstamo."
                    )

                # La relación concreta constituye el hecho principal. El rol
                # general GARANTE se agrega solo como clasificación acumulable.
                if not self.personas.tiene_rol(garante_id, "GARANTE"):
                    self.personas.agregar_rol(garante_id, "GARANTE")

                garantia_id = self.garantias.crear(
                    prestamo_id=prestamo_id,
                    garante_id=garante_id,
                    alcance=alcance,
                    monto_maximo=monto_maximo,
                    fecha_constitucion=fecha_constitucion,
                    creado_por=usuario,
                )
                self.auditoria.registrar(
                    usuario=usuario,
                    operacion="GARANTIA_PERSONAL_CONSTITUIDA",
                    entidad="GARANTIA_PRESTAMO",
                    entidad_id=garantia_id,
                    correlacion_id=nuevo_correlacion_id(),
                    datos_nuevos={
                        "prestamo_id": prestamo_id,
                        "garante_id": garante_id,
                        "alcance": alcance,
                        "monto_maximo": monto_maximo,
                        "moneda": "ARS",
                        "fecha_constitucion": fecha_constitucion.isoformat(),
                        "estado": "ACTIVA",
                    },
                    motivo="Registro de garantía personal por préstamo",
                )
        except ErrorTransaccion as exc:
            if (
                isinstance(exc.__cause__, sqlite3.IntegrityError)
                and (
                    "uq_garantia_activa_prestamo_persona" in str(exc.__cause__)
                    or (
                        "UNIQUE constraint failed" in str(exc.__cause__)
                        and "garantias_prestamo.prestamo_id" in str(exc.__cause__)
                        and "garantias_prestamo.garante_id" in str(exc.__cause__)
                    )
                )
            ):
                raise ValueError(
                    "Esa persona ya tiene una garantía activa para este préstamo."
                ) from exc
            causa = exc.__cause__
            if isinstance(causa, ValueError):
                raise causa
            raise

        garantia = self.garantias.obtener(garantia_id)
        if garantia is None:
            raise RuntimeError("No se pudo leer la garantía recién creada.")
        return garantia

    def finalizar(
        self,
        *,
        garantia_id: int,
        usuario: str,
        motivo: str,
        anulada: bool = False,
        fecha_fin: date | None = None,
    ):
        """Libera o anula una garantía activa sin borrar la relación histórica."""
        usuario = self._validar_usuario(usuario)
        motivo = (motivo or "").strip()
        if not motivo:
            raise ValueError("Indicá el motivo para finalizar la garantía.")
        if len(motivo) > 500:
            raise ValueError("El motivo no puede superar 500 caracteres.")
        fecha_fin = fecha_fin or date.today()
        if not isinstance(fecha_fin, date):
            raise ValueError("La fecha de finalización no es válida.")
        estado_nuevo = "ANULADA" if anulada else "LIBERADA"

        with self.db.transaccion():
            anterior = self.garantias.obtener(garantia_id)
            if anterior is None:
                raise ValueError("La garantía que querés modificar no existe.")
            if anterior.estado != "ACTIVA":
                raise ValueError("Solo se puede finalizar una garantía activa.")

            self.garantias.finalizar(
                garantia_id=garantia_id,
                estado=estado_nuevo,
                fecha_fin=fecha_fin,
                motivo=motivo,
            )
            actualizado = self.garantias.obtener(garantia_id)
            if actualizado is None or actualizado.estado != estado_nuevo:
                raise ValueError("La garantía cambió y ya no está activa.")

            self.auditoria.registrar(
                usuario=usuario,
                operacion=(
                    "GARANTIA_PERSONAL_ANULADA"
                    if anulada
                    else "GARANTIA_PERSONAL_LIBERADA"
                ),
                entidad="GARANTIA_PRESTAMO",
                entidad_id=garantia_id,
                correlacion_id=nuevo_correlacion_id(),
                datos_anteriores={"estado": anterior.estado},
                datos_nuevos={
                    "estado": estado_nuevo,
                    "fecha_fin": fecha_fin.isoformat(),
                    "motivo_fin": motivo,
                },
                motivo=motivo,
            )

        return self.garantias.obtener(garantia_id)

    @staticmethod
    def _validar_alcance(alcance: str) -> str:
        if not isinstance(alcance, str):
            raise ValueError("El alcance de la garantía debe ser texto.")
        alcance = alcance.strip()
        if not alcance:
            raise ValueError("Describí el alcance de la garantía.")
        if len(alcance) > 500:
            raise ValueError("El alcance no puede superar 500 caracteres.")
        return alcance

    @staticmethod
    def _validar_monto(monto: Decimal | None) -> Decimal | None:
        if monto is None:
            return None
        if not isinstance(monto, Decimal):
            raise ValueError("El tope máximo debe expresarse como Decimal.")
        if not monto.is_finite() or monto <= Decimal("0"):
            raise ValueError("El tope máximo debe ser mayor a cero.")
        return monto

    @staticmethod
    def _validar_usuario(usuario: str) -> str:
        if not isinstance(usuario, str) or not usuario.strip():
            raise ValueError("Se requiere una cuenta para auditar la operación.")
        return usuario.strip()
