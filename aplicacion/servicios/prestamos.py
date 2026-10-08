"""
Servicio de préstamos.

Orquesta la creación de un préstamo completo:
  1. Valida los datos.
  2. Crea el préstamo en estado BORRADOR.
  3. Crea la versión inicial de tasa.
  4. Genera la tabla de amortización con el motor del dominio.
  5. Persiste las cuotas.
  6. Crea las participaciones de los inversores.
  7. Registra el desembolso en el ledger.
  8. Registra la auditoría.
  9. Cambia el préstamo a estado ACTIVO.

Todo en una única transacción atómica: o se completa todo, o no
se guarda nada. Nunca queda un préstamo a medio construir.
"""
from datetime import date
from decimal import Decimal

from dominio import (
    generar_tabla,
    SistemaAmortizacion,
    ModalidadTasa,
    ConvencionDias,
)

from infraestructura.db import BaseDatos
from infraestructura.repositorios import (
    PersonaRepo,
    PrestamoRepo,
    ParticipacionRepo,
    LedgerRepo,
    AuditoriaRepo,
)
from infraestructura.repositorios.base import nuevo_correlacion_id

from .excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido


class ServicioPrestamos:
    """
    Servicio de aplicación para operaciones con préstamos.

    Uso típico:
        servicio = ServicioPrestamos(db)
        prestamo_id = servicio.crear_completo(
            deudor_id=1,
            capital=Decimal("20000000"),
            plazo_meses=36,
            tasa_anual=Decimal("0.30"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": 2, "monto": Decimal("10000000")},
                {"persona_id": 3, "monto": Decimal("6000000")},
                {"persona_id": 4, "monto": Decimal("4000000")},
            ],
            usuario="admin",
        )
    """

    def __init__(self, db: BaseDatos):
        self.db = db
        self.personas = PersonaRepo(db)
        self.prestamos = PrestamoRepo(db)
        self.participaciones = ParticipacionRepo(db)
        self.ledger = LedgerRepo(db)
        self.auditoria = AuditoriaRepo(db)

    # ============================================================
    # Alta completa de préstamo
    # ============================================================

    def crear_completo(
        self,
        deudor_id: int,
        capital: Decimal,
        plazo_meses: int,
        tasa_anual: Decimal,
        modalidad_tasa: str,
        sistema: str,
        convencion_dias: str,
        fecha_inicio: date,
        inversores: list[dict],
        usuario: str,
        tc_inicial: Decimal | None = None,
        destino: str | None = None,
        descripcion: str | None = None,
    ) -> int:
        """
        Crea un préstamo completo con todo lo necesario.

        Parámetros:
            deudor_id: ID de la persona que recibe el préstamo.
            capital: monto prestado (Decimal positivo).
            plazo_meses: cantidad de cuotas.
            tasa_anual: tasa nominal o efectiva anual (0.30 = 30%).
            modalidad_tasa: "TNA" o "TEA".
            sistema: "FRANCES", "ALEMAN" o "INTERES_ONLY".
            convencion_dias: "MENSUAL", "ACTUAL_365", etc.
            fecha_inicio: fecha del primer período.
            inversores: lista de dicts con:
                {persona_id: int, monto: Decimal}
                La suma de los montos debe ser exactamente el capital.
            usuario: quién ejecuta la operación (para auditoría).
            tc_inicial: tipo de cambio ARS/USD al momento del desembolso.
            destino: para qué es el préstamo ("Cambio de auto").
            descripcion: notas libres.

        Devuelve:
            El ID del préstamo creado.

        Errores:
            ErrorDatosInvalidos: si algún parámetro es inválido, si
                el deudor no existe, si la suma de aportes no coincide
                con el capital, o si hay inversores duplicados.
        """
        # ------------------------------------------------------------
        # Validaciones previas
        # ------------------------------------------------------------
        self._validar_alta(
            deudor_id=deudor_id,
            capital=capital,
            plazo_meses=plazo_meses,
            inversores=inversores,
        )

        correlacion_id = nuevo_correlacion_id()
        fecha_str = fecha_inicio.isoformat()

        # ------------------------------------------------------------
        # Toda la operación en una sola transacción
        # ------------------------------------------------------------
        with self.db.transaccion():
            # 1. Crear el préstamo (en BORRADOR)
            prestamo_id = self.prestamos.crear(
                deudor_id=deudor_id,
                capital_original=capital,
                plazo_meses=plazo_meses,
                sistema=sistema,
                convencion_dias=convencion_dias,
                fecha_inicio=fecha_inicio,
                tc_inicial=tc_inicial,
                destino=destino,
                descripcion=descripcion,
            )

            # 2. Crear la versión inicial de tasa
            version_id = self.prestamos.crear_version_tasa(
                prestamo_id=prestamo_id,
                tasa_anual=tasa_anual,
                modalidad_tasa=modalidad_tasa,
                fecha_desde=fecha_inicio,
                motivo="Versión inicial",
            )

            # 3. Generar la tabla de amortización con el motor del dominio
            tabla = generar_tabla(
                capital=capital,
                tasa_anual=tasa_anual,
                modalidad=ModalidadTasa(modalidad_tasa),
                meses=plazo_meses,
                fecha_inicio=fecha_inicio,
                sistema=SistemaAmortizacion(sistema.lower()),
            )

            # 4. Persistir las cuotas
            self.prestamos.guardar_tabla_amortizacion(version_id, tabla)

            # 5. Crear las participaciones de los inversores
            for inv in inversores:
                porcentaje = inv["monto"] / capital
                tc_aporte = tc_inicial
                capital_usd_ref = (
                    inv["monto"] / tc_inicial if tc_inicial else None
                )
                self.participaciones.crear(
                    prestamo_id=prestamo_id,
                    inversor_id=inv["persona_id"],
                    capital_aportado=inv["monto"],
                    porcentaje=porcentaje,
                    fecha_aporte=fecha_inicio,
                    tc_aporte=tc_aporte,
                    capital_usd_ref=capital_usd_ref,
                )

            # 6. Registrar el desembolso en el ledger (doble entrada)
            self.ledger.registrar_operacion(
                movimientos=[
                    {
                        "entidad": "PRESTAMO",
                        "entidad_id": prestamo_id,
                        "tipo_movimiento": "DESEMBOLSO",
                        "debe": capital,
                        "haber": Decimal("0"),
                        "fecha": fecha_inicio,
                    },
                    {
                        "entidad": "INVERSOR",
                        "entidad_id": prestamo_id,  # el "pool" de inversores
                        "tipo_movimiento": "APORTE_INVERSORES",
                        "debe": Decimal("0"),
                        "haber": capital,
                        "fecha": fecha_inicio,
                    },
                ],
                correlacion_id=correlacion_id,
            )

            # 7. Auditoría del alta
            self.auditoria.registrar(
                usuario=usuario,
                operacion="PRESTAMO_CREADO",
                entidad="PRESTAMO",
                entidad_id=prestamo_id,
                correlacion_id=correlacion_id,
                datos_nuevos={
                    "capital": str(capital),
                    "plazo": plazo_meses,
                    "tasa": str(tasa_anual),
                    "modalidad": modalidad_tasa,
                    "sistema": sistema,
                    "inversores": len(inversores),
                    "fecha_inicio": fecha_str,
                },
                motivo="Alta completa de préstamo",
            )

            # 8. Activar el préstamo
            self.prestamos.actualizar_estado(prestamo_id, "ACTIVO")

            # 9. Auditoría de la activación
            self.auditoria.registrar(
                usuario=usuario,
                operacion="PRESTAMO_ACTIVADO",
                entidad="PRESTAMO",
                entidad_id=prestamo_id,
                correlacion_id=correlacion_id,
                datos_anteriores={"estado": "BORRADOR"},
                datos_nuevos={"estado": "ACTIVO"},
                motivo="Activación tras alta completa",
            )

        return prestamo_id

    # ============================================================
    # Ciclo de vida del préstamo
    # ============================================================

    ESTADOS_PRESTAMO = (
        "BORRADOR",
        "ACTIVO",
        "EN_MORA",
        "REFINANCIADO",
        "CANCELADO",
        "FINALIZADO",
        "ANULADO",
    )

    TRANSICIONES_PRESTAMO = {
        "BORRADOR": {"ACTIVO", "ANULADO"},
        "ACTIVO": {"EN_MORA", "FINALIZADO", "REFINANCIADO", "CANCELADO", "ANULADO"},
        "EN_MORA": {"ACTIVO", "FINALIZADO", "REFINANCIADO", "CANCELADO", "ANULADO"},
        "REFINANCIADO": set(),
        "CANCELADO": set(),
        "FINALIZADO": set(),
        "ANULADO": set(),
    }

    def cambiar_estado(
        self,
        prestamo_id: int,
        nuevo_estado: str,
        *,
        usuario: str,
        motivo: str | None = None,
    ) -> None:
        """Cambia el estado de un préstamo mediante una transición explícita.

        Toda transición queda registrada en auditoría y se ejecuta
        atómicamente junto con el cambio de estado.
        """
        if nuevo_estado not in self.ESTADOS_PRESTAMO:
            raise ErrorDatosInvalidos(f"Estado de préstamo inválido: {nuevo_estado}")
        if not usuario or not usuario.strip():
            raise ErrorDatosInvalidos("Se requiere un usuario")

        prestamo = self.prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorDatosInvalidos(f"El préstamo {prestamo_id} no existe")

        if nuevo_estado == prestamo.estado:
            raise ErrorEstadoInvalido(
                f"El préstamo ya se encuentra en estado {prestamo.estado}"
            )

        permitidos = self.TRANSICIONES_PRESTAMO.get(prestamo.estado, set())
        if nuevo_estado not in permitidos:
            raise ErrorEstadoInvalido(
                f"No se permite pasar de {prestamo.estado} a {nuevo_estado}"
            )

        if nuevo_estado in {"CANCELADO", "REFINANCIADO", "ANULADO"} and not (motivo or "").strip():
            raise ErrorDatosInvalidos(
                f"El cambio a {nuevo_estado} requiere un motivo"
            )

        if nuevo_estado == "FINALIZADO" and not self.puede_finalizar(prestamo_id):
            raise ErrorEstadoInvalido(
                "No se puede finalizar un préstamo que todavía tiene cuotas pendientes"
            )

        correlacion_id = nuevo_correlacion_id()
        with self.db.transaccion():
            self.prestamos.actualizar_estado(prestamo_id, nuevo_estado)
            self.auditoria.registrar(
                usuario=usuario,
                operacion="PRESTAMO_ESTADO_CAMBIADO",
                entidad="PRESTAMO",
                entidad_id=prestamo_id,
                correlacion_id=correlacion_id,
                datos_anteriores={"estado": prestamo.estado},
                datos_nuevos={"estado": nuevo_estado},
                motivo=(motivo or "").strip() or None,
            )

    def puede_finalizar(self, prestamo_id: int) -> bool:
        """Indica si todas las cuotas de la versión vigente están cerradas."""
        prestamo = self.prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorDatosInvalidos(f"El préstamo {prestamo_id} no existe")

        version_id = self.prestamos.version_activa(prestamo_id)
        if version_id is None:
            return False

        cuotas = self.prestamos.cuotas(version_id)
        if not cuotas:
            return False

        estados_terminales = {"PAGADA", "ANULADA"}
        return all(cuota.estado in estados_terminales for cuota in cuotas)

    def opciones_de_estado(self, prestamo_id: int) -> tuple[str, ...]:
        """Devuelve las transiciones válidas para mostrar en la UI."""
        prestamo = self.prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorDatosInvalidos(f"El préstamo {prestamo_id} no existe")

        return tuple(sorted(self.TRANSICIONES_PRESTAMO.get(prestamo.estado, set())))

    # ============================================================
    # Validaciones
    # ============================================================

    def _validar_alta(
        self,
        deudor_id: int,
        capital: Decimal,
        plazo_meses: int,
        inversores: list[dict],
    ) -> None:
        """Valida que todos los datos del alta sean coherentes."""

        # Deudor existente
        deudor = self.personas.obtener(deudor_id)
        if deudor is None:
            raise ErrorDatosInvalidos(
                f"El deudor con ID {deudor_id} no existe"
            )

        # Capital y plazo positivos
        if capital <= 0:
            raise ErrorDatosInvalidos("El capital debe ser mayor a cero")
        if plazo_meses <= 0:
            raise ErrorDatosInvalidos("El plazo debe ser mayor a cero")

        # Al menos un inversor
        if not inversores:
            raise ErrorDatosInvalidos("Debe haber al menos un inversor")

        # Verificar que los inversores existan y no estén duplicados
        ids_vistos = set()
        for inv in inversores:
            pid = inv.get("persona_id")
            if pid is None:
                raise ErrorDatosInvalidos(
                    "Cada inversor debe tener persona_id"
                )
            if pid == deudor_id:
                raise ErrorDatosInvalidos(
                    f"El deudor no puede ser inversor de su propio préstamo "
                    f"(persona_id {pid})"
                )
            if pid in ids_vistos:
                raise ErrorDatosInvalidos(
                    f"Inversor duplicado: persona_id {pid}"
                )
            ids_vistos.add(pid)

            persona = self.personas.obtener(pid)
            if persona is None:
                raise ErrorDatosInvalidos(
                    f"El inversor con ID {pid} no existe"
                )

            monto = inv.get("monto")
            if monto is None or monto <= 0:
                raise ErrorDatosInvalidos(
                    f"El monto del inversor {pid} debe ser mayor a cero"
                )

        # Suma de aportes == capital
        suma_aportes = sum(
            (inv["monto"] for inv in inversores), Decimal("0")
        )
        if suma_aportes != capital:
            raise ErrorDatosInvalidos(
                f"La suma de aportes ({suma_aportes}) no coincide con "
                f"el capital ({capital})"
            )