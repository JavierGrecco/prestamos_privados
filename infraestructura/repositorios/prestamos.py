"""
Repositorio de préstamos, versiones de tasa y cuotas.
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
from .modelos import Prestamo, Cuota


class PrestamoRepo(RepositorioBase):
    def __init__(self, db: BaseDatos):
        super().__init__(db)

    # ============================================================
    # Préstamos
    # ============================================================
    def _siguiente_numero(self) -> str:
        fila = self.db.consultar_uno(
            "SELECT MAX(CAST(SUBSTR(numero, 4) AS INTEGER)) AS ult FROM prestamos"
        )
        ultimo = fila["ult"] if fila and fila["ult"] is not None else 0
        return f"PR-{ultimo + 1:06d}"

    def crear(
        self,
        deudor_id: int,
        capital_original: Decimal,
        plazo_meses: int,
        sistema: str,
        convencion_dias: str,
        fecha_inicio: date,
        tc_inicial: Decimal | None = None,
        destino: str | None = None,
        descripcion: str | None = None,
    ) -> int:
        if capital_original <= 0:
            raise ValueError("El capital debe ser mayor a cero")
        if plazo_meses <= 0:
            raise ValueError("El plazo debe ser mayor a cero")

        numero = self._siguiente_numero()
        ahora = ahora_iso()

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO prestamos
                (numero, deudor_id, moneda_contractual, capital_original,
                 plazo_meses, sistema, convencion_dias, tc_inicial,
                 fecha_inicio, estado, destino, descripcion, creado_en)
                VALUES (?, ?, 'ARS', ?, ?, ?, ?, ?, ?, 'BORRADOR', ?, ?, ?)
                """,
                (
                    numero, deudor_id,
                    decimal_a_str(capital_original),
                    plazo_meses, sistema, convencion_dias,
                    decimal_a_str(tc_inicial),
                    fecha_a_iso(fecha_inicio),
                    destino, descripcion, ahora,
                ),
            )
            return self.db.ultimo_id_insertado()

    def obtener(self, prestamo_id: int) -> Prestamo | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM prestamos WHERE id = ?", (prestamo_id,)
        )
        return self._fila_a_prestamo(fila) if fila else None

    def listar(self, estado=None, deudor_id=None) -> list[Prestamo]:
        condiciones = []
        params = []
        if estado:
            condiciones.append("estado = ?")
            params.append(estado)
        if deudor_id:
            condiciones.append("deudor_id = ?")
            params.append(deudor_id)

        where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
        filas = self.db.consultar(
            f"SELECT * FROM prestamos{where} ORDER BY fecha_inicio DESC",
            tuple(params),
        )
        return [self._fila_a_prestamo(f) for f in filas]

    def actualizar_estado(self, prestamo_id: int, nuevo_estado: str) -> None:
        with self.db.transaccion():
            self.db.ejecutar(
                "UPDATE prestamos SET estado = ?, actualizado_en = ? WHERE id = ?",
                (nuevo_estado, ahora_iso(), prestamo_id),
            )

    # ============================================================
    # Versiones de tasa
    # ============================================================
    def crear_version_tasa(
        self,
        prestamo_id: int,
        tasa_anual: Decimal,
        modalidad_tasa: str,
        fecha_desde: date,
        motivo: str = "Versión inicial",
    ) -> int:
        fila = self.db.consultar_uno(
            "SELECT id FROM versiones_tasa WHERE prestamo_id = ? AND fecha_hasta IS NULL",
            (prestamo_id,),
        )
        version_anterior = fila["id"] if fila else None

        fila = self.db.consultar_uno(
            "SELECT MAX(version) AS v FROM versiones_tasa WHERE prestamo_id = ?",
            (prestamo_id,),
        )
        nro_version = (fila["v"] or 0) + 1 if fila else 1

        with self.db.transaccion():
            if version_anterior is not None:
                self.db.ejecutar(
                    "UPDATE versiones_tasa SET fecha_hasta = ? WHERE id = ?",
                    (fecha_a_iso(fecha_desde), version_anterior),
                )
            self.db.ejecutar(
                """
                INSERT INTO versiones_tasa
                (prestamo_id, version, fecha_desde, tasa_anual,
                 modalidad_tasa, motivo, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prestamo_id, nro_version,
                    fecha_a_iso(fecha_desde),
                    decimal_a_str(tasa_anual),
                    modalidad_tasa, motivo, ahora_iso(),
                ),
            )
            return self.db.ultimo_id_insertado()

    def version_activa(self, prestamo_id: int) -> int | None:
        fila = self.db.consultar_uno(
            "SELECT id FROM versiones_tasa WHERE prestamo_id = ? AND fecha_hasta IS NULL",
            (prestamo_id,),
        )
        return fila["id"] if fila else None

    def info_tasa_activa(self, prestamo_id: int) -> dict | None:
        fila = self.db.consultar_uno(
            """
            SELECT tasa_anual, modalidad_tasa
            FROM versiones_tasa
            WHERE prestamo_id = ? AND fecha_hasta IS NULL
            """,
            (prestamo_id,),
        )
        if not fila:
            return None
        return {
            "tasa_anual": str_a_decimal(fila["tasa_anual"]),
            "modalidad": fila["modalidad_tasa"],
        }

    # ============================================================
    # Cuotas
    # ============================================================
    def guardar_tabla_amortizacion(self, version_id: int, tabla: list[dict]) -> int:
        if not tabla:
            raise ValueError("La tabla de amortización está vacía")

        ahora = ahora_iso()
        with self.db.transaccion():
            for fila in tabla:
                self.db.ejecutar(
                    """
                    INSERT INTO cuotas
                    (version_id, numero, fecha_vencimiento, capital_inicial,
                     interes, interes_carencia, interes_carencia_pendiente,
                     capital, cuota, saldo, monto_pendiente, interes_pendiente,
                     capital_pendiente, mora_pendiente, fue_mora, tuvo_pago_parcial,
                     fue_recalculada, estado, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '0', '0', '0', '0',
                            0, 0, 0, 'PENDIENTE', ?)
                    """,
                    (
                        version_id, fila["numero"],
                        fecha_a_iso(fila["vencimiento"]),
                        decimal_a_str(fila["capital_inicial"]),
                        decimal_a_str(fila["interes"]),
                        decimal_a_str(Decimal(str(fila.get("interes_carencia", "0.00")))),
                        decimal_a_str(Decimal(str(fila.get(
                            "interes_carencia_pendiente",
                            fila.get("interes_carencia", "0.00"),
                        )))),
                        decimal_a_str(fila["capital"]),
                        decimal_a_str(fila["cuota"]),
                        decimal_a_str(fila["saldo"]),
                        ahora,
                    ),
                )
        return len(tabla)

    def cuotas(self, version_id: int) -> list[Cuota]:
        filas = self.db.consultar(
            "SELECT * FROM cuotas WHERE version_id = ? ORDER BY numero",
            (version_id,),
        )
        return [self._fila_a_cuota(f) for f in filas]

    def actualizar_cuota(
        self,
        cuota_id: int,
        estado: str,
        interes_pendiente: Decimal,
        capital_pendiente: Decimal,
        mora_pendiente: Decimal,
        fue_mora: bool,
        tuvo_pago_parcial: bool | None = None,
        fue_recalculada: bool | None = None,
        interes_carencia_pendiente: Decimal | None = None,
    ) -> None:
        monto_total = interes_pendiente + capital_pendiente + mora_pendiente

        campos = [
            "estado = ?",
            "interes_pendiente = ?",
            "capital_pendiente = ?",
            "mora_pendiente = ?",
            "monto_pendiente = ?",
            "fue_mora = ?",
        ]
        valores = [
            estado,
            decimal_a_str(interes_pendiente),
            decimal_a_str(capital_pendiente),
            decimal_a_str(mora_pendiente),
            decimal_a_str(monto_total),
            1 if fue_mora else 0,
        ]

        if interes_carencia_pendiente is not None:
            campos.append("interes_carencia_pendiente = ?")
            valores.append(decimal_a_str(interes_carencia_pendiente))

        if tuvo_pago_parcial is not None:
            campos.append("tuvo_pago_parcial = ?")
            valores.append(1 if tuvo_pago_parcial else 0)

        if fue_recalculada is not None:
            campos.append("fue_recalculada = ?")
            valores.append(1 if fue_recalculada else 0)

        valores.append(cuota_id)

        with self.db.transaccion():
            self.db.ejecutar(
                f"UPDATE cuotas SET {', '.join(campos)} WHERE id = ?",
                tuple(valores),
            )

    def borrar_cuotas_pendientes_desde(
        self,
        version_id: int,
        numero_desde: int,
    ) -> int:
        with self.db.transaccion():
            cursor = self.db.ejecutar(
                """
                DELETE FROM cuotas
                WHERE version_id = ?
                  AND numero >= ?
                  AND estado = 'PENDIENTE'
                """,
                (version_id, numero_desde),
            )
            return cursor.rowcount

    def crear_cuota_individual(
        self,
        version_id: int,
        numero: int,
        fecha_vencimiento: date,
        capital_inicial: Decimal,
        interes: Decimal,
        capital: Decimal,
        cuota: Decimal,
        saldo: Decimal,
        fue_recalculada: bool = False,
        interes_carencia: Decimal = Decimal("0.00"),
        interes_carencia_pendiente: Decimal | None = None,
    ) -> int:
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO cuotas
                (version_id, numero, fecha_vencimiento, capital_inicial,
                 interes, interes_carencia, interes_carencia_pendiente,
                 capital, cuota, saldo, monto_pendiente, interes_pendiente,
                 capital_pendiente, mora_pendiente, fue_mora, tuvo_pago_parcial,
                 fue_recalculada, estado, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '0', '0', '0', '0', 0, 0, ?,
                        'PENDIENTE', ?)
                """,
                (
                    version_id, numero,
                    fecha_a_iso(fecha_vencimiento),
                    decimal_a_str(capital_inicial),
                    decimal_a_str(interes),
                    decimal_a_str(interes_carencia),
                    decimal_a_str(
                        interes_carencia
                        if interes_carencia_pendiente is None
                        else interes_carencia_pendiente
                    ),
                    decimal_a_str(capital),
                    decimal_a_str(cuota),
                    decimal_a_str(saldo),
                    1 if fue_recalculada else 0,
                    ahora_iso(),
                ),
            )
            return self.db.ultimo_id_insertado()

    # ============================================================
    # Conversión
    # ============================================================
    def _fila_a_prestamo(self, fila) -> Prestamo:
        return Prestamo(
            id=fila["id"],
            numero=fila["numero"],
            deudor_id=fila["deudor_id"],
            moneda_contractual=fila["moneda_contractual"],
            capital_original=str_a_decimal(fila["capital_original"]),
            plazo_meses=fila["plazo_meses"],
            sistema=fila["sistema"],
            convencion_dias=fila["convencion_dias"],
            tc_inicial=str_a_decimal(fila["tc_inicial"]) if fila["tc_inicial"] else None,
            fecha_inicio=iso_a_fecha(fila["fecha_inicio"]),
            fecha_fin_estimada=iso_a_fecha(fila["fecha_fin_estimada"]),
            estado=fila["estado"],
            destino=fila["destino"],
            descripcion=fila["descripcion"],
            creado_en=fila["creado_en"],
            actualizado_en=fila["actualizado_en"],
        )

    def _fila_a_cuota(self, fila) -> Cuota:
        def _leer(nombre, default="0"):
            try:
                return fila[nombre]
            except (KeyError, IndexError):
                return default

        return Cuota(
            id=fila["id"],
            version_id=fila["version_id"],
            numero=fila["numero"],
            fecha_vencimiento=iso_a_fecha(fila["fecha_vencimiento"]),
            capital_inicial=str_a_decimal(fila["capital_inicial"]),
            interes=str_a_decimal(fila["interes"]),
            interes_carencia=str_a_decimal(_leer("interes_carencia")),
            interes_carencia_pendiente=str_a_decimal(
                _leer("interes_carencia_pendiente")
            ),
            capital=str_a_decimal(fila["capital"]),
            cuota=str_a_decimal(fila["cuota"]),
            saldo=str_a_decimal(fila["saldo"]),
            interes_pendiente=str_a_decimal(_leer("interes_pendiente")),
            capital_pendiente=str_a_decimal(_leer("capital_pendiente")),
            mora_pendiente=str_a_decimal(_leer("mora_pendiente")),
            monto_pendiente=str_a_decimal(_leer("monto_pendiente")),
            fue_mora=bool(_leer("fue_mora", 0) not in ("0", 0, None)),
            tuvo_pago_parcial=bool(
                _leer("tuvo_pago_parcial", 0) not in ("0", 0, None)
            ),
            fue_recalculada=bool(
                _leer("fue_recalculada", 0) not in ("0", 0, None)
            ),
            estado=fila["estado"],
            creado_en=fila["creado_en"],
        )