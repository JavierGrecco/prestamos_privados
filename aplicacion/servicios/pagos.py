"""
Servicio de pagos.
"""
import json
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

from .excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido


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

    # ============================================================
    # RESUMEN
    # ============================================================
    def resumen_impacto_financiero(self, prestamo_id: int) -> dict:
        version_id = self.prestamos.version_activa(prestamo_id)
        if version_id is None:
            return self._resumen_vacio()

        cuotas = self.prestamos.cuotas(version_id)
        pagos = self.pagos.por_prestamo(prestamo_id)
        pagos_validos = [p for p in pagos if p.estado == "VALIDA"]

        interes_extra_generado = sum(
            (p.interes_extra_generado for p in pagos_validos),
            Decimal("0.00"),
        )
        mora_generada = sum(
            (c.mora_pendiente for c in cuotas), Decimal("0.00")
        )
        intereses_ahorrados = sum(
            (p.intereses_ahorrados for p in pagos_validos),
            Decimal("0.00"),
        )
        capital_adelantado = sum(
            (p.monto_a_capital for p in pagos_validos),
            Decimal("0.00"),
        )

        con_atraso = [c for c in cuotas if c.fue_mora]

        costos_totales = interes_extra_generado + mora_generada
        ahorros_totales = intereses_ahorrados
        balance = costos_totales - ahorros_totales

        return {
            "mora_pendiente": mora_generada,
            "interes_extra_acumulado": interes_extra_generado,
            "intereses_ahorrados": intereses_ahorrados,
            "capital_adelantado": capital_adelantado,
            "cuotas_con_atraso": len(con_atraso),
            "cuotas_totales": len(cuotas),
            "numeros_con_atraso": [c.numero for c in con_atraso],
            "costos_totales": costos_totales,
            "ahorros_totales": ahorros_totales,
            "sobrecosto_total": balance,
            "hubo_decisiones": (
                costos_totales > 0
                or ahorros_totales > 0
                or len(con_atraso) > 0
            ),
        }

    def _resumen_vacio(self) -> dict:
        return {
            "mora_pendiente": Decimal("0.00"),
            "interes_extra_acumulado": Decimal("0.00"),
            "intereses_ahorrados": Decimal("0.00"),
            "capital_adelantado": Decimal("0.00"),
            "cuotas_con_atraso": 0,
            "cuotas_totales": 0,
            "numeros_con_atraso": [],
            "costos_totales": Decimal("0.00"),
            "ahorros_totales": Decimal("0.00"),
            "sobrecosto_total": Decimal("0.00"),
            "hubo_decisiones": False,
        }

    # ============================================================
    # HISTORIAL
    # ============================================================
    def historial_decisiones(self, prestamo_id: int) -> list[dict]:
        pagos = self.pagos.por_prestamo(prestamo_id)
        eventos = []

        for pago in pagos:
            if pago.estado != "VALIDA":
                continue

            tipo = pago.tipo_pago or "CUOTA"

            if tipo == "PARCIAL":
                if pago.interes_extra_generado > 0:
                    eventos.append({
                        "fecha": pago.fecha_real,
                        "tipo": "PAGO_PARCIAL",
                        "icono": "↩",
                        "titulo": "Pago parcial",
                        "descripcion": "Pagaste menos del total del mes",
                        "impacto": (
                            f"Ese monto generó "
                            f"{self._fmt(pago.interes_extra_generado)} "
                            f"de interés extra al mes siguiente"
                        ),
                        "monto_impacto": pago.interes_extra_generado,
                    })

            elif tipo in ("ADELANTO_RAI", "ADELANTO_RNI"):
                opcion = "RAI" if tipo == "ADELANTO_RAI" else "RNI"
                if pago.intereses_ahorrados > 0:
                    eventos.append({
                        "fecha": pago.fecha_real,
                        "tipo": tipo,
                        "icono": "💰",
                        "titulo": f"Adelanto {opcion}",
                        "descripcion": (
                            f"Adelantaste "
                            f"{self._fmt(pago.monto_a_capital)} a capital"
                        ),
                        "impacto": (
                            f"Ahorraste "
                            f"{self._fmt(pago.intereses_ahorrados)} "
                            f"en intereses"
                        ),
                        "monto_impacto": -pago.intereses_ahorrados,
                    })

        eventos.sort(key=lambda e: e["fecha"] or date.min)
        return eventos

    @staticmethod
    def _fmt(v: Decimal) -> str:
        entero, decimales = f"{v:.2f}".split(".")
        entero_con_puntos = f"{int(entero):,}".replace(",", ".")
        return f"$ {entero_con_puntos},{decimales}"

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
                    arrastre_capital * i_mensual
                ).quantize(Decimal("0.01"))
                if politica.interes_compensatorio_post_vencimiento
                else Decimal("0.00")

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
        politica = politica or self.politicas_pago.obtener_vigente(
            prestamo_id, fecha_calculo
        )
        return ServicioDeudaProximoPago(self.db).calcular(
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
    ) -> int:
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

        politica = politica or self.politicas_pago.obtener_vigente(
            prestamo_id, fecha_real
        )
        deuda = self.calcular_deuda_proximo_pago(
            prestamo_id, fecha_real, politica=politica
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

            if restante_mora > 0 and nueva_mora > 0:
                p = min(restante_mora, nueva_mora)
                nueva_mora -= p
                restante_mora -= p
            if restante_interes > 0 and nuevo_interes > 0:
                p = min(restante_interes, nuevo_interes)
                nuevo_interes -= p
                restante_interes -= p
            if restante_capital > 0 and nuevo_capital > 0:
                p = min(restante_capital, nuevo_capital)
                nuevo_capital -= p
                restante_capital -= p

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

        interes_obj_total = deuda["cuota_interes"] + deuda["interes_extra"]
        pago_interes_obj = min(restante_interes, interes_obj_total)
        nuevo_interes_obj = interes_obj_total - pago_interes_obj

        capital_obj_total = deuda["cuota_capital"]
        pago_capital_obj = min(restante_capital, capital_obj_total)
        nuevo_capital_obj = capital_obj_total - pago_capital_obj

        nueva_mora_obj = deuda["mora_nueva"]
        if restante_mora > 0 and nueva_mora_obj > 0:
            p = min(restante_mora, nueva_mora_obj)
            nueva_mora_obj -= p
            restante_mora -= p

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

        correlacion_id = nuevo_correlacion_id()

        with self.db.transaccion():
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
                    fecha=fecha_real,
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

        with self.db.transaccion():
            self.db.ejecutar(
                """
                UPDATE pagos
                SET intereses_ahorrados = ?,
                    cuotas_restantes_despues = ?,
                    opcion_adelanto = ?
                WHERE id = ?
                """,
                (
                    str(intereses_ahorrados),
                    cuotas_despues,
                    opcion,
                    pago_id,
                ),
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