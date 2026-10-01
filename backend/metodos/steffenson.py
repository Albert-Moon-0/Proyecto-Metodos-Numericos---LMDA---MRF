"""
Método: Steffensen

Acelera la convergencia del método de Punto Fijo usando el proceso
Delta-cuadrado de Aitken. A partir de un único valor inicial x0 y una
función de iteración g(x) (tal que la raíz buscada cumple x = g(x)),
en cada paso calcula:

    x1 = g(x0)
    x2 = g(x1)
    x_nuevo = x0 - (x1 - x0)² / (x2 - 2·x1 + x0)

x_nuevo es la extrapolación de Aitken sobre la sucesión x0, x1, x2, y
normalmente converge de forma cuadrática aunque la iteración de punto
fijo "cruda" (x0, x1, x2, ...) converja solo linealmente.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Bisección, Secante, Falsa Posición ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion

blueprint = Blueprint('steffensen', __name__, url_prefix='/api/steffensen')


class ErrorSteffensen(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorSteffensen(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorSteffensen(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorSteffensen(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorSteffensen(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_steffensen(g, x0, tolerancia, max_iteraciones):
    x = x0
    iteraciones = []

    for i in range(1, max_iteraciones + 1):
        x1 = g(x)
        x2 = g(x1)
        denominador = x2 - 2 * x1 + x

        if denominador == 0:
            raise ErrorSteffensen(
                'La extrapolación de Aitken se estancó (denominador cero) antes de alcanzar la tolerancia. '
                'Prueba con otro x0 o revisa que g(x) esté bien planteada.'
            )

        x_nuevo = x - (x1 - x) ** 2 / denominador
        error_absoluto = abs(x_nuevo - x)
        error_aproximado = error_absoluto / abs(x_nuevo) if x_nuevo != 0 else error_absoluto

        iteraciones.append({
            'iteracion': i,
            'x0': x,
            'x1': x1,
            'x2': x2,
            'x': x_nuevo,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if error_aproximado < tolerancia:
            return x_nuevo, iteraciones, True

        x = x_nuevo

    return x, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        x0 = _leer_numero(datos.get('x0'), 'Valor inicial x0')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if tolerancia <= 0:
            raise ErrorSteffensen('El error máximo debe ser mayor que cero.')

        g = crear_funcion(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_steffensen(g, x0, tolerancia, max_iteraciones)

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
    except (ErrorSteffensen, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Steffensen: {error}'}), 500