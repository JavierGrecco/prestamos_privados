"""
Repositorio de pagos e imputaciones.
"""
from datetime import date
from decimal import Decimal

from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    fecha_a_iso,
    iso_a_fecha,
    decimal_a_str,
    str_a_decimal,
)
from .modelos import Pago, Imputacion


class PagoRepo(RepositorioBase):
    """Acceso a las tablas `pagos` e `imputaciones`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def registrar(
        self,
        prestamo_id: int,
        fecha_real: date,
        monto_moneda_pago: Decimal,
        imputaciones: list[dict],
        fecha_valor: date | None = None,
        medio: str | None = None,
        referencia: str | None = None,
        nota: str | None = None,
        tc_aplicado: Decimal | None = None,
        monto_usd_ref: Decimal | None = None,
        creado_por: str | None = None,
        tipo_pago: str = "CUOTA",
        monto_a_capital: Decimal = Decimal("0.00"),
        intereses_ahorrados: Decimal = Decimal("0.00"),
        interes_extra_generado: Decimal = Decimal("0.00"),
        cuotas_restantes_antes: int = 0,
        cuotas_restantes_despues: int = 0,
        opcion_adelanto: str | None = None,
        politica_pago_id: int | None = None,
    ) -> int:
        if monto_moneda_pago <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero")
        if not imputaciones:
            raise ValueError("El pago debe tener al menos una imputación")

        suma_imp = sum(
            (Decimal(str(i["monto"])) for i in imputaciones),
            Decimal("0"),
        )
        if suma_imp != monto_moneda_pago:
            raise ValueError(
                f"La suma de imputaciones ({suma_imp}) no coincide con "
                f"el monto del pago ({monto_moneda_pago})"
            )

        ahora = ahora_iso()
        fecha_valor = fecha_valor or fecha_real
        columnas_pago_extra = ""
        valores_pago_extra = ""
        parametros_pago_extra: tuple[object, ...] = ()
        columnas = "politica_pago_id" in {
            str(fila["name"]) for fila in self.db.consultar("PRAGMA table_info(pagos)")
        }
        if columnas and politica_pago_id is not None:
            columnas_pago_extra = ", politica_pago_id"
            valores_pago_extra = ", ?"
            parametros_pago_extra = (politica_pago_id,)

        with self.db.transaccion():
            self.db.ejecutar(
                f"""
                INSERT INTO pagos
                (prestamo_id, fecha_real, fecha_valor, fecha_registro,
                 moneda_pago, monto_moneda_pago, tc_aplicado,
                 monto_moneda_contractual, monto_usd_ref, medio,
                 referencia, nota, estado, creado_por,
                 tipo_pago, monto_a_capital, intereses_ahorrados,
                 interes_extra_generado,
                 cuotas_restantes_antes, cuotas_restantes_despues,
                 opcion_adelanto{columnas_pago_extra})
                VALUES (?, ?, ?, ?, 'ARS', ?, ?, ?, ?, ?, ?, ?, 'VALIDA', ?,
                        ?, ?, ?, ?, ?, ?, ?{valores_pago_extra})
                """,
                (
                    prestamo_id,
                    fecha_a_iso(fecha_real),
                    fecha_a_iso(fecha_valor),
                    ahora,
                    decimal_a_str(monto_moneda_pago),
                    decimal_a_str(tc_aplicado),
                    decimal_a_str(monto_moneda_pago),
                    decimal_a_str(monto_usd_ref),
                    medio,
                    referencia,
                    nota,
                    creado_por,
                    tipo_pago,
                    decimal_a_str(monto_a_capital),
                    decimal_a_str(intereses_ahorrados),
                    decimal_a_str(interes_extra_generado),
                    cuotas_restantes_antes,
                    cuotas_restantes_despues,
                    opcion_adelanto,
                    *parametros_pago_extra,
                ),
            )
            pago_id = self.db.ultimo_id_insertado()

            for imp in imputaciones:
                self.db.ejecutar(
                    """
                    INSERT INTO imputaciones
                    (pago_id, cuota_id, concepto, monto, creado_en)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        pago_id,
                        imp.get("cuota_id"),
                        imp["concepto"],
                        decimal_a_str(Decimal(str(imp["monto"]))),
                        ahora,
                    ),
                )

        return pago_id

    def obtener(self, pago_id: int) -> Pago | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM pagos WHERE id = ?",
            (pago_id,),
        )
        return self._fila_a_pago(fila) if fila else None

    def por_prestamo(self, prestamo_id: int) -> list[Pago]:
        filas = self.db.consultar(
            """
            SELECT * FROM pagos
            WHERE prestamo_id = ?
            ORDER BY fecha_real, id
            """,
            (prestamo_id,),
        )
        return [self._fila_a_pago(f) for f in filas]

    def imputaciones_de(self, pago_id: int) -> list[Imputacion]:
        filas = self.db.consultar(
            "SELECT * FROM imputaciones WHERE pago_id = ? ORDER BY id",
            (pago_id,),
        )
        return [self._fila_a_imputacion(f) for f in filas]

    def anular(self, pago_id: int, motivo: str) -> None:
        if not motivo or not motivo.strip():
            raise ValueError("Se requiere un motivo para anular un pago")

        with self.db.transaccion():
            self.db.ejecutar(
                """
                UPDATE pagos
                SET estado = 'ANULADA', motivo_anulacion = ?
                WHERE id = ? AND estado = 'VALIDA'
                """,
                (motivo.strip(), pago_id),
            )

    def _fila_a_pago(self, fila) -> Pago:
        def _leer(nombre, default=None):
            try:
                return fila[nombre]
            except (KeyError, IndexError):
                return default

        return Pago(
            id=fila["id"],
            prestamo_id=fila["prestamo_id"],
            fecha_real=iso_a_fecha(fila["fecha_real"]),
            fecha_valor=iso_a_fecha(fila["fecha_valor"]),
            fecha_registro=fila["fecha_registro"],
            moneda_pago=fila["moneda_pago"],
            monto_moneda_pago=str_a_decimal(fila["monto_moneda_pago"]),
            tc_aplicado=str_a_decimal(fila["tc_aplicado"]) if fila["tc_aplicado"] else None,
            monto_moneda_contractual=str_a_decimal(fila["monto_moneda_contractual"]),
            monto_usd_ref=str_a_decimal(fila["monto_usd_ref"]) if fila["monto_usd_ref"] else None,
            medio=fila["medio"],
            referencia=fila["referencia"],
            nota=fila["nota"],
            estado=fila["estado"],
            motivo_anulacion=fila["motivo_anulacion"],
            creado_por=fila["creado_por"],
            tipo_pago=_leer("tipo_pago", "CUOTA") or "CUOTA",
            monto_a_capital=str_a_decimal(_leer("monto_a_capital", "0")),
            intereses_ahorrados=str_a_decimal(_leer("intereses_ahorrados", "0")),
            interes_extra_generado=str_a_decimal(_leer("interes_extra_generado", "0")),
            cuotas_restantes_antes=_leer("cuotas_restantes_antes", 0) or 0,
            cuotas_restantes_despues=_leer("cuotas_restantes_despues", 0) or 0,
            opcion_adelanto=_leer("opcion_adelanto"),
            politica_pago_id=(
                int(_leer("politica_pago_id"))
                if _leer("politica_pago_id") is not None
                else None
            ),
        )

    def _fila_a_imputacion(self, fila) -> Imputacion:
        return Imputacion(
            id=fila["id"],
            pago_id=fila["pago_id"],
            cuota_id=fila["cuota_id"],
            concepto=fila["concepto"],
            monto=str_a_decimal(fila["monto"]),
            creado_en=fila["creado_en"],
        )