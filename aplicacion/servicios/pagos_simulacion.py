"""Extensión del servicio de pagos para simular decisiones sin guardar cambios.

La simulación y el registro usan el mismo plan puro. La diferencia es que la
simulación solamente lo devuelve; registrar_pago() lo aplica dentro de una
transacción.
"""
from datetime import date
from decimal import Decimal

from dominio import ModalidadTasa, tasa_mensual
from dominio.plan_pago import CuotaParaPago, planificar_pago

from .pagos import ServicioPagos as ServicioPagosBase
from .excepciones import ErrorDatosInvalidos, ErrorEstadoInvalido


class ServicioPagosConSimulacion(ServicioPagosBase):
    """Agrega simulación previa sin cambiar la API pública del servicio."""

    def simular_pago(
        self,
        prestamo_id: int,
        monto: Decimal,
        fecha_calculo: date,
    ) -> dict:
        """Calcula un pago y devuelve el mismo plan que luego puede registrarse."""
        if monto <= 0:
            raise ErrorDatosInvalidos("El monto debe ser mayor a cero")

        prestamo = self.prestamos.obtener(prestamo_id)
        if prestamo is None:
            raise ErrorDatosInvalidos(f"El préstamo {prestamo_id} no existe")
        if prestamo.estado not in ("ACTIVO", "EN_MORA"):
            raise ErrorEstadoInvalido(
                f"No se puede simular un pago en un préstamo "
                f"en estado {prestamo.estado}"
            )

        deuda = self.calcular_deuda_proximo_pago(prestamo_id, fecha_calculo)
        if deuda is None:
            raise ErrorEstadoInvalido("El préstamo no tiene cuotas pendientes")

        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            raise ErrorEstadoInvalido("El préstamo no tiene una tasa activa")

        tasa = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )

        version_id = self.prestamos.version_activa(prestamo_id)
        cuotas = self.prestamos.cuotas(version_id)
        cuotas_para_plan = [
            CuotaParaPago(
                id=c.id,
                numero=c.numero,
                estado=c.estado,
                interes_pendiente=c.interes_pendiente,
                capital_pendiente=c.capital_pendiente,
                mora_pendiente=c.mora_pendiente,
                fue_mora=c.fue_mora,
                tuvo_pago_parcial=c.tuvo_pago_parcial,
                fue_recalculada=c.fue_recalculada,
            )
            for c in cuotas
        ]

        plan = planificar_pago(
            monto=monto,
            cuotas=cuotas_para_plan,
            cuota_objetivo_id=deuda["cuota_objetivo"].id,
            cuota_interes=deuda["cuota_interes"],
            cuota_capital=deuda["cuota_capital"],
            tasa_mensual=tasa,
            arrastre_interes=deuda["arrastre_interes"],
            arrastre_capital=deuda["arrastre_capital"],
            arrastre_mora=deuda["arrastre_mora"],
            interes_extra=deuda["interes_extra"],
            mora_nueva=deuda["mora_nueva"],
        )

        salida = {
            "prestamo_id": prestamo_id,
            "fecha_calculo": fecha_calculo,
            "cuota_objetivo": deuda["cuota_objetivo"],
            "total_a_pagar": deuda["total_a_pagar"],
            "resultado": plan.resultado,
            "plan": plan,
            "deuda": {
                "arrastre_interes": deuda["arrastre_interes"],
                "arrastre_capital": deuda["arrastre_capital"],
                "arrastre_mora": deuda["arrastre_mora"],
                "interes_extra": deuda["interes_extra"],
                "mora_nueva": deuda["mora_nueva"],
            },
            "adelanto": None,
        }

        # Un excedente se sigue mostrando con RAI/RNI. Es una proyección y no
        # cambia ninguna cuota hasta que el usuario confirme el pago.
        if plan.resultado.excedente > 0:
            salida["adelanto"] = self.simular_adelanto(
                prestamo_id=prestamo_id,
                monto_adelanto=plan.resultado.excedente,
                fecha_calculo=fecha_calculo,
            )

        return salida
