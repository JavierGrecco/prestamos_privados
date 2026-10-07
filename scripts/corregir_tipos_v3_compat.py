#!/usr/bin/env python3
"""Agrega únicamente los símbolos de compatibilidad requeridos por Motor V3-G4/G5.

No reemplaza dominio/tipos.py completo: modifica solo cuando faltan ZERO o
TipoRecalculo, preservando el resto del archivo del proyecto.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re


ZERO_BLOCK = '\nZERO = Decimal("0")\n'
TIPO_RECALCULO_BLOCK = '''\n\nclass TipoRecalculo(str, Enum):\n    RAI = "RAI"\n    RNI = "RNI"\n'''


def _tiene_zero(texto: str) -> bool:
    return re.search(r"^ZERO\s*=\s*Decimal\([\"']0(?:\\.0+)?[\"']\)\s*$", texto, re.MULTILINE) is not None


def _tiene_tipo_recalculo(texto: str) -> bool:
    return re.search(r"^class\s+TipoRecalculo\s*\(", texto, re.MULTILINE) is not None


def aplicar(path: Path) -> tuple[bool, list[str]]:
    texto = path.read_text(encoding="utf-8")
    cambios: list[str] = []

    if not _tiene_zero(texto):
        # Inserción mínima y estable: después de PRECISION_TASA si existe;
        # en su defecto, después de CENT.
        patron = re.compile(r"^(PRECISION_TASA\s*=.*)$", re.MULTILINE)
        m = patron.search(texto)
        if m:
            pos = m.end()
            texto = texto[:pos] + ZERO_BLOCK + texto[pos:]
        else:
            patron_cent = re.compile(r"^(CENT\s*=.*)$", re.MULTILINE)
            m = patron_cent.search(texto)
            if not m:
                raise RuntimeError("No pude localizar CENT ni PRECISION_TASA en dominio/tipos.py")
            pos = m.end()
            texto = texto[:pos] + ZERO_BLOCK + texto[pos:]
        cambios.append("ZERO")

    if not _tiene_tipo_recalculo(texto):
        # Se coloca después de ConceptoImputacion, antes del orden de imputación
        # si está presente. Esto mantiene la semántica de enums del dominio.
        patron_orden = re.compile(r"^ORDEN_DEFAULT_IMPUTACION\s*=", re.MULTILINE)
        m_orden = patron_orden.search(texto)
        if m_orden:
            texto = texto[:m_orden.start()] + TIPO_RECALCULO_BLOCK + "\n" + texto[m_orden.start():]
        else:
            texto = texto.rstrip() + TIPO_RECALCULO_BLOCK + "\n"
        cambios.append("TipoRecalculo")

    if cambios:
        path.write_text(texto, encoding="utf-8")
    return bool(cambios), cambios


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Raíz del repositorio")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    path = root / "dominio" / "tipos.py"
    if not path.is_file():
        raise SystemExit(f"ERROR: no existe {path}")

    changed, symbols = aplicar(path)
    if changed:
        print("CORREGIDO: agregados " + ", ".join(symbols))
    else:
        print("OK: dominio/tipos.py ya contiene ZERO y TipoRecalculo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
