"""
Método: Integración de Romberg

Aproxima la integral de f(x) en [a, b] combinando la regla del trapecio
compuesta con extrapolación de Richardson.

  Columna 0 (trapecio):   R(k,0) = trapecio compuesto con n = 2^k subintervalos
  Columnas siguientes:    R(k,j) = ( 4^j · R(k,j-1) - R(k-1,j-1) ) / ( 4^j - 1 )

Cada columna elimina un término del error: R(k,1) equivale a Simpson 1/3
compuesto, R(k,2) a Boole, etc. La diagonal R(k,k) es la mejor aproximación
de cada fila y el método se detiene cuando

    | R(k,k) - R(k-1,k-1) | < tolerancia      o al llegar a las iteraciones máximas.

Reutilización: la columna 0 NO se reimplementa; se obtiene con
`calcular_compuesto` de trapecio_simpsons.py (la misma regla compuesta de la
página de Trapecio/Simpson), solo que aquí con puntos equiespaciados 2^k.

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
from metodos.trapecio_simpsons import REGLAS, calcular_compuesto

blueprint = Blueprint('romberg', __name__, url_prefix='/api/romberg')

# 2^15 = 32768 subintervalos en la última fila: suficiente para cualquier
# integral razonable y sigue respondiendo en una fracción de segundo.
LIMITE_ITERACIONES = 15


class ErrorRomberg(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


def trapecio_2k(f, a, b, k):
    """Trapecio compuesto con 2^k subintervalos (reutiliza trapecio_simpsons)."""
    n = 2 ** k
    paso = (b - a) / n
    xs = [a + i * paso for i in range(n)] + [b]  # extremo exacto, sin acumular error
    valor, h, _ = calcular_compuesto(REGLAS['trapecio'], f, xs)
    return valor, h, n


def romberg(f, a, b, tolerancia, max_iteraciones):
    """Regresa (filas, convergio). Cada fila: dict con k, n, h, r (R(k,0..k)), error."""
    filas = []
    convergio = False

    for k in range(max_iteraciones + 1):
        trapecio, h, n = trapecio_2k(f, a, b, k)
        r = [trapecio]

        for j in range(1, k + 1):
            factor = 4 ** j
            r.append((factor * r[j - 1] - filas[k - 1]['r'][j - 1]) / (factor - 1))

        error = abs(r[k] - filas[k - 1]['r'][k - 1]) if k >= 1 else None
        filas.append({'k': k, 'n': n, 'h': h, 'r': r, 'error': error})

        if error is not None and error < tolerancia:
            convergio = True
            break

    return filas, convergio


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        a = _leer_numero(datos.get('a'), 'Punto a', ErrorRomberg)
        b = _leer_numero(datos.get('b'), 'Punto b', ErrorRomberg)
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo', ErrorRomberg)
        max_iteraciones = _leer_entero_positivo(
            datos.get('maxIteraciones'), 'Iteraciones máximas', ErrorRomberg
        )

        if a >= b:
            raise ErrorRomberg('El punto a debe ser menor que el punto b.')
        if tolerancia <= 0:
            raise ErrorRomberg('El error máximo debe ser mayor que 0.')
        if max_iteraciones > LIMITE_ITERACIONES:
            raise ErrorRomberg(f'Las iteraciones máximas no pueden pasar de {LIMITE_ITERACIONES}.')

        f = crear_funcion(datos.get('funcion'))
        filas, convergio = romberg(f, a, b, tolerancia, max_iteraciones)

        ultima = filas[-1]
        aproximacion = ultima['r'][-1]

        if not math.isfinite(aproximacion):
            raise ErrorRomberg('El resultado no es un número finito. Revisa f(x) en el intervalo.')

        if convergio:
            mensaje = (
                f'∫ f(x) dx ≈ {aproximacion:.10f}  (Romberg, {ultima["k"]} iteraciones, '
                f'{ultima["n"]} subintervalos, error ≈ {ultima["error"]:.3e})'
            )
        else:
            mensaje = (
                f'∫ f(x) dx ≈ {aproximacion:.10f}  No se alcanzó el error máximo en '
                f'{max_iteraciones} iteraciones (error ≈ {ultima["error"]:.3e}). '
                'Aumenta las iteraciones o el error máximo.'
            )

        return jsonify({
            'aproximacion': aproximacion,
            'errorEstimado': ultima['error'],
            'convergio': convergio,
            'iteraciones': filas,
            'mensaje': mensaje,
        })
    except (ErrorRomberg, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en Romberg: {error}'}), 500