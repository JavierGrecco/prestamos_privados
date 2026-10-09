"""Hash y validación de contraseñas para cuentas locales.

No almacena ni devuelve contraseñas en texto plano. El formato codificado
incluye algoritmo/parámetros, salt aleatorio y resultado para permitir una
evolución posterior de los parámetros.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITMO = "scrypt"
_N = 2**14
_R = 8
_P = 1
_LONGITUD_SALT = 16
_LONGITUD_HASH = 32
_LONGITUD_MINIMA = 12
_LONGITUD_MAXIMA = 1024


def validar_password(password: str) -> str:
    """Valida longitud sin recortar espacios intencionales de la contraseña."""
    if not isinstance(password, str):
        raise ValueError("La contraseña debe ser texto.")
    if len(password) < _LONGITUD_MINIMA:
        raise ValueError(
            f"La contraseña debe tener al menos {_LONGITUD_MINIMA} caracteres."
        )
    if len(password) > _LONGITUD_MAXIMA:
        raise ValueError(
            f"La contraseña no puede superar {_LONGITUD_MAXIMA} caracteres."
        )
    if not password.strip():
        raise ValueError("La contraseña no puede estar formada solo por espacios.")
    return password


def hash_password(password: str) -> str:
    """Devuelve un hash scrypt con salt aleatorio específico por contraseña."""
    password = validar_password(password)
    salt = secrets.token_bytes(_LONGITUD_SALT)
    derivado = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_LONGITUD_HASH,
    )
    return "$".join(
        [_ALGORITMO, str(_N), str(_R), str(_P), salt.hex(), derivado.hex()]
    )


def verificar_password(password: str, hash_codificado: str) -> bool:
    """Verifica un hash almacenado; los formatos desconocidos fallan cerrados."""
    if not isinstance(password, str) or not isinstance(hash_codificado, str):
        return False
    if len(password) > _LONGITUD_MAXIMA:
        return False

    try:
        algoritmo, n_texto, r_texto, p_texto, salt_hex, hash_hex = (
            hash_codificado.split("$")
        )
        if algoritmo != _ALGORITMO:
            return False
        n, r, p = int(n_texto), int(r_texto), int(p_texto)
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
        if (
            n < 2**14
            or n > 2**18
            or n & (n - 1) != 0
            or not 1 <= r <= 16
            or not 1 <= p <= 4
            or not 8 <= len(salt) <= 64
            or not 16 <= len(esperado) <= 64
        ):
            return False
        observado = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(esperado),
        )
        return hmac.compare_digest(observado, esperado)
    except (ValueError, TypeError, OverflowError):
        return False
