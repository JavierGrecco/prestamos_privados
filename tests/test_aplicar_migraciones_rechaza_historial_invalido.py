"""La API de migraciones rechaza estados de schema no confiables sin mutarlos."""
from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.excepciones import ErrorMigracion
from infraestructura.migraciones import aplicar_migraciones


def _nombres_objetos(db: BaseDatos) -> tuple[tuple[str, str], ...]:
    filas = db.consultar(
        """
        SELECT type, name
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    )
    return tuple((str(fila["type"]), str(fila["name"])) for fila in filas)


def test_no_crea_historial_ni_aplica_schema_si_ya_hay_tablas_sin_historial(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "sin-historial.db") as db:
        db.ejecutar(
            "CREATE TABLE datos_historicos (id INTEGER PRIMARY KEY, importe TEXT)"
        )
        db.ejecutar(
            "INSERT INTO datos_historicos (id, importe) VALUES (1, '1234.56')"
        )
        objetos_antes = _nombres_objetos(db)

        with pytest.raises(ErrorMigracion, match="no tiene historial"):
            aplicar_migraciones(db)

        assert _nombres_objetos(db) == objetos_antes
        fila = db.consultar_uno(
            "SELECT id, importe FROM datos_historicos WHERE id = 1"
        )
        assert tuple(fila) == (1, "1234.56")


def test_no_repara_silenciosamente_una_secuencia_de_migraciones_con_saltos(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "historial-con-salto.db") as db:
        assert aplicar_migraciones(db) == list(range(1, 26))
        db.ejecutar("DELETE FROM migraciones WHERE version = 12")
        objetos_antes = _nombres_objetos(db)
        aplicadas_antes = tuple(
            int(fila["version"])
            for fila in db.consultar("SELECT version FROM migraciones ORDER BY version")
        )

        with pytest.raises(ErrorMigracion, match="saltos o versiones ausentes"):
            aplicar_migraciones(db)

        assert _nombres_objetos(db) == objetos_antes
        aplicadas_despues = tuple(
            int(fila["version"])
            for fila in db.consultar("SELECT version FROM migraciones ORDER BY version")
        )
        assert aplicadas_despues == aplicadas_antes
        assert 12 not in aplicadas_despues


def test_rechaza_una_version_desconocida_sin_aplicar_cambios(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "version-futura.db") as db:
        aplicar_migraciones(db)
        db.ejecutar(
            """
            INSERT INTO migraciones (version, nombre, aplicada_en, hash)
            VALUES (99, 'futura_desconocida', '2026-10-12T00:00:00', NULL)
            """
        )
        objetos_antes = _nombres_objetos(db)

        with pytest.raises(ErrorMigracion, match="no reconoce"):
            aplicar_migraciones(db)

        assert _nombres_objetos(db) == objetos_antes
        assert db.consultar_uno(
            "SELECT COUNT(*) AS total FROM migraciones WHERE version = 99"
        )["total"] == 1


def test_rechaza_un_historial_malformado_sin_reemplazarlo(
    tmp_path: Path,
) -> None:
    with BaseDatos(tmp_path / "historial-malformado.db") as db:
        db.ejecutar(
            """
            CREATE TABLE migraciones (
                version INTEGER PRIMARY KEY,
                etiqueta_legacy TEXT NOT NULL
            )
            """
        )
        objetos_antes = _nombres_objetos(db)

        with pytest.raises(ErrorMigracion, match="No se pudo verificar"):
            aplicar_migraciones(db)

        assert _nombres_objetos(db) == objetos_antes
