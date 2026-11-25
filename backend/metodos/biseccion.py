"""
Método: Bisección

Busca la raíz de f(x) en un intervalo [a, b] donde f(a) y f(b) tienen
signos opuestos. Reporta, por cada iteración, el error absoluto
(la mitad del ancho del intervalo) y el error aproximado (la variación
porcentual entre la aproximación actual y la anterior).

Además de la tabla, la respuesta incluye `grafica` (puntos de f(x) y rango
vertical, ver comun/grafica.py) y, por iteración, fa y fb: con ellos la página
dibuja el cambio de signo del intervalo en cada paso.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Secante ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.grafica import armar_grafica
from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion, _leer_entero_positivo, _leer_numero

blueprint = Blueprint('biseccion', __name__, url_prefix='/api/biseccion')


class ErrorBiseccion(Exception):
    """Se lanza cuando la entrada del usuario o el intervalo no son válidos."""

def calcular_biseccion(f, a, b, tolerancia, max_iteraciones):
    fa, fb = f(a), f(b)
    if fa * fb >= 0:
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
            'fa': fa,
            'fb': fb,
            'fc': fc,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if fc == 0 or error_absoluto < tolerancia:
            return c, iteraciones, True

        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc

        c_anterior = c

    return c, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        a = _leer_numero(datos.get('a'), 'Punto a', ErrorBiseccion)
        b = _leer_numero(datos.get('b'), 'Punto b', ErrorBiseccion)
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo', ErrorBiseccion)
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas', ErrorBiseccion)

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

        # Bisección también "converge" hacia una discontinuidad (tan, 1/x): ahí el
        # signo cambia sin que haya raíz. Se detecta porque |f(c)| no baja.
        advertencia = None
        extremo = max(abs(iteraciones[0]['fa']), abs(iteraciones[0]['fb']))
        if convergio and abs(iteraciones[-1]['fc']) > extremo:
            advertencia = (
                'Ojo: |f(c)| es grande en la última iteración; el cambio de signo parece venir '
                'de una discontinuidad de f(x) y no de una raíz.'
            )
            mensaje += '. ' + advertencia

        respuesta = {
            'raiz': raiz,
            'advertencia': advertencia,
            'convergio': convergio,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
        }

        # La gráfica es un extra: si falla, el cálculo se entrega igual.
        try:
            inicial = iteraciones[0]
            respuesta['grafica'] = armar_grafica(
                f, inicial['a'], inicial['b'], valores_clave=[inicial['fa'], inicial['fb']]
            )
        except Exception:  # noqa: BLE001
            respuesta['grafica'] = None

        return jsonify(respuesta)
    except (ErrorBiseccion, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Bisección: {error}'}), 500