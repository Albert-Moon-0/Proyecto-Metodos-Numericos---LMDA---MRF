"""
Método: Interpolación de Lagrange

Dada una función f(x), un intervalo [a, b] y una cantidad de puntos N, se
toman N nodos equiespaciados x0 = a, ..., x(N-1) = b, se calculan los
valores f(xi) y se construye el polinomio de grado N-1 que pasa por todos
ellos:

    P(x) = Σ f(xi) · Li(x),      Li(x) = Π (x - xj) / (xi - xj),   j ≠ i

El backend devuelve:
- la tabla de nodos (xi, f(xi)),
- el polinomio expandido (coeficientes calculados en aritmética exacta con
  fracciones, para evitar errores de cancelación al expandir),
- puntos muestreados de f(x) y de P(x) para dibujar ambas gráficas,
- el error máximo |f(x) - P(x)| observado en las muestras,
- opcionalmente, la evaluación de P en un punto x* indicado por el usuario.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math
from fractions import Fraction

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, _leer_numero, crear_funcion

blueprint = Blueprint('lagrange', __name__, url_prefix='/api/lagrange')

MIN_PUNTOS = 2
# Con muchos nodos equiespaciados el polinomio oscila mucho en los extremos
# (fenómeno de Runge), así que se mantiene un tope razonable.
MAX_PUNTOS = 20
MUESTRAS_GRAFICA = 240


class ErrorLagrange(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


def _numero(valor, nombre):
    return _leer_numero(valor, nombre, ErrorLagrange)


def _leer_cantidad_puntos(valor):
    numero = _numero(valor, 'Número de puntos')
    if not float(numero).is_integer():
        raise ErrorLagrange('El número de puntos debe ser un entero.')
    cantidad = int(numero)
    if cantidad < MIN_PUNTOS or cantidad > MAX_PUNTOS:
        raise ErrorLagrange(f'El número de puntos debe estar entre {MIN_PUNTOS} y {MAX_PUNTOS}.')
    return cantidad


# ---------------------------------------------------------------------------
# Nodos y polinomio
# ---------------------------------------------------------------------------

def _nodos_equiespaciados(a, b, cantidad):
    h = (b - a) / (cantidad - 1)
    return [b if i == cantidad - 1 else a + i * h for i in range(cantidad)], h


def _pesos(xs):
    """wi = 1 / Π (xi - xj), j ≠ i. Sirven para evaluar P(x) rápido."""
    pesos = []
    for i, xi in enumerate(xs):
        producto = 1.0
        for j, xj in enumerate(xs):
            if j != i:
                producto *= xi - xj
        pesos.append(1.0 / producto)
    return pesos


def evaluar_polinomio(xs, ys, pesos, x):
    """Evalúa P(x) con la fórmula de Lagrange."""
    total = 0.0
    for i in range(len(xs)):
        termino = ys[i] * pesos[i]
        for j in range(len(xs)):
            if j != i:
                termino *= x - xs[j]
        total += termino
    return total


def calcular_coeficientes(xs, ys):
    """Coeficientes [c0, c1, ..., cn] de P(x) = c0 + c1·x + ... + cn·x^n.

    Se usa aritmética exacta (Fraction) porque expandir los Li(x) con
    decimales pierde mucha precisión cuando hay varios nodos.
    """
    n = len(xs)
    X = [Fraction(x) for x in xs]
    Y = [Fraction(y) for y in ys]
    total = [Fraction(0)] * n

    for i in range(n):
        base = [Fraction(1)]  # Π (x - xj), j ≠ i; coeficientes en orden ascendente
        denominador = Fraction(1)

        for j in range(n):
            if j == i:
                continue
            nueva = [Fraction(0)] * (len(base) + 1)
            for k, c in enumerate(base):
                nueva[k] -= c * X[j]
                nueva[k + 1] += c
            base = nueva
            denominador *= X[i] - X[j]

        factor = Y[i] / denominador
        for k, c in enumerate(base):
            total[k] += factor * c

    try:
        return [float(c) for c in total]
    except OverflowError as error:
        raise ErrorLagrange('Los coeficientes del polinomio son demasiado grandes.') from error


def _formatear_polinomio(coeficientes):
    """Texto copiable: 0.5*x^3 - 2*x + 1 (se puede pegar como f(x) en otros métodos)."""
    mayor = max((abs(c) for c in coeficientes), default=0.0)
    umbral = mayor * 1e-10
    terminos = []

    for grado in range(len(coeficientes) - 1, -1, -1):
        c = coeficientes[grado]
        if abs(c) <= umbral:
            continue

        magnitud = f'{abs(c):.6g}'
        if grado == 0:
            cuerpo = magnitud
        else:
            variable = 'x' if grado == 1 else f'x^{grado}'
            cuerpo = variable if magnitud == '1' else f'{magnitud}*{variable}'

        signo = '-' if c < 0 else '+'
        terminos.append((signo, cuerpo))

    if not terminos:
        return '0'

    signo, cuerpo = terminos[0]
    texto = ('-' if signo == '-' else '') + cuerpo
    for signo, cuerpo in terminos[1:]:
        texto += f' {signo} {cuerpo}'
    return texto


# ---------------------------------------------------------------------------
# Muestreo para las gráficas
# ---------------------------------------------------------------------------

def _evaluar_o_none(f, x):
    try:
        return f(x)
    except ErrorFuncion:
        return None


def _muestrear(f, xs, ys, pesos, a, b):
    """Puntos de f(x) y P(x) en [a, b]. Si f no está definida en un punto
    (p. ej. log(x) con x ≤ 0) esa muestra va como null para cortar la línea."""
    puntos_f, puntos_p = [], []
    error_maximo = None

    for k in range(MUESTRAS_GRAFICA + 1):
        x = b if k == MUESTRAS_GRAFICA else a + (b - a) * k / MUESTRAS_GRAFICA
        p = evaluar_polinomio(xs, ys, pesos, x)
        fx = _evaluar_o_none(f, x)

        puntos_p.append({'x': x, 'y': p} if math.isfinite(p) else None)
        puntos_f.append({'x': x, 'y': fx} if fx is not None else None)

        if fx is not None and math.isfinite(p):
            diferencia = abs(fx - p)
            if error_maximo is None or diferencia > error_maximo:
                error_maximo = diferencia

    return puntos_f, puntos_p, error_maximo


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        a = _numero(datos.get('a'), 'Punto inicial a')
        b = _numero(datos.get('b'), 'Punto final b')
        if a >= b:
            raise ErrorLagrange('El punto inicial a debe ser menor que el punto final b.')

        cantidad = _leer_cantidad_puntos(datos.get('puntos'))
        f = crear_funcion(datos.get('funcion'))

        xs, h = _nodos_equiespaciados(a, b, cantidad)
        ys = [f(x) for x in xs]
        pesos = _pesos(xs)

        coeficientes = calcular_coeficientes(xs, ys)
        polinomio = _formatear_polinomio(coeficientes)
        puntos_f, puntos_p, error_maximo = _muestrear(f, xs, ys, pesos, a, b)

        evaluacion = None
        texto_x = datos.get('xEvaluar')
        if texto_x is not None and str(texto_x).strip() != '':
            x_eval = _numero(texto_x, 'Evaluar en x')
            p_eval = evaluar_polinomio(xs, ys, pesos, x_eval)
            f_eval = _evaluar_o_none(f, x_eval)
            evaluacion = {
                'x': x_eval,
                'p': p_eval,
                'f': f_eval,
                'error': abs(f_eval - p_eval) if f_eval is not None else None,
                'fueraDeIntervalo': x_eval < a or x_eval > b,
            }

        grado = cantidad - 1
        mensaje = f'Polinomio de grado {grado} con {cantidad} puntos equiespaciados (h = {h:g}).'

        return jsonify({
            'a': a,
            'b': b,
            'h': h,
            'cantidad': cantidad,
            'grado': grado,
            'nodos': [{'i': i, 'x': xs[i], 'fx': ys[i]} for i in range(cantidad)],
            'coeficientes': coeficientes,
            'polinomio': polinomio,
            'grafica': {'puntosF': puntos_f, 'puntosP': puntos_p},
            'errorMaximo': error_maximo,
            'evaluacion': evaluacion,
            'mensaje': mensaje,
        })
    except (ErrorLagrange, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la interpolación de Lagrange: {error}'}), 500