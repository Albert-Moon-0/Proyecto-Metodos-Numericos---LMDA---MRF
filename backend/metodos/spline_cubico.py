"""
Método: Spline cúbico natural

Dada una función f(x), un intervalo [a, b] y una cantidad de puntos N, se
toman N nodos equiespaciados x0 = a, ..., x(N-1) = b, se calculan los
valores aj = f(xj) y se construye, en cada tramo [xj, xj+1], un polinomio
cúbico

    Sj(x) = aj + bj (x - xj) + cj (x - xj)^2 + dj (x - xj)^3

que pasa por los puntos y es continuo junto con S' y S'' en los nodos
interiores. Frontera natural: S''(x0) = S''(xn) = 0 (c0 = cn = 0).

Procedimiento (el mismo de la hoja de Excel):
    hj = xj+1 - xj
    Sistema tridiagonal  A·c = B
        fila 0 y fila n:  1 en la diagonal, B = 0
        filas interiores: [hj-1, 2(hj-1 + hj), hj]
                          Bj = 3/hj·(aj+1 - aj) - 3/hj-1·(aj - aj-1)
    bj = (aj+1 - aj)/hj - hj/3·(2cj + cj+1)
    dj = (cj+1 - cj) / (3hj)

El backend devuelve las secciones del procedimiento paso a paso (matriz A,
vector B, tabla de coeficientes y tabla de splines), los puntos muestreados
de f(x) y de cada tramo del spline para graficar, el error máximo
|f(x) - S(x)| observado y, opcionalmente, la evaluación de S en un punto x*.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math
from bisect import bisect_right

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, _leer_numero, crear_funcion

blueprint = Blueprint('spline_cubico', __name__, url_prefix='/api/spline-cubico')

MIN_PUNTOS = 3
# Los splines no oscilan como los polinomios de alto grado, así que se
# permiten más nodos; el tope evita tablas inmanejables.
MAX_PUNTOS = 40
MUESTRAS_F = 300
MAX_PUNTOS_MATRIZ = 12  # por encima de esto la matriz A no se muestra completa

_SUBINDICES = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


class ErrorSpline(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


def _numero(valor, nombre):
    return _leer_numero(valor, nombre, ErrorSpline)


def _leer_cantidad_puntos(valor):
    numero = _numero(valor, 'Número de puntos')
    if not float(numero).is_integer():
        raise ErrorSpline('El número de puntos debe ser un entero.')
    cantidad = int(numero)
    if cantidad < MIN_PUNTOS or cantidad > MAX_PUNTOS:
        raise ErrorSpline(f'El número de puntos debe estar entre {MIN_PUNTOS} y {MAX_PUNTOS}.')
    return cantidad


def _sub(numero):
    return str(numero).translate(_SUBINDICES)


def _num4(valor):
    """Número con hasta 4 decimales y sin ceros sobrantes (como en el Excel)."""
    texto = f'{round(valor, 4):.4f}'.rstrip('0').rstrip('.')
    return '0' if texto in ('-0', '') else texto


def _factor(xj, escala):
    """Factor (x - xj) escrito como (x+3), (x-1) o x cuando xj = 0."""
    if abs(xj) <= 1e-12 * escala:
        return 'x'
    return f'(x+{abs(xj):.6g})' if xj < 0 else f'(x-{xj:.6g})'


# ---------------------------------------------------------------------------
# Cálculo del spline
# ---------------------------------------------------------------------------

def _nodos_equiespaciados(a, b, cantidad):
    h = (b - a) / (cantidad - 1)
    return [b if i == cantidad - 1 else a + i * h for i in range(cantidad)], h


def _vector_b(a, h):
    """B0 = Bn = 0 (frontera natural); Bj = 3/hj (aj+1 - aj) - 3/hj-1 (aj - aj-1)."""
    n = len(h)
    B = [0.0] * (n + 1)
    for j in range(1, n):
        B[j] = (3.0 / h[j]) * (a[j + 1] - a[j]) - (3.0 / h[j - 1]) * (a[j] - a[j - 1])
    return B


def _diagonales(h):
    n = len(h)
    inferior = [0.0] * (n + 1)
    principal = [1.0] * (n + 1)
    superior = [0.0] * (n + 1)
    for j in range(1, n):
        inferior[j] = h[j - 1]
        principal[j] = 2.0 * (h[j - 1] + h[j])
        superior[j] = h[j]
    return inferior, principal, superior


def _matriz_a(h):
    n = len(h)
    inferior, principal, superior = _diagonales(h)
    matriz = [[0.0] * (n + 1) for _ in range(n + 1)]
    for j in range(n + 1):
        matriz[j][j] = principal[j]
        if j > 0:
            matriz[j][j - 1] = inferior[j]
        if j < n:
            matriz[j][j + 1] = superior[j]
    return matriz


def _resolver_tridiagonal(h, B):
    """Resuelve A·c = B con el algoritmo de Thomas (A es diagonal dominante)."""
    n = len(h)
    inferior, principal, superior = _diagonales(h)

    cp = [0.0] * (n + 1)
    dp = [0.0] * (n + 1)
    cp[0] = superior[0] / principal[0]
    dp[0] = B[0] / principal[0]
    for i in range(1, n + 1):
        divisor = principal[i] - inferior[i] * cp[i - 1]
        cp[i] = superior[i] / divisor
        dp[i] = (B[i] - inferior[i] * dp[i - 1]) / divisor

    c = [0.0] * (n + 1)
    c[n] = dp[n]
    for i in range(n - 1, -1, -1):
        c[i] = dp[i] - cp[i] * c[i + 1]
    return c


def _coeficientes(a, h, c):
    n = len(h)
    b = [(a[j + 1] - a[j]) / h[j] - (h[j] / 3.0) * (2.0 * c[j] + c[j + 1]) for j in range(n)]
    d = [(c[j + 1] - c[j]) / (3.0 * h[j]) for j in range(n)]
    return b, d


def _tramo(xs, x):
    """Índice j del tramo [xj, xj+1] que contiene a x (el último incluye a b)."""
    return min(max(bisect_right(xs, x) - 1, 0), len(xs) - 2)


def _evaluar(xs, a, b, c, d, x):
    j = _tramo(xs, x)
    dx = x - xs[j]
    return j, a[j] + dx * (b[j] + dx * (c[j] + dx * d[j]))


# ---------------------------------------------------------------------------
# Secciones del procedimiento paso a paso
# ---------------------------------------------------------------------------

def _seccion_sistema(h, B, cantidad):
    n = len(h)
    descripcion = (
        'Frontera natural: c₀ = cₙ = 0. Fila interior j: [hⱼ₋₁, 2(hⱼ₋₁ + hⱼ), hⱼ] y '
        'Bⱼ = 3/hⱼ·(aⱼ₊₁ − aⱼ) − 3/hⱼ₋₁·(aⱼ − aⱼ₋₁).'
    )

    if cantidad > MAX_PUNTOS_MATRIZ:
        return {
            'titulo': '1. Sistema tridiagonal A·c = B',
            'descripcion': descripcion,
            'columnas': [],
            'filas': [],
            'nota': (
                f'La matriz A es de {cantidad}×{cantidad} y solo tiene 3 diagonales (1 en las esquinas '
                'y [hⱼ₋₁, 2(hⱼ₋₁ + hⱼ), hⱼ] en las filas interiores), por eso no se muestra completa. '
                'Los valores de Bⱼ están en la tabla del paso 2.'
            ),
        }

    matriz = _matriz_a(h)
    columnas = ['j'] + [f'c{_sub(j)}' for j in range(n + 1)] + ['Bⱼ']
    filas = [[j] + matriz[j] + [B[j]] for j in range(n + 1)]
    return {
        'titulo': '1. Sistema tridiagonal A·c = B',
        'descripcion': descripcion,
        'columnas': columnas,
        'filas': filas,
        'resaltar': [[j, n + 2] for j in range(n + 1)],
    }


def _seccion_coeficientes(xs, a, h, B, c, b, d):
    n = len(h)
    columnas = ['j', 'xⱼ', 'aⱼ = f(xⱼ)', 'hⱼ', 'Bⱼ', 'cⱼ', 'bⱼ', 'dⱼ']
    filas = []
    for j in range(n + 1):
        ultimo = j == n
        filas.append([
            j, xs[j], a[j],
            None if ultimo else h[j],
            B[j], c[j],
            None if ultimo else b[j],
            None if ultimo else d[j],
        ])
    return {
        'titulo': '2. Coeficientes de cada tramo',
        'descripcion': (
            'cⱼ es la solución de A·c = B (columna resaltada). '
            'bⱼ = (aⱼ₊₁ − aⱼ)/hⱼ − hⱼ(2cⱼ + cⱼ₊₁)/3 y dⱼ = (cⱼ₊₁ − cⱼ)/(3hⱼ).'
        ),
        'columnas': columnas,
        'filas': filas,
        'resaltar': [[j, 5] for j in range(n + 1)],
    }


def _seccion_splines(xs, a, b, c, d):
    n = len(a) - 1
    filas = []
    for j in range(n):
        filas.append([f'S{_sub(j)}', f'[{xs[j]:.6g}, {xs[j + 1]:.6g}]', a[j], b[j], c[j], d[j]])
    return {
        'titulo': '3. Splines cúbicos por tramo',
        'descripcion': 'Sⱼ(x) = a + b(x − xⱼ) + c(x − xⱼ)² + d(x − xⱼ)³, válido en el intervalo indicado.',
        'columnas': ['Sⱼ', 'Intervalo', 'a', 'b', 'c', 'd'],
        'filas': filas,
    }


def _formulas_splines(xs, a, b, c, d):
    escala = max((abs(x) for x in xs), default=1.0) or 1.0
    lineas = []
    for j in range(len(xs) - 1):
        f = _factor(xs[j], escala)
        lineas.append(
            f'S{_sub(j)}(x) = {_num4(a[j])} + ({_num4(b[j])}){f} + ({_num4(c[j])}){f}² + ({_num4(d[j])}){f}³'
            f',   {xs[j]:.6g} ≤ x ≤ {xs[j + 1]:.6g}'
        )
    return lineas


# ---------------------------------------------------------------------------
# Muestreo para las gráficas
# ---------------------------------------------------------------------------

def _evaluar_o_none(f, x):
    try:
        return f(x)
    except ErrorFuncion:
        return None


def _muestras_f(f, xs, a_c, b_c, c_c, d_c, a, b):
    """Puntos de f(x) en [a, b] (null donde f no está definida) y error máximo |f - S|."""
    puntos = []
    error_maximo = None
    for k in range(MUESTRAS_F + 1):
        x = b if k == MUESTRAS_F else a + (b - a) * k / MUESTRAS_F
        fx = _evaluar_o_none(f, x)
        puntos.append({'x': x, 'y': fx} if fx is not None else None)
        if fx is not None:
            _, s = _evaluar(xs, a_c, b_c, c_c, d_c, x)
            diferencia = abs(fx - s)
            if error_maximo is None or diferencia > error_maximo:
                error_maximo = diferencia
    return puntos, error_maximo


def _muestras_tramos(xs, a, b, c, d):
    """Una lista de puntos por tramo (cada tramo se dibuja como una serie)."""
    n = len(xs) - 1
    por_tramo = min(60, max(14, 360 // n))
    tramos = []
    for j in range(n):
        puntos = []
        for k in range(por_tramo + 1):
            x = xs[j + 1] if k == por_tramo else xs[j] + (xs[j + 1] - xs[j]) * k / por_tramo
            dx = x - xs[j]
            puntos.append({'x': x, 'y': a[j] + dx * (b[j] + dx * (c[j] + dx * d[j]))})
        tramos.append(puntos)
    return tramos


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        x_inicial = _numero(datos.get('a'), 'Punto inicial a')
        x_final = _numero(datos.get('b'), 'Punto final b')
        if x_inicial >= x_final:
            raise ErrorSpline('El punto inicial a debe ser menor que el punto final b.')

        cantidad = _leer_cantidad_puntos(datos.get('puntos'))
        f = crear_funcion(datos.get('funcion'))

        texto_x = datos.get('xEvaluar')
        x_eval = None
        if texto_x is not None and str(texto_x).strip() != '':
            x_eval = _numero(texto_x, 'Evaluar en x')
            if x_eval < x_inicial or x_eval > x_final:
                raise ErrorSpline(
                    f'El spline solo está definido en [{x_inicial:g}, {x_final:g}]; '
                    'elige un valor de x dentro de ese intervalo.'
                )

        xs, paso = _nodos_equiespaciados(x_inicial, x_final, cantidad)
        a = [f(x) for x in xs]
        h = [xs[j + 1] - xs[j] for j in range(cantidad - 1)]

        B = _vector_b(a, h)
        c = _resolver_tridiagonal(h, B)
        b, d = _coeficientes(a, h, c)

        puntos_f, error_maximo = _muestras_f(f, xs, a, b, c, d, x_inicial, x_final)
        tramos_s = _muestras_tramos(xs, a, b, c, d)

        evaluacion = None
        if x_eval is not None:
            j, s_eval = _evaluar(xs, a, b, c, d, x_eval)
            f_eval = _evaluar_o_none(f, x_eval)
            evaluacion = {
                'x': x_eval,
                's': s_eval,
                'f': f_eval,
                'error': abs(f_eval - s_eval) if f_eval is not None else None,
                'tramo': j,
            }

        if not all(math.isfinite(v) for v in c):
            raise ErrorSpline('No se pudo resolver el sistema del spline con estos datos.')

        tramos = cantidad - 1
        mensaje = (
            f'Spline cúbico natural con {cantidad} puntos equiespaciados '
            f'({tramos} tramos, h = {paso:g}).'
        )

        return jsonify({
            'a': x_inicial,
            'b': x_final,
            'h': paso,
            'cantidad': cantidad,
            'tramos': tramos,
            'nodos': [{'i': i, 'x': xs[i], 'fx': a[i]} for i in range(cantidad)],
            'coeficientes': [
                {'j': j, 'a': a[j], 'b': b[j], 'c': c[j], 'd': d[j]} for j in range(tramos)
            ],
            'formulas': _formulas_splines(xs, a, b, c, d),
            'pasos': [
                _seccion_sistema(h, B, cantidad),
                _seccion_coeficientes(xs, a, h, B, c, b, d),
                _seccion_splines(xs, a, b, c, d),
            ],
            'grafica': {'puntosF': puntos_f, 'tramosS': tramos_s},
            'errorMaximo': error_maximo,
            'evaluacion': evaluacion,
            'mensaje': mensaje,
        })
    except (ErrorSpline, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el spline cúbico: {error}'}), 500