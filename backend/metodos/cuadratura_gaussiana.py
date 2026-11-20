"""
Método: Cuadratura gaussiana (Gauss-Legendre), simple y compuesta

Aproxima la integral de f(x) en [a, b] con n puntos ("grado" n):

  En [-1, 1]:   ∫ f(t) dt ≈ c1·f(t1) + c2·f(t2) + ... + cn·f(tn)

  Los nodos ti son las raíces del polinomio de Legendre de grado n y los
  pesos ci son las constantes asociadas. Con n puntos la fórmula es EXACTA
  para polinomios de grado <= 2n - 1.

  Cambio de variable a [a, b]:
      xi = (b - a)/2 · ti + (a + b)/2
      ∫ f(x) dx ≈ (b - a)/2 · [ c1·f(x1) + ... + cn·f(xn) ]

  Simple:     se aplica la fórmula una sola vez sobre [a, b].
  Compuesta:  se divide [a, b] en m subintervalos iguales y se suma la
              fórmula simple en cada uno (misma idea que Trapecio/Simpson
              compuestos: la compuesta es la simple aplicada por tramos).

TODO el método depende de la tabla CONSTANTES: para soportar otro grado solo
hay que agregar una entrada (nodos y pesos). Los valores se calcularon con
precisión de 40 dígitos (raíces de Legendre por Newton, pesos
ci = 2 / ((1 - ti²)·P'n(ti)²)) y se redondearon a doble precisión.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import (
    ErrorFuncion,
    _leer_entero_positivo,
    _leer_numero,
    crear_funcion,
)

blueprint = Blueprint('cuadratura_gaussiana', __name__, url_prefix='/api/cuadratura_gaussiana')

TIPOS = ('simple', 'compuesto')
LIMITE_SUBINTERVALOS = 1000

# grado n -> nodos ti y pesos ci en [-1, 1]
CONSTANTES = {
    1: {
        'nodos': [
            0.0,
        ],
        'pesos': [
            2.0,
        ],
    },
    2: {
        'nodos': [
            -0.5773502691896257,
            0.5773502691896257,
        ],
        'pesos': [
            1.0,
            1.0,
        ],
    },
    3: {
        'nodos': [
            -0.7745966692414834,
            0.0,
            0.7745966692414834,
        ],
        'pesos': [
            0.5555555555555556,
            0.8888888888888888,
            0.5555555555555556,
        ],
    },
    4: {
        'nodos': [
            -0.8611363115940526,
            -0.33998104358485626,
            0.33998104358485626,
            0.8611363115940526,
        ],
        'pesos': [
            0.34785484513745385,
            0.6521451548625461,
            0.6521451548625461,
            0.34785484513745385,
        ],
    },
    5: {
        'nodos': [
            -0.906179845938664,
            -0.5384693101056831,
            0.0,
            0.5384693101056831,
            0.906179845938664,
        ],
        'pesos': [
            0.23692688505618908,
            0.47862867049936647,
            0.5688888888888889,
            0.47862867049936647,
            0.23692688505618908,
        ],
    },
    6: {
        'nodos': [
            -0.932469514203152,
            -0.6612093864662645,
            -0.2386191860831969,
            0.2386191860831969,
            0.6612093864662645,
            0.932469514203152,
        ],
        'pesos': [
            0.17132449237917036,
            0.3607615730481386,
            0.46791393457269104,
            0.46791393457269104,
            0.3607615730481386,
            0.17132449237917036,
        ],
    },
    7: {
        'nodos': [
            -0.9491079123427585,
            -0.7415311855993945,
            -0.4058451513773972,
            0.0,
            0.4058451513773972,
            0.7415311855993945,
            0.9491079123427585,
        ],
        'pesos': [
            0.1294849661688697,
            0.27970539148927664,
            0.3818300505051189,
            0.4179591836734694,
            0.3818300505051189,
            0.27970539148927664,
            0.1294849661688697,
        ],
    },
    8: {
        'nodos': [
            -0.9602898564975363,
            -0.7966664774136267,
            -0.525532409916329,
            -0.1834346424956498,
            0.1834346424956498,
            0.525532409916329,
            0.7966664774136267,
            0.9602898564975363,
        ],
        'pesos': [
            0.10122853629037626,
            0.22238103445337448,
            0.31370664587788727,
            0.362683783378362,
            0.362683783378362,
            0.31370664587788727,
            0.22238103445337448,
            0.10122853629037626,
        ],
    },
    9: {
        'nodos': [
            -0.9681602395076261,
            -0.8360311073266358,
            -0.6133714327005904,
            -0.3242534234038089,
            0.0,
            0.3242534234038089,
            0.6133714327005904,
            0.8360311073266358,
            0.9681602395076261,
        ],
        'pesos': [
            0.08127438836157441,
            0.1806481606948574,
            0.26061069640293544,
            0.31234707704000286,
            0.3302393550012598,
            0.31234707704000286,
            0.26061069640293544,
            0.1806481606948574,
            0.08127438836157441,
        ],
    },
    10: {
        'nodos': [
            -0.9739065285171717,
            -0.8650633666889845,
            -0.6794095682990244,
            -0.4333953941292472,
            -0.14887433898163122,
            0.14887433898163122,
            0.4333953941292472,
            0.6794095682990244,
            0.8650633666889845,
            0.9739065285171717,
        ],
        'pesos': [
            0.06667134430868814,
            0.1494513491505806,
            0.21908636251598204,
            0.26926671930999635,
            0.29552422471475287,
            0.29552422471475287,
            0.26926671930999635,
            0.21908636251598204,
            0.1494513491505806,
            0.06667134430868814,
        ],
    },
}


class ErrorGauss(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


def gauss_simple(f, a, b, grado):
    """Fórmula de Gauss-Legendre de `grado` puntos sobre [a, b].

    Regresa (valor, detalle) con el detalle de cada punto: i, t, c, x, f(x).
    """
    constantes = CONSTANTES[grado]
    mitad = (b - a) / 2
    centro = (a + b) / 2

    detalle = []
    for i, (t, c) in enumerate(zip(constantes['nodos'], constantes['pesos']), start=1):
        x = mitad * t + centro
        detalle.append({'i': i, 't': t, 'c': c, 'x': x, 'fx': f(x)})

    valor = mitad * math.fsum(punto['c'] * punto['fx'] for punto in detalle)
    return valor, detalle


def gauss_compuesto(f, a, b, grado, subintervalos):
    """Suma la fórmula simple sobre `subintervalos` tramos iguales de [a, b].

    Regresa (valor, tramos, detalle_primero): la lista de tramos con su valor
    y el detalle de puntos del primer tramo (para mostrar la sustitución).
    """
    h = (b - a) / subintervalos
    tramos = []
    detalle_primero = None

    for k in range(subintervalos):
        ak = a + k * h
        bk = b if k == subintervalos - 1 else a + (k + 1) * h  # extremo exacto
        valor, detalle = gauss_simple(f, ak, bk, grado)
        tramos.append({'k': k + 1, 'a': ak, 'b': bk, 'valor': valor})
        if detalle_primero is None:
            detalle_primero = detalle

    return math.fsum(tramo['valor'] for tramo in tramos), tramos, detalle_primero


def _tabla_constantes():
    return {
        str(grado): {'nodos': datos['nodos'], 'pesos': datos['pesos'], 'exactoHasta': 2 * grado - 1}
        for grado, datos in CONSTANTES.items()
    }


@blueprint.route('/constantes', methods=['GET', 'POST'])
def constantes():
    """Nodos y pesos de todos los grados: la página los usa para mostrar la fórmula."""
    return jsonify({'grados': _tabla_constantes()})


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        tipo = datos.get('tipo')
        if tipo not in TIPOS:
            raise ErrorGauss('Elige un tipo: Simple o Compuesto.')

        grado = _leer_entero_positivo(datos.get('grado'), 'Grado', ErrorGauss)
        if grado not in CONSTANTES:
            raise ErrorGauss(f'El grado debe estar entre {min(CONSTANTES)} y {max(CONSTANTES)}.')

        a = _leer_numero(datos.get('a'), 'Punto a', ErrorGauss)
        b = _leer_numero(datos.get('b'), 'Punto b', ErrorGauss)
        if a >= b:
            raise ErrorGauss('El punto a debe ser menor que el punto b.')

        subintervalos = 1
        if tipo == 'compuesto':
            subintervalos = _leer_entero_positivo(
                datos.get('subintervalos'), 'Número de subintervalos', ErrorGauss
            )
            if subintervalos > LIMITE_SUBINTERVALOS:
                raise ErrorGauss(f'No se pueden usar más de {LIMITE_SUBINTERVALOS} subintervalos.')

        f = crear_funcion(datos.get('funcion'))

        if tipo == 'simple':
            valor, detalle = gauss_simple(f, a, b, grado)
            tramos = []
            intervalo_detalle = [a, b]
            resumen = f'grado {grado}, {grado} evaluaciones de f'
        else:
            valor, tramos, detalle = gauss_compuesto(f, a, b, grado, subintervalos)
            intervalo_detalle = [tramos[0]['a'], tramos[0]['b']]
            resumen = (
                f'grado {grado}, {subintervalos} subintervalos, '
                f'{grado * subintervalos} evaluaciones de f'
            )

        if not math.isfinite(valor):
            raise ErrorGauss('El resultado no es un número finito. Revisa f(x) en el intervalo.')

        nombre = 'simple' if tipo == 'simple' else 'compuesta'
        mensaje = f'∫ f(x) dx ≈ {valor:.10f}  (Cuadratura gaussiana {nombre}, {resumen})'

        return jsonify({
            'aproximacion': valor,
            'tipo': tipo,
            'grado': grado,
            'subintervalos': subintervalos,
            'intervaloDetalle': intervalo_detalle,
            'detalle': detalle,
            'tramos': tramos,
            'mensaje': mensaje,
        })
    except (ErrorGauss, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la cuadratura gaussiana: {error}'}), 500