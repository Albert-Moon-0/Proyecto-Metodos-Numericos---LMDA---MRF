"""
Método: Euler

Aproxima la solución de una EDO de valor inicial

    dy/dt = f(t, y),    y(t0) = w0,    t en [t0, tn]

dividiendo el intervalo en n subintervalos de ancho h = (tn - t0) / n y
avanzando con

    w_{i+1} = w_i + h · f(t_i, w_i),    t_i = t0 + i·h

Por cada iteración se reporta el tiempo t_i y la aproximación w_i ≈ y(t_i).
Si tn < t0, h resulta negativo y el método avanza hacia atrás.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás. La función f(t, y) se interpreta con
crear_funcion_edo de metodos/comun/parser_funciones.py (dos variables).
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion_edo, _leer_numero, _leer_entero_positivo

blueprint = Blueprint('euler', __name__, url_prefix='/api/euler')

LIMITE_SUBINTERVALOS = 5000


class ErrorEuler(Exception):
    """Se lanza cuando la entrada del usuario o el intervalo no son válidos."""

def calcular_euler(f, t0, tn, n, w0):
    h = (tn - t0) / n
    w = w0

    iteraciones = [{'iteracion': 0, 't': t0, 'w': w0}]

    for i in range(1, n + 1):
        t_anterior = t0 + (i - 1) * h
        w = w + h * f(t_anterior, w)

        if not math.isfinite(w):
            raise ErrorEuler(
                f'La aproximación se volvió infinita o indefinida en la iteración {i}. '
                'Prueba con más subintervalos o revisa f(t, y).'
            )
        t = tn if i == n else t0 + i * h

        iteraciones.append({'iteracion': i, 't': t, 'w': w})

    return h, iteraciones, w


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        t0 = _leer_numero(datos.get('t0'), 'Punto t0', ErrorEuler)
        tn = _leer_numero(datos.get('tn'), 'Punto tn', ErrorEuler)
        n = _leer_entero_positivo(datos.get('n'), 'Número de subintervalos', ErrorEuler)
        w0 = _leer_numero(datos.get('w0'), 'Valor inicial y(t0)', ErrorEuler)

        if t0 == tn:
            raise ErrorEuler('Los puntos "t0" y "tn" deben ser distintos.')

        if n > LIMITE_SUBINTERVALOS:
            raise ErrorEuler(f'El número de subintervalos no puede pasar de {LIMITE_SUBINTERVALOS}.')

        f = crear_funcion_edo(datos.get('funcion'))
        h, iteraciones, aproximacion = calcular_euler(f, t0, tn, n, w0)

        mensaje = (
            f'Aproximación: y({tn:g}) ≈ {aproximacion:.6f} '
            f'(h = {h:g}, {n} subintervalos)'
        )

        return jsonify({
            'aproximacion': aproximacion,
            'h': h,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
        })
    except (ErrorEuler, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Euler: {error}'}), 500