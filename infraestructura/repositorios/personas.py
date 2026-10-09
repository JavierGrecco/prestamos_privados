"""
Repositorio de personas y sus roles.

Una persona es la entidad central del sistema. Puede tener varios
roles (INVERSOR, DEUDOR, GARANTE, ADMIN) y participar en múltiples
préstamos en distintos roles.
"""
from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    nuevo_correlacion_id,
)
from .modelos import Persona


class PersonaRepo(RepositorioBase):
    """Acceso a la tabla `personas` y `roles_persona`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    # ============================================================
    # CRUD básico
    # ============================================================

    def crear(
        self,
        nombre: str,
        apellido: str = "",
        documento: str | None = None,
        telefono: str | None = None,
        email: str | None = None,
        domicilio: str | None = None,
        notas: str | None = None,
    ) -> int:
        """
        Crea una persona y devuelve su ID.

        Errores:
            sqlite3.IntegrityError: si el documento ya existe.
        """
        if not nombre or not nombre.strip():
            raise ValueError("El nombre es obligatorio")

        ahora = ahora_iso()
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO personas
                (nombre, apellido, documento, telefono, email, domicilio,
                 notas, estado, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVO', ?)
                """,
                (nombre.strip(), apellido.strip(), documento, telefono,
                 email, domicilio, notas, ahora),
            )
            return self.db.ultimo_id_insertado()

    def obtener(self, persona_id: int) -> Persona | None:
        """Devuelve la persona con ese ID, o None si no existe."""
        fila = self.db.consultar_uno(
            "SELECT * FROM personas WHERE id = ?",
            (persona_id,),
        )
        return self._fila_a_persona(fila) if fila else None

    def obtener_por_documento(self, documento: str) -> Persona | None:
        """Busca una persona por su documento."""
        fila = self.db.consultar_uno(
            "SELECT * FROM personas WHERE documento = ?",
            (documento,),
        )
        return self._fila_a_persona(fila) if fila else None

    def listar(
        self,
        estado: str | None = None,
        rol: str | None = None,
    ) -> list[Persona]:
        """
        Lista personas, con filtros opcionales.

        Si se pasa `rol`, devuelve solo las personas que tienen ese rol
        activo (sin fecha_baja).
        """
        if rol:
            condiciones = ["r.rol = ?", "r.fecha_baja IS NULL"]
            params = [rol]
            if estado:
                condiciones.append("p.estado = ?")
                params.append(estado)
            filas = self.db.consultar(
                "SELECT p.* FROM personas p "
                "INNER JOIN roles_persona r ON r.persona_id = p.id "
                f"WHERE {' AND '.join(condiciones)} "
                "ORDER BY p.nombre, p.apellido",
                tuple(params),
            )
        elif estado:
            filas = self.db.consultar(
                "SELECT * FROM personas WHERE estado = ? ORDER BY nombre, apellido",
                (estado,),
            )
        else:
            filas = self.db.consultar(
                "SELECT * FROM personas ORDER BY nombre, apellido"
            )
        return [self._fila_a_persona(f) for f in filas]

    def actualizar(self, persona_id: int, **campos) -> None:
        """
        Actualiza campos de una persona.

        Solo se actualizan los campos permitidos. Ejemplo:
            repo.actualizar(1, telefono="11-1234-5678", email="a@b.com")
        """
        permitidos = {
            "nombre", "apellido", "documento", "telefono", "email",
            "domicilio", "notas", "estado",
        }
        cambios = {k: v for k, v in campos.items() if k in permitidos}
        if not cambios:
            return

        set_clause = ", ".join(f"{k} = ?" for k in cambios)
        valores = list(cambios.values())
        valores.append(ahora_iso())
        valores.append(persona_id)

        with self.db.transaccion():
            self.db.ejecutar(
                f"UPDATE personas SET {set_clause}, actualizado_en = ? WHERE id = ?",
                tuple(valores),
            )

    # ============================================================
    # Roles
    # ============================================================

    def agregar_rol(self, persona_id: int, rol: str) -> None:
        """
        Agrega un rol a una persona.

        Si ya lo tiene activo, no hace nada (idempotente).
        Si lo tuvo y fue dado de baja, reactiva el rol existente.
        """
        # ADMIN es un valor histórico de roles_persona, no asignable a nuevas personas.
        roles_validos = {"INVERSOR", "DEUDOR", "GARANTE"}
        if rol not in roles_validos:
            raise ValueError(
                f"Rol inválido: {rol}. Válidos: {sorted(roles_validos)}"
            )

        if self.tiene_rol(persona_id, rol):
            return  # ya lo tiene activo

        # ¿Existe un rol dado de baja? Reactivarlo
        fila = self.db.consultar_uno(
            """
            SELECT fecha_baja FROM roles_persona
            WHERE persona_id = ? AND rol = ?
            """,
            (persona_id, rol),
        )

        with self.db.transaccion():
            if fila is not None:
                self.db.ejecutar(
                    """
                    UPDATE roles_persona
                    SET fecha_alta = ?, fecha_baja = NULL, motivo_baja = NULL
                    WHERE persona_id = ? AND rol = ?
                    """,
                    (ahora_iso(), persona_id, rol),
                )
            else:
                self.db.ejecutar(
                    """
                    INSERT INTO roles_persona (persona_id, rol, fecha_alta)
                    VALUES (?, ?, ?)
                    """,
                    (persona_id, rol, ahora_iso()),
                )

    def quitar_rol(self, persona_id: int, rol: str, motivo: str = "") -> None:
        """
        Da de baja un rol (sin eliminarlo del historial).

        El rol se marca con fecha_baja. No se elimina nunca, para
        poder reconstruir el historial.
        """
        with self.db.transaccion():
            self.db.ejecutar(
                """
                UPDATE roles_persona
                SET fecha_baja = ?, motivo_baja = ?
                WHERE persona_id = ? AND rol = ? AND fecha_baja IS NULL
                """,
                (ahora_iso(), motivo, persona_id, rol),
            )

    def tiene_rol(self, persona_id: int, rol: str) -> bool:
        """Devuelve True si la persona tiene ese rol activo."""
        fila = self.db.consultar_uno(
            """
            SELECT 1 FROM roles_persona
            WHERE persona_id = ? AND rol = ? AND fecha_baja IS NULL
            """,
            (persona_id, rol),
        )
        return fila is not None

    def roles(self, persona_id: int) -> list[str]:
        """Devuelve la lista de roles activos de una persona."""
        filas = self.db.consultar(
            """
            SELECT rol FROM roles_persona
            WHERE persona_id = ? AND fecha_baja IS NULL
            ORDER BY rol
            """,
            (persona_id,),
        )
        return [f["rol"] for f in filas]

    # ============================================================
    # Conversión
    # ============================================================

    def _fila_a_persona(self, fila) -> Persona:
        """Convierte una fila de SQLite a una dataclass Persona."""
        return Persona(
            id=fila["id"],
            nombre=fila["nombre"],
            apellido=fila["apellido"] or "",
            documento=fila["documento"],
            telefono=fila["telefono"],
            email=fila["email"],
            domicilio=fila["domicilio"],
            notas=fila["notas"],
            estado=fila["estado"],
            creado_en=fila["creado_en"],
            actualizado_en=fila["actualizado_en"],
        )