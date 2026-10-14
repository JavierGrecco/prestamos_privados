"""Aplicación del recálculo de cronograma después de un adelanto Legacy.

Este colaborador agrupa las operaciones de un adelanto RAI/RNI: obtiene las
cuotas futuras, calcula el cronograma nuevo y registra sus metadatos y
evidencias. Recibe repositorios por contratos y no abre una transacción propia;
el manejador de pago lo ejecuta dentro de la unidad atómica del registro.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from dominio import ModalidadTasa, SistemaAmortizacion
from dominio.recalculo import recalcular_rai, recalcular_rni
from aplicacion.puertos.registro_pago_legacy import (
    RepositorioPrestamosRegistroPago,
    RepositorioPagosRegistroPago,
    RegistroRecalculosPago,
)


class AplicadorAdelantoLegacy:
    """Recalcula el cronograma y persiste las evidencias del adelanto."""

    def __init__(
        self,
        *,
        prestamos: RepositorioPrestamosRegistroPago,
        pagos: RepositorioPagosRegistroPago,
        recalculos: RegistroRecalculosPago,
    ) -> None:
        self._prestamos = prestamos
        self._pagos = pagos
        self._recalculos = recalculos

    def aplicar(
        self,
        *,
        prestamo_id: int,
        pago_id: int,
        cuota_objetivo,
        monto_adelanto: Decimal,
        opcion: str,
        fecha: date,
    ) -> None:
        """Actualiza cuotas futuras y deja la traza del recálculo dentro de la transacción exterior."""
        version_id = self._prestamos.version_activa(prestamo_id)
        info_tasa = self._prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return

        cuotas = self._prestamos.cuotas(version_id)

        cuotas_futuras = []
        encontrado = False
        for cuota in cuotas:
            if cuota.id == cuota_objetivo.id:
                encontrado = True
                continue
            if encontrado and cuota.estado == "PENDIENTE":
                cuotas_futuras.append(cuota)

        if not cuotas_futuras:
            return

        meses_restantes = len(cuotas_futuras)
        fecha_ultimo_venc = cuotas_futuras[-1].fecha_vencimiento
        intereses_antes = sum(
            (cuota.interes for cuota in cuotas_futuras), Decimal("0.00")
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
            (fila["interes"] for fila in nueva_tabla), Decimal("0.00")
        )
        intereses_ahorrados = intereses_antes - intereses_despues

        numero_inicio = cuota_objetivo.numero + 1
        self._prestamos.borrar_cuotas_pendientes_desde(
            version_id, numero_inicio
        )

        for indice, fila in enumerate(nueva_tabla):
            self._prestamos.crear_cuota_individual(
                version_id=version_id,
                numero=numero_inicio + indice,
                fecha_vencimiento=fila["vencimiento"],
                capital_inicial=fila["capital_inicial"],
                interes=fila["interes"],
                capital=fila["capital"],
                cuota=fila["cuota"],
                saldo=fila["saldo"],
                fue_recalculada=True,
            )

        self._pagos.actualizar_datos_adelanto(
            pago_id=pago_id,
            intereses_ahorrados=intereses_ahorrados,
            cuotas_restantes_despues=cuotas_despues,
            opcion_adelanto=opcion,
        )

        detalle = json.dumps(nueva_tabla, default=str)
        self._recalculos.registrar(
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


__all__ = ["AplicadorAdelantoLegacy"]
