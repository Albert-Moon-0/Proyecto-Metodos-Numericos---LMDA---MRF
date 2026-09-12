"""
Método: Falsa Posición (Regula Falsi)

Combina bisección y secante: parte de un intervalo [a, b] donde f(a) y
f(b) tienen signos opuestos (como bisección), pero en vez de usar el
punto medio, calcula la intersección con el eje X de la recta secante
que pasa por (a, f(a)) y (b, f(b)) — igual que en el método de la
Secante. Esa intersección c siempre reemplaza al extremo del intervalo
que comparte signo con ella, de modo que [a, b] sigue encerrando la
raíz en cada iteración (a diferencia de la Secante pura, que puede
divergir).

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Bisección, Secante ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion

blueprint = Blueprint('falsa_posicion', __name__, url_prefix='/api/falsa-posicion')


class ErrorFalsaPosicion(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorFalsaPosicion(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorFalsaPosicion(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorFalsaPosicion(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorFalsaPosicion(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_falsa_posicion(f, a, b, tolerancia, max_iteraciones):
    fa = f(a)
    fb = f(b)

    if fa * fb >= 0:
        raise ErrorFalsaPosicion('El intervalo no es válido: f(a) y f(b) deben tener signos opuestos.')

    iteraciones = []
    c = a

    for i in range(1, max_iteraciones + 1):
        fa = f(a)
        fb = f(b)

        if fb - fa == 0:
            raise ErrorFalsaPosicion('La falsa posición no puede continuar: f(b) - f(a) = 0.')

        # Intersección de la recta secante entre (a, fa) y (b, fb) con el eje X.
        c = b - fb * (b - a) / (fb - fa)
        fc = f(c)

        error_absoluto = abs(c - b)
        error_aproximado = error_absoluto / abs(c) if c != 0 else error_absoluto

        iteraciones.append({
            'iteracion': i,
            'a': a,
            'b': b,
            'c': c,
            'fc': fc,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if fc == 0 or error_aproximado < tolerancia:
            return c, iteraciones, True

        # Regla de bisección aplicada al punto c: solo se reemplaza el
        # extremo que comparte signo con f(c), así el intervalo [a, b]
        # nunca deja de encerrar la raíz.
        if fa * fc < 0:
            b = c
        else:
            a = c

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
            raise ErrorFalsaPosicion('Los puntos "a" y "b" deben ser distintos.')

        if tolerancia <= 0:
            raise ErrorFalsaPosicion('El error máximo debe ser mayor que cero.')

        f = crear_funcion(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_falsa_posicion(f, a, b, tolerancia, max_iteraciones)

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
    except (ErrorFalsaPosicion, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de la Falsa Posición: {error}'}), 500