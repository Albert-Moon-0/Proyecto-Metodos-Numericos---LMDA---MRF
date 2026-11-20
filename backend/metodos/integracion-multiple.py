"""
Método: Integración múltiple (integral doble) con trapecio compuesto

Aproxima  ∫∫ f(x, y) dy dx  de dos formas, según cómo esté delimitada la región:

  intervalos   Rectángulo [a, b] × [c, d]:
                   ∫ₐᵇ ∫_c^d f(x, y) dy dx
  funciones    Región entre dos curvas, con x en [a, b]:
                   ∫ₐᵇ ∫_{f1(x)}^{f2(x)} f(x, y) dy dx

La integral doble es una integral dentro de otra, así que se calcula igual:
trapecio compuesto por dentro y trapecio compuesto por fuera.

    G(x) = ∫ f(x, y) dy      ≈ trapecio compuesto en y con m subintervalos
    I    = ∫ₐᵇ G(x) dx       ≈ trapecio compuesto en x con n subintervalos

En la región entre curvas, los límites de y cambian con x, por eso el paso
en y es hy(x) = (f2(x) - f1(x)) / m y se recalcula en cada x.

Reutilización: el trapecio compuesto de una variable es el de
trapecio_simpsons.py (calcular_compuesto), aplicado dos veces.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import (
    ErrorFuncion,
    _compilar_codigo,
    _entorno_base,
    _evaluar,
    _leer_entero_positivo,
    _leer_numero,
    _preparar_arbol,
    crear_funcion,
)
from metodos.trapecio_simpsons import REGLAS, calcular_compuesto

blueprint = Blueprint('integracion_multiple', __name__, url_prefix='/api/integracion_multiple')

TIPOS = ('intervalos', 'funciones')

# Se evalúan (n + 1)(m + 1) puntos: con 500 y 500 son ~251 mil evaluaciones.
LIMITE_SUBINTERVALOS = 500

trapecio = REGLAS['trapecio']


class ErrorIntegracionMultiple(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


# ---------------------------------------------------------------------------
# f(x, y): función de dos variables, con el mismo parser seguro de f(x)
# ---------------------------------------------------------------------------

def crear_funcion_xy(expresion_original):
    """Convierte el texto de f(x, y) en una función Python f(x, y) -> float."""

    nodo = _preparar_arbol(expresion_original, variables=('x', 'y'), nombre_funcion='f(x, y)')
    codigo = _compilar_codigo(nodo)
    entorno_base = _entorno_base()

    def f(x, y):
        entorno = dict(entorno_base)
        entorno['x'] = x
        entorno['y'] = y
        return _evaluar(codigo, entorno, f'f({x:g}, {y:g})', f'x = {x:g}, y = {y:g}')

    return f


# ---------------------------------------------------------------------------
# Trapecio doble = trapecio compuesto de un trapecio compuesto
# ---------------------------------------------------------------------------

def _puntos(inicio, fin, subintervalos):
    """subintervalos + 1 puntos equiespaciados; el último es exactamente `fin`."""
    paso = (fin - inicio) / subintervalos
    return [inicio + i * paso for i in range(subintervalos)] + [fin]


def _memorizar(funcion):
    """Cada punto se evalúa una sola vez aunque el trapecio lo use en dos subintervalos."""
    cache = {}

    def memorizada(valor):
        if valor not in cache:
            cache[valor] = funcion(valor)
        return cache[valor]

    return memorizada


def trapecio_doble(f, a, b, n, limites_y, m):
    """∫ₐᵇ ∫ f(x, y) dy dx con n subintervalos en x y m en y.

    `limites_y(x)` regresa (y_inferior, y_superior) para ese x.
    """

    def integral_en_y(x):
        y_inferior, y_superior = limites_y(x)
        valor, _, _ = calcular_compuesto(
            trapecio,
            _memorizar(lambda y: f(x, y)),
            _puntos(y_inferior, y_superior, m),
        )
        return valor

    valor, _, _ = calcular_compuesto(trapecio, _memorizar(integral_en_y), _puntos(a, b, n))
    return valor


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------

def _funcion_de_x(texto, nombre):
    """f1(x) / f2(x): indica cuál de las dos falló."""
    try:
        return crear_funcion(texto)
    except ErrorFuncion as error:
        raise ErrorIntegracionMultiple(f'{nombre}: {error}') from error


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        tipo = datos.get('tipo')
        if tipo not in TIPOS:
            raise ErrorIntegracionMultiple('Elige un tipo: Intervalos o Funciones.')

        a = _leer_numero(datos.get('a'), 'Punto a', ErrorIntegracionMultiple)
        b = _leer_numero(datos.get('b'), 'Punto b', ErrorIntegracionMultiple)
        if a >= b:
            raise ErrorIntegracionMultiple('El punto a debe ser menor que el punto b.')

        n = _leer_entero_positivo(datos.get('n'), 'Subintervalos n', ErrorIntegracionMultiple)
        m = _leer_entero_positivo(datos.get('m'), 'Subintervalos m', ErrorIntegracionMultiple)
        for nombre, valor in (('n', n), ('m', m)):
            if valor > LIMITE_SUBINTERVALOS:
                raise ErrorIntegracionMultiple(
                    f'Los subintervalos {nombre} no pueden pasar de {LIMITE_SUBINTERVALOS}.'
                )

        if tipo == 'intervalos':
            c = _leer_numero(datos.get('c'), 'Punto c', ErrorIntegracionMultiple)
            d = _leer_numero(datos.get('d'), 'Punto d', ErrorIntegracionMultiple)
            if c >= d:
                raise ErrorIntegracionMultiple('El punto c debe ser menor que el punto d.')

            f = crear_funcion_xy(datos.get('funcion'))
            valor = trapecio_doble(f, a, b, n, lambda x: (c, d), m)
        else:
            f1 = _funcion_de_x(datos.get('f1'), 'f1(x)')
            f2 = _funcion_de_x(datos.get('f2'), 'f2(x)')

            def limites_y(x):
                inferior, superior = f1(x), f2(x)
                if superior < inferior:
                    raise ErrorIntegracionMultiple(
                        f'f2(x) debe ser mayor o igual que f1(x) en [a, b]; '
                        f'en x = {x:g} resulta f1 = {inferior:g} y f2 = {superior:g}.'
                    )
                return inferior, superior

            f = crear_funcion_xy(datos.get('funcion'))
            valor = trapecio_doble(f, a, b, n, limites_y, m)

        if not math.isfinite(valor):
            raise ErrorIntegracionMultiple('El resultado no es un número finito. Revisa f(x, y) en la región.')

        evaluaciones = (n + 1) * (m + 1)
        mensaje = (
            f'∫∫ f(x, y) dy dx ≈ {valor:.10f}  '
            f'(Trapecio compuesto, n = {n}, m = {m}, {evaluaciones} evaluaciones de f)'
        )

        return jsonify({
            'aproximacion': valor,
            'tipo': tipo,
            'n': n,
            'm': m,
            'evaluaciones': evaluaciones,
            'mensaje': mensaje,
        })
    except (ErrorIntegracionMultiple, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la integración múltiple: {error}'}), 500