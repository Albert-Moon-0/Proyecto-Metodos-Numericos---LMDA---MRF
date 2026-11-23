"""
Método: Runge-Kutta (órdenes 2 a 6) y Runge-Kutta-Fehlberg (RKF45)

Resuelve el problema de valor inicial

    dy/dt = f(t, y),    y(t0) = w0,    t en [t0, tn]

Runge-Kutta de paso fijo
    h = (tn - t0) / n. En cada paso se calculan las pendientes K1, K2, ...
    (las "K" que se reescriben como variables para no repetir la fórmula) y
    w_{i+1} = w_i + (combinación de las K).
    El parámetro `h_en_k` decide la convención:
      - True : K_j = h · f(...)      y   w_{i+1} = w_i + Σ b_j K_j
      - False: K_j = f(...)          y   w_{i+1} = w_i + h Σ b_j K_j

Runge-Kutta-Fehlberg (paso variable)
    Calcula w_i (orden 4) y w~_i (orden 5) con las mismas 6 evaluaciones,
        R = |w~_i - w_i| / h,
        q = (TOL / (2R))^(1/4)  (≈ 0.84 (TOL/R)^(1/4) del libro de Burden),
    y ajusta h: q < 1 reduce el paso, q ≥ 1 lo conserva o lo aumenta.
    Criterio de aceptación (parámetro `criterio`):
      - 'R'  (por defecto): se acepta si R ≤ TOL (Burden).
      - 'q'  : se acepta si q ≥ 1 (equivale a R ≤ TOL/2, más estricto).

Cada método se describe con su tablero de Butcher (c, A, b) con fracciones
exactas; de ahí salen tanto el cálculo como las fórmulas de las K que se
muestran en pantalla, así que no pueden desincronizarse.

Este archivo es independiente del resto de los métodos. La función f(t, y)
se interpreta con crear_funcion_edo de metodos/comun/parser_funciones.py.
"""

import math
from fractions import Fraction as F

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion_edo

blueprint = Blueprint('runge_kutta', __name__, url_prefix='/api/runge_kutta')

LIMITE_SUBINTERVALOS = 5000
LIMITE_INTENTOS_RKF = 5000


class ErrorRungeKutta(Exception):
    """Entrada inválida o fallo numérico del método."""


# ---------------------------------------------------------------------------
# Tableros de Butcher.  a[j] = coeficientes de K_1..K_j para la etapa j+1.
# ---------------------------------------------------------------------------
def _tablero(nombre, orden, c, a, b):
    return {'nombre': nombre, 'orden': orden, 'c': c, 'a': a, 'b': b}


METODOS = {
    'rk2': _tablero(
        'Runge-Kutta orden 2 (Heun)', 2,
        [F(0), F(1)],
        [[], [F(1)]],
        [F(1, 2), F(1, 2)],
    ),
    'rk2m': _tablero(
        'Runge-Kutta orden 2 (punto medio)', 2,
        [F(0), F(1, 2)],
        [[], [F(1, 2)]],
        [F(0), F(1)],
    ),
    'rk3': _tablero(
        'Runge-Kutta orden 3 (Kutta)', 3,
        [F(0), F(1, 2), F(1)],
        [[], [F(1, 2)], [F(-1), F(2)]],
        [F(1, 6), F(4, 6), F(1, 6)],
    ),
    'rk4': _tablero(
        'Runge-Kutta orden 4 (clásico)', 4,
        [F(0), F(1, 2), F(1, 2), F(1)],
        [[], [F(1, 2)], [F(0), F(1, 2)], [F(0), F(0), F(1)]],
        [F(1, 6), F(2, 6), F(2, 6), F(1, 6)],
    ),
    'rk5': _tablero(
        'Runge-Kutta orden 5 (Butcher, 6 etapas)', 5,
        [F(0), F(1, 4), F(1, 4), F(1, 2), F(3, 4), F(1)],
        [
            [],
            [F(1, 4)],
            [F(1, 8), F(1, 8)],
            [F(0), F(0), F(1, 2)],
            [F(3, 16), F(-3, 8), F(3, 8), F(9, 16)],
            [F(-3, 7), F(8, 7), F(6, 7), F(-12, 7), F(8, 7)],
        ],
        [F(7, 90), F(0), F(32, 90), F(12, 90), F(32, 90), F(7, 90)],
    ),
    'rk6': _tablero(
        'Runge-Kutta orden 6 (Butcher, 7 etapas)', 6,
        [F(0), F(1, 3), F(2, 3), F(1, 3), F(1, 2), F(1, 2), F(1)],
        [
            [],
            [F(1, 3)],
            [F(0), F(2, 3)],
            [F(1, 12), F(1, 3), F(-1, 12)],
            [F(-1, 16), F(9, 8), F(-3, 16), F(-3, 8)],
            [F(0), F(9, 8), F(-3, 8), F(-3, 4), F(1, 2)],
            [F(9, 44), F(-9, 11), F(63, 44), F(18, 11), F(0), F(-16, 11)],
        ],
        [F(11, 120), F(0), F(27, 40), F(27, 40), F(-4, 15), F(-4, 15), F(11, 120)],
    ),
}

# Fehlberg 4(5): c, A y las dos filas de pesos (orden 4 -> w, orden 5 -> w~).
RKF = {
    'c': [F(0), F(1, 4), F(3, 8), F(12, 13), F(1), F(1, 2)],
    'a': [
        [],
        [F(1, 4)],
        [F(3, 32), F(9, 32)],
        [F(1932, 2197), F(-7200, 2197), F(7296, 2197)],
        [F(439, 216), F(-8), F(3680, 513), F(-845, 4104)],
        [F(-8, 27), F(2), F(-3544, 2565), F(1859, 4104), F(-11, 40)],
    ],
    'b4': [F(25, 216), F(0), F(1408, 2565), F(2197, 4104), F(-1, 5), F(0)],
    'b5': [F(16, 135), F(0), F(6656, 12825), F(28561, 56430), F(-9, 50), F(2, 55)],
}


# ---------------------------------------------------------------------------
# Texto de las fórmulas (a partir del tablero)
# ---------------------------------------------------------------------------
def _frac(x):
    return f'{x.numerator}/{x.denominator}' if x.denominator != 1 else str(x.numerator)


def _coef_por(x, simbolo):
    """'1/2·K₁', 'K₁', '−2·K₂' ... (x ya distinto de 0)."""
    if x == 1:
        return simbolo
    if x == -1:
        return f'−{simbolo}'
    texto = _frac(abs(x))
    return f'{"−" if x < 0 else ""}{texto}·{simbolo}'


def _suma(coefs, h_en_k, prefijo='K'):
    """Σ a_j K_j como texto; devuelve '' si todos son 0."""
    partes = []
    for j, x in enumerate(coefs, start=1):
        if x == 0:
            continue
        partes.append(_coef_por(x, f'{prefijo}{j}'))
    if not partes:
        return ''
    texto = partes[0]
    for p in partes[1:]:
        texto += f' − {p[1:]}' if p.startswith('−') else f' + {p}'
    return texto


def _argumentos(c, fila, h_en_k):
    """(texto del argumento t, texto del argumento y) de la etapa."""
    if c == 0:
        t_txt = 'tᵢ'
    else:
        t_txt = f'tᵢ + {_coef_por(c, "h")}' if c != 1 else 'tᵢ + h'
    suma = _suma(fila, h_en_k)
    if not suma:
        y_txt = 'wᵢ'
    elif h_en_k:
        y_txt = f'wᵢ + {suma}' if not suma.startswith('−') else f'wᵢ − {suma[1:]}'
    else:
        y_txt = f'wᵢ + h·({suma})'
    return t_txt, y_txt


def definiciones(tab_c, tab_a, h_en_k):
    """Lista [{'nombre': 'K2', 'formula': 'K₂ = ...'}] para mostrar en pantalla."""
    subs = '₀₁₂₃₄₅₆₇₈₉'
    resultado = []
    for j, (c, fila) in enumerate(zip(tab_c, tab_a), start=1):
        t_txt, y_txt = _argumentos(c, fila, h_en_k)
        llamada = f'f({t_txt}, {y_txt})'
        if h_en_k:
            llamada = f'h·{llamada}'
        nombre = f'K{str(j).translate(str.maketrans("0123456789", subs))}'
        resultado.append({'nombre': f'K{j}', 'formula': f'{nombre} = {llamada}'})
    return resultado


def formula_w(pesos, h_en_k, nuevo='wᵢ₊₁'):
    suma = _con_subindices(_suma(pesos, True))
    if h_en_k:
        return f'{nuevo} = wᵢ + {suma}'
    return f'{nuevo} = wᵢ + h·({suma})'


def _con_subindices(texto):
    subs = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
    salida, i = '', 0
    while i < len(texto):
        salida += texto[i]
        if texto[i] == 'K' and i + 1 < len(texto) and texto[i + 1].isdigit():
            salida += texto[i + 1].translate(subs)
            i += 1
        i += 1
    return salida


# ---------------------------------------------------------------------------
# Un paso de Runge-Kutta con tablero explícito
# ---------------------------------------------------------------------------
def _verificar_finito(valor, donde):
    if not math.isfinite(valor):
        raise ErrorRungeKutta(
            f'El valor se volvió infinito o indefinido en {donde}. '
            'Prueba con más subintervalos o revisa f(t, y).'
        )


def paso_rk(f, c, a, b, t, w, h, h_en_k):
    """Devuelve (w_siguiente, [K1..Ks]) y [(t_arg, y_arg)] de cada etapa."""
    c = [float(x) for x in c]
    a = [[float(x) for x in fila] for fila in a]
    b = [float(x) for x in b]

    ks, argumentos = [], []
    for j in range(len(c)):
        t_arg = t + c[j] * h
        if h_en_k:
            y_arg = w + sum(a[j][m] * ks[m] for m in range(j))
        else:
            y_arg = w + h * sum(a[j][m] * ks[m] for m in range(j))
        valor = f(t_arg, y_arg)
        _verificar_finito(valor, f't = {t_arg:g}')
        ks.append(h * valor if h_en_k else valor)
        argumentos.append((t_arg, y_arg))

    if h_en_k:
        w_sig = w + sum(bj * k for bj, k in zip(b, ks))
    else:
        w_sig = w + h * sum(bj * k for bj, k in zip(b, ks))
    return w_sig, ks, argumentos


def resolver_rk(f, clave, t0, tn, n, w0, h_en_k):
    tab = METODOS[clave]
    h = (tn - t0) / n
    w = w0
    iteraciones = [{'iteracion': 0, 't': t0, 'w': w0, 'k': None}]
    paso1 = None

    for i in range(1, n + 1):
        t = t0 + (i - 1) * h
        w, ks, argumentos = paso_rk(f, tab['c'], tab['a'], tab['b'], t, w, h, h_en_k)
        _verificar_finito(w, f'la iteración {i}')

        if i == 1:
            paso1 = [
                {'nombre': f'K{j + 1}', 't': argumentos[j][0], 'y': argumentos[j][1], 'valor': ks[j]}
                for j in range(len(ks))
            ]

        t_nuevo = tn if i == n else t0 + i * h
        iteraciones.append({'iteracion': i, 't': t_nuevo, 'w': w, 'k': ks})

    defs = definiciones(tab['c'], tab['a'], h_en_k)
    for d in defs:
        d['formula'] = _con_subindices(d['formula'])

    return {
        'tipo': 'rk',
        'metodo': clave,
        'nombre': tab['nombre'],
        'orden': tab['orden'],
        'hEnK': h_en_k,
        'h': h,
        'definiciones': defs,
        'formulaW': formula_w(tab['b'], h_en_k),
        'paso1': paso1,
        'aproximacion': w,
        'iteraciones': iteraciones,
    }


# ---------------------------------------------------------------------------
# Runge-Kutta-Fehlberg
# ---------------------------------------------------------------------------
def _paso_fehlberg(f, t, w, h):
    """K1..K6 con h incluida (convención de Burden). Devuelve (w4, w5, ks)."""
    a = [[float(x) for x in fila] for fila in RKF['a']]
    c = [float(x) for x in RKF['c']]
    ks = []
    for j in range(6):
        y_arg = w + sum(a[j][m] * ks[m] for m in range(j))
        valor = f(t + c[j] * h, y_arg)
        _verificar_finito(valor, f't = {t + c[j] * h:g}')
        ks.append(h * valor)
    w4 = w + sum(float(bj) * k for bj, k in zip(RKF['b4'], ks))
    w5 = w + sum(float(bj) * k for bj, k in zip(RKF['b5'], ks))
    return w4, w5, ks


def resolver_rkf(f, t0, tn, w0, tol, hmax, hmin, criterio):
    t, w, h = t0, w0, hmax
    iteraciones = [{
        'intento': 0, 'i': 0, 't': t0, 'h': None, 'w': w0, 'wTilde': None,
        'R': None, 'q': None, 'aceptado': None, 'hSiguiente': None, 'k': None,
    }]
    aceptados = rechazados = 0
    paso_aceptado = 0
    paso1 = None
    umbral = 1e-14 * max(1.0, abs(tn - t0))

    for intento in range(1, LIMITE_INTENTOS_RKF + 1):
        if tn - t <= umbral:
            break

        h = min(h, tn - t)          # no pasarse de tn
        ultimo = (tn - t) <= h * (1 + 1e-12)

        w4, w5, ks = _paso_fehlberg(f, t, w, h)
        r = abs(w5 - w4) / h

        if r == 0:
            q = 4.0                  # error nulo: se permite crecer al máximo
            q_crudo = math.inf
        else:
            q_crudo = (tol / (2 * r)) ** 0.25
            q = q_crudo

        aceptado = (r <= tol) if criterio == 'R' else (q_crudo >= 1)
        q_usado = min(max(q, 0.1), 4.0)
        h_sig = min(q_usado * h, hmax)

        if paso1 is None:
            paso1 = [{'nombre': f'K{j + 1}', 'valor': ks[j]} for j in range(6)]

        fila = {
            'intento': intento,
            'i': paso_aceptado + 1 if aceptado else None,
            't': t + h if aceptado else t,
            'tIntento': t,
            'h': h,
            'w': w4,
            'wTilde': w5,
            'R': r,
            'q': q_crudo if math.isfinite(q_crudo) else None,
            'qUsado': q_usado,
            'aceptado': aceptado,
            'hSiguiente': h_sig,
            'k': ks,
        }

        if aceptado:
            aceptados += 1
            paso_aceptado += 1
            t = tn if ultimo else t + h
            w = w4
            _verificar_finito(w, f'el paso {paso_aceptado}')
            iteraciones.append(fila)
            h = h_sig
        else:
            rechazados += 1
            iteraciones.append(fila)
            h = h_sig
            if h < hmin:
                raise ErrorRungeKutta(
                    f'El paso se volvió menor que hmín = {hmin:g} en t = {t:g} sin cumplir la tolerancia. '
                    'Aumenta la tolerancia o reduce hmín.'
                )
    else:
        raise ErrorRungeKutta(
            f'Se superaron {LIMITE_INTENTOS_RKF} intentos sin llegar a tn. '
            'Aumenta la tolerancia o el paso máximo.'
        )

    return {
        'tipo': 'rkf',
        'metodo': 'rkf45',
        'nombre': 'Runge-Kutta-Fehlberg (4,5)',
        'orden': 5,
        'criterio': criterio,
        'definiciones': [
            dict(d, formula=_con_subindices(d['formula']))
            for d in definiciones(RKF['c'], RKF['a'], True)
        ],
        'formulaW': _con_subindices(formula_w(RKF['b4'], True, 'wᵢ₊₁')),
        'formulaWTilde': _con_subindices(formula_w(RKF['b5'], True, 'w̃ᵢ₊₁')),
        'paso1': paso1,
        'aproximacion': w,
        'tFinal': t,
        'aceptados': aceptados,
        'rechazados': rechazados,
        'iteraciones': iteraciones,
    }


# ---------------------------------------------------------------------------
# Lectura de datos
# ---------------------------------------------------------------------------
def _leer_numero(valor, nombre):
    if valor is None or str(valor).strip() == '':
        raise ErrorRungeKutta(f'El campo "{nombre}" debe ser un número válido.')
    try:
        numero = float(str(valor).strip().replace(',', '.'))
    except (TypeError, ValueError):
        raise ErrorRungeKutta(f'El campo "{nombre}" debe ser un número válido.')
    if not math.isfinite(numero):
        raise ErrorRungeKutta(f'El campo "{nombre}" debe ser un número finito.')
    return numero


def _leer_entero_positivo(valor, nombre):
    numero = _leer_numero(valor, nombre)
    if not numero.is_integer() or numero <= 0:
        raise ErrorRungeKutta(f'El campo "{nombre}" debe ser un entero positivo.')
    return int(numero)


def descripcion(clave, h_en_k=True):
    """Fórmulas (K y w) de un método, sin calcular nada. Las usa la pantalla
    para mostrar las K en cuanto se elige el método."""
    if clave == 'rkf45':
        return {
            'tipo': 'rkf',
            'metodo': 'rkf45',
            'nombre': 'Runge-Kutta-Fehlberg (4,5)',
            'definiciones': [
                dict(d, formula=_con_subindices(d['formula']))
                for d in definiciones(RKF['c'], RKF['a'], True)
            ],
            'formulaW': _con_subindices(formula_w(RKF['b4'], True, 'wᵢ₊₁')),
            'formulaWTilde': _con_subindices(formula_w(RKF['b5'], True, 'w̃ᵢ₊₁')),
        }
    tab = METODOS[clave]
    return {
        'tipo': 'rk',
        'metodo': clave,
        'nombre': tab['nombre'],
        'orden': tab['orden'],
        'hEnK': h_en_k,
        'definiciones': [
            dict(d, formula=_con_subindices(d['formula']))
            for d in definiciones(tab['c'], tab['a'], h_en_k)
        ],
        'formulaW': formula_w(tab['b'], h_en_k),
    }


@blueprint.route('/formulas', methods=['POST'])
def formulas():
    datos = request.get_json(force=True, silent=True) or {}
    clave = str(datos.get('metodo', 'rk4'))
    if clave != 'rkf45' and clave not in METODOS:
        return jsonify({'error': 'Método de Runge-Kutta no reconocido.'}), 400
    return jsonify(descripcion(clave, bool(datos.get('hEnK', True))))


@blueprint.route('/metodos', methods=['GET', 'POST'])
def listar_metodos():
    return jsonify({'metodos': [
        {'clave': k, 'nombre': v['nombre'], 'orden': v['orden'], 'etapas': len(v['b'])}
        for k, v in METODOS.items()
    ]})


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        metodo = str(datos.get('metodo', 'rk4'))
        t0 = _leer_numero(datos.get('t0'), 'Punto t0')
        tn = _leer_numero(datos.get('tn'), 'Punto tn')
        w0 = _leer_numero(datos.get('w0'), 'Valor inicial y(t0)')
        if t0 == tn:
            raise ErrorRungeKutta('Los puntos "t0" y "tn" deben ser distintos.')

        f = crear_funcion_edo(datos.get('funcion'))

        if metodo == 'rkf45':
            if tn < t0:
                raise ErrorRungeKutta('Runge-Kutta-Fehlberg necesita tn > t0.')
            tol = _leer_numero(datos.get('tol'), 'Tolerancia TOL')
            hmax = _leer_numero(datos.get('hmax'), 'Paso máximo hmáx')
            hmin = _leer_numero(datos.get('hmin'), 'Paso mínimo hmín')
            if tol <= 0 or hmax <= 0 or hmin <= 0:
                raise ErrorRungeKutta('TOL, hmáx y hmín deben ser positivos.')
            if hmin > hmax:
                raise ErrorRungeKutta('hmín no puede ser mayor que hmáx.')
            criterio = 'q' if str(datos.get('criterio', 'R')) == 'q' else 'R'

            resultado = resolver_rkf(f, t0, tn, w0, tol, hmax, hmin, criterio)
            resultado['mensaje'] = (
                f'Aproximación: y({tn:g}) ≈ {resultado["aproximacion"]:.8f} '
                f'({resultado["aceptados"]} pasos aceptados, {resultado["rechazados"]} rechazados)'
            )
            return jsonify(resultado)

        if metodo not in METODOS:
            raise ErrorRungeKutta('Método de Runge-Kutta no reconocido.')

        n = _leer_entero_positivo(datos.get('n'), 'Número de subintervalos')
        if n > LIMITE_SUBINTERVALOS:
            raise ErrorRungeKutta(f'El número de subintervalos no puede pasar de {LIMITE_SUBINTERVALOS}.')
        h_en_k = bool(datos.get('hEnK', True))

        resultado = resolver_rk(f, metodo, t0, tn, n, w0, h_en_k)
        resultado['mensaje'] = (
            f'Aproximación: y({tn:g}) ≈ {resultado["aproximacion"]:.8f} '
            f'(h = {resultado["h"]:g}, {n} subintervalos)'
        )
        return jsonify(resultado)
    except (ErrorRungeKutta, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en Runge-Kutta: {error}'}), 500