"""
Método: Interpolación polinomial (Lagrange, Neville y Diferencias divididas)

Dada una función f(x), un intervalo [a, b] y una cantidad de puntos N, se
toman N nodos equiespaciados x0 = a, ..., x(N-1) = b, se calculan los
valores f(xi) y se obtiene el polinomio de grado N-1 que pasa por todos
ellos. El polinomio interpolante es único; lo que cambia entre métodos es
cómo se arma paso a paso:

    Lagrange:               P(x) = Σ f(xi) · Li(x),   Li(x) = Π (x - xj) / (xi - xj),  j ≠ i
    Diferencias divididas:  P(x) = f[x0] + f[x0,x1](x-x0) + f[x0,x1,x2](x-x0)(x-x1) + ...
    Neville:                Qi,j = [(x - x(i-j))·Qi,j-1 - (x - xi)·Qi-1,j-1] / (xi - x(i-j))

El backend devuelve:
- el polinomio expandido (coeficientes calculados en aritmética exacta con
  fracciones, para evitar errores de cancelación al expandir),
- la forma propia del método (Newton / Lagrange) cuando aplica,
- la tabla del procedimiento paso a paso del método elegido,
- puntos muestreados de f(x) y de P(x) para dibujar ambas gráficas,
- el error máximo |f(x) - P(x)| observado en las muestras,
- opcionalmente, la evaluación de P en un punto x* indicado por el usuario
  (obligatorio para Neville).

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math
from fractions import Fraction

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, _leer_numero, crear_funcion

blueprint = Blueprint('lagrange', __name__, url_prefix='/api/lagrange')

METODOS = {
    'lagrange': 'Lagrange',
    'neville': 'Neville',
    'diferencias': 'Diferencias divididas',
}

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
# Procedimiento paso a paso de cada método
# ---------------------------------------------------------------------------

_SUBINDICES = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
_ORDINALES = {1: '1ra', 2: '2da', 3: '3ra', 4: '4ta', 5: '5ta', 6: '6ta', 7: '7ma', 8: '8va', 9: '9na', 10: '10ma'}


def _sub(numero):
    return str(numero).translate(_SUBINDICES)


def _num4(valor):
    """Número con hasta 4 decimales y sin ceros sobrantes (como en el Excel)."""
    texto = f'{round(valor, 4):.4f}'.rstrip('0').rstrip('.')
    return '0' if texto in ('-0', '') else texto


def _factor(xi, escala):
    """Factor (x - xi) escrito como (x+3), (x-1) o x cuando xi = 0."""
    if abs(xi) <= 1e-12 * escala:
        return 'x'
    return f'(x+{abs(xi):.6g})' if xi < 0 else f'(x-{xi:.6g})'


def _escala(xs):
    return max((abs(x) for x in xs), default=1.0) or 1.0


def _denominadores(xs):
    """Π (xi - xj), j ≠ i, para cada nodo."""
    resultado = []
    for i, xi in enumerate(xs):
        producto = 1.0
        for j, xj in enumerate(xs):
            if j != i:
                producto *= xi - xj
        resultado.append(producto)
    return resultado


def _paso_lagrange(xs, ys, x_eval):
    n = len(xs)
    escala = _escala(xs)
    denominadores = _denominadores(xs)

    columnas = ['i', 'xᵢ', 'fᵢ = f(xᵢ)', 'Π (xᵢ − xⱼ), j ≠ i']
    pesos_eval = None
    if x_eval is not None:
        etiqueta_x = f'{x_eval:.6g}'
        columnas += [f'Lᵢ({etiqueta_x})', f'fᵢ·Lᵢ({etiqueta_x})']
        pesos_eval = []
        for i in range(n):
            numerador = 1.0
            for j in range(n):
                if j != i:
                    numerador *= x_eval - xs[j]
            pesos_eval.append(numerador / denominadores[i])

    filas = []
    for i in range(n):
        fila = [i, xs[i], ys[i], denominadores[i]]
        if pesos_eval is not None:
            fila += [pesos_eval[i], ys[i] * pesos_eval[i]]
        filas.append(fila)

    formulas = []
    if n <= 8:
        for i in range(n):
            numerador = ''.join(_factor(xs[j], escala) for j in range(n) if j != i)
            formulas.append(f'L{_sub(i)}(x) = {numerador} / {denominadores[i]:.6g}')

    valor = None
    resumen = None
    resaltar = []
    if pesos_eval is not None:
        valor = sum(ys[i] * pesos_eval[i] for i in range(n))
        resumen = f'P({x_eval:.6g}) = Σ fᵢ·Lᵢ({x_eval:.6g}) = {valor:.6f}'
        resaltar = [[i, len(columnas) - 1] for i in range(n)]

    return {
        'tipo': 'lagrange',
        'titulo': 'Polinomios base de Lagrange',
        'descripcion': 'Lᵢ(x) vale 1 en xᵢ y 0 en los demás nodos; P(x) = Σ fᵢ·Lᵢ(x).',
        'formulas': formulas,
        'columnas': columnas,
        'filas': filas,
        'resaltar': resaltar,
        'resumen': resumen,
    }, valor


def _forma_lagrange(ys):
    terminos = [f'{_num4(y)}·L{_sub(i)}(x)' for i, y in enumerate(ys)]
    return 'P(x) = ' + ' + '.join(terminos).replace('+ -', '− ')


def _diferencias_divididas(xs, ys):
    """tabla[j][i] = f[xi, ..., x(i+j)]."""
    n = len(xs)
    tabla = [list(ys)]
    for j in range(1, n):
        previa = tabla[-1]
        tabla.append([(previa[i + 1] - previa[i]) / (xs[i + j] - xs[i]) for i in range(n - j)])
    return tabla


def _ordinal(k):
    return _ORDINALES.get(k, f'{k}.ª')


def _forma_newton(xs, coeficientes):
    escala = _escala(xs)
    texto = _num4(coeficientes[0])
    for k in range(1, len(coeficientes)):
        factores = ''.join(_factor(xs[m], escala) for m in range(k))
        texto += f' + ({_num4(coeficientes[k])}){factores}'
    return 'P(x) = ' + texto


def _paso_diferencias(xs, ys, x_eval):
    n = len(xs)
    tabla = _diferencias_divididas(xs, ys)
    coeficientes = [tabla[j][0] for j in range(n)]

    columnas = ['xᵢ', 'fᵢ = f[xᵢ]'] + [f'{_ordinal(k)} Dif' for k in range(1, n)]
    filas = []
    for i in range(n):
        fila = [xs[i]]
        for j in range(n):
            fila.append(tabla[j][i] if i + j < n else None)
        filas.append(fila)

    valor = None
    resumen = None
    if x_eval is not None:
        valor = coeficientes[-1]
        for k in range(n - 2, -1, -1):
            valor = valor * (x_eval - xs[k]) + coeficientes[k]
        resumen = f'P({x_eval:.6g}) = {valor:.6f}'

    return {
        'tipo': 'diferencias',
        'titulo': 'Tabla de diferencias divididas',
        'descripcion': (
            'f[xᵢ,…,xᵢ₊ⱼ] = (f[xᵢ₊₁,…,xᵢ₊ⱼ] − f[xᵢ,…,xᵢ₊ⱼ₋₁]) / (xᵢ₊ⱼ − xᵢ). '
            'Los coeficientes del polinomio de Newton son los de la primera fila (resaltados).'
        ),
        'formulas': [],
        'columnas': columnas,
        'filas': filas,
        'resaltar': [[0, j + 1] for j in range(n)],
        'resumen': resumen,
    }, valor, _forma_newton(xs, coeficientes)


def _paso_neville(xs, ys, x_eval):
    n = len(xs)
    Q = [[None] * n for _ in range(n)]
    for i in range(n):
        Q[i][0] = ys[i]
    for i in range(1, n):
        for j in range(1, i + 1):
            Q[i][j] = ((x_eval - xs[i - j]) * Q[i][j - 1] - (x_eval - xs[i]) * Q[i - 1][j - 1]) / (xs[i] - xs[i - j])

    etiqueta_x = f'{x_eval:.6g}'
    columnas = ['xᵢ', 'fᵢ = Qᵢ,₀']
    columnas += [f'Qᵢ,{_sub(j)}' for j in range(1, n - 1)]
    if n > 1:
        columnas.append(f'Qᵢ,{_sub(n - 1)} (P({etiqueta_x}))')

    filas = []
    for i in range(n):
        fila = [xs[i]]
        for j in range(n):
            fila.append(Q[i][j] if j <= i else None)
        filas.append(fila)

    valor = Q[n - 1][n - 1]
    return {
        'tipo': 'neville',
        'titulo': 'Tabla de Neville',
        'descripcion': (
            f'Qᵢ,ⱼ = [(x − xᵢ₋ⱼ)·Qᵢ,ⱼ₋₁ − (x − xᵢ)·Qᵢ₋₁,ⱼ₋₁] / (xᵢ − xᵢ₋ⱼ), con x = {etiqueta_x}. '
            'El valor buscado es el último de la tabla (resaltado). Neville no construye el polinomio: '
            'la expresión y la gráfica son del mismo polinomio interpolante.'
        ),
        'formulas': [],
        'columnas': columnas,
        'filas': filas,
        'resaltar': [[n - 1, n]],
        'resumen': f'P({etiqueta_x}) = Q{_sub(n - 1)},{_sub(n - 1)} = {valor:.6f}',
    }, valor


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
        metodo = str(datos.get('metodo') or 'lagrange').strip().lower()
        if metodo not in METODOS:
            raise ErrorLagrange('Método no válido. Elige Lagrange, Neville o Diferencias divididas.')

        f = crear_funcion(datos.get('funcion'))

        texto_x = datos.get('xEvaluar')
        x_eval = None
        if texto_x is not None and str(texto_x).strip() != '':
            x_eval = _numero(texto_x, 'Evaluar en x')
        elif metodo == 'neville':
            raise ErrorLagrange('El método de Neville necesita el valor x en el que se evalúa P(x).')

        xs, h = _nodos_equiespaciados(a, b, cantidad)
        ys = [f(x) for x in xs]
        pesos = _pesos(xs)

        coeficientes = calcular_coeficientes(xs, ys)
        polinomio = _formatear_polinomio(coeficientes)
        puntos_f, puntos_p, error_maximo = _muestrear(f, xs, ys, pesos, a, b)

        # Procedimiento propio de cada método
        forma_metodo = None
        if metodo == 'lagrange':
            pasos, valor_metodo = _paso_lagrange(xs, ys, x_eval)
            forma_metodo = {'etiqueta': 'Forma de Lagrange', 'texto': _forma_lagrange(ys)}
        elif metodo == 'diferencias':
            pasos, valor_metodo, texto_newton = _paso_diferencias(xs, ys, x_eval)
            forma_metodo = {'etiqueta': 'Forma de Newton (diferencias divididas)', 'texto': texto_newton}
        else:
            pasos, valor_metodo = _paso_neville(xs, ys, x_eval)

        evaluacion = None
        if x_eval is not None:
            f_eval = _evaluar_o_none(f, x_eval)
            evaluacion = {
                'x': x_eval,
                'p': valor_metodo,
                'f': f_eval,
                'error': abs(f_eval - valor_metodo) if f_eval is not None else None,
                'fueraDeIntervalo': x_eval < a or x_eval > b,
            }

        grado = cantidad - 1
        mensaje = (
            f'{METODOS[metodo]}: polinomio de grado {grado} con {cantidad} puntos '
            f'equiespaciados (h = {h:g}).'
        )

        return jsonify({
            'metodo': metodo,
            'a': a,
            'b': b,
            'h': h,
            'cantidad': cantidad,
            'grado': grado,
            'nodos': [{'i': i, 'x': xs[i], 'fx': ys[i]} for i in range(cantidad)],
            'coeficientes': coeficientes,
            'polinomio': polinomio,
            'formaMetodo': forma_metodo,
            'pasos': pasos,
            'grafica': {'puntosF': puntos_f, 'puntosP': puntos_p},
            'errorMaximo': error_maximo,
            'evaluacion': evaluacion,
            'mensaje': mensaje,
        })
    except (ErrorLagrange, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la interpolación de Lagrange: {error}'}), 500