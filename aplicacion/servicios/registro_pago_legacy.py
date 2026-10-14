"""Coordinador de escritura para el registro de pagos Legacy.

La fachada histórica `ServicioPagos` conserva la API pública y la política
de idempotencia. Este componente concentra la escritura y depende de contratos,
no de SQLite: imputación, actualización de cuotas, RAI/RNI, distribución,
ledger y auditoría permanecen dentro de una unidad de trabajo.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from dominio import tasa_mensual, ModalidadTasa, SistemaAmortizacion, PoliticaImputacionPago
from dominio.escenarios_pago import DeudaPago, simular_pago
from dominio.recalculo import recalcular_rai, recalcular_rni
from aplicacion.puertos.registro_pago_legacy import (
    UnidadTrabajoRegistroPago, RepositorioPrestamosRegistroPago,
    RepositorioPagosRegistroPago, ConsultaParticipacionesRegistroPago,
    RegistroLedgerPago, RegistroAuditoriaPago, RegistroRecalculosPago,
    RepositorioPoliticasPago, CalculadorDeudaProximoPago,
    GeneradorCorrelacionPago,
)
from .excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido


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

        restante_mora = a_mora
        restante_interes = a_interes
        restante_capital = a_capital

        actualizaciones = []
        for c in todas_las_cuotas:
            if c.id == cuota_obj.id:
                break
            if c.total_pendiente == 0:
                continue

            nueva_mora = c.mora_pendiente
            nuevo_interes = c.interes_pendiente
            nuevo_capital = c.capital_pendiente

            saldos = {
                "MORA": nueva_mora,
                "INTERES": nuevo_interes,
                "CAPITAL": nuevo_capital,
            }
            restantes = {
                "MORA": restante_mora,
                "INTERES": restante_interes,
                "CAPITAL": restante_capital,
            }
            for concepto in politica.orden_waterfall:
                disponible = saldos[concepto.value]
                pendiente_pago = restantes[concepto.value]
                if pendiente_pago <= 0 or disponible <= 0:
                    continue
                p = min(pendiente_pago, disponible)
                saldos[concepto.value] = disponible - p
                restantes[concepto.value] = pendiente_pago - p
            nueva_mora = saldos["MORA"]
            nuevo_interes = saldos["INTERES"]
            nuevo_capital = saldos["CAPITAL"]
            restante_mora = restantes["MORA"]
            restante_interes = restantes["INTERES"]
            restante_capital = restantes["CAPITAL"]

            if nueva_mora == 0 and nuevo_interes == 0 and nuevo_capital == 0:
                nuevo_estado = "PAGADA"
            else:
                nuevo_estado = "PARCIAL"

            sigue_pendiente = (
                nueva_mora > 0 or nuevo_interes > 0 or nuevo_capital > 0
            )
            nuevo_tuvo_parcial = c.tuvo_pago_parcial or sigue_pendiente

            actualizaciones.append({
                "cuota_id": c.id,
                "estado": nuevo_estado,
                "interes_pendiente": nuevo_interes,
                "capital_pendiente": nuevo_capital,
                "mora_pendiente": nueva_mora,
                "fue_mora": c.fue_mora,
                "tuvo_pago_parcial": nuevo_tuvo_parcial,
                "fue_recalculada": c.fue_recalculada,
            })

        nueva_mora_obj = deuda["mora_nueva"]
        nuevo_interes_obj = deuda["cuota_interes"] + deuda["interes_extra"]
        nuevo_capital_obj = deuda["cuota_capital"]

        pago_mora_obj = min(restante_mora, nueva_mora_obj)
        nueva_mora_obj = nueva_mora_obj - pago_mora_obj
        restante_mora = restante_mora - pago_mora_obj

        pago_interes_obj = min(restante_interes, nuevo_interes_obj)
        nuevo_interes_obj = nuevo_interes_obj - pago_interes_obj
        restante_interes = restante_interes - pago_interes_obj

        pago_capital_obj = min(restante_capital, nuevo_capital_obj)
        nuevo_capital_obj = nuevo_capital_obj - pago_capital_obj
        restante_capital = restante_capital - pago_capital_obj

        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        i_mensual = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )
        interes_extra_generado = Decimal("0.00")
        if politica.interes_compensatorio_post_vencimiento and nuevo_capital_obj > 0:
            interes_extra_generado = (
                nuevo_capital_obj * i_mensual
            ).quantize(Decimal("0.01"))

        if (
            nueva_mora_obj == 0
            and nuevo_interes_obj == 0
            and nuevo_capital_obj == 0
        ):
            nuevo_estado_obj = "PAGADA"
        else:
            nuevo_estado_obj = "PARCIAL"

        sigue_pendiente_obj = (
            nueva_mora_obj > 0
            or nuevo_interes_obj > 0
            or nuevo_capital_obj > 0
        )
        nuevo_tuvo_parcial_obj = (
            cuota_obj.tuvo_pago_parcial or sigue_pendiente_obj
        )

        actualizaciones.append({
            "cuota_id": cuota_obj.id,
            "estado": nuevo_estado_obj,
            "interes_pendiente": nuevo_interes_obj,
            "capital_pendiente": nuevo_capital_obj,
            "mora_pendiente": nueva_mora_obj,
            "fue_mora": cuota_obj.fue_mora or deuda["mora_nueva"] > 0,
            "tuvo_pago_parcial": nuevo_tuvo_parcial_obj,
            "fue_recalculada": cuota_obj.fue_recalculada,
        })

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
            imputaciones = []
            if a_mora > 0:
                imputaciones.append({
                    "cuota_id": cuota_obj.id,
                    "concepto": "MORA",
                    "monto": a_mora,
                })
            if a_interes > 0:
                imputaciones.append({
                    "cuota_id": cuota_obj.id,
                    "concepto": "INTERES",
                    "monto": a_interes,
                })
            if a_capital + monto_a_capital > 0:
                imputaciones.append({
                    "cuota_id": cuota_obj.id,
                    "concepto": "CAPITAL",
                    "monto": a_capital + monto_a_capital,
                })

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
        version_id = self.prestamos.version_activa(prestamo_id)
        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return

        cuotas = self.prestamos.cuotas(version_id)

        cuotas_futuras = []
        encontrado = False
        for c in cuotas:
            if c.id == cuota_objetivo.id:
                encontrado = True
                continue
            if encontrado and c.estado == "PENDIENTE":
                cuotas_futuras.append(c)

        if not cuotas_futuras:
            return

        meses_restantes = len(cuotas_futuras)
        fecha_ultimo_venc = cuotas_futuras[-1].fecha_vencimiento
        intereses_antes = sum(
            (c.interes for c in cuotas_futuras), Decimal("0.00")
        )

        capital_al_final = cuota_objetivo.saldo - monto_adelanto
        if capital_al_final < 0:
            capital_al_final = Decimal("0.00")

        if opcion == "RAI":
            nueva_tabla = recalcular_rai(
                capital_pendiente=capital_al_final,
                tasa_anual=info_tasa["tasa_anual"],
                modalidad=ModalidadTasa(info_tasa["modalidad"]),
                meses_restantes=meses_restantes,
                fecha_ultimo_vencimiento=fecha_ultimo_venc,
                sistema=SistemaAmortizacion("frances"),
            )
            cuotas_despues = meses_restantes
        else:
            nueva_tabla, n = recalcular_rni(
                capital_pendiente=capital_al_final,
                tasa_anual=info_tasa["tasa_anual"],
                modalidad=ModalidadTasa(info_tasa["modalidad"]),
                cuota_objetivo=cuota_objetivo.cuota,
                fecha_ultimo_vencimiento=fecha_ultimo_venc,
                sistema=SistemaAmortizacion("frances"),
            )
            if nueva_tabla is None:
                return
            cuotas_despues = n

        intereses_despues = sum(
            (f["interes"] for f in nueva_tabla), Decimal("0.00")
        )
        intereses_ahorrados = intereses_antes - intereses_despues

        numero_inicio = cuota_objetivo.numero + 1
        self.prestamos.borrar_cuotas_pendientes_desde(
            version_id, numero_inicio
        )

        for i, fila in enumerate(nueva_tabla):
            self.prestamos.crear_cuota_individual(
                version_id=version_id,
                numero=numero_inicio + i,
                fecha_vencimiento=fila["vencimiento"],
                capital_inicial=fila["capital_inicial"],
                interes=fila["interes"],
                capital=fila["capital"],
                cuota=fila["cuota"],
                saldo=fila["saldo"],
                fue_recalculada=True,
            )

        self.pagos.actualizar_datos_adelanto(
            pago_id=pago_id,
            intereses_ahorrados=intereses_ahorrados,
            cuotas_restantes_despues=cuotas_despues,
            opcion_adelanto=opcion,
        )

        detalle = json.dumps(nueva_tabla, default=str)
        self.recalculos.registrar(
            prestamo_id=prestamo_id,
            pago_id=pago_id,
            tipo=opcion,
            fecha=fecha,
            capital_antes=cuota_objetivo.saldo,
            capital_despues=capital_al_final,
            cuotas_antes=meses_restantes,
            cuotas_despues=cuotas_despues,
            intereses_antes=intereses_antes,
            intereses_despues=intereses_despues,
            detalle_json=detalle,
            cuota_objetivo_numero=cuota_objetivo.numero,
        )

    def _distribuir_a_inversores(
        self,
        prestamo_id: int,
        pago_id: int,
        aplicado: dict,
        fecha_real: date,
        correlacion_id: str,
    ) -> None:
        partes = self.participaciones.por_prestamo(prestamo_id)
        if not partes:
            return

        monto_total = sum(aplicado.values(), Decimal("0"))
        if monto_total <= 0:
            return

        movimientos = []
        for parte in partes:
            monto_inversor = monto_total * parte.porcentaje
            if monto_inversor > 0:
                movimientos.append({
                    "entidad": "INVERSOR",
                    "entidad_id": parte.inversor_id,
                    "tipo_movimiento": "COBRO_PAGO",
                    "debe": monto_inversor,
                    "haber": Decimal("0"),
                    "fecha": fecha_real,
                })
                movimientos.append({
                    "entidad": "PRESTAMO",
                    "entidad_id": prestamo_id,
                    "tipo_movimiento": "DISTRIBUCION_INVERSOR",
                    "debe": Decimal("0"),
                    "haber": monto_inversor,
                    "fecha": fecha_real,
                })

        if movimientos:
            self.ledger.registrar_operacion(
                movimientos=movimientos,
                correlacion_id=correlacion_id,
            )


__all__ = ["ManejadorRegistroPagoLegacy"]
