"""Adaptador SQLite real para la frontera de registro de pagos V3.1.

La capa implementa el puerto de ``aplicacion.servicios.registro_pago_v3``.
No contiene el waterfall financiero: recibe un PlanPago ya validado y lo
persiste de forma atómica junto con cuotas, imputaciones, ledger y auditoría.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import uuid

from infraestructura.db import BaseDatos
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.motor_pagos_v3 import OrigenImputacion
from dominio.tipos import ConceptoImputacion, money
from aplicacion.servicios.registro_pago_v3 import (
    EstadoRegistroPagoV3,
    IdempotenciaPagoV3,
)
from dominio.motor_pagos_v3 import ObligacionSnapshot
from dominio.adelanto_v3 import CuotaFuturaAdelantoV3, PlanAdelantoV3


MOTOR_VERSION_V3 = "V3-F3.1"
ESTADOS_PRESTAMO_PAGO = ("ACTIVO", "EN_MORA")
ESTADOS_ABIERTOS = ("PENDIENTE", "PARCIAL", "VENCIDA")


class RepositorioRegistroPagoSQLiteV3:
    """Implementación concreta de persistencia para RegistrarPagoV3."""

    def __init__(self, db: BaseDatos) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Transacción crítica
    # ------------------------------------------------------------------
    def begin(self) -> None:
        conexion = self.db.conexion
        if conexion.in_transaction:
            raise ErrorInvariante("No se puede iniciar F3 dentro de otra transacción")
        # BEGIN IMMEDIATE reserva el lock de escritura antes de la lectura
        # crítica. Esto reduce el riesgo de que dos escritores calculen sobre
        # el mismo revision_prestamo y luego compitan por persistir.
        conexion.execute("BEGIN IMMEDIATE")

    def commit(self) -> None:
        self.db.conexion.execute("COMMIT")

    def rollback(self) -> None:
        conexion = self.db.conexion
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")

    # ------------------------------------------------------------------
    # Idempotencia
    # ------------------------------------------------------------------
    def buscar_idempotencia(self, idempotency_key: str) -> IdempotenciaPagoV3 | None:
        fila = self.db.consultar_uno(
            """
            SELECT id, idempotency_key, idempotency_fingerprint
            FROM pagos
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        )
        if fila is None:
            return None
        fingerprint = fila["idempotency_fingerprint"]
        if not fingerprint:
            raise ErrorInvariante(
                f"El pago {fila['id']} tiene idempotency_key pero no fingerprint"
            )
        return IdempotenciaPagoV3(
            idempotency_key=fila["idempotency_key"],
            fingerprint=fingerprint,
            pago_id=int(fila["id"]),
        )

    # ------------------------------------------------------------------
    # Snapshot vigente
    # ------------------------------------------------------------------
    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3:
        fila_prestamo = self.db.consultar_uno(
            """
            SELECT id, estado, revision_prestamo
            FROM prestamos
            WHERE id = ?
            """,
            (prestamo_id,),
        )
        if fila_prestamo is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no existe")
        if fila_prestamo["estado"] not in ESTADOS_PRESTAMO_PAGO:
            raise ErrorValidacion(
                f"No se puede registrar un pago en un préstamo en estado {fila_prestamo['estado']}"
            )

        revision = int(fila_prestamo["revision_prestamo"])
        version = self.db.consultar_uno(
            """
            SELECT id
            FROM versiones_tasa
            WHERE prestamo_id = ? AND fecha_hasta IS NULL
            ORDER BY version DESC, id DESC
            LIMIT 1
            """,
            (prestamo_id,),
        )
        if version is None:
            raise ErrorValidacion(
                f"El préstamo {prestamo_id} no tiene una versión de tasa activa"
            )

        filas = self.db.consultar(
            """
            SELECT
                id, numero, fecha_vencimiento, estado,
                interes, capital, cuota,
                interes_pendiente, capital_pendiente, mora_pendiente,
                monto_pendiente, tuvo_pago_parcial
            FROM cuotas
            WHERE version_id = ?
            ORDER BY fecha_vencimiento, numero, id
            """,
            (version["id"],),
        )

        snapshots: list[tuple[ObligacionSnapshot, Decimal]] = []
        for fila in filas:
            estado = str(fila["estado"])
            interes_pendiente = _decimal(fila["interes_pendiente"])
            capital_pendiente = _decimal(fila["capital_pendiente"])
            mora_pendiente = _decimal(fila["mora_pendiente"])
            tuvo_parcial = bool(fila["tuvo_pago_parcial"])

            # Compatibilidad con cuotas nuevas creadas por el plan de
            # amortización: antes de su primer pago, los campos _pendiente
            # históricamente se guardan en cero. Su obligación contractual se
            # encuentra en interes/capital.
            if (
                estado == "PENDIENTE"
                and not tuvo_parcial
                and interes_pendiente == 0
                and capital_pendiente == 0
                and mora_pendiente == 0
            ):
                interes_pendiente = _decimal(fila["interes"])
                capital_pendiente = _decimal(fila["capital"])

            total = money(interes_pendiente + capital_pendiente + mora_pendiente)
            if estado == "PAGADA" and total != 0:
                raise ErrorInvariante(
                    f"La cuota {fila['id']} figura PAGADA con saldo pendiente {total}"
                )
            if estado in ("ANULADA", "REESTRUCTURADA") and total != 0:
                raise ErrorInvariante(
                    f"La cuota {fila['id']} está {estado} pero conserva saldo {total}"
                )

            snapshot = ObligacionSnapshot.desde_cuota_actual(
                cuota_id=int(fila["id"]),
                numero_cuota=int(fila["numero"]),
                vencimiento=date.fromisoformat(fila["fecha_vencimiento"]),
                estado=estado,
                tuvo_pago_parcial=tuvo_parcial,
                interes_pendiente=interes_pendiente,
                capital_pendiente=capital_pendiente,
                mora_pendiente=mora_pendiente,
                monto_mora_base=_decimal(fila["cuota"]),
            )
            snapshots.append((snapshot, total))

        # El pago ordinario llega hasta la primera obligación contractual que
        # todavía esté abierta. Las cuotas futuras NO forman parte del
        # waterfall; un importe que supere esta obligación es un excedente y
        # debe resolverse explícitamente como PREPAGO/RAI/RNI.
        abiertas = [(snap, total) for snap, total in snapshots if total > 0]
        if abiertas:
            primer_pendiente = next(
                (i for i, (snap, _) in enumerate(snapshots) if snap.estado == "PENDIENTE" and (snap.saldo.total > 0)),
                None,
            )
            if primer_pendiente is None:
                limite = max(i for i, (snap, total) in enumerate(snapshots) if total > 0)
            else:
                limite = primer_pendiente
            obligaciones = tuple(
                snap for i, (snap, total) in enumerate(snapshots)
                if i <= limite and total > 0
            )
        else:
            obligaciones = tuple()

        return EstadoRegistroPagoV3(
            prestamo_id=prestamo_id,
            revision_prestamo=revision,
            obligaciones=obligaciones,
        )

    # ------------------------------------------------------------------
    # Persistencia atómica
    # ------------------------------------------------------------------
    def persistir_pago(
        self,
        command,
        plan,
        *,
        fingerprint: str,
        revision_esperada: int,
        permitir_excedente: bool = False,
        monto_adelanto: Decimal = Decimal("0.00"),
        tipo_pago_override: str | None = None,
        intereses_ahorrados: Decimal = Decimal("0.00"),
    ) -> int:
        from dominio.tipos import ZERO

        plan.validar()
        if plan.prestamo_id != command.prestamo_id:
            raise ErrorInvariante("El plan no corresponde al préstamo del comando")
        if plan.fecha_valor != command.fecha_valor:
            raise ErrorInvariante("El plan no corresponde a la fecha valor del comando")
        if plan.monto_pago_recibido != command.monto:
            raise ErrorInvariante("El plan no corresponde al monto del comando")
        if plan.revision_prestamo != revision_esperada:
            raise ErrorInvariante("La revisión del plan no coincide con la esperada")

        monto_adelanto = money(monto_adelanto)
        intereses_ahorrados = money(intereses_ahorrados)
        if plan.excedente.monto > ZERO:
            if not permitir_excedente:
                raise ErrorValidacion(
                    "El plan contiene excedente: debe resolverse explícitamente como RAI o RNI"
                )
            if monto_adelanto != plan.excedente.monto:
                raise ErrorInvariante("El monto de adelanto no coincide con el excedente del plan")
            if command.opcion_adelanto not in ("RAI", "RNI"):
                raise ErrorValidacion("Un excedente requiere opcion_adelanto RAI o RNI")
            if tipo_pago_override not in ("ADELANTO_RAI", "ADELANTO_RNI"):
                raise ErrorInvariante("El tipo de pago de adelanto no es válido")
        else:
            if monto_adelanto != ZERO or intereses_ahorrados != ZERO or tipo_pago_override is not None:
                raise ErrorInvariante("Se informó información de prepago sin excedente")
            if command.opcion_adelanto is not None:
                raise ErrorValidacion("No existe excedente al cual aplicar RAI/RNI")
        if not plan.aplicaciones and monto_adelanto == ZERO:
            raise ErrorInvariante("No se puede persistir un pago sin imputaciones")

        fila_prestamo = self.db.consultar_uno(
            "SELECT estado, revision_prestamo FROM prestamos WHERE id = ?",
            (command.prestamo_id,),
        )
        if fila_prestamo is None:
            raise ErrorValidacion(f"El préstamo {command.prestamo_id} no existe")
        if fila_prestamo["estado"] not in ESTADOS_PRESTAMO_PAGO:
            raise ErrorValidacion(
                f"No se puede registrar un pago en estado {fila_prestamo['estado']}"
            )
        if int(fila_prestamo["revision_prestamo"]) != revision_esperada:
            raise ErrorInvariante(
                "Conflicto de revisión del préstamo al persistir"
            )

        correlacion_id = str(uuid.uuid4())
        ahora = datetime.now().isoformat(timespec="seconds")
        cuotas_antes = self._cantidad_obligaciones_abiertas(command.prestamo_id)

        plan_json = _serializar_plan(plan)
        plan_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()
        politica_pago_id = self._politica_pago_id_vigente(
            command.prestamo_id,
            command.fecha_valor,
        )

        try:
            columnas_extra = ""
            valores_extra = ""
            parametros_extra: tuple[object, ...] = ()
            if politica_pago_id is not None:
                columnas_extra = ", politica_pago_id"
                valores_extra = ", ?"
                parametros_extra = (politica_pago_id,)

            self.db.ejecutar(
                f"""
                INSERT INTO pagos
                (prestamo_id, fecha_real, fecha_valor, fecha_registro,
                 moneda_pago, monto_moneda_pago, tc_aplicado,
                 monto_moneda_contractual, monto_usd_ref, medio, referencia, nota,
                 estado, creado_por,
                 tipo_pago, monto_a_capital, intereses_ahorrados,
                 interes_extra_generado,
                 cuotas_restantes_antes, cuotas_restantes_despues,
                 opcion_adelanto,
                 idempotency_key, idempotency_fingerprint,
                 motor_version, plan_hash, plan_json{columnas_extra})
                VALUES (?, ?, ?, ?, 'ARS', ?, NULL, ?, NULL, ?, ?, ?,
                        'VALIDA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?{valores_extra})
                """,
                (
                    command.prestamo_id,
                    command.fecha_real.isoformat(),
                    command.fecha_valor.isoformat(),
                    ahora,
                    str(command.monto),
                    str(command.monto),
                    command.medio,
                    command.referencia,
                    command.nota,
                    command.usuario,
                    tipo_pago_override or plan.tipo.value,
                    str(money(plan.monto_a_capital + monto_adelanto)),
                    str(intereses_ahorrados),
                    str(money(plan.interes_generado)),
                    cuotas_antes,
                    cuotas_antes,
                    command.opcion_adelanto,
                    command.idempotency_key,
                    fingerprint,
                    MOTOR_VERSION_V3,
                    plan_hash,
                    plan_json,
                    *parametros_extra,
                ),
            )
            pago_id = int(self.db.ultimo_id_insertado())

            for aplicacion in plan.aplicaciones:
                self.db.ejecutar(
                    """
                    INSERT INTO imputaciones
                    (pago_id, cuota_id, concepto, monto, creado_en,
                     origen, referencias_devengamiento)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pago_id,
                        aplicacion.cuota_id,
                        aplicacion.concepto.value,
                        str(aplicacion.monto),
                        ahora,
                        aplicacion.origen.value,
                        json.dumps(
                            list(aplicacion.referencias_devengamiento),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    ),
                )

            if monto_adelanto > ZERO:
                self.db.ejecutar(
                    """
                    INSERT INTO imputaciones
                    (pago_id, cuota_id, concepto, monto, creado_en,
                     origen, referencias_devengamiento)
                    VALUES (?, NULL, 'CAPITAL', ?, ?, 'PREPAGO', '[]')
                    """,
                    (pago_id, str(monto_adelanto), ahora),
                )

            filas_imputaciones = self.db.consultar(
                "SELECT monto FROM imputaciones WHERE pago_id = ? ORDER BY id",
                (pago_id,),
            )
            suma_imputaciones = money(
                sum((_decimal(f["monto"]) for f in filas_imputaciones), ZERO)
            )
            if suma_imputaciones != command.monto:
                raise ErrorInvariante(
                    f"Conservación de imputaciones violada: {money(suma_imputaciones)} != {command.monto}"
                )

            for afectada in plan.obligaciones_afectadas:
                fila = self.db.consultar_uno(
                    "SELECT fue_mora FROM cuotas WHERE id = ?",
                    (afectada.cuota_id,),
                )
                if fila is None:
                    raise ErrorInvariante(
                        f"La cuota {afectada.cuota_id} desapareció durante persistencia"
                    )
                fue_mora = bool(fila["fue_mora"]) or afectada.mora_generada > ZERO
                self.db.ejecutar(
                    """
                    UPDATE cuotas
                    SET estado = ?,
                        interes_pendiente = ?,
                        capital_pendiente = ?,
                        mora_pendiente = ?,
                        monto_pendiente = ?,
                        fue_mora = ?,
                        tuvo_pago_parcial = ?
                    WHERE id = ?
                    """,
                    (
                        afectada.estado_posterior,
                        str(afectada.saldo_posterior.interes),
                        str(afectada.saldo_posterior.capital),
                        str(afectada.saldo_posterior.mora),
                        str(afectada.saldo_posterior.total),
                        1 if fue_mora else 0,
                        1 if afectada.tuvo_pago_parcial_posterior else 0,
                        afectada.cuota_id,
                    ),
                )

            # El incremento de revisión es parte de la misma transacción.
            cursor = self.db.ejecutar(
                """
                UPDATE prestamos
                SET revision_prestamo = revision_prestamo + 1,
                    actualizado_en = ?
                WHERE id = ? AND revision_prestamo = ?
                """,
                (ahora, command.prestamo_id, revision_esperada),
            )
            if cursor.rowcount != 1:
                raise ErrorInvariante(
                    "No se pudo incrementar revision_prestamo de forma atómica"
                )

            cuotas_despues = self._cantidad_obligaciones_abiertas(command.prestamo_id)
            self.db.ejecutar(
                "UPDATE pagos SET cuotas_restantes_despues = ? WHERE id = ?",
                (cuotas_despues, pago_id),
            )

            # Ledger de doble entrada: operación recibida contra el pago.
            self.db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber,
                 fecha, metadata, correlacion_id, creado_en)
                VALUES ('PRESTAMO', ?, 'PAGO_RECIBIDO', '0', ?, ?, ?, ?, ?)
                """,
                (
                    command.prestamo_id,
                    str(command.monto),
                    command.fecha_real.isoformat(),
                    json.dumps({"pago_id": pago_id}, separators=(",", ":")),
                    correlacion_id,
                    ahora,
                ),
            )
            self.db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber,
                 fecha, metadata, correlacion_id, creado_en)
                VALUES ('PAGO', ?, 'PAGO', ?, '0', ?, ?, ?, ?)
                """,
                (
                    pago_id,
                    str(command.monto),
                    command.fecha_real.isoformat(),
                    json.dumps({"prestamo_id": command.prestamo_id}, separators=(",", ":")),
                    correlacion_id,
                    ahora,
                ),
            )

            self.db.ejecutar(
                """
                INSERT INTO auditoria
                (fecha, usuario, operacion, entidad, entidad_id,
                 datos_anteriores, datos_nuevos, motivo, correlacion_id)
                VALUES (?, ?, 'PAGO_REGISTRADO_V3', 'PAGO', ?, NULL, ?, ?, ?)
                """,
                (
                    ahora,
                    command.usuario,
                    pago_id,
                    json.dumps(
                        {
                            "prestamo_id": command.prestamo_id,
                            "monto": str(command.monto),
                            "fecha_real": command.fecha_real.isoformat(),
                            "fecha_valor": command.fecha_valor.isoformat(),
                            "motor_version": MOTOR_VERSION_V3,
                            "plan_hash": plan_hash,
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "Registro mediante Motor de Pagos V3",
                    correlacion_id,
                ),
            )
            return pago_id
        except Exception:
            # No hacemos rollback aquí: F2 es dueño de la transacción y debe
            # ser quien decida el rollback. Relevante para conservar el
            # contrato de la frontera de aplicación.
            raise

    def _politica_pago_id_vigente(
        self,
        prestamo_id: int,
        fecha_valor: date,
    ) -> int | None:
        """Resuelve la versión efectiva de política en la transacción actual.

        El campo llegó en v016; conservar NULL permite que adaptadores V3
        sigan siendo compatibles con bases previas a esa migración.
        """
        columnas = self.db.consultar("PRAGMA table_info(pagos)")
        if not any(str(fila["name"]) == "politica_pago_id" for fila in columnas):
            return None

        fila = self.db.consultar_uno(
            """
            SELECT pp.id
            FROM politicas_pago pp
            WHERE pp.prestamo_id = ?
              AND pp.vigente_desde <= ?
              AND (pp.vigente_hasta IS NULL OR pp.vigente_hasta > ?)
            ORDER BY pp.version DESC, pp.id DESC
            LIMIT 1
            """,
            (prestamo_id, fecha_valor.isoformat(), fecha_valor.isoformat()),
        )
        if fila is None:
            raise ErrorInvariante(
                f"El préstamo {prestamo_id} no tiene política de pagos vigente "
                f"para {fecha_valor.isoformat()}"
            )
        return int(fila["id"])

    def correlacion_ledger_pago(self, pago_id: int) -> str:
        fila = self.db.consultar_uno(
            "SELECT correlacion_id FROM ledger WHERE entidad='PAGO' AND entidad_id=? ORDER BY id LIMIT 1",
            (pago_id,),
        )
        if fila is None:
            raise ErrorInvariante(f"No existe correlación de ledger para pago {pago_id}")
        return str(fila["correlacion_id"])

    def persistir_distribucion_inversores(self, *, prestamo_id: int, pago_id: int, monto: Decimal, fecha: date, correlacion_id: str, usuario: str) -> tuple:
        from infraestructura.repositorios.participaciones_pago_v3 import RepositorioParticipacionesPagoSQLiteV3
        # Reutiliza el mismo objeto DB y la transacción ya abierta por F2/F3.
        repo = RepositorioParticipacionesPagoSQLiteV3(self.db)
        return repo.persistir_distribucion_sin_transaccion(
            prestamo_id=prestamo_id, pago_id=pago_id, monto=monto,
            fecha=fecha, correlacion_id=correlacion_id, usuario=usuario,
        )

    def ultimo_hasta_mora_contractual_por_cuotas(self, prestamo_id: int, cuota_ids: tuple[int, ...]) -> dict[int, date]:
        if not cuota_ids:
            return {}
        placeholders = ",".join("?" for _ in cuota_ids)
        filas = self.db.consultar(
            f"""SELECT cuota_id, MAX(fecha_hasta) AS fecha_hasta
                FROM devengamientos
                WHERE prestamo_id = ?
                  AND concepto = 'MORA'
                  AND origen = 'MORA_CONTRACTUAL'
                  AND cuota_id IN ({placeholders})
                GROUP BY cuota_id""",
            (prestamo_id, *cuota_ids),
        )
        return {
            int(f["cuota_id"]): date.fromisoformat(f["fecha_hasta"])
            for f in filas
        }

    def ultimo_hasta_interes_capital_por_cuotas(self, prestamo_id: int, cuota_ids: tuple[int, ...]) -> dict[int, date]:
        if not cuota_ids:
            return {}
        placeholders = ",".join("?" for _ in cuota_ids)
        filas = self.db.consultar(
            f"""SELECT cuota_id, MAX(fecha_hasta) AS fecha_hasta
                FROM devengamientos
                WHERE prestamo_id = ?
                  AND concepto = 'INTERES'
                  AND origen = 'INTERES_CAPITAL_PENDIENTE'
                  AND cuota_id IN ({placeholders})
                GROUP BY cuota_id""",
            (prestamo_id, *cuota_ids),
        )
        return {int(f["cuota_id"]): date.fromisoformat(f["fecha_hasta"]) for f in filas}

    def persistir_pago_y_devengamientos(self, command, resultado, *, fingerprint: str, revision_esperada: int) -> int:
        plan = resultado.plan
        plan.validar()
        ids_afectadas = {o.cuota_id for o in plan.obligaciones_afectadas}
        for cuota_id, eventos in resultado.devengamientos_nuevos.items():
            if cuota_id not in ids_afectadas:
                continue
            for devengamiento in eventos:
                self._registrar_devengamiento_sin_transaccion(
                    prestamo_id=command.prestamo_id, cuota_id=cuota_id, devengamiento=devengamiento
                )
        return self.persistir_pago(command, plan, fingerprint=fingerprint, revision_esperada=revision_esperada)

    def persistir_pago_y_devengamientos_y_adelanto(
        self, command, resultado, plan_adelanto: PlanAdelantoV3, *,
        fingerprint: str, revision_esperada: int,
    ) -> int:
        if plan_adelanto.monto_adelanto != resultado.plan.excedente.monto:
            raise ErrorInvariante("El adelanto no coincide con el excedente del PlanPago")
        ids_afectadas = {o.cuota_id for o in resultado.plan.obligaciones_afectadas}
        for cuota_id, eventos in resultado.devengamientos_nuevos.items():
            if cuota_id not in ids_afectadas:
                continue
            for devengamiento in eventos:
                self._registrar_devengamiento_sin_transaccion(
                    prestamo_id=command.prestamo_id, cuota_id=cuota_id, devengamiento=devengamiento
                )
        return self.persistir_pago(
            command, resultado.plan, fingerprint=fingerprint, revision_esperada=revision_esperada,
            permitir_excedente=True, monto_adelanto=plan_adelanto.monto_adelanto,
            tipo_pago_override=f"ADELANTO_{plan_adelanto.tipo.value}",
            intereses_ahorrados=plan_adelanto.intereses_ahorrados,
        )

    def _registrar_devengamiento_sin_transaccion(self, *, prestamo_id: int, cuota_id: int, devengamiento) -> int:
        if devengamiento.monto <= Decimal("0.00"):
            raise ErrorValidacion("No se persisten devengamientos de monto cero")
        if devengamiento.fecha_hasta <= devengamiento.fecha_desde:
            raise ErrorValidacion("El evento de devengamiento debe tener un período positivo")
        fila = self.db.consultar_uno(
            """SELECT c.id FROM cuotas c JOIN versiones_tasa v ON v.id = c.version_id
               WHERE c.id = ? AND v.prestamo_id = ?""",
            (cuota_id, prestamo_id),
        )
        if fila is None:
            raise ErrorValidacion(f"La cuota {cuota_id} no pertenece al préstamo {prestamo_id}")
        from infraestructura.repositorios.devengamientos_v3 import _huella
        motor_version = "V3-G3"
        huella = _huella(prestamo_id=prestamo_id, cuota_id=cuota_id, devengamiento=devengamiento, motor_version=motor_version)
        ahora = datetime.now().isoformat(timespec="seconds")
        self.db.ejecutar(
            """INSERT INTO devengamientos
               (prestamo_id, cuota_id, concepto, monto, fecha_desde, fecha_hasta, origen, referencia,
                base, tasa_anual, modalidad_tasa, convencion_dias, dias, fraccion_anual, huella, motor_version, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prestamo_id, cuota_id, devengamiento.concepto.value, str(money(devengamiento.monto)),
                devengamiento.fecha_desde.isoformat(), devengamiento.fecha_hasta.isoformat(),
                devengamiento.origen, devengamiento.referencia, str(money(devengamiento.base)),
                str(devengamiento.tasa_anual), None if devengamiento.modalidad_tasa is None else devengamiento.modalidad_tasa.value,
                None if devengamiento.convencion_dias is None else devengamiento.convencion_dias.value,
                int(devengamiento.dias), str(devengamiento.fraccion_anual), huella, motor_version, ahora,
            ),
        )
        return int(self.db.ultimo_id_insertado())

    def cuotas_futuras_para_adelanto(self, prestamo_id: int, numero_desde: int) -> tuple[CuotaFuturaAdelantoV3, ...]:
        version = self.db.consultar_uno(
            """SELECT id FROM versiones_tasa WHERE prestamo_id = ? AND fecha_hasta IS NULL
               ORDER BY version DESC, id DESC LIMIT 1""",
            (prestamo_id,),
        )
        if version is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no tiene una tasa activa")
        filas = self.db.consultar(
            """SELECT id, numero, fecha_vencimiento, capital_inicial, interes, capital, cuota, saldo
               FROM cuotas
               WHERE version_id = ? AND numero >= ? AND estado = 'PENDIENTE'
               ORDER BY numero, id""",
            (version["id"], numero_desde),
        )
        return tuple(
            CuotaFuturaAdelantoV3(
                cuota_id=int(f["id"]),
                numero=int(f["numero"]),
                vencimiento=date.fromisoformat(f["fecha_vencimiento"]),
                capital_inicial=_decimal(f["capital_inicial"]),
                interes=_decimal(f["interes"]),
                capital=_decimal(f["capital"]),
                cuota=_decimal(f["cuota"]),
                saldo=_decimal(f["saldo"]),
            )
            for f in filas
        )

    def persistir_adelanto_sin_transaccion(
        self,
        *,
        prestamo_id: int,
        pago_id: int,
        plan: PlanAdelantoV3,
        fecha: date,
        usuario: str,
    ) -> tuple[int, ...]:
        """Reemplaza solo cuotas futuras vigentes, preservando sus filas históricas."""
        ahora = datetime.now().isoformat(timespec="seconds")
        ids_reemplazadas = tuple(c.cuota_id for c in plan.cuotas_reemplazadas)
        if not ids_reemplazadas:
            raise ErrorInvariante("El recálculo debe identificar al menos una cuota reemplazada")

        for cuota in plan.cuotas_reemplazadas:
            fila = self.db.consultar_uno(
                "SELECT estado FROM cuotas WHERE id = ? AND estado = 'PENDIENTE'",
                (cuota.cuota_id,),
            )
            if fila is None:
                raise ErrorInvariante(f"La cuota {cuota.cuota_id} ya no es una obligación futura vigente")
            self.db.ejecutar(
                """UPDATE cuotas
                   SET estado='REESTRUCTURADA', monto_pendiente='0.00',
                       interes_pendiente='0.00', capital_pendiente='0.00',
                       mora_pendiente='0.00'
                   WHERE id = ?""",
                (cuota.cuota_id,),
            )

        version = self.db.consultar_uno(
            "SELECT id FROM versiones_tasa WHERE prestamo_id = ? AND fecha_hasta IS NULL ORDER BY version DESC, id DESC LIMIT 1",
            (prestamo_id,),
        )
        if version is None:
            raise ErrorValidacion(f"El préstamo {prestamo_id} no tiene una tasa activa")
        nuevos_ids = []
        for cuota in plan.cuotas_nuevas:
            self.db.ejecutar(
                """INSERT INTO cuotas
                   (version_id, numero, fecha_vencimiento, capital_inicial, interes, capital, cuota, saldo,
                    monto_pendiente, interes_pendiente, capital_pendiente, mora_pendiente,
                    fue_mora, tuvo_pago_parcial, fue_recalculada, estado, creado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '0.00', 0, 0, 1, 'PENDIENTE', ?)""",
                (
                    version["id"], cuota.numero, cuota.vencimiento.isoformat(),
                    str(cuota.capital_inicial), str(cuota.interes), str(cuota.capital),
                    str(cuota.cuota), str(cuota.saldo), str(cuota.cuota),
                    str(cuota.interes), str(cuota.capital), ahora,
                ),
            )
            nuevos_ids.append(int(self.db.ultimo_id_insertado()))

        detalle = json.dumps(
            {
                "cuotas_reemplazadas": [
                    {"id": c.cuota_id, "numero": c.numero, "vencimiento": c.vencimiento.isoformat(),
                     "capital_inicial": str(c.capital_inicial), "interes": str(c.interes),
                     "capital": str(c.capital), "cuota": str(c.cuota), "saldo": str(c.saldo)}
                    for c in plan.cuotas_reemplazadas
                ],
                "cuotas_nuevas_ids": nuevos_ids,
                "cuotas_nuevas": [
                    {"numero": c.numero, "vencimiento": c.vencimiento.isoformat(),
                     "capital_inicial": str(c.capital_inicial), "interes": str(c.interes),
                     "capital": str(c.capital), "cuota": str(c.cuota), "saldo": str(c.saldo)}
                    for c in plan.cuotas_nuevas
                ],
            },
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        self.db.ejecutar(
            """INSERT INTO historial_recalculos
               (prestamo_id, pago_id, tipo, fecha, capital_antes, capital_despues,
                cuotas_antes, cuotas_despues, intereses_antes, intereses_despues,
                detalle_json, creado_en, cuota_objetivo_numero)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prestamo_id, pago_id, plan.tipo.value, fecha.isoformat(),
                str(plan.capital_antes), str(plan.capital_despues),
                plan.cuotas_antes, plan.cuotas_despues,
                str(plan.intereses_antes), str(plan.intereses_despues),
                detalle, ahora, plan.cuota_objetivo_numero,
            ),
        )
        recalculo_id = int(self.db.ultimo_id_insertado())
        self.db.ejecutar(
            "UPDATE pagos SET intereses_ahorrados = ?, cuotas_restantes_despues = ?, opcion_adelanto = ? WHERE id = ?",
            (str(plan.intereses_ahorrados), self._cantidad_obligaciones_abiertas(prestamo_id), plan.tipo.value, pago_id),
        )
        self.db.ejecutar(
            """INSERT INTO auditoria
               (fecha, usuario, operacion, entidad, entidad_id, datos_anteriores, datos_nuevos, motivo, correlacion_id)
               SELECT ?, ?, ?, 'PAGO', ?, NULL, ?, ?, correlacion_id FROM auditoria
               WHERE entidad='PAGO' AND entidad_id=? AND operacion='PAGO_REGISTRADO_V3' ORDER BY id LIMIT 1""",
            (
                ahora, usuario, f"RECALCULO_{plan.tipo.value}", pago_id,
                json.dumps({"recalculo_id": recalculo_id, "capital_adelanto": str(plan.monto_adelanto), "intereses_ahorrados": str(plan.intereses_ahorrados)}, sort_keys=True, separators=(",", ":")),
                f"Registro de {plan.tipo.value} posterior a un prepago", pago_id,
            ),
        )
        return tuple(nuevos_ids)

    def _cantidad_obligaciones_abiertas(self, prestamo_id: int) -> int:
        # Métrica de cronograma completo, no el horizonte de cálculo del waterfall.
        fila = self.db.consultar_uno(
            """SELECT COUNT(*) AS n
               FROM cuotas c JOIN versiones_tasa v ON v.id = c.version_id
               WHERE v.prestamo_id = ?
                 AND c.estado IN ('PENDIENTE','PARCIAL','VENCIDA')""",
            (prestamo_id,),
        )
        return int(fila["n"]) if fila else 0


def _decimal(valor) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0.00")
    return Decimal(str(valor))


def _serializable(valor):
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Enum):
        return valor.value
    if is_dataclass(valor):
        return {k: _serializable(v) for k, v in asdict(valor).items()}
    if isinstance(valor, dict):
        return {str(k): _serializable(v) for k, v in sorted(valor.items(), key=lambda kv: str(kv[0]))}
    if isinstance(valor, (tuple, list)):
        return [_serializable(v) for v in valor]
    return valor


def _serializar_plan(plan) -> str:
    return json.dumps(
        _serializable(plan),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
