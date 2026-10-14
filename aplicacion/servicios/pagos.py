"""
Servicio de pagos.
"""
import sqlite3
from datetime import date
from decimal import Decimal

from dominio import PoliticaImputacionPago

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
from aplicacion.consultas.estado_cuotas_con_arrastre import ConsultaEstadoCuotasConArrastre
from aplicacion.consultas.simulacion_adelanto_legacy import ConsultaSimulacionAdelantoLegacy
from aplicacion.consultas.impacto_pagos import ConsultaImpactoPagos
from aplicacion.servicios.registro_pago_legacy import ManejadorRegistroPagoLegacy
from aplicacion.puertos.registro_pago_legacy import (
    RepositorioPrestamosRegistroPago,
    RepositorioPagosRegistroPago,
    ConsultaParticipacionesRegistroPago,
    RegistroLedgerPago,
    RegistroAuditoriaPago,
    RegistroRecalculosPago,
    RepositorioPoliticasPago,
)
from aplicacion.puertos.registro_pago_ui import ResultadoRegistroPago

from .excepciones import (
    ErrorDatosInvalidos,
    ErrorEstadoInvalido,
)
from infraestructura.excepciones import ErrorTransaccion
from dominio.excepciones import ErrorValidacion


class ServicioPagos:
    def __init__(
        self,
        db: BaseDatos,
        *,
        prestamos: RepositorioPrestamosRegistroPago | None = None,
        pagos: RepositorioPagosRegistroPago | None = None,
        participaciones: ConsultaParticipacionesRegistroPago | None = None,
        ledger: RegistroLedgerPago | None = None,
        auditoria: RegistroAuditoriaPago | None = None,
        recalculos: RegistroRecalculosPago | None = None,
        politicas_pago: RepositorioPoliticasPago | None = None,
    ) -> None:
        """Construye la fachada con colaboradores inyectados.

        La composición oficial los recibe desde infraestructura. El camino
        `ServicioPagos(db)` se mantiene temporalmente como puente compatible
        para consumidores antiguos que aún no usan la fábrica.
        """
        self.db = db
        colaboradores = (
            prestamos, pagos, participaciones, ledger, auditoria, recalculos,
            politicas_pago,
        )
        if all(item is None for item in colaboradores):
            # Puente temporal de compatibilidad: el camino oficial se ensambla
            # en infraestructura.composicion.servicio_pagos_legacy.
            self.prestamos = PrestamoRepo(db)
            self.pagos = PagoRepo(db)
            self.participaciones = ParticipacionRepo(db)
            self.ledger = LedgerRepo(db)
            self.auditoria = AuditoriaRepo(db)
            self.recalculos = RecalculoRepo(db)
            self.politicas_pago = PoliticaPagoRepo(db)
        elif any(item is None for item in colaboradores):
            raise ValueError(
                "La inyección requiere todos los repositorios y colaboradores "
                "de pagos; use crear_servicio_pagos_legacy() para ensamblarlos."
            )
        else:
            self.prestamos = prestamos
            self.pagos = pagos
            self.participaciones = participaciones
            self.ledger = ledger
            self.auditoria = auditoria
            self.recalculos = recalculos
            self.politicas_pago = politicas_pago

        # Los coordinadores de aplicación reciben colaboradores ya montados;
        # no crean repositorios ni conocen infraestructura concreta.
        self._consulta_impacto = ConsultaImpactoPagos(self.prestamos, self.pagos)
        self._consulta_estado_cuotas_con_arrastre = ConsultaEstadoCuotasConArrastre(
            self.prestamos,
            self.politicas_pago,
        )
        # Se mantiene la resolución de deuda del método público, incluida su
        # política vigente y el fallback histórico de bases anteriores.
        self._consulta_simulacion_adelanto_legacy = ConsultaSimulacionAdelantoLegacy(
            self.prestamos,
            lambda prestamo_id, fecha: self.calcular_deuda_proximo_pago(
                prestamo_id, fecha
            ),
        )
        self._manejador_registro_pago_legacy = ManejadorRegistroPagoLegacy(
            unidad_trabajo=db,
            prestamos=self.prestamos,
            pagos=self.pagos,
            participaciones=self.participaciones,
            ledger=self.ledger,
            auditoria=self.auditoria,
            recalculos=self.recalculos,
            politicas_pago=self.politicas_pago,
            calcular_deuda_proximo_pago=self.calcular_deuda_proximo_pago,
            nuevo_correlacion_id=nuevo_correlacion_id,
        )

    def _normalizar_idempotencia(
        self,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
    ) -> tuple[str | None, str | None]:
        """Compatibilidad: la validación reside en el manejador de escritura."""
        return self._manejador_registro_pago_legacy._normalizar_idempotencia(
            idempotency_key, idempotency_fingerprint
        )

    def _buscar_pago_idempotente(
        self,
        idempotency_key: str,
        idempotency_fingerprint: str,
    ) -> ResultadoRegistroPago | None:
        """Compatibilidad para los consumidores internos históricos."""
        return self._manejador_registro_pago_legacy._buscar_pago_idempotente(
            idempotency_key, idempotency_fingerprint
        )

    def buscar_reintento_idempotente(
        self,
        *,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
    ) -> ResultadoRegistroPago | None:
        """Compatibilidad pública para SOMBRA; el manejador resuelve el reintento."""
        return self._manejador_registro_pago_legacy.buscar_reintento_idempotente(
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
        )

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
        """Conserva la API histórica y delega la proyección de solo lectura."""
        return self._consulta_estado_cuotas_con_arrastre.obtener(
            prestamo_id,
            fecha_calculo,
        )

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
        """Conserva la API pública y delega la simulación sin escribir datos."""
        return self._consulta_simulacion_adelanto_legacy.simular(
            prestamo_id,
            monto_adelanto,
            fecha_calculo,
        )

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
        """Fachada compatible; el manejador coordina la unidad atómica completa."""
        try:
            return self._manejador_registro_pago_legacy.registrar_pago_atomico(
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
                devolver_resultado=devolver_resultado,
            )
        except ErrorTransaccion as exc:
            # La infraestructura envuelve fallos de reglas al revertir. La
            # fachada conserva la traducción histórica para que la UI reciba
            # excepciones de aplicación y no errores internos de transacción.
            causa = exc.__cause__
            while causa is not None:
                if isinstance(
                    causa,
                    (ErrorDatosInvalidos, ErrorEstadoInvalido, ErrorValidacion),
                ):
                    raise causa
                causa = causa.__cause__
            raise

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
