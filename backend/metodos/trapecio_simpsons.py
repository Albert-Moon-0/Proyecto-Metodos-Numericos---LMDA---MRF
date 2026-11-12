"""
Métodos: Regla del Trapecio, Simpson 1/3 y Simpson 3/8 (simples y compuestas)

Aproximan la integral de una función f(x) en un intervalo [a, b]:

  Simple (se aplica una sola vez sobre [a, b]):
    Trapecio     (b-a)/2 · [f(a) + f(b)]
    Simpson 1/3  h/3 · [f(a) + 4f(a+h) + f(b)]                    con h = (b-a)/2
    Simpson 3/8  3h/8 · [f(a) + 3f(a+h) + 3f(a+2h) + f(b)]        con h = (b-a)/3

  Compuesta (se divide [a, b] en subintervalos usando una lista de puntos
  x0 < x1 < ... < xn y se suma la regla simple sobre cada grupo de
  subintervalos consecutivos):
    Trapecio     grupos de 1 subintervalo  -> n cualquiera, x pueden estar
                                              espaciados de forma irregular
    Simpson 1/3  grupos de 2 subintervalos -> n par, x equiespaciados
    Simpson 3/8  grupos de 3 subintervalos -> n múltiplo de 3, x equiespaciados

Por eso aquí NO hay una fórmula compuesta aparte para cada regla: la
compuesta es la simple aplicada grupo por grupo (calcular_compuesto), y las
tres reglas solo difieren en su fórmula simple y en cuántos subintervalos
abarca cada grupo. Añadir otra regla (p. ej. Boole, de 4 subintervalos) es
agregar una entrada a REGLAS.

La función f(x) siempre se pide como texto y se evalúa con crear_funcion
de metodos/comun/parser_funciones.py (no se piden valores tabulados de f).

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, _leer_numero, crear_funcion

blueprint = Blueprint('trapecio_simpsons', __name__, url_prefix='/api/trapecio_simpsons')

# Tope de subintervalos: la interfaz crea un campo por punto, así que se
# mantiene en un tamaño manejable.
LIMITE_SUBINTERVALOS = 200


class ErrorIntegracion(Exception):
    """Se lanza cuando la entrada del usuario o los puntos no son válidos."""


def _numero(valor, nombre):
    return _leer_numero(valor, nombre, ErrorIntegracion)


# ---------------------------------------------------------------------------
# Reglas simples: cada una integra f sobre UN grupo [a, b]
# ---------------------------------------------------------------------------

def trapecio_simple(f, a, b):
    return (b - a) / 2 * (f(a) + f(b))


def simpson_13_simple(f, a, b):
    h = (b - a) / 2
    return h / 3 * (f(a) + 4 * f(a + h) + f(b))


def simpson_38_simple(f, a, b):
    h = (b - a) / 3
    return 3 * h / 8 * (f(a) + 3 * f(a + h) + 3 * f(a + 2 * h) + f(b))


# nombre mostrado, fórmula simple, subintervalos que abarca cada grupo
REGLAS = {
    'trapecio': {'nombre': 'Trapecio', 'simple': trapecio_simple, 'grupo': 1},
    'simpson13': {'nombre': 'Simpson 1/3', 'simple': simpson_13_simple, 'grupo': 2},
    'simpson38': {'nombre': 'Simpson 3/8', 'simple': simpson_38_simple, 'grupo': 3},
}

TIPOS = ('simple', 'compuesto')


# ---------------------------------------------------------------------------
# Compuesta = simple aplicada a grupos consecutivos
# ---------------------------------------------------------------------------

def _paso_uniforme(xs):
    """Regresa h si los puntos están equiespaciados; None si no."""
    h = xs[1] - xs[0]
    for i in range(1, len(xs) - 1):
        if not math.isclose(xs[i + 1] - xs[i], h, rel_tol=1e-9, abs_tol=1e-12):
            return None
    return h


def calcular_compuesto(regla, f, xs):
    n = len(xs) - 1
    grupo = regla['grupo']

    if n % grupo != 0:
        if grupo == 2:
            requisito = 'un número par de subintervalos (un número impar de puntos)'
        else:
            requisito = f'un número de subintervalos múltiplo de {grupo}'
        raise ErrorIntegracion(
            f'{regla["nombre"]} compuesto necesita {requisito}. '
            f'Tienes {len(xs)} puntos ({n} subintervalos); agrega o quita puntos.'
        )

    h = _paso_uniforme(xs)

    # Simpson usa los puntos interiores de cada grupo (a+h, a+2h): solo son
    # los x ingresados si están equiespaciados.
    if grupo > 1 and h is None:
        raise ErrorIntegracion(
            f'{regla["nombre"]} compuesto necesita puntos equiespaciados '
            '(la misma distancia entre un punto y el siguiente).'
        )

    contribuciones = [regla['simple'](f, xs[i], xs[i + grupo]) for i in range(0, n, grupo)]

    return math.fsum(contribuciones), h, n


def calcular_simple(regla, f, a, b):
    valor = regla['simple'](f, a, b)
    return valor, (b - a) / regla['grupo']


# ---------------------------------------------------------------------------
# Lectura de la entrada
# ---------------------------------------------------------------------------

def _leer_puntos(valores):
    if not isinstance(valores, list):
        raise ErrorIntegracion('Ingresa los valores de x como una lista de puntos.')

    if len(valores) < 2:
        raise ErrorIntegracion('Se necesitan al menos 2 puntos x.')

    if len(valores) - 1 > LIMITE_SUBINTERVALOS:
        raise ErrorIntegracion(f'No se pueden usar más de {LIMITE_SUBINTERVALOS} subintervalos.')

    xs = []
    for indice, valor in enumerate(valores):
        numero = _numero(valor, f'x{indice}')
        xs.append(numero)

    for i in range(len(xs) - 1):
        if xs[i + 1] <= xs[i]:
            raise ErrorIntegracion(
                f'Los puntos x deben ir en orden creciente y sin repetirse '
                f'(revisa x{i} y x{i + 1}).'
            )

    return xs


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        clave_regla = datos.get('regla')
        tipo = datos.get('tipo')

        if clave_regla not in REGLAS:
            raise ErrorIntegracion('Elige una regla: Trapecio, Simpson 1/3 o Simpson 3/8.')
        if tipo not in TIPOS:
            raise ErrorIntegracion('Elige un tipo: Simple o Compuesto.')

        regla = REGLAS[clave_regla]

        if tipo == 'simple':
            a = _numero(datos.get('x0'), 'Punto inicial x₀')
            b = _numero(datos.get('xn'), 'Punto final xₙ')

            if a >= b:
                raise ErrorIntegracion('El punto inicial x₀ debe ser menor que el punto final xₙ.')

            f = crear_funcion(datos.get('funcion'))
            valor, h = calcular_simple(regla, f, a, b)
            detalle = f'h = {h:g}'
            subintervalos = regla['grupo']
        else:
            xs = _leer_puntos(datos.get('xs'))

            f = crear_funcion(datos.get('funcion'))
            valor, h, subintervalos = calcular_compuesto(regla, f, xs)
            detalle = f'h = {h:g}, ' if h is not None else 'espaciado irregular, '
            detalle += f'{subintervalos} subintervalos'

        if not math.isfinite(valor):
            raise ErrorIntegracion('El resultado no es un número finito. Revisa f(x) en el intervalo.')

        mensaje = f'∫ f(x) dx ≈ {valor:.6f}  ({regla["nombre"]} {tipo}, {detalle})'

        return jsonify({
            'aproximacion': valor,
            'h': h,
            'subintervalos': subintervalos,
            'regla': clave_regla,
            'tipo': tipo,
            'mensaje': mensaje,
        })
    except (ErrorIntegracion, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la integración numérica: {error}'}), 500