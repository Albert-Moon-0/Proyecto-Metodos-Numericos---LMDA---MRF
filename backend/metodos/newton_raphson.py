"""
Método: Newton-Raphson

Busca la raíz de f(x) a partir de una aproximación inicial p0, usando la
intersección con el eje X de la recta tangente a f(x) en cada
aproximación: p_{n+1} = p_n - f(p_n) / f'(p_n).

La derivada f'(x) se calcula de forma simbólica (exacta, no numérica)
con `comun/derivador.py`, así que f(x) puede ser cualquier función
algebraica, trigonométrica, hiperbólica, exponencial o logarítmica.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Bisección, Secante, Falsa Posición,
Punto Fijo ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.derivador import ErrorDerivada, crear_funcion_y_derivada
from metodos.comun.parser_funciones import ErrorFuncion

blueprint = Blueprint('newton_raphson', __name__, url_prefix='/api/newton-raphson')


class ErrorNewtonRaphson(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorNewtonRaphson(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorNewtonRaphson(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorNewtonRaphson(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorNewtonRaphson(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_newton_raphson(f, f_prima, p0, tolerancia, max_iteraciones):
    iteraciones = []
    p1 = p0

    for i in range(1, max_iteraciones + 1):
        fp0 = f(p0)
        dfp0 = f_prima(p0)

        if dfp0 == 0:
            raise ErrorNewtonRaphson(f"La derivada se anula en p = {p0}; Newton-Raphson no puede continuar.")

        p1 = p0 - fp0 / dfp0
        fp1 = f(p1)

        error_absoluto = abs(p1 - p0)
        error_aproximado = abs(error_absoluto / p1) * 100 if p1 != 0 else None

        iteraciones.append({
            'iteracion': i,
            'p0': p0,
            'fp0': fp0,
            'dfp0': dfp0,
            'p1': p1,
            'fp1': fp1,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if fp1 == 0 or error_absoluto < tolerancia:
            return p1, iteraciones, True

        p0 = p1

    return p1, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        p0 = _leer_numero(datos.get('p0'), 'Aproximación inicial p0')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if tolerancia <= 0:
            raise ErrorNewtonRaphson('El error máximo debe ser mayor que cero.')

        f, f_prima = crear_funcion_y_derivada(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_newton_raphson(f, f_prima, p0, tolerancia, max_iteraciones)

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
    except (ErrorNewtonRaphson, ErrorDerivada, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Newton-Raphson: {error}'}), 500
