"""
Método: Derivación numérica (fórmulas de 2, 3 y 5 puntos)

Aproxima f'(x0) usando solo evaluaciones de f en nodos igualmente espaciados
x_i = x_0 + i·h. Las fórmulas salen de derivar el polinomio interpolante de
Lagrange que pasa por los nodos elegidos (o de la serie de Taylor):

    2 puntos  (progresiva):  f'(x0) ≈ (f1 − f0) / h                    E = −h/2 · f''(ξ)      O(h)
    2 puntos  (regresiva):   f'(x1) ≈ (f1 − f0) / h                    E = +h/2 · f''(ξ)      O(h)
    2 puntos  (centrada):    f'(x1) ≈ (f2 − f0) / 2h                   E = −h²/6 · f'''(ξ)    O(h²)
    3 puntos  (extremos):    f'(x0) ≈ (−3f0 + 4f1 − f2) / 2h           E = +h²/3 · f'''(ξ)    O(h²)
    5 puntos  (punto medio): f'(x2) ≈ (f0 − 8f1 + 8f3 − f4) / 12h      E = +h⁴/30 · f⁽⁵⁾(ξ)   O(h⁴)

Hay dos formas de dar los datos:

- "tabla":   el usuario escribe los nodos x_i y los valores f(x_i) (datos
            experimentales o tabulados).
- "funcion": el usuario escribe f(x), un intervalo [a, b] y la cantidad de
            nodos; así se conoce la derivada exacta (simbólica, con
            `comun/derivador.py`) y se puede medir el error real.

El backend devuelve, además de f'(x0):

- la fórmula elegida automáticamente (la de mayor orden que cabe en la tabla)
  o la que pida el usuario, con su sustitución numérica paso a paso,
- la comparación de TODAS las fórmulas aplicables en x0,
- f'(x_i) y f''(x_i) en todos los nodos,
- una estimación del error aunque no se conozca la derivada exacta
  (|D_n − D_(n−1)|, diferencia contra la fórmula de un orden menor),
- (solo con función) extrapolación de Richardson y un estudio del paso h que
  muestra el equilibrio entre error de truncamiento y error de redondeo,
- puntos muestreados para dibujar f(x), la recta tangente numérica y exacta,
  la derivada numérica contra la exacta y la curva error-vs-h.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás.
"""

import math
import re

from flask import Blueprint, jsonify, request

from metodos.comun.derivador import ErrorDerivada, crear_funcion_y_derivada
from metodos.comun.grafica import muestrear
from metodos.comun.parser_funciones import ErrorFuncion, _leer_numero

blueprint = Blueprint('derivacion_numerica', __name__, url_prefix='/api/derivacion-numerica')

METODOS = {
    'auto': 'Automático',
    '2p': '2 puntos',
    '2pc': '2 puntos (centrada)',
    '3p': '3 puntos',
    '5p': '5 puntos',
}

MIN_NODOS = 2
MAX_NODOS_TABLA = 200
MAX_NODOS_FUNCION = 60
MUESTRAS_GRAFICA = 240
TOLERANCIA_ESPACIADO = 1e-6
NIVELES_RICHARDSON = 4
EXPONENTES_H = [k / 2 for k in range(2, 25)]  # h = 10^-1 ... 10^-12


class ErrorDerivacion(Exception):
    """Se lanza cuando la entrada del usuario no es válida."""


def _numero(valor, nombre):
    return _leer_numero(valor, nombre, ErrorDerivacion)


# ---------------------------------------------------------------------------
# Tabla de fórmulas
#   (método, k) -> (coeficientes, divisor [× h], error de truncamiento, orden)
#   k = posición de x0 dentro de la ventana de nodos usada por la fórmula.
# ---------------------------------------------------------------------------

_FORMULAS = {
    ('2p', 0): ([-1, 1], 1, '−h/2 · f″(ξ)', 1),
    ('2p', 1): ([-1, 1], 1, '+h/2 · f″(ξ)', 1),
    ('2pc', 1): ([-1, 0, 1], 2, '−h²/6 · f‴(ξ)', 2),
    ('3p', 0): ([-3, 4, -1], 2, '+h²/3 · f‴(ξ)', 2),
    ('3p', 1): ([-1, 0, 1], 2, '−h²/6 · f‴(ξ)', 2),
    ('3p', 2): ([1, -4, 3], 2, '+h²/3 · f‴(ξ)', 2),
    ('5p', 0): ([-25, 48, -36, 16, -3], 12, '+h⁴/5 · f⁽⁵⁾(ξ)', 4),
    ('5p', 1): ([-3, -10, 18, -6, 1], 12, '−h⁴/20 · f⁽⁵⁾(ξ)', 4),
    ('5p', 2): ([1, -8, 0, 8, -1], 12, '+h⁴/30 · f⁽⁵⁾(ξ)', 4),
    ('5p', 3): ([-1, 6, -18, 10, 3], 12, '−h⁴/20 · f⁽⁵⁾(ξ)', 4),
    ('5p', 4): ([3, -16, 36, -48, 25], 12, '+h⁴/5 · f⁽⁵⁾(ξ)', 4),
}

_NOMBRES = {'2p': '2 puntos', '2pc': '2 puntos', '3p': '3 puntos', '5p': '5 puntos'}

_POSICION = {
    ('2p', 0): 'progresiva', ('2p', 1): 'regresiva', ('2pc', 1): 'centrada',
    ('3p', 0): 'extremo izquierdo', ('3p', 1): 'punto medio', ('3p', 2): 'extremo derecho',
    ('5p', 0): 'extremo izquierdo', ('5p', 1): 'interior izquierdo', ('5p', 2): 'punto medio',
    ('5p', 3): 'interior derecho', ('5p', 4): 'extremo derecho',
}

_SUBINDICES = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
_SUPERINDICES = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def _sub(numero):
    return str(numero).translate(_SUBINDICES)


def _sup(numero):
    return str(numero).translate(_SUPERINDICES)


def _num6(valor):
    """Número con 6 cifras significativas y sin ceros sobrantes."""
    texto = f'{valor:.6g}'
    return '0' if texto in ('-0', '') else texto


def _finito(valor):
    return valor if valor is not None and math.isfinite(valor) else None


# ---------------------------------------------------------------------------
# Lectura y validación de datos
# ---------------------------------------------------------------------------

def _leer_lista(texto, nombre):
    """'1.0, 1.2  1.4; 1.6' -> [1.0, 1.2, 1.4, 1.6]"""
    partes = [p for p in re.split(r'[\s,;]+', str(texto or '').strip()) if p]
    if not partes:
        raise ErrorDerivacion(f'El campo "{nombre}" no puede estar vacío.')
    return [_numero(p, nombre) for p in partes]


def _nodos_equiespaciados(a, b, cantidad):
    h = (b - a) / (cantidad - 1)
    return [b if i == cantidad - 1 else a + i * h for i in range(cantidad)], h


def _validar_tabla(xs, fs):
    if len(xs) != len(fs):
        raise ErrorDerivacion(
            f'Hay {len(xs)} valores de x y {len(fs)} de f(x): deben ser la misma cantidad.'
        )
    if len(xs) < MIN_NODOS:
        raise ErrorDerivacion(f'Se necesitan al menos {MIN_NODOS} puntos.')
    if len(xs) > MAX_NODOS_TABLA:
        raise ErrorDerivacion(f'Máximo {MAX_NODOS_TABLA} puntos.')

    h = xs[1] - xs[0]
    if h <= 0:
        raise ErrorDerivacion('Los valores de x deben estar en orden creciente (sin repetidos).')
    for i in range(1, len(xs)):
        if abs((xs[i] - xs[i - 1]) - h) > TOLERANCIA_ESPACIADO * abs(h):
            raise ErrorDerivacion(
                f'Los nodos deben estar igualmente espaciados: x{_sub(i)} − x{_sub(i - 1)} = '
                f'{_num6(xs[i] - xs[i - 1])} pero h = x₁ − x₀ = {_num6(h)}.'
            )
    return h


def _buscar_indice(xs, x0, h, ajustar):
    """Índice del nodo x0. Con `ajustar` toma el nodo más cercano (modo función)."""
    cercano = min(range(len(xs)), key=lambda i: abs(xs[i] - x0))
    if abs(xs[cercano] - x0) <= TOLERANCIA_ESPACIADO * h:
        return cercano, False
    if ajustar:
        return cercano, True
    nodos = ', '.join(_num6(x) for x in xs[:12]) + (' …' if len(xs) > 12 else '')
    raise ErrorDerivacion(f'x₀ = {_num6(x0)} no es uno de los nodos de la tabla. Nodos: {nodos}.')


# ---------------------------------------------------------------------------
# Núcleo numérico
# ---------------------------------------------------------------------------

def _ventana(i, n_nodos, n):
    """Posición k de x_i dentro de una ventana de n nodos lo más centrada posible."""
    inicio = min(max(i - n // 2, 0), n_nodos - n)
    return i - inicio


def _formula_auto(i, n_nodos):
    """Fórmula de mayor orden que cabe en la tabla para el nodo i."""
    if n_nodos >= 5:
        return '5p', _ventana(i, n_nodos, 5)
    if n_nodos >= 3:
        return '3p', _ventana(i, n_nodos, 3)
    return '2p', (0 if i < n_nodos - 1 else 1)


def _formula_inferior(clave, i, n_nodos):
    """Fórmula de un orden menor: sirve para estimar el error sin conocer f'."""
    if clave == '5p' and n_nodos >= 3:
        return '3p', _ventana(i, n_nodos, 3)
    if clave == '3p':
        return ('2pc', 1) if 0 < i < n_nodos - 1 else ('2p', 0 if i < n_nodos - 1 else 1)
    return None


def _calcular(fs, h, i, clave, k):
    """Aplica la fórmula (clave, k) en el nodo i. Devuelve (valor, numerador, inicio de ventana)."""
    if (clave, k) not in _FORMULAS:
        raise ErrorDerivacion(f'La posición k = {k} no existe para el método {METODOS.get(clave, clave)}.')
    coef, divisor, _, _ = _FORMULAS[(clave, k)]
    inicio = i - k
    if inicio < 0 or inicio + len(coef) > len(fs):
        raise ErrorDerivacion(
            f'La fórmula de {_NOMBRES[clave]} ({_POSICION[(clave, k)]}) necesita nodos que no están en la tabla.'
        )
    numerador = sum(c * fs[inicio + j] for j, c in enumerate(coef))
    return numerador / (divisor * h), numerador, inicio


def _elegir_formula(metodo, k, i, n_nodos):
    if metodo == 'auto':
        return _formula_auto(i, n_nodos)
    if metodo == '2pc':
        return '2pc', 1
    if k is not None:
        return metodo, k
    if metodo == '2p':
        return '2p', (0 if i < n_nodos - 1 else 1)
    return metodo, _ventana(i, n_nodos, 3 if metodo == '3p' else 5)


def _termino(c, j, primero):
    magnitud = abs(c)
    cuerpo = f'f{_sub(j)}' if magnitud == 1 else f'{magnitud}·f{_sub(j)}'
    if primero:
        return ('−' if c < 0 else '') + cuerpo
    return f' {"−" if c < 0 else "+"} {cuerpo}'


def _aplicar(xs, fs, h, i, clave, k, exacta=None):
    """Resultado completo de una fórmula en el nodo i (valor, errores, procedimiento)."""
    valor, numerador, inicio = _calcular(fs, h, i, clave, k)
    coef, divisor, error_formula, orden = _FORMULAS[(clave, k)]

    activos = [(j, c) for j, c in enumerate(coef) if c != 0]
    simbolica = ''.join(_termino(c, j, n == 0) for n, (j, c) in enumerate(activos))
    sustitucion = ' + '.join(f'({c})({_num6(fs[inicio + j])})' for j, c in activos).replace('+ (-', '+ (−')
    divisor_h = f'{divisor}h' if divisor > 1 else 'h'
    denominador = divisor * h

    formulas = [
        f"f′(x{_sub(k)}) ≈ 1/({divisor_h}) · [{simbolica}]",
        f'          = 1/{_num6(denominador)} · [{sustitucion}]',
        f'          = {_num6(numerador)} / {_num6(denominador)}',
        f'          = {valor:.6f}',
    ]

    formulas = [linea.replace('-', '−') for linea in formulas]  # un solo tipo de signo menos

    resultado = {
        'clave': clave,
        'k': k,
        'indice': i,
        'inicio': inicio,
        'metodo': _NOMBRES[clave],
        'posicion': _POSICION[(clave, k)],
        'valor': valor,
        'orden': orden,
        'errorFormula': error_formula,
        'coeficientes': coef,
        'divisor': divisor,
        'numerador': numerador,
        'formulas': formulas,
        'errorEstimado': None,
        'errorReal': None,
    }

    inferior = _formula_inferior(clave, i, len(fs))
    if inferior:
        try:
            resultado['errorEstimado'] = abs(valor - _calcular(fs, h, i, *inferior)[0])
        except ErrorDerivacion:
            pass
    if exacta is not None:
        resultado['errorReal'] = abs(exacta - valor)
    return resultado


def _comparar(xs, fs, h, i, exacta):
    """Todas las fórmulas posibles en x_i, de mayor a menor orden."""
    resultados = []
    for (clave, k) in _FORMULAS:
        try:
            resultados.append(_aplicar(xs, fs, h, i, clave, k, exacta))
        except ErrorDerivacion:
            continue
    resultados.sort(key=lambda r: (-r['orden'], r['errorReal'] if r['errorReal'] is not None else 0.0))
    return resultados


def _segunda_derivada(fs, h, i):
    """f''(x_i): centrada de 3 puntos en el interior; de 4 puntos en los extremos. O(h²)."""
    n = len(fs)
    if 0 < i < n - 1:
        return (fs[i - 1] - 2 * fs[i] + fs[i + 1]) / (h * h)
    if n >= 4 and i == 0:
        return (2 * fs[0] - 5 * fs[1] + 4 * fs[2] - fs[3]) / (h * h)
    if n >= 4 and i == n - 1:
        return (2 * fs[-1] - 5 * fs[-2] + 4 * fs[-3] - fs[-4]) / (h * h)
    return None


# ---------------------------------------------------------------------------
# Extras que necesitan la función f(x)
# ---------------------------------------------------------------------------

def _central_2p(f, x0, h):
    return (f(x0 + h) - f(x0 - h)) / (2 * h)


def _central_5p(f, x0, h):
    return (f(x0 - 2 * h) - 8 * f(x0 - h) + 8 * f(x0 + h) - f(x0 + 2 * h)) / (12 * h)


def _richardson(f, x0, h, exacta):
    """Tabla de Richardson sobre la diferencia centrada: R(k,j) elimina el término h^(2j)."""
    R = []
    for k in range(NIVELES_RICHARDSON):
        paso = h / 2 ** k
        fila = [_central_2p(f, x0, paso)]
        for j in range(1, k + 1):
            fila.append(fila[j - 1] + (fila[j - 1] - R[k - 1][j - 1]) / (4 ** j - 1))
        R.append(fila)

    columnas = ['h', 'D(h) · O(h²)'] + [f'R(k,{j}) · O(h{_sup(2 * j + 2)})' for j in range(1, NIVELES_RICHARDSON)]
    if exacta is not None:
        columnas.append('Error de R(k,k)')

    filas, resaltar = [], []
    for k, fila_r in enumerate(R):
        fila = [h / 2 ** k] + [fila_r[j] if j <= k else None for j in range(NIVELES_RICHARDSON)]
        if exacta is not None:
            fila.append(abs(exacta - fila_r[k]))
        filas.append(fila)
        resaltar.append([k, k + 1])

    return {
        'titulo': 'Extrapolación de Richardson',
        'descripcion': (
            'Se parte de la diferencia centrada con h, h/2, h/4, … y cada columna elimina un término más '
            'del error: R(k,j) = R(k,j−1) + [R(k,j−1) − R(k−1,j−1)] / (4ʲ − 1). '
            'La diagonal (resaltada) es la mejor aproximación de cada fila.'
        ),
        'columnas': columnas,
        'filas': filas,
        'resaltar': resaltar,
        'nota': f'Mejor valor extrapolado: f′(x₀) ≈ {R[-1][-1]:.8f}',
    }, R[-1][-1]


def _analisis_h(f, x0, exacta):
    """Error contra h en escala logarítmica: truncamiento (baja con h) + redondeo (sube al achicar h)."""
    metodos = [
        ('adelante', '2 puntos progresiva', lambda h: (f(x0 + h) - f(x0)) / h),
        ('centrada', '2 puntos centrada', lambda h: _central_2p(f, x0, h)),
        ('cinco', '5 puntos centrada', lambda h: _central_5p(f, x0, h)),
    ]
    series = {clave: [] for clave, _, _ in metodos}
    mejores = {}
    filas = []

    for exponente in EXPONENTES_H:
        h = 10 ** (-exponente)
        fila = [h]
        for clave, _, calcular in metodos:
            try:
                error = abs(exacta - calcular(h))
            except (ErrorFuncion, ZeroDivisionError, OverflowError):
                error = None
            fila.append(error)
            if error is not None and math.isfinite(error):
                series[clave].append({'x': -exponente, 'y': math.log10(max(error, 1e-17))})
                if clave not in mejores or error < mejores[clave][1]:
                    mejores[clave] = (h, error)
        filas.append(fila)

    optimos = [
        {'metodo': nombre, 'h': mejores[clave][0], 'error': mejores[clave][1]}
        for clave, nombre, _ in metodos if clave in mejores
    ]
    texto_optimos = ' · '.join(
        f"{o['metodo']}: h ≈ {o['h']:.0e} (error {o['error']:.1e})" for o in optimos
    )
    seccion = {
        'titulo': 'Análisis del paso h',
        'descripcion': (
            'Achicar h reduce el error de truncamiento, pero por debajo de cierto valor domina el error de '
            'redondeo (cancelación al restar números casi iguales) y el error vuelve a subir. '
            'El mejor h es el del mínimo de cada columna.'
        ),
        'columnas': ['h', 'Error 2 pts progresiva', 'Error 2 pts centrada', 'Error 5 pts centrada'],
        'filas': filas,
        'nota': f'Mejor h observado — {texto_optimos}' if texto_optimos else None,
    }
    return seccion, series, optimos


# ---------------------------------------------------------------------------
# Secciones del procedimiento paso a paso (formato de js/tabla-pasos.js)
# ---------------------------------------------------------------------------

def _seccion_datos(xs, fs, h, i, modo):
    filas = [[n, xs[n], fs[n]] for n in range(len(xs))]
    origen = 'tabla ingresada' if modo == 'tabla' else 'f(x) evaluada en los nodos'
    return {
        'titulo': '1. Datos y paso h',
        'descripcion': (
            f'Nodos igualmente espaciados ({origen}) con h = xᵢ₊₁ − xᵢ = {_num6(h)}. '
            f'Se deriva en x{_sub(i)} = {_num6(xs[i])} (fila resaltada).'
        ),
        'columnas': ['i', 'xᵢ', 'fᵢ = f(xᵢ)'],
        'filas': filas,
        'resaltar': [[i, 0], [i, 1], [i, 2]],
    }


def _seccion_formula(xs, fs, h, principal):
    inicio, coef = principal['inicio'], principal['coeficientes']
    filas = [
        [j, xs[inicio + j], fs[inicio + j], c, c * fs[inicio + j]]
        for j, c in enumerate(coef)
    ]
    n = len(coef)
    nota = (
        f'Error de truncamiento: E = {principal["errorFormula"]}, con ξ entre x{_sub(inicio)} y '
        f'x{_sub(inicio + n - 1)}. Orden de precisión O(h{_sup(principal["orden"])}).'
    )
    return {
        'titulo': f'2. Fórmula de {principal["metodo"]} ({principal["posicion"]})',
        'descripcion': (
            'Se usan los nodos de la ventana (f₀ es el primero de ellos). Cada fᵢ se multiplica por su '
            'coeficiente cᵢ; la suma de la última columna se divide entre el divisor de la fórmula por h.'
        ),
        'formulas': principal['formulas'],
        'columnas': ['j', 'xⱼ', 'fⱼ', 'cⱼ', 'cⱼ·fⱼ'],
        'filas': filas,
        'resaltar': [[j, 4] for j in range(n) if coef[j] != 0],
        'nota': nota,
    }


def _seccion_comparacion(comparacion, principal, tiene_exacta):
    columnas = ['Fórmula', 'Posición', "f′(x₀)", 'Orden', 'Error de truncamiento']
    columnas.append('Error real' if tiene_exacta else '|Δ| vs. elegida')

    filas, resaltar = [], []
    for n, r in enumerate(comparacion):
        diferencia = r['errorReal'] if tiene_exacta else abs(r['valor'] - principal['valor'])
        filas.append([r['metodo'], r['posicion'], f"{r['valor']:.6f}", f"O(h{_sup(r['orden'])})",
                      r['errorFormula'], f'{diferencia:.3e}'])
        if r['clave'] == principal['clave'] and r['k'] == principal['k']:
            resaltar.extend([[n, c] for c in range(len(columnas))])

    return {
        'titulo': '3. Comparación de todas las fórmulas aplicables',
        'descripcion': (
            'Mismas evaluaciones de f, distintas fórmulas. Con la derivada exacta se muestra el error real; '
            'si no se conoce, la diferencia contra la fórmula elegida.'
        ),
        'columnas': columnas,
        'filas': filas,
        'resaltar': resaltar,
    }


def _seccion_nodos(filas_nodos, tiene_exacta):
    columnas = ['i', 'xᵢ', 'fᵢ', "f′(xᵢ)", 'Fórmula usada', "f″(xᵢ)"]
    if tiene_exacta:
        columnas += ["f′ exacta", 'Error']
    filas = []
    for nodo in filas_nodos:
        fila = [nodo['i'], nodo['x'], nodo['fx'], nodo['derivada'], nodo['formula'], nodo['segunda']]
        if tiene_exacta:
            fila += [nodo['exacta'], nodo['error']]
        filas.append(fila)
    return {
        'titulo': '4. Derivada en todos los nodos',
        'descripcion': (
            "En cada nodo se usa la fórmula de mayor orden que cabe en la tabla (centrada en el interior, "
            "progresiva/regresiva en los bordes). f″ se obtiene con la diferencia de 3 puntos "
            "(f₋₁ − 2f₀ + f₁)/h², de 4 puntos en los extremos."
        ),
        'columnas': columnas,
        'filas': filas,
    }


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def _recta(x0, y0, pendiente, ancho):
    return [{'x': x0 - ancho, 'y': y0 - pendiente * ancho}, {'x': x0 + ancho, 'y': y0 + pendiente * ancho}]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        modo = str(datos.get('modo') or 'tabla').strip().lower()
        if modo not in ('tabla', 'funcion'):
            raise ErrorDerivacion('Modo no válido. Elige datos tabulados o función f(x).')

        metodo = str(datos.get('metodo') or 'auto').strip().lower()
        if metodo not in METODOS:
            raise ErrorDerivacion('Método no válido. Elige Automático, 2, 3 o 5 puntos.')

        k_texto = datos.get('k')
        k = None
        if k_texto is not None and str(k_texto).strip() not in ('', 'auto'):
            k = int(_numero(k_texto, 'Posición de x₀'))

        f = f_prima = None
        exacta = None
        aviso = None

        if modo == 'tabla':
            xs = _leer_lista(datos.get('xs'), 'Valores de x')
            fs = _leer_lista(datos.get('fs'), 'Valores de f(x)')
            h = _validar_tabla(xs, fs)
            if str(datos.get('exacto') or '').strip() != '':
                exacta = _numero(datos.get('exacto'), "f′(x₀) exacta")
            if str(datos.get('x0') or '').strip() == '':
                raise ErrorDerivacion('Escribe el nodo x₀ donde quieres derivar.')
            x0 = _numero(datos.get('x0'), 'Nodo x₀')
            i, _ = _buscar_indice(xs, x0, h, ajustar=False)
        else:
            a = _numero(datos.get('a'), 'Punto inicial a')
            b = _numero(datos.get('b'), 'Punto final b')
            if a >= b:
                raise ErrorDerivacion('El punto inicial a debe ser menor que el punto final b.')
            cantidad_numero = _numero(datos.get('puntos'), 'Número de nodos')
            if not float(cantidad_numero).is_integer() or not MIN_NODOS <= cantidad_numero <= MAX_NODOS_FUNCION:
                raise ErrorDerivacion(f'El número de nodos debe ser un entero entre {MIN_NODOS} y {MAX_NODOS_FUNCION}.')
            cantidad = int(cantidad_numero)

            texto_funcion = datos.get('funcion')
            try:
                f, f_prima = crear_funcion_y_derivada(texto_funcion)
            except ErrorDerivada as error:
                from metodos.comun.parser_funciones import crear_funcion
                f = crear_funcion(texto_funcion)
                aviso = f'No se pudo derivar f(x) simbólicamente ({error}); se omiten las comparaciones con la derivada exacta.'

            xs, h = _nodos_equiespaciados(a, b, cantidad)
            fs = [f(x) for x in xs]

            if str(datos.get('x0') or '').strip() == '':
                i, ajustado = cantidad // 2, False
            else:
                i, ajustado = _buscar_indice(xs, _numero(datos.get('x0'), 'Nodo x₀'), h, ajustar=True)
            if ajustado:
                aviso = (aviso + ' ' if aviso else '') + f'x₀ se ajustó al nodo más cercano: {_num6(xs[i])}.'
            if f_prima is not None:
                exacta = f_prima(xs[i])

        x0 = xs[i]
        clave, kk = _elegir_formula(metodo, k, i, len(xs))
        principal = _aplicar(xs, fs, h, i, clave, kk, exacta)
        comparacion = _comparar(xs, fs, h, i, exacta)
        tiene_exacta = exacta is not None

        # Derivada en todos los nodos (mejor fórmula en cada uno)
        nodos = []
        for n in range(len(xs)):
            c, kn = _formula_auto(n, len(xs))
            r = _aplicar(xs, fs, h, n, c, kn)
            exacta_n = f_prima(xs[n]) if f_prima is not None else None
            nodos.append({
                'i': n, 'x': xs[n], 'fx': fs[n], 'derivada': r['valor'],
                'formula': f"{r['metodo']} ({r['posicion']})",
                'segunda': _finito(_segunda_derivada(fs, h, n)),
                'exacta': exacta_n,
                'error': abs(exacta_n - r['valor']) if exacta_n is not None else None,
            })

        # Secciones del procedimiento
        secciones = [
            _seccion_datos(xs, fs, h, i, modo),
            _seccion_formula(xs, fs, h, principal),
            _seccion_comparacion(comparacion, principal, tiene_exacta),
            _seccion_nodos(nodos, tiene_exacta),
        ]

        richardson = None
        analisis_h = None
        if f is not None and tiene_exacta:
            try:
                seccion_r, valor_r = _richardson(f, x0, h, exacta)
                secciones.append({**seccion_r, 'titulo': '5. ' + seccion_r['titulo']})
                richardson = {'valor': valor_r, 'error': abs(exacta - valor_r)}
            except ErrorFuncion:
                pass
            seccion_h, series_h, optimos = _analisis_h(f, x0, exacta)
            secciones.append({**seccion_h, 'titulo': '6. ' + seccion_h['titulo']})
            analisis_h = {'series': series_h, 'optimos': optimos}

        # Datos de las gráficas
        ancho_recta = 2 * h
        if modo == 'funcion':
            puntos_f = muestrear(f, xs[0], xs[-1], MUESTRAS_GRAFICA)
            puntos_exacta = muestrear(f_prima, xs[0], xs[-1], MUESTRAS_GRAFICA) if f_prima else None
        else:
            puntos_f = [{'x': xs[n], 'y': fs[n]} for n in range(len(xs))]
            puntos_exacta = None

        grafica = {
            'puntosF': puntos_f,
            'tangenteNumerica': _recta(x0, fs[i], principal['valor'], ancho_recta),
            'tangenteExacta': _recta(x0, fs[i], exacta, ancho_recta) if tiene_exacta else None,
            'nodos': [{'x': xs[n], 'y': fs[n]} for n in range(len(xs))],
            'derivadaNumerica': [{'x': nd['x'], 'y': nd['derivada']} for nd in nodos],
            'derivadaExacta': puntos_exacta,
            'analisisH': analisis_h['series'] if analisis_h else None,
        }

        mensaje = (
            f"Derivación numérica: {principal['metodo']} ({principal['posicion']}) en "
            f"x₀ = {_num6(x0)} con h = {_num6(h)}  →  f′(x₀) ≈ {principal['valor']:.6f}"
        )

        return jsonify({
            'modo': modo,
            'metodo': principal['clave'],
            'h': h,
            'cantidad': len(xs),
            'x0': x0,
            'indice': i,
            'exacta': exacta,
            'principal': {k_: v for k_, v in principal.items() if k_ not in ('formulas', 'numerador', 'inicio')},
            'comparacion': [
                {k_: v for k_, v in r.items() if k_ not in ('formulas', 'numerador')} for r in comparacion
            ],
            'nodos': nodos,
            'richardson': richardson,
            'optimos': analisis_h['optimos'] if analisis_h else None,
            'pasos': secciones,
            'grafica': grafica,
            'aviso': aviso,
            'mensaje': mensaje,
        })
    except (ErrorDerivacion, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en la derivación numérica: {error}'}), 500