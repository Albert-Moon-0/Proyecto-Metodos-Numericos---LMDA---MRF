"""
Método: Secante

Busca la raíz de f(x) a partir de dos aproximaciones iniciales p0 y p1,
usando la recta secante entre (p0, f(p0)) y (p1, f(p1)) para generar la
siguiente aproximación.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Bisección ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion

blueprint = Blueprint('secante', __name__, url_prefix='/api/secante')


class ErrorSecante(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorSecante(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorSecante(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorSecante(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorSecante(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_secante(f, p0, p1, tolerancia, max_iteraciones):
    if abs(f(p1) - f(p0)) < 1e-10:
        raise ErrorSecante('Los valores iniciales son demasiado cercanos.')

    iteraciones = []
    p2 = 0.0

    for i in range(1, max_iteraciones + 1):
        fp0 = f(p0)
        fp1 = f(p1)

        if fp1 - fp0 == 0:
            raise ErrorSecante('La secante no puede continuar: f(p1) - f(p0) = 0.')

        p2 = p1 - (fp1 * (p1 - p0)) / (fp1 - fp0)
        fp2 = f(p2)
        error = abs(p2 - p1)

        iteraciones.append({
            'iteracion': i,
            'p0': p0,
            'p1': p1,
            'p2': p2,
            'fp2': fp2,
            'error': error,
        })

        if fp2 == 0 or error < tolerancia:
            return p2, iteraciones, True

        p0, p1 = p1, p2

    return p2, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        p0 = _leer_numero(datos.get('a'), 'Punto p0')
        p1 = _leer_numero(datos.get('b'), 'Punto p1')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if p0 == p1:
            raise ErrorSecante('Los puntos deben ser distintos.')

        if tolerancia <= 0:
            raise ErrorSecante('El error máximo debe ser mayor que cero.')

        f = crear_funcion(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_secante(f, p0, p1, tolerancia, max_iteraciones)

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
    except (ErrorSecante, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de la Secante: {error}'}), 500
