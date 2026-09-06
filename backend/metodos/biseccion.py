"""
Método: Bisección

Busca la raíz de f(x) en un intervalo [a, b] donde f(a) y f(b) tienen
signos opuestos. Reporta, por cada iteración, el error absoluto
(la mitad del ancho del intervalo) y el error aproximado (la variación
porcentual entre la aproximación actual y la anterior).

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Secante ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion

blueprint = Blueprint('biseccion', __name__, url_prefix='/api/biseccion')


class ErrorBiseccion(Exception):
    """Se lanza cuando la entrada del usuario o el intervalo no son válidos."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorBiseccion(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorBiseccion(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorBiseccion(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorBiseccion(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_biseccion(f, a, b, tolerancia, max_iteraciones):
    if f(a) * f(b) >= 0:
        raise ErrorBiseccion('El intervalo no es válido: f(a) y f(b) deben tener signos opuestos.')

    iteraciones = []
    c = a
    c_anterior = None

    for i in range(1, max_iteraciones + 1):
        c = (a + b) / 2
        fc = f(c)
        error_absoluto = abs(b - a) / 2

        error_aproximado = None
        if c_anterior is not None and c != 0:
            error_aproximado = abs((c - c_anterior) / c) * 100

        iteraciones.append({
            'iteracion': i,
            'a': a,
            'b': b,
            'c': c,
            'fc': fc,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if fc == 0 or error_absoluto < tolerancia:
            return c, iteraciones, True

        if f(a) * fc < 0:
            b = c
        else:
            a = c

        c_anterior = c

    return c, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        a = _leer_numero(datos.get('a'), 'Punto a')
        b = _leer_numero(datos.get('b'), 'Punto b')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if a == b:
            raise ErrorBiseccion('Los puntos "a" y "b" deben ser distintos.')

        if tolerancia <= 0:
            raise ErrorBiseccion('El error máximo debe ser mayor que cero.')

        f = crear_funcion(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_biseccion(f, a, b, tolerancia, max_iteraciones)

        mensaje = (
            f'Raíz aproximada: x ≈ {raiz:.6f} ({len(iteraciones)} iteraciones)'
            if convergio
            else f'No se alcanzó la tolerancia tras {len(iteraciones)} iteraciones. '
                 f'Mejor aproximación: x ≈ {raiz:.6f}'
        )

        return jsonify({
            'raiz': raiz,
            'convergio': convergio,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
        })
    except (ErrorBiseccion, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Bisección: {error}'}), 500
