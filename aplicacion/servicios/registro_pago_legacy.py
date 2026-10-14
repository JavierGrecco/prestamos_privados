"""Coordinador de escritura para el registro de pagos Legacy.

La fachada histórica `ServicioPagos` conserva la API pública; este manejador coordina
la idempotencia y la unidad de trabajo inmediata de la escritura. Depende de contratos,
no de SQLite: validación, imputación, actualización de cuotas, RAI/RNI, distribución,
ledger y auditoría permanecen dentro de la misma operación atómica.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from dominio import tasa_mensual, ModalidadTasa, PoliticaImputacionPago
from dominio.escenarios_pago import DeudaPago, simular_pago
from aplicacion.puertos.registro_pago_legacy import (
    UnidadTrabajoRegistroPago, RepositorioPrestamosRegistroPago,
    RepositorioPagosRegistroPago, ConsultaParticipacionesRegistroPago,
    RegistroLedgerPago, RegistroAuditoriaPago, RegistroRecalculosPago,
    RepositorioPoliticasPago, CalculadorDeudaProximoPago,
    GeneradorCorrelacionPago,
)
from aplicacion.puertos.registro_pago_ui import ResultadoRegistroPago
from .excepciones import (
    ErrorDatosInvalidos,
    ErrorConflictoIdempotencia,
    ErrorEstadoInvalido,
)
from .validacion_monetaria import validar_importe_centavos
from .distribucion_pago_legacy import DistribuidorPagoLegacy
from .aplicador_adelanto_legacy import AplicadorAdelantoLegacy
from .preparacion_cuotas_anteriores_pago_legacy import (
    PreparadorCuotasAnterioresPagoLegacy,
)
from .preparacion_cuota_objetivo_pago_legacy import (
    PreparadorCuotaObjetivoPagoLegacy,
)


class ManejadorRegistroPagoLegacy:
    """Coordina una escritura Legacy sin conocer tablas ni conexión SQLite."""

    def __init__(
        self, *, unidad_trabajo: UnidadTrabajoRegistroPago,
        prestamos: RepositorioPrestamosRegistroPago,
        pagos: RepositorioPagosRegistroPago,
        participaciones: ConsultaParticipacionesRegistroPago,
        ledger: RegistroLedgerPago, auditoria: RegistroAuditoriaPago,
        recalculos: RegistroRecalculosPago,
        politicas_pago: RepositorioPoliticasPago,
        calcular_deuda_proximo_pago: CalculadorDeudaProximoPago,
        nuevo_correlacion_id: GeneradorCorrelacionPago,
    ) -> None:
        self.unidad_trabajo = unidad_trabajo
        self.prestamos = prestamos
        self.pagos = pagos
        self.participaciones = participaciones
        self.ledger = ledger
        self.auditoria = auditoria
        self.recalculos = recalculos
        self.politicas_pago = politicas_pago
        self._calcular_deuda_proximo_pago = calcular_deuda_proximo_pago
        self._nuevo_correlacion_id = nuevo_correlacion_id
        self._distribuidor_pago_legacy = DistribuidorPagoLegacy(
            participaciones=participaciones,
            ledger=ledger,
        )
        self._aplicador_adelanto_legacy = AplicadorAdelantoLegacy(
            prestamos=prestamos,
            pagos=pagos,
            recalculos=recalculos,
        )
        self._preparador_cuotas_anteriores = PreparadorCuotasAnterioresPagoLegacy()
        self._preparador_cuota_objetivo = PreparadorCuotaObjetivoPagoLegacy()

    def _normalizar_idempotencia(
        self,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
    ) -> tuple[str | None, str | None]:
        """Valida y normaliza una clave y una huella antes de abrir la transacción."""
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
        """Reconoce una repetición antes del snapshot de SOMBRA.

        El alta vuelve a comprobar la clave dentro de la transacción inmediata,
        para evitar duplicados en carreras entre la consulta previa y la escritura.
        """
        clave, huella = self._normalizar_idempotencia(
            idempotency_key, idempotency_fingerprint
        )
        if clave is None or huella is None:
            return None
        return self._buscar_pago_idempotente(clave, huella)

    def registrar_pago_atomico(
        self,
        *,
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
        """Ejecuta la comprobación idempotente y el pago dentro de una única unidad.

        La reserva de escritura ocurre antes de consultar la deuda. Un reintento
        duplicado devuelve el pago existente; una clave con otra huella se rechaza.
        """
        validar_importe_centavos(monto, "El monto del pago")
        if type(fecha_real) is not date:
            raise ErrorDatosInvalidos("fecha_real debe ser una fecha civil sin hora")
        if fecha_valor is None:
            fecha_valor = fecha_real
        elif type(fecha_valor) is not date:
            raise ErrorDatosInvalidos("fecha_valor debe ser una fecha civil sin hora")

        clave, huella = self._normalizar_idempotencia(
            idempotency_key, idempotency_fingerprint
        )
        pago_existente_id: int | None = None
        pago_nuevo_id: int | None = None

        with self.unidad_trabajo.transaccion(inmediata=True):
            existente = (
                self._buscar_pago_idempotente(clave, huella)
                if clave is not None and huella is not None
                else None
            )
            if existente is not None:
                pago_existente_id = existente.pago_id

            if pago_existente_id is None:
                pago_nuevo_id = self.registrar_en_transaccion(
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
                    idempotency_key=clave,
                    idempotency_fingerprint=huella,
                )

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

    def registrar_en_transaccion(
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
        if type(fecha_real) is not date:
            raise ErrorDatosInvalidos("fecha_real debe ser una fecha civil sin hora")
        if fecha_valor is None:
            fecha_valor = fecha_real
        elif type(fecha_valor) is not date:
            raise ErrorDatosInvalidos("fecha_valor debe ser una fecha civil sin hora")
        if monto <= 0:
            raise ErrorDatosInvalidos("El monto debe ser mayor a cero")

        prestamo = self.prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorDatosInvalidos(f"El préstamo {prestamo_id} no existe")
        if prestamo.estado not in ("ACTIVO", "EN_MORA"):
            raise ErrorEstadoInvalido(
                f"No se puede registrar un pago en un préstamo "
                f"en estado {prestamo.estado}"
            )

        politica_pago_id = None
        if politica is None:
            politica_pago_id, politica = (
                self.politicas_pago.obtener_vigente_con_id_o_canonica(
                    prestamo_id, fecha_valor
                )
            )
        # La fecha valor define la fecha económica para determinar deuda,
        # mora e intereses; fecha_real se conserva para el evento de caja/ledger.
        deuda = self._calcular_deuda_proximo_pago(
            prestamo_id, fecha_valor, politica=politica
        )
        if deuda is None:
            raise ErrorEstadoInvalido("El préstamo no tiene cuotas pendientes")

        cuota_obj = deuda["cuota_objetivo"]
        total_a_pagar = deuda["total_a_pagar"]

        excedente_previo = monto - total_a_pagar
        es_adelanto = excedente_previo > 0

        tiene_arrastre = (
            deuda["arrastre_capital"] > 0
            or deuda["arrastre_interes"] > 0
            or deuda["arrastre_mora"] > 0
            or deuda["interes_extra"] > 0
        )

        if es_adelanto and opcion_adelanto not in ("RAI", "RNI"):
            raise ErrorDatosInvalidos(
                "El pago excede el total del mes. Tenés que elegir "
                "entre RAI (reducir cuota) o RNI (acortar plazo)."
            )

        d_mora = deuda["arrastre_mora"] + deuda["mora_nueva"]
        d_interes = (
            deuda["arrastre_interes"]
            + deuda["cuota_interes"]
            + deuda["interes_extra"]
        )
        d_capital = deuda["arrastre_capital"] + deuda["cuota_capital"]

        deuda_pago = DeudaPago(
            cuota_interes=deuda["cuota_interes"],
            cuota_capital=deuda["cuota_capital"],
            arrastre_interes=deuda["arrastre_interes"],
            arrastre_capital=deuda["arrastre_capital"],
            arrastre_mora=deuda["arrastre_mora"],
            interes_extra=deuda["interes_extra"],
            mora_nueva=deuda["mora_nueva"],
        )
        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            raise ErrorDatosInvalidos("El préstamo no tiene tasa activa")
        resultado_imputacion = simular_pago(
            monto,
            deuda_pago,
            tasa_mensual(
                info_tasa["tasa_anual"],
                ModalidadTasa(info_tasa["modalidad"]),
            ),
            politica=politica,
        )
        a_mora = resultado_imputacion.aplicado_mora
        a_interes = resultado_imputacion.aplicado_interes
        a_capital = resultado_imputacion.aplicado_capital

        monto_a_capital = excedente_previo if es_adelanto else Decimal("0.00")

        version_id = self.prestamos.version_activa(prestamo_id)
        todas_las_cuotas = self.prestamos.cuotas(version_id)

        resultado_cuotas_anteriores = self._preparador_cuotas_anteriores.preparar(
            cuotas=todas_las_cuotas,
            cuota_objetivo=cuota_obj,
            aplicado_mora=a_mora,
            aplicado_interes=a_interes,
            aplicado_capital=a_capital,
            orden_waterfall=politica.orden_waterfall,
        )
        actualizaciones = list(resultado_cuotas_anteriores.actualizaciones)
        restante_mora = resultado_cuotas_anteriores.restante_mora
        restante_interes = resultado_cuotas_anteriores.restante_interes
        restante_capital = resultado_cuotas_anteriores.restante_capital

        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        i_mensual = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )
        resultado_cuota_objetivo = self._preparador_cuota_objetivo.preparar(
            cuota_objetivo=cuota_obj,
            deuda=deuda,
            restante_mora=restante_mora,
            restante_interes=restante_interes,
            restante_capital=restante_capital,
            aplicado_mora=a_mora,
            aplicado_interes=a_interes,
            aplicado_capital=a_capital,
            monto_a_capital=monto_a_capital,
            tasa_mensual=i_mensual,
            interes_compensatorio_post_vencimiento=(
                politica.interes_compensatorio_post_vencimiento
            ),
        )
        actualizaciones.append(resultado_cuota_objetivo.actualizacion)
        interes_extra_generado = resultado_cuota_objetivo.interes_extra_generado
        imputaciones = list(resultado_cuota_objetivo.imputaciones)

        if es_adelanto:
            tipo_pago = f"ADELANTO_{opcion_adelanto}"
        elif monto < total_a_pagar:
            tipo_pago = "PARCIAL"
        elif tiene_arrastre:
            tipo_pago = "COMPLEMENTO"
        else:
            tipo_pago = "CUOTA"

        correlacion_id = self._nuevo_correlacion_id()

        with self.unidad_trabajo.transaccion():
            pago_id = self.pagos.registrar(
                prestamo_id=prestamo_id,
                fecha_real=fecha_real,
                fecha_valor=fecha_valor,
                monto_moneda_pago=monto,
                imputaciones=imputaciones,
                medio=medio,
                referencia=referencia,
                nota=nota,
                creado_por=usuario,
                tipo_pago=tipo_pago,
                monto_a_capital=monto_a_capital,
                interes_extra_generado=interes_extra_generado,
                cuotas_restantes_antes=len(
                    [c for c in todas_las_cuotas if c.estado == "PENDIENTE"]
                ),
                politica_pago_id=politica_pago_id,
                idempotency_key=idempotency_key,
                idempotency_fingerprint=idempotency_fingerprint,
            )

            for act in actualizaciones:
                self.prestamos.actualizar_cuota(
                    cuota_id=act["cuota_id"],
                    estado=act["estado"],
                    interes_pendiente=act["interes_pendiente"],
                    capital_pendiente=act["capital_pendiente"],
                    mora_pendiente=act["mora_pendiente"],
                    fue_mora=act["fue_mora"],
                    tuvo_pago_parcial=act.get("tuvo_pago_parcial"),
                    fue_recalculada=act.get("fue_recalculada"),
                )

            if es_adelanto and monto_a_capital > 0:
                self._aplicar_adelanto(
                    prestamo_id=prestamo_id,
                    pago_id=pago_id,
                    cuota_objetivo=cuota_obj,
                    monto_adelanto=monto_a_capital,
                    opcion=opcion_adelanto,
                    fecha=fecha_valor,
                )

            aplicado = {
                "MORA": a_mora,
                "INTERES": a_interes,
                "CAPITAL": a_capital + monto_a_capital,
            }
            self._distribuir_a_inversores(
                prestamo_id=prestamo_id,
                pago_id=pago_id,
                aplicado=aplicado,
                fecha_real=fecha_real,
                correlacion_id=correlacion_id,
            )

            self.ledger.registrar_operacion(
                movimientos=[
                    {
                        "entidad": "PRESTAMO",
                        "entidad_id": prestamo_id,
                        "tipo_movimiento": "PAGO_RECIBIDO",
                        "debe": Decimal("0"),
                        "haber": monto,
                        "fecha": fecha_real,
                    },
                    {
                        "entidad": "PAGO",
                        "entidad_id": pago_id,
                        "tipo_movimiento": "PAGO",
                        "debe": monto,
                        "haber": Decimal("0"),
                        "fecha": fecha_real,
                    },
                ],
                correlacion_id=correlacion_id,
            )

            self.auditoria.registrar(
                usuario=usuario,
                operacion="PAGO_REGISTRADO",
                entidad="PAGO",
                entidad_id=pago_id,
                correlacion_id=correlacion_id,
                datos_nuevos={
                    "prestamo_id": prestamo_id,
                    "monto": str(monto),
                    "fecha": fecha_real.isoformat(),
                    "fecha_valor": fecha_valor.isoformat(),
                    "tipo_pago": tipo_pago,
                    "cuota_objetivo": cuota_obj.numero,
                    "monto_a_capital": str(monto_a_capital),
                    "interes_extra_generado": str(interes_extra_generado),
                    "opcion_adelanto": opcion_adelanto,
                },
                motivo=f"Pago registrado por {usuario}",
            )

        return pago_id

    def _aplicar_adelanto(
        self,
        prestamo_id: int,
        pago_id: int,
        cuota_objetivo,
        monto_adelanto: Decimal,
        opcion: str,
        fecha: date,
    ) -> None:
        """Conserva el punto interno histórico y delega el recálculo."""
        self._aplicador_adelanto_legacy.aplicar(
            prestamo_id=prestamo_id,
            pago_id=pago_id,
            cuota_objetivo=cuota_objetivo,
            monto_adelanto=monto_adelanto,
            opcion=opcion,
            fecha=fecha,
        )

    def _distribuir_a_inversores(
        self,
        prestamo_id: int,
        pago_id: int,
        aplicado: dict,
        fecha_real: date,
        correlacion_id: str,
    ) -> None:
        """Conserva el punto de extensión histórico y delega el reparto."""
        self._distribuidor_pago_legacy.distribuir(
            prestamo_id=prestamo_id,
            aplicado=aplicado,
            fecha_real=fecha_real,
            correlacion_id=correlacion_id,
        )


__all__ = ["ManejadorRegistroPagoLegacy"]
