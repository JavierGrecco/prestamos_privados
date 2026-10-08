"""Validador fail-closed del paquete de evidencia del canary V3.

No ejecuta pagos, no modifica la base y no cambia el modo persistido.
Combina la evidencia de readiness con un backup verificable y controla
la antigüedad de la evaluación.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from infraestructura.backup import verificar_backup
from infraestructura.excepciones import ErrorBackup


FORMATO_EVIDENCIA = 1
MODOS_PREVIOS = {"LEGACY", "SOMBRA"}


@dataclass(frozen=True)
class ResultadoValidacionEvidenciaCanaryV3:
    """Resultado completo de la validación del paquete."""

    apto: bool
    formato_ok: bool
    readiness_ok: bool
    backup_ok: bool
    antiguedad_ok: bool
    edad_segundos: float | None
    sha256_backup: str | None
    motivos_rechazo: tuple[str, ...]


class ValidadorEvidenciaCanaryV3:
    """Valida que un paquete pueda sostener una decisión de canary."""

    def __init__(
        self,
        *,
        schema_minimo: int = 13,
        ejecuciones_minimas: int = 100,
        tasa_coincidencia_minima: float = 1.0,
        divergencias_maximas: int = 0,
        errores_maximos: int = 0,
        max_edad_horas: float = 24.0,
    ) -> None:
        if schema_minimo <= 0:
            raise ValueError("schema_minimo debe ser positivo")
        if ejecuciones_minimas < 0:
            raise ValueError("ejecuciones_minimas no puede ser negativa")
        if not 0 <= tasa_coincidencia_minima <= 1:
            raise ValueError(
                "tasa_coincidencia_minima debe estar entre 0 y 1"
            )
        if divergencias_maximas < 0 or errores_maximos < 0:
            raise ValueError("los máximos permitidos no pueden ser negativos")
        if max_edad_horas < 0:
            raise ValueError("max_edad_horas no puede ser negativa")

        self._schema_minimo = schema_minimo
        self._ejecuciones_minimas = ejecuciones_minimas
        self._tasa_coincidencia_minima = tasa_coincidencia_minima
        self._divergencias_maximas = divergencias_maximas
        self._errores_maximos = errores_maximos
        self._max_edad_segundos = max_edad_horas * 3600

    def validar(
        self,
        readiness_path: str | Path,
        backup_path: str | Path,
        *,
        ahora: datetime | None = None,
    ) -> ResultadoValidacionEvidenciaCanaryV3:
        motivos: list[str] = []
        formato_ok = False
        readiness_ok = False
        backup_ok = False
        antiguedad_ok = False
        edad_segundos: float | None = None
        sha256_backup: str | None = None

        try:
            evidencia = self._leer_json(readiness_path)
            formato_ok = evidencia.get("evidence_format_version") == FORMATO_EVIDENCIA
            if not formato_ok:
                motivos.append(
                    "El formato de evidencia no es compatible."
                )

            readiness_motivos = self._validar_readiness(evidencia)
            motivos.extend(readiness_motivos)

            fecha_texto = evidencia.get("evaluated_at")
            fecha_evaluacion = _parsear_fecha(fecha_texto)
            ahora_real = ahora or datetime.now(timezone.utc)
            edad_segundos = (ahora_real - fecha_evaluacion).total_seconds()
            if edad_segundos < 0:
                motivos.append("La evidencia tiene fecha futura.")
            elif edad_segundos > self._max_edad_segundos:
                motivos.append(
                    "La evidencia supera la antigüedad máxima permitida."
                )
            else:
                antiguedad_ok = True

            try:
                backup = verificar_backup(backup_path)
                backup_ok = True
                sha256_backup = backup.sha256
            except (ErrorBackup, OSError) as exc:
                motivos.append(f"El backup no es verificable: {type(exc).__name__}: {exc}")

            readiness_ok = not readiness_motivos and formato_ok

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            motivos.append(
                f"No se pudo validar el archivo de readiness: "
                f"{type(exc).__name__}: {exc}"
            )

        return ResultadoValidacionEvidenciaCanaryV3(
            apto=(
                formato_ok
                and readiness_ok
                and backup_ok
                and antiguedad_ok
                and not motivos
            ),
            formato_ok=formato_ok,
            readiness_ok=readiness_ok,
            backup_ok=backup_ok,
            antiguedad_ok=antiguedad_ok,
            edad_segundos=edad_segundos,
            sha256_backup=sha256_backup,
            motivos_rechazo=tuple(dict.fromkeys(motivos)),
        )

    @staticmethod
    def _leer_json(path: str | Path) -> dict:
        ruta = Path(path)
        if not ruta.is_file():
            raise FileNotFoundError(
                f"No existe la evidencia de readiness: {ruta}"
            )
        return json.loads(ruta.read_text(encoding="utf-8"))

    def _validar_readiness(self, evidencia: dict) -> list[str]:
        motivos: list[str] = []

        if evidencia.get("listo_para_canary") is not True:
            motivos.append("El readiness indica que la base no está lista.")

        if evidencia.get("preflight_apto") is not True:
            motivos.append("El preflight no está aprobado.")

        if evidencia.get("integridad_ok") is not True:
            motivos.append("La integridad V3 no está aprobada.")

        if evidencia.get("modo_actual") not in MODOS_PREVIOS:
            motivos.append(
                "El modo actual no es LEGACY ni SOMBRA; no es un estado "
                "válido previo a la activación."
            )

        politica = evidencia.get("politica")
        sombra = evidencia.get("evidencia_sombra")
        if not isinstance(politica, dict) or not isinstance(sombra, dict):
            motivos.append(
                "La evidencia no contiene política y evidencia SOMBRA completas."
            )
            return motivos

        schema = politica.get("schema_minimo")
        runs_policy = politica.get("ejecuciones_minimas")
        match_policy = _float(politica.get("tasa_coincidencia_minima"))
        div_policy = politica.get("divergencias_maximas")
        err_policy = politica.get("errores_maximos")

        runs = sombra.get("ejecuciones")
        match = _float(sombra.get("coincidencia"))
        divergencias = sombra.get("divergencias")
        errores = sombra.get("errores")

        if not isinstance(schema, int) or schema < self._schema_minimo:
            motivos.append(
                "La política de schema usada en readiness es inferior a la requerida."
            )
        if not isinstance(runs_policy, int) or runs_policy < self._ejecuciones_minimas:
            motivos.append(
                "La política de ejecuciones usada en readiness es inferior a la requerida."
            )
        if match_policy is None or match_policy < self._tasa_coincidencia_minima:
            motivos.append(
                "La política de coincidencia usada en readiness es inferior a la requerida."
            )
        if not isinstance(div_policy, int) or div_policy > self._divergencias_maximas:
            motivos.append(
                "La política de divergencias usada en readiness es más permisiva que la requerida."
            )
        if not isinstance(err_policy, int) or err_policy > self._errores_maximos:
            motivos.append(
                "La política de errores usada en readiness es más permisiva que la requerida."
            )

        if not isinstance(runs, int) or runs < self._ejecuciones_minimas:
            motivos.append(
                f"Ejecuciones SOMBRA insuficientes: {runs!r}."
            )
        if match is None or match < self._tasa_coincidencia_minima:
            motivos.append(
                f"Tasa de coincidencia insuficiente: {match!r}."
            )
        if not isinstance(divergencias, int) or divergencias > self._divergencias_maximas:
            motivos.append(
                f"Divergencias fuera de política: {divergencias!r}."
            )
        if not isinstance(errores, int) or errores > self._errores_maximos:
            motivos.append(
                f"Errores SOMBRA fuera de política: {errores!r}."
            )

        if evidencia.get("motivos_rechazo"):
            motivos.append(
                "El readiness contiene motivos de rechazo."
            )

        return motivos


def _parsear_fecha(valor: object) -> datetime:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("evaluated_at no está presente o no es texto")
    fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if fecha.tzinfo is None:
        raise ValueError("evaluated_at debe incluir zona horaria")
    return fecha.astimezone(timezone.utc)


def _float(valor: object) -> float | None:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
