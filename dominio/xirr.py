"""
XIRR: Tasa Interna de Retorno con fechas irregulares.

Calcula la tasa anualizada que hace que el valor presente neto de todos
los flujos de caja sea cero, usando fechas reales.

Convención de signos:
  - Aportes (dinero que sale del inversor): NEGATIVO
  - Cobros (dinero que entra al inversor): POSITIVO

Criterio de seguridad:
  - Los flujos de una misma fecha se compensan antes de resolver.
  - Si los flujos netos alternan de signo más de una vez, la tasa puede
    ser ambigua y no se informa una solución única.
  - Se usa bisección acotada sobre tasas mayores que -100 %, evitando
    convergencias arbitrarias de Newton-Raphson.
"""
from datetime import date
from decimal import Decimal
import math

from .excepciones import ErrorCalculo, ErrorValidacion


def xirr(
    flujos: list[tuple[date, Decimal]],
    guess: float = 0.1,
    tolerancia: float = 1e-9,
    max_iter: int = 200,
) -> Decimal:
    """
    Calcula una tasa anualizada para flujos con fechas irregulares.

    Los montos negativos representan dinero aportado por el inversor y
    los positivos representan cobros o valor final. Los flujos de una
    misma fecha se netean antes del cálculo.

    Se rechazan series cuyos flujos netos cronológicos cambian de signo
    más de una vez: esas series pueden tener más de una XIRR válida. La raíz
    se busca con bisección en una región numéricamente acotada.

    `guess` se conserva por compatibilidad con llamadas existentes, pero
    la bisección no depende de una estimación inicial.

    Devuelve la tasa anualizada como Decimal (0.10 = 10 %).

    Lanza ErrorValidacion ante datos inválidos o ambigüedad y ErrorCalculo
    cuando no se encuentra una raíz dentro del rango numérico admitido.
    """
    if len(flujos) < 2:
        raise ErrorValidacion("XIRR requiere al menos 2 flujos")
    if (
        not isinstance(tolerancia, (int, float))
        or not math.isfinite(tolerancia)
        or tolerancia <= 0
    ):
        raise ErrorValidacion("La tolerancia de XIRR debe ser positiva y finita")
    if (
        not isinstance(max_iter, int)
        or isinstance(max_iter, bool)
        or max_iter < 1
    ):
        raise ErrorValidacion(
            "El máximo de iteraciones de XIRR debe ser un entero positivo"
        )

    # Compensar aportes y cobros que compartan fecha.
    netos_por_fecha: dict[date, Decimal] = {}
    for elemento in flujos:
        try:
            fecha, monto = elemento
        except (TypeError, ValueError) as exc:
            raise ErrorValidacion(
                "Cada flujo de XIRR debe contener fecha y monto"
            ) from exc
        if not isinstance(fecha, date):
            raise ErrorValidacion("Cada flujo de XIRR debe tener una fecha válida")
        if not isinstance(monto, Decimal) or not monto.is_finite():
            raise ErrorValidacion("Cada monto de XIRR debe ser un Decimal finito")
        netos_por_fecha[fecha] = (
            netos_por_fecha.get(fecha, Decimal("0")) + monto
        )

    flujos_ordenados = [
        (fecha, monto)
        for fecha, monto in sorted(netos_por_fecha.items())
        if monto != 0
    ]
    if len(flujos_ordenados) < 2:
        raise ErrorValidacion(
            "XIRR requiere al menos dos fechas con flujos netos no nulos"
        )

    signos = [1 if monto > 0 else -1 for _, monto in flujos_ordenados]
    if 1 not in signos or -1 not in signos:
        raise ErrorValidacion(
            "XIRR necesita al menos un flujo neto negativo y uno positivo"
        )

    cambios_signo = sum(
        actual != anterior for anterior, actual in zip(signos, signos[1:])
    )
    if cambios_signo > 1:
        raise ErrorValidacion(
            "XIRR no se informa: los flujos netos alternan de signo más de una vez "
            "y podrían admitir más de una tasa válida"
        )

    if sum((monto for _, monto in flujos_ordenados), Decimal("0")) == 0:
        return Decimal("0.00000000")

    fecha_inicial = flujos_ordenados[0][0]
    tiempos: list[float] = []
    montos: list[float] = []
    for fecha, monto in flujos_ordenados:
        monto_float = float(monto)
        if not math.isfinite(monto_float) or monto_float == 0:
            raise ErrorValidacion(
                "Un monto de XIRR está fuera del rango numérico admitido"
            )
        tiempos.append((fecha - fecha_inicial).days / 365.0)
        montos.append(monto_float)

    def signo_van(log_factor: float) -> float:
        """Signo del VAN con escala logarítmica para evitar desbordes."""
        logaritmos = [
            math.log(abs(monto)) - tiempo * log_factor
            for tiempo, monto in zip(tiempos, montos)
        ]
        maximo = max(logaritmos)
        return math.fsum(
            (1.0 if monto > 0 else -1.0) * math.exp(logaritmo - maximo)
            for monto, logaritmo in zip(montos, logaritmos)
        )

    # y = ln(1 + tasa) limita la búsqueda a tasas mayores que -100 %.
    izquierda, derecha = -40.0, 40.0
    f_izquierda = signo_van(izquierda)
    f_derecha = signo_van(derecha)

    if f_izquierda == 0:
        log_factor = izquierda
    elif f_derecha == 0:
        log_factor = derecha
    elif (f_izquierda > 0) == (f_derecha > 0):
        raise ErrorCalculo(
            "No se encontró una XIRR dentro del rango numérico admitido"
        )
    else:
        for _ in range(max_iter):
            medio = (izquierda + derecha) / 2.0
            f_medio = signo_van(medio)
            if f_medio == 0:
                izquierda = derecha = medio
                break
            if (f_medio > 0) == (f_izquierda > 0):
                izquierda = medio
                f_izquierda = f_medio
            else:
                derecha = medio
                f_derecha = f_medio
            if derecha - izquierda <= tolerancia:
                break
        else:
            raise ErrorCalculo(
                "XIRR no convergió dentro del máximo de iteraciones"
            )
        log_factor = (izquierda + derecha) / 2.0

    tasa = math.expm1(log_factor)
    if not math.isfinite(tasa):
        raise ErrorCalculo(
            "La XIRR calculada está fuera del rango numérico admitido"
        )
    tasa_decimal = Decimal(str(tasa)).quantize(Decimal("0.00000001"))
    if tasa_decimal <= Decimal("-1"):
        raise ErrorCalculo(
            "La XIRR está demasiado cerca de -100 % para informarla con precisión"
        )
    return tasa_decimal
