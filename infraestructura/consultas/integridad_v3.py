"""G8: auditoría global de integridad del Motor de Pagos V3.

La consulta es estrictamente de solo lectura. No modifica datos, no recalcula
planes y no ejecuta operaciones de negocio. Está pensada como gate de
pre-cutover para detectar inconsistencias antes de activar V3 como escritura
efectiva.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json

from dominio.excepciones import ErrorValidacion
from dominio.tipos import money

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class IncidenciaIntegridadV3:
    categoria: str
    detalle: str
    entidad: str | None = None
    entidad_id: int | None = None


@dataclass(frozen=True)
class InformeIntegridadV3:
    pagos_v3: int
    imputaciones_v3: int
    devengamientos: int
    incidencias: tuple[IncidenciaIntegridadV3, ...]

    @property
    def ok(self) -> bool:
        return not self.incidencias

    @property
    def cantidad_incidencias(self) -> int:
        return len(self.incidencias)


def auditar_integridad_v3(db) -> InformeIntegridadV3:
    """Recorre las entidades V3 y devuelve un informe determinista.

    La función nunca escribe en la base. Si faltan tablas/migraciones V3,
    reporta la condición como incidencia en lugar de intentar repararla.
    """
    incidencias: list[IncidenciaIntegridadV3] = []

    tablas = {
        str(f["name"])
        for f in db.consultar("SELECT name FROM sqlite_master WHERE type='table'")
    }
    requeridas = {"migraciones", "prestamos", "pagos", "imputaciones", "cuotas", "ledger", "auditoria", "devengamientos"}
    faltantes = sorted(requeridas - tablas)
    if faltantes:
        for tabla in faltantes:
            incidencias.append(IncidenciaIntegridadV3(
                "ESQUEMA", f"Falta la tabla requerida por V3: {tabla}", "TABLA", None
            ))
        return InformeIntegridadV3(0, 0, 0, tuple(incidencias))

    fila_migracion = db.consultar_uno("SELECT MAX(version) AS v FROM migraciones")
    version_actual = 0 if fila_migracion is None or fila_migracion["v"] is None else int(fila_migracion["v"])
    if version_actual < 10:
        incidencias.append(IncidenciaIntegridadV3(
            "MIGRACION", f"La base está en migración v{version_actual:03d}; V3-G1 requiere v010", "MIGRACIONES", None
        ))

    pagos = db.consultar(
        "SELECT id, prestamo_id, monto_moneda_contractual, plan_hash, plan_json, motor_version FROM pagos WHERE motor_version LIKE 'V3-%' ORDER BY id"
    )
    pagos_v3 = len(pagos)
    imputaciones_v3 = 0

    # Invariantes globales que no dependen de que exista un pago V3.
    revision_negativa = db.consultar("SELECT id FROM prestamos WHERE revision_prestamo < 0")
    for f in revision_negativa:
        incidencias.append(IncidenciaIntegridadV3(
            "REVISION", "revision_prestamo no puede ser negativa", "PRESTAMO", int(f["id"])
        ))

    cuotas_negativas = db.consultar(
        """
        SELECT id, interes_pendiente, capital_pendiente, mora_pendiente, monto_pendiente
        FROM cuotas
        WHERE CAST(interes_pendiente AS REAL) < 0
           OR CAST(capital_pendiente AS REAL) < 0
           OR CAST(mora_pendiente AS REAL) < 0
           OR CAST(monto_pendiente AS REAL) < 0
        ORDER BY id
        """
    )
    for f in cuotas_negativas:
        incidencias.append(IncidenciaIntegridadV3(
            "CUOTA", "Una cuota conserva un saldo pendiente negativo", "CUOTA", int(f["id"])
        ))

    cuotas_pagadas = db.consultar(
        """
        SELECT id, interes_pendiente, capital_pendiente, mora_pendiente, monto_pendiente
        FROM cuotas WHERE estado='PAGADA'
        """
    )
    for f in cuotas_pagadas:
        total = money(
            _decimal(f["interes_pendiente"]) +
            _decimal(f["capital_pendiente"]) +
            _decimal(f["mora_pendiente"])
        )
        pendiente = money(_decimal(f["monto_pendiente"]))
        if total != ZERO or pendiente != ZERO:
            incidencias.append(IncidenciaIntegridadV3(
                "CUOTA", "Una cuota PAGADA conserva saldo pendiente", "CUOTA", int(f["id"])
            ))

    duplicadas = db.consultar(
        """
        SELECT idempotency_key, COUNT(*) AS n
        FROM pagos
        WHERE idempotency_key IS NOT NULL
        GROUP BY idempotency_key HAVING COUNT(*) > 1
        """
    )
    for f in duplicadas:
        incidencias.append(IncidenciaIntegridadV3(
            "IDEMPOTENCIA", f"idempotency_key duplicada: {f['idempotency_key']}", "PAGO", None
        ))

    # Indexamos metadata contable en memoria para evitar depender de
    # json_extract() durante la auditoría. Así, un metadata corrupto se
    # convierte en una incidencia y no derriba el proceso completo.
    ledger_por_pago: dict[int, list] = {}
    ledger_filas = db.consultar(
        "SELECT id, entidad, entidad_id, tipo_movimiento, debe, haber, metadata, correlacion_id FROM ledger ORDER BY id"
    )
    for fila in ledger_filas:
        metadata = fila["metadata"]
        if metadata in (None, ""):
            continue
        try:
            objeto = json.loads(str(metadata))
        except json.JSONDecodeError:
            incidencias.append(IncidenciaIntegridadV3(
                "LEDGER_METADATA", "Metadata contable con JSON inválido", "LEDGER", int(fila["id"])
            ))
            continue
        if not isinstance(objeto, dict):
            incidencias.append(IncidenciaIntegridadV3(
                "LEDGER_METADATA", "La metadata contable debe ser un objeto JSON", "LEDGER", int(fila["id"])
            ))
            continue
        pago_ref = objeto.get("pago_id")
        if pago_ref is not None:
            try:
                pago_ref_int = int(pago_ref)
            except (TypeError, ValueError):
                incidencias.append(IncidenciaIntegridadV3(
                    "LEDGER_METADATA", "pago_id de metadata no es entero", "LEDGER", int(fila["id"])
                ))
                continue
            ledger_por_pago.setdefault(pago_ref_int, []).append(fila)

    devengamientos = db.consultar("SELECT id, prestamo_id, cuota_id, monto, fecha_desde, fecha_hasta, huella FROM devengamientos ORDER BY id")
    huellas: set[str] = set()
    devengamientos_count = len(devengamientos)
    for f in devengamientos:
        huella = str(f["huella"])
        if huella in huellas:
            incidencias.append(IncidenciaIntegridadV3(
                "DEVENGAMIENTO", f"Huella duplicada: {huella}", "DEVENGAMIENTO", int(f["id"])
            ))
        huellas.add(huella)
        if _decimal(f["monto"]) <= ZERO:
            incidencias.append(IncidenciaIntegridadV3(
                "DEVENGAMIENTO", "El monto del devengamiento debe ser positivo", "DEVENGAMIENTO", int(f["id"])
            ))
        if str(f["fecha_hasta"]) <= str(f["fecha_desde"]):
            incidencias.append(IncidenciaIntegridadV3(
                "DEVENGAMIENTO", "El período del devengamiento no es positivo", "DEVENGAMIENTO", int(f["id"])
            ))

    for pago in pagos:
        pago_id = int(pago["id"])
        prestamo_id = int(pago["prestamo_id"])
        monto = money(_decimal(pago["monto_moneda_contractual"]))

        # Plan hash / JSON: V3 no debe perder su huella reproducible.
        plan_json = pago["plan_json"]
        plan_hash = None if pago["plan_hash"] is None else str(pago["plan_hash"])
        if not plan_json or not plan_hash:
            incidencias.append(IncidenciaIntegridadV3(
                "PLAN", "Pago V3 sin plan_json y/o plan_hash", "PAGO", pago_id
            ))
        else:
            try:
                json.loads(str(plan_json))
            except json.JSONDecodeError:
                incidencias.append(IncidenciaIntegridadV3(
                    "PLAN", "plan_json no contiene JSON válido", "PAGO", pago_id
                ))
            hash_obtenido = hashlib.sha256(str(plan_json).encode("utf-8")).hexdigest()
            if hash_obtenido != plan_hash:
                incidencias.append(IncidenciaIntegridadV3(
                    "PLAN", "plan_hash no concilia con plan_json", "PAGO", pago_id
                ))

        imputaciones = db.consultar(
            "SELECT id, cuota_id, monto, referencias_devengamiento FROM imputaciones WHERE pago_id=? ORDER BY id",
            (pago_id,),
        )
        imputaciones_v3 += len(imputaciones)
        suma_imp = money(sum((_decimal(f["monto"]) for f in imputaciones), ZERO))
        if suma_imp != monto:
            incidencias.append(IncidenciaIntegridadV3(
                "IMPUTACION", f"Suma de imputaciones {suma_imp} != pago {monto}", "PAGO", pago_id
            ))

        for imp in imputaciones:
            refs_raw = imp["referencias_devengamiento"]
            if refs_raw in (None, "", "[]"):
                continue
            try:
                refs = json.loads(str(refs_raw))
            except json.JSONDecodeError:
                incidencias.append(IncidenciaIntegridadV3(
                    "DEVENGAMIENTO_REF", "referencias_devengamiento no contiene JSON válido", "IMPUTACION", int(imp["id"])
                ))
                continue
            if not isinstance(refs, list):
                incidencias.append(IncidenciaIntegridadV3(
                    "DEVENGAMIENTO_REF", "referencias_devengamiento debe ser una lista", "IMPUTACION", int(imp["id"])
                ))
                continue
            for referencia in refs:
                fila = db.consultar_uno(
                    "SELECT id FROM devengamientos WHERE prestamo_id=? AND referencia=?",
                    (prestamo_id, str(referencia)),
                )
                if fila is None:
                    incidencias.append(IncidenciaIntegridadV3(
                        "DEVENGAMIENTO_REF", f"No existe el devengamiento referenciado: {referencia}", "IMPUTACION", int(imp["id"])
                    ))

        ledger = [
            fila for fila in ledger_por_pago.get(pago_id, [])
            if not (fila["entidad"] == "PAGO" and int(fila["entidad_id"]) == pago_id)
        ]
        ledger_directo = [
            fila for fila in ledger_filas
            if fila["entidad"] == "PAGO" and int(fila["entidad_id"]) == pago_id
        ]
        ledger = sorted(ledger_directo + ledger, key=lambda f: int(f["id"]))
        if not ledger:
            incidencias.append(IncidenciaIntegridadV3(
                "LEDGER", "Pago V3 sin movimientos contables", "PAGO", pago_id
            ))
        else:
            debe_total = money(sum((_decimal(f["debe"]) for f in ledger), ZERO))
            haber_total = money(sum((_decimal(f["haber"]) for f in ledger), ZERO))
            if debe_total != haber_total:
                incidencias.append(IncidenciaIntegridadV3(
                    "LEDGER", f"Ledger no balanceado: debe {debe_total}, haber {haber_total}", "PAGO", pago_id
                ))

            debe_pago = money(sum((_decimal(f["debe"]) for f in ledger if f["entidad"] == "PAGO" and f["tipo_movimiento"] == "PAGO"), ZERO))
            haber_recibido = money(sum((_decimal(f["haber"]) for f in ledger if f["entidad"] == "PRESTAMO" and f["tipo_movimiento"] == "PAGO_RECIBIDO"), ZERO))
            if debe_pago != monto or haber_recibido != monto:
                incidencias.append(IncidenciaIntegridadV3(
                    "LEDGER", "Los movimientos principales del pago no concilian con el monto", "PAGO", pago_id
                ))

            correlaciones = {str(f["correlacion_id"]) for f in ledger}
            if len(correlaciones) != 1:
                incidencias.append(IncidenciaIntegridadV3(
                    "CORRELACION", "El pago tiene más de una correlación contable", "PAGO", pago_id
                ))
            else:
                corr = next(iter(correlaciones))
                auditorias = db.consultar(
                    "SELECT id, correlacion_id, operacion FROM auditoria WHERE entidad='PAGO' AND entidad_id=? ORDER BY id",
                    (pago_id,),
                )
                if not auditorias:
                    incidencias.append(IncidenciaIntegridadV3(
                        "AUDITORIA", "Pago V3 sin auditoría asociada", "PAGO", pago_id
                    ))
                elif any(str(a["correlacion_id"]) != corr for a in auditorias):
                    incidencias.append(IncidenciaIntegridadV3(
                        "CORRELACION", "La auditoría no comparte la correlación del ledger", "PAGO", pago_id
                    ))

    return InformeIntegridadV3(
        pagos_v3=pagos_v3,
        imputaciones_v3=imputaciones_v3,
        devengamientos=devengamientos_count,
        incidencias=tuple(incidencias),
    )


def exigir_integridad_v3(db) -> InformeIntegridadV3:
    """Ejecuta la auditoría y falla si existe cualquier incidencia."""
    informe = auditar_integridad_v3(db)
    if not informe.ok:
        primera = informe.incidencias[0]
        raise ErrorValidacion(
            f"La auditoría de integridad V3 detectó {informe.cantidad_incidencias} incidencia(s): "
            f"{primera.categoria}: {primera.detalle}"
        )
    return informe


def _decimal(valor) -> Decimal:
    if valor in (None, ""):
        return ZERO
    return Decimal(str(valor))
