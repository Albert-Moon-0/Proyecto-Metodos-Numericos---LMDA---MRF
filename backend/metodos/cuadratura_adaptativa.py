"""
Método: Cuadratura adaptativa (Simpson adaptativo con árbol binario)

Aproxima la integral de f(x) en [a, b] subdividiendo SOLO donde hace falta.
Para un intervalo [a, b] con error permitido E y c = (a + b)/2:

    S(a, b)                   Simpson 1/3 sobre todo el intervalo
    S(a, c) + S(c, b)         Simpson 1/3 sobre cada mitad

    Error aprox = | S(a, b) - S(a, c) - S(c, b) |

  - Si  Error aprox < 15·E  ->  el intervalo se acepta y aporta S(a, c) + S(c, b).
  - Si no                   ->  se divide en [a, c] y [c, b], cada uno con E/2.

Cada intervalo evaluado es un NODO del árbol binario (la raíz es [a, b]; los
hijos son las mitades). Como los E se reparten a la mitad en cada nivel, la
suma de los E de las hojas es E: ese es el error total permitido.

Este archivo hace TODO el cálculo y regresa el árbol completo como JSON (lista
de nodos con su padre e hijos); el navegador solo lo dibuja con Cytoscape.js.

Reutilización: Simpson 1/3 simple es el mismo de trapecio_simpsons.py (REGLAS).

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
from metodos.trapecio_simpsons import REGLAS

blueprint = Blueprint('cuadratura_adaptativa', __name__, url_prefix='/api/cuadratura_adaptativa')

simpson = REGLAS['simpson13']['simple']

# Un árbol con más nodos ya no se puede leer ni dibujar con sentido.
MAX_NODOS = 255
LIMITE_NIVEL = 12


class ErrorAdaptativa(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el árbol es demasiado grande."""


def _con_cache(f):
    """Los puntos a, c y b se repiten entre S(a,b), S(a,c) y S(c,b): se evalúan una sola vez."""
    cache = {}

    def g(x):
        if x not in cache:
            cache[x] = f(x)
        return cache[x]

    g.evaluaciones = lambda: len(cache)
    return g


def construir_arbol(f, a, b, tolerancia, nivel_maximo):
    """Regresa la lista de nodos (en preorden). La raíz es nodos[0]."""
    nodos = []

    def visitar(a, b, error_permitido, nivel, padre):
        if len(nodos) >= MAX_NODOS:
            raise ErrorAdaptativa(
                f'El árbol tendría más de {MAX_NODOS} nodos y no se puede mostrar. '
                'Aumenta el error máximo E o reduce el nivel máximo.'
            )

        c = (a + b) / 2
        s_ab = simpson(f, a, b)
        s_ac = simpson(f, a, c)
        s_cb = simpson(f, c, b)
        s_dividido = s_ac + s_cb

        error_aprox = abs(s_ab - s_dividido)
        umbral = 15 * error_permitido
        cumple = error_aprox < umbral

        nodo = {
            'id': f'n{len(nodos)}',
            'padre': padre,
            'hijos': [],
            'nivel': nivel,
            'a': a,
            'b': b,
            'c': c,
            'E': error_permitido,          # error permitido en este intervalo
            'umbral': umbral,              # 15·E
            'S_ab': s_ab,
            'S_ac': s_ac,
            'S_cb': s_cb,
            'S_dividido': s_dividido,      # S(a,c) + S(c,b)
            'errorAprox': error_aprox,     # |S(a,b) - S(a,c) - S(c,b)|
            'cumple': cumple,              # Error aprox < 15·E
        }
        nodos.append(nodo)

        if cumple:
            nodo['estado'] = 'aceptado'
            nodo['aporte'] = s_dividido
        elif nivel >= nivel_maximo:
            nodo['estado'] = 'limite'      # no cumple, pero ya no se puede dividir más
            nodo['aporte'] = s_dividido
        else:
            nodo['estado'] = 'dividido'
            izquierdo = visitar(a, c, error_permitido / 2, nivel + 1, nodo['id'])
            derecho = visitar(c, b, error_permitido / 2, nivel + 1, nodo['id'])
            nodo['hijos'] = [izquierdo['id'], derecho['id']]
            nodo['aporte'] = izquierdo['aporte'] + derecho['aporte']

        return nodo

    visitar(a, b, tolerancia, 0, None)
    return nodos


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        a = _leer_numero(datos.get('a'), 'Punto a', ErrorAdaptativa)
        b = _leer_numero(datos.get('b'), 'Punto b', ErrorAdaptativa)
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo E', ErrorAdaptativa)
        nivel_maximo = _leer_entero_positivo(datos.get('nivelMaximo'), 'Nivel máximo', ErrorAdaptativa)

        if a >= b:
            raise ErrorAdaptativa('El punto a debe ser menor que el punto b.')
        if tolerancia <= 0:
            raise ErrorAdaptativa('El error máximo E debe ser mayor que 0.')
        if nivel_maximo > LIMITE_NIVEL:
            raise ErrorAdaptativa(f'El nivel máximo no puede pasar de {LIMITE_NIVEL}.')

        f = _con_cache(crear_funcion(datos.get('funcion')))
        nodos = construir_arbol(f, a, b, tolerancia, nivel_maximo)

        hojas = [nodo for nodo in nodos if not nodo['hijos']]
        aproximacion = math.fsum(hoja['aporte'] for hoja in hojas)
        en_limite = [hoja for hoja in hojas if hoja['estado'] == 'limite']

        if not math.isfinite(aproximacion):
            raise ErrorAdaptativa('El resultado no es un número finito. Revisa f(x) en el intervalo.')

        nivel_alcanzado = max(nodo['nivel'] for nodo in nodos)
        resumen = (
            f'{len(hojas)} subintervalos finales, {len(nodos)} nodos, '
            f'nivel alcanzado {nivel_alcanzado}'
        )

        if en_limite:
            mensaje = (
                f'∫ f(x) dx ≈ {aproximacion:.10f}  ({resumen}). '
                f'En {len(en_limite)} subintervalo(s) no se cumplió Error aprox < 15E dentro del '
                f'nivel máximo {nivel_maximo}: el resultado puede no cumplir E = {tolerancia:g}.'
            )
        else:
            mensaje = (
                f'∫ f(x) dx ≈ {aproximacion:.10f}  ({resumen}; '
                f'cuadratura adaptativa con E = {tolerancia:g})'
            )

        return jsonify({
            'aproximacion': aproximacion,
            'convergio': not en_limite,
            'nodos': nodos,
            'hojas': len(hojas),
            'nodosTotales': len(nodos),
            'nivelAlcanzado': nivel_alcanzado,
            'evaluaciones': f.evaluaciones(),
            'mensaje': mensaje,
        })
    except (ErrorAdaptativa, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la cuadratura adaptativa: {error}'}), 500