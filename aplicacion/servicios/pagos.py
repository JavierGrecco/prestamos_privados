"""
Servicio de pagos.
"""
import sqlite3
from datetime import date
from decimal import Decimal

from dominio import (
    calcular_mora,
    tasa_mensual,
    ModalidadTasa,
    SistemaAmortizacion,
    PoliticaImputacionPago,
)
from dominio.escenarios_pago import DeudaPago, simular_pago
from dominio.recalculo import (
    recalcular_rai,
    recalcular_rni,
    calcular_impacto,
)

from infraestructura.db import BaseDatos
from infraestructura.repositorios import (
    PrestamoRepo,
    PagoRepo,
    ParticipacionRepo,
    LedgerRepo,
    AuditoriaRepo,
    RecalculoRepo,
    PoliticaPagoRepo,
)
from infraestructura.repositorios.base import nuevo_correlacion_id

from aplicacion.consultas.deuda_proximo_pago import ServicioDeudaProximoPago
from aplicacion.consultas.impacto_pagos import ConsultaImpactoPagos
from aplicacion.servicios.registro_pago_legacy import ManejadorRegistroPagoLegacy
from aplicacion.puertos.registro_pago_ui import ResultadoRegistroPago

from .excepciones import (
    ErrorDatosInvalidos,
    ErrorConflictoIdempotencia,
    ErrorEstadoInvalido,
)
from infraestructura.excepciones import ErrorTransaccion
from dominio.excepciones import ErrorValidacion
from .validacion_monetaria import validar_importe_centavos


class ServicioPagos:
    def __init__(self, db: BaseDatos):
        self.db = db
        self.prestamos = PrestamoRepo(db)
        self.pagos = PagoRepo(db)
        self.participaciones = ParticipacionRepo(db)
        self.ledger = LedgerRepo(db)
        self.auditoria = AuditoriaRepo(db)
        self.recalculos = RecalculoRepo(db)
        self.politicas_pago = PoliticaPagoRepo(db)
        # La fachada mantiene compatibilidad; lecturas y escritura tienen
        # coordinadores explícitos para migrar la composición por etapas.
        self._consulta_impacto = ConsultaImpactoPagos(self.prestamos, self.pagos)
        self._manejador_registro_pago_legacy = ManejadorRegistroPagoLegacy(
            unidad_trabajo=db, prestamos=self.prestamos, pagos=self.pagos,
            participaciones=self.participaciones, ledger=self.ledger,
            auditoria=self.auditoria, recalculos=self.recalculos,
            politicas_pago=self.politicas_pago,
            calcular_deuda_proximo_pago=self.calcular_deuda_proximo_pago,
            nuevo_correlacion_id=nuevo_correlacion_id,
        )

    def _normalizar_idempotencia(
        self,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
    ) -> tuple[str | None, str | None]:
        """Valida y normaliza los datos de idempotencia una sola vez."""
        if (idempotency_key is None) != (idempotency_fingerprint is None):
            raise ErrorDatosInvalidos(
                "La clave y la huella de idempotencia deben informarse juntas"
            )
        if idempotency_key is None:
            return None, None
        if not isinstance(idempotency_key, str) or not isinstance(
            idempotency_fingerprint, str
        ):
            raise ErrorDatosInvalidos(
                "La clave y la huella de idempotencia deben ser texto"
            )

        idempotency_key = idempotency_key.strip()
        idempotency_fingerprint = idempotency_fingerprint.strip()
        if not idempotency_key or not idempotency_fingerprint:
            raise ErrorDatosInvalidos(
                "La clave y la huella de idempotencia no pueden estar vacías"
            )
        if len(idempotency_key) > 255:
            raise ErrorDatosInvalidos(
                "La clave de idempotencia no puede superar 255 caracteres"
            )
        if not self.pagos.admite_idempotencia():
            raise ErrorDatosInvalidos(
                "La base no admite idempotencia de pagos; se requiere la migración v009"
            )
        return idempotency_key, idempotency_fingerprint

    def _buscar_pago_idempotente(
        self,
        idempotency_key: str,
        idempotency_fingerprint: str,
    ) -> ResultadoRegistroPago | None:
        existente = self.pagos.buscar_por_clave_idempotencia(idempotency_key)
        if existente is None:
            return None
        pago_id, huella_guardada = existente
        if huella_guardada != idempotency_fingerprint:
            raise ErrorConflictoIdempotencia(
                "La clave de idempotencia ya está asociada a un pago anterior "
                "con datos diferentes; se rechazó el reintento.",
                pago_existente_id=pago_id,
            )
        return ResultadoRegistroPago(
            pago_id=pago_id,
            es_repeticion_idempotente=True,
        )

    def buscar_reintento_idempotente(
        self,
        *,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
    ) -> ResultadoRegistroPago | None:
        """Reconoce una repetición antes de capturar el snapshot de SOMBRA.

        El servicio volverá a comprobar la clave dentro de la transacción
        crítica de escritura para cerrar carreras entre esta lectura y el alta.
        """
        clave, huella = self._normalizar_idempotencia(
            idempotency_key,
            idempotency_fingerprint,
        )
        if clave is None or huella is None:
            return None
        return self._buscar_pago_idempotente(clave, huella)

    # ============================================================
    # RESUMEN E HISTORIAL DE IMPACTO
    # ============================================================
    def resumen_impacto_financiero(self, prestamo_id: int) -> dict:
        """Conserva la API histórica y delega la proyección a una consulta de lectura."""
        return self._consulta_impacto.resumen_impacto_financiero(prestamo_id)

    def _resumen_vacio(self) -> dict:
        """Compatibilidad para consumidores internos que usen el resumen vacío."""
        return self._consulta_impacto._resumen_vacio()

    def historial_decisiones(self, prestamo_id: int) -> list[dict]:
        """Conserva la API histórica del historial de decisiones de pago."""
        return self._consulta_impacto.historial_decisiones(prestamo_id)

    @staticmethod
    def _fmt(v: Decimal) -> str:
        """Compatibilidad con el formateador histórico de esta fachada."""
        return ConsultaImpactoPagos._fmt(v)

    # ============================================================
    # ESTADO DE CUOTAS
    # ============================================================
    def estado_cuotas_con_arrastre(
        self,
        prestamo_id: int,
        fecha_calculo: date,
    ) -> list[dict]:
        version_id = self.prestamos.version_activa(prestamo_id)
        if version_id is None:
            return []

        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return []
        politica = self.politicas_pago.obtener_vigente(prestamo_id, fecha_calculo)

        i_mensual = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )

        cuotas = self.prestamos.cuotas(version_id)

        proxima_idx = None
        for i, c in enumerate(cuotas):
            if c.estado == "PENDIENTE":
                proxima_idx = i
                break

        arrastre_capital = Decimal("0.00")
        arrastre_interes = Decimal("0.00")
        arrastre_mora = Decimal("0.00")

        resultado = []
        for i, c in enumerate(cuotas):
            item = {
                "numero": c.numero,
                "vencimiento": c.fecha_vencimiento,
                "estado": c.estado,
                "cuota_teorica": c.cuota,
                "interes_teorico": c.interes,
                "capital_teorico": c.capital,
                "saldo_teorico": c.saldo,
                "es_proxima": False,
                "monto_real": c.cuota,
                "desglose": None,
                "tuvo_pago_parcial": c.tuvo_pago_parcial,
                "fue_recalculada": c.fue_recalculada,
            }

            if i == proxima_idx:
                interes_extra = (
                    (arrastre_capital * i_mensual).quantize(Decimal("0.01"))
                    if politica.interes_compensatorio_post_vencimiento
                    else Decimal("0.00")
                )

                mora_nueva = Decimal("0.00")
                if (
                    politica.mora_habilitada
                    and c.fecha_vencimiento
                    and c.fecha_vencimiento < fecha_calculo
                ):
                    base_mora = (
                        c.cuota
                        if politica.mora_base.value == "CUOTA_CONTRACTUAL"
                        else c.capital
                    )
                    mora_nueva = calcular_mora(
                        monto_vencido=base_mora,
                        tasa_mora_anual=politica.mora_tasa_anual,
                        fecha_vencimiento=c.fecha_vencimiento,
                        fecha_calculo=fecha_calculo,
                    )

                tiene_arrastre = (
                    arrastre_capital > 0
                    or arrastre_interes > 0
                    or arrastre_mora > 0
                    or interes_extra > 0
                    or mora_nueva > 0
                )

                item["es_proxima"] = True
                item["monto_real"] = (
                    c.cuota
                    + arrastre_capital
                    + arrastre_interes
                    + arrastre_mora
                    + interes_extra
                    + mora_nueva
                )

                if tiene_arrastre:
                    item["desglose"] = {
                        "cuota_teorica": c.cuota,
                        "arrastre_capital": arrastre_capital,
                        "arrastre_interes": arrastre_interes,
                        "arrastre_mora": arrastre_mora,
                        "interes_extra": interes_extra,
                        "mora_nueva": mora_nueva,
                    }

            arrastre_capital += c.capital_pendiente
            arrastre_interes += c.interes_pendiente
            arrastre_mora += c.mora_pendiente

            resultado.append(item)

        return resultado

    # ============================================================
    # Cálculo de la deuda
    # ============================================================
    def calcular_deuda_proximo_pago(
        self,
        prestamo_id: int,
        fecha_calculo: date,
        politica: PoliticaImputacionPago | None = None,
    ) -> dict | None:
        """Compatibilidad pública con la consulta compartida de deuda."""
        if politica is None:
            try:
                politica = self.politicas_pago.obtener_vigente(
                    prestamo_id, fecha_calculo
                )
            except sqlite3.OperationalError as exc:
                if "no such table: politicas_pago" not in str(exc):
                    raise
                politica = PoliticaImputacionPago.canonica()
        return ServicioDeudaProximoPago(self.prestamos).calcular(
            prestamo_id,
            fecha_calculo,
            politica=politica,
        )

    # ============================================================
    # Simulación
    # ============================================================
    def simular_adelanto(
        self,
        prestamo_id: int,
        monto_adelanto: Decimal,
        fecha_calculo: date,
    ) -> dict | None:
        deuda = self.calcular_deuda_proximo_pago(prestamo_id, fecha_calculo)
        if deuda is None:
            return None

        version_id = self.prestamos.version_activa(prestamo_id)
        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return None

        cuota_obj = deuda["cuota_objetivo"]
        cuotas_actuales = self.prestamos.cuotas(version_id)

        cuotas_futuras = []
        encontrado = False
        for c in cuotas_actuales:
            if c.id == cuota_obj.id:
                encontrado = True
                continue
            if encontrado and c.estado == "PENDIENTE":
                cuotas_futuras.append(c)

        if not cuotas_futuras:
            return None

        capital_al_final_objetivo = cuota_obj.saldo
        capital_nuevo = capital_al_final_objetivo - monto_adelanto
        if capital_nuevo < 0:
            capital_nuevo = Decimal("0.00")

        meses_restantes = len(cuotas_futuras)
        fecha_ultimo_venc = cuotas_futuras[-1].fecha_vencimiento
        cuota_referencia = cuota_obj.cuota

        try:
            tabla_rai = recalcular_rai(
                capital_pendiente=capital_nuevo,
                tasa_anual=info_tasa["tasa_anual"],
                modalidad=ModalidadTasa(info_tasa["modalidad"]),
                meses_restantes=meses_restantes,
                fecha_ultimo_vencimiento=fecha_ultimo_venc,
                sistema=SistemaAmortizacion("frances"),
            )
            imp_rai = calcular_impacto(
                [{"interes": c.interes, "cuota": c.cuota} for c in cuotas_futuras],
                tabla_rai,
            )
        except Exception:
            tabla_rai = None
            imp_rai = None

        tabla_rni, n_rni = recalcular_rni(
            capital_pendiente=capital_nuevo,
            tasa_anual=info_tasa["tasa_anual"],
            modalidad=ModalidadTasa(info_tasa["modalidad"]),
            cuota_objetivo=cuota_referencia,
            fecha_ultimo_vencimiento=fecha_ultimo_venc,
            sistema=SistemaAmortizacion("frances"),
        )

        if tabla_rni is not None:
            imp_rni = calcular_impacto(
                [{"interes": c.interes, "cuota": c.cuota} for c in cuotas_futuras],
                tabla_rni,
            )
        else:
            imp_rni = None

        return {
            "capital_pendiente_actual": capital_al_final_objetivo,
            "capital_despues_adelanto": capital_nuevo,
            "monto_adelanto": monto_adelanto,
            "cuotas_restantes_antes": meses_restantes,
            "fecha_ultimo_vencimiento": fecha_ultimo_venc,
            "rai": {"tabla": tabla_rai, "impacto": imp_rai},
            "rni": {
                "tabla": tabla_rni,
                "cuotas_nuevas": n_rni,
                "impacto": imp_rni,
            },
        }

    # ============================================================
    # Registro de pago
    # ============================================================
    def registrar_pago(
        self,
        prestamo_id: int,
        monto: Decimal,
        fecha_real: date,
        usuario: str,
        medio: str | None = None,
        referencia: str | None = None,
        nota: str | None = None,
        opcion_adelanto: str | None = None,
        politica: PoliticaImputacionPago | None = None,
        idempotency_key: str | None = None,
        idempotency_fingerprint: str | None = None,
        devolver_resultado: bool = False,
        fecha_valor: date | None = None,
    ) -> int | ResultadoRegistroPago:
        validar_importe_centavos(monto, "El monto del pago")
        if type(fecha_real) is not date:
            raise ErrorDatosInvalidos("fecha_real debe ser una fecha civil sin hora")
        if fecha_valor is None:
            fecha_valor = fecha_real
        elif type(fecha_valor) is not date:
            raise ErrorDatosInvalidos("fecha_valor debe ser una fecha civil sin hora")

        idempotency_key, idempotency_fingerprint = self._normalizar_idempotencia(
            idempotency_key,
            idempotency_fingerprint,
        )

        pago_existente_id: int | None = None
        pago_nuevo_id: int | None = None
        try:
            # Reservar el turno de escritura antes de leer la deuda garantiza
            # que el cálculo y la persistencia usan el mismo estado del préstamo.
            with self.db.transaccion(inmediata=True):
                existente = (
                    self._buscar_pago_idempotente(
                        idempotency_key,
                        idempotency_fingerprint,
                    )
                    if idempotency_key is not None
                    and idempotency_fingerprint is not None
                    else None
                )
                if existente is not None:
                    pago_existente_id = existente.pago_id

                if pago_existente_id is None:
                    pago_nuevo_id = self._registrar_pago_en_transaccion(
                        prestamo_id=prestamo_id,
                        monto=monto,
                        fecha_real=fecha_real,
                        fecha_valor=fecha_valor,
                        usuario=usuario,
                        medio=medio,
                        referencia=referencia,
                        nota=nota,
                        opcion_adelanto=opcion_adelanto,
                        politica=politica,
                        idempotency_key=idempotency_key,
                        idempotency_fingerprint=idempotency_fingerprint,
                    )
        except ErrorTransaccion as exc:
            # La infraestructura traduce excepciones dentro de una unidad
            # transaccional a ErrorTransaccion. Mantener los errores de regla
            # de negocio como tales para que la UI pueda mostrarlos al usuario.
            causa = exc.__cause__
            while causa is not None:
                if isinstance(
                    causa,
                    (ErrorDatosInvalidos, ErrorEstadoInvalido, ErrorValidacion),
                ):
                    raise causa
                causa = causa.__cause__
            raise

        if pago_existente_id is not None:
            if devolver_resultado:
                return ResultadoRegistroPago(
                    pago_id=pago_existente_id,
                    es_repeticion_idempotente=True,
                )
            return pago_existente_id
        if pago_nuevo_id is None:
            raise ErrorDatosInvalidos("No se pudo confirmar el resultado del pago")
        if devolver_resultado:
            return ResultadoRegistroPago(
                pago_id=pago_nuevo_id,
                es_repeticion_idempotente=False,
            )
        return pago_nuevo_id

    def _registrar_pago_en_transaccion(
        self,
        prestamo_id: int,
        monto: Decimal,
        fecha_real: date,
        usuario: str,
        medio: str | None = None,
        referencia: str | None = None,
        nota: str | None = None,
        opcion_adelanto: str | None = None,
        politica: PoliticaImputacionPago | None = None,
        idempotency_key: str | None = None,
        idempotency_fingerprint: str | None = None,
        fecha_valor: date | None = None,
    ) -> int:
        """Mantiene la ruta interna histórica y delega la escritura al manejador."""
        return self._manejador_registro_pago_legacy.registrar_en_transaccion(
            prestamo_id=prestamo_id, monto=monto, fecha_real=fecha_real,
            usuario=usuario, medio=medio, referencia=referencia, nota=nota,
            opcion_adelanto=opcion_adelanto, politica=politica,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
            fecha_valor=fecha_valor,
        )
