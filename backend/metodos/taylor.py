"""
Método: Taylor

Aproxima la solución de una EDO de valor inicial

    dy/dt = f(t, y),    y(t0) = w0,    t en [t0, tn]

dividiendo el intervalo en n subintervalos de ancho h = (tn - t0) / n y
avanzando con la serie de Taylor de orden p:

    w_{i+1} = w_i + h·F0 + (h²/2!)·F1 + ... + (h^p/p!)·F_{p-1},    t_i = t0 + i·h

donde, evaluadas en (t_i, w_i):

    F0 = f(t, y)
    F_{k+1} = ∂F_k/∂t + ∂F_k/∂y · f        (derivada total respecto a t,
                                             usando que y' = f(t, y))

Con p = 1 el método es idéntico al de Euler. Por cada iteración se reporta
el tiempo t_i y la aproximación w_i ≈ y(t_i). Si tn < t0, h resulta
negativo y el método avanza hacia atrás.

Cómo se usa sympy aquí: solo UNA vez por petición, para derivar f(t, y)
simbólicamente y convertir cada F_k en una función numérica (lambdify). Los
n pasos del método se calculan con floats normales, sin sympy, así que
n = 5000 y orden 10 siguen siendo instantáneos.

Por qué no se usa crear_funcion_edo: esa función devuelve un evaluador
NUMÉRICO (acepta números, no símbolos de sympy), así que no se puede derivar.
En su lugar se reutiliza _preparar_arbol de metodos/comun/parser_funciones.py,
que ya valida el texto con la lista blanca (mismas funciones, mismos nombres,
mismo límite de longitud), y el árbol validado se traduce a sympy aquí mismo.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a los demás. Requiere `sympy` (agrégalo a requirements.txt).
"""

import ast
import math

import sympy as sp
from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import (
    ErrorFuncion,
    _leer_entero_positivo,
    _leer_numero,
    _preparar_arbol,
)

blueprint = Blueprint('taylor', __name__, url_prefix='/api/taylor')

# Tope de subintervalos: evita respuestas gigantes y tablas imposibles de pintar.
LIMITE_SUBINTERVALOS = 5000

ORDEN_MAXIMO = 10

# Al derivar varias veces, la expresión puede crecer de forma explosiva
# (p. ej. sin(cos(tan(y*t))) con orden 6 ya pasa del millón de operaciones y
# tarda segundos). Se corta antes de que eso congele el servidor.
LIMITE_OPERACIONES = 20000

# Mismo motivo que _EnterosAFloat en el parser: con sympy, algo como
# 9**9**9**9 se quedaría calculando para siempre. Si un exponente que ya es
# un número pasa de este valor, se rechaza antes de calcular la potencia.
LIMITE_EXPONENTE = 10000


class ErrorTaylor(Exception):
    """Se lanza cuando la entrada del usuario o el intervalo no son válidos."""


# ---------------------------------------------------------------------------
# Texto -> expresión de sympy
# ---------------------------------------------------------------------------

_FUNCIONES_UNARIAS = {
    'sin': sp.sin,
    'cos': sp.cos,
    'tan': sp.tan,
    'asin': sp.asin,
    'acos': sp.acos,
    'atan': sp.atan,
    'sinh': sp.sinh,
    'cosh': sp.cosh,
    'tanh': sp.tanh,
    'exp': sp.exp,
    'sqrt': sp.sqrt,
    'abs': sp.Abs,
    'fabs': sp.Abs,
    'floor': sp.floor,
    'ceil': sp.ceiling,
}


def _potencia(base, exponente):
    if exponente.is_number and abs(exponente) > LIMITE_EXPONENTE:
        raise ErrorFuncion('La función contiene una potencia con un exponente demasiado grande.')
    return base ** exponente


def _llamar(nombre, argumentos):
    if nombre in ('log', 'ln'):
        if len(argumentos) not in (1, 2):
            raise ErrorFuncion(f'"{nombre}" recibe 1 argumento (o 2: log(x, base)).')
        return sp.log(*argumentos)

    if nombre in ('log10', 'log2'):
        if len(argumentos) != 1:
            raise ErrorFuncion(f'"{nombre}" recibe exactamente 1 argumento.')
        return sp.log(argumentos[0], 10 if nombre == 'log10' else 2)

    if len(argumentos) != 1:
        raise ErrorFuncion(f'"{nombre}" recibe exactamente 1 argumento.')
    return _FUNCIONES_UNARIAS[nombre](argumentos[0])


def _a_sympy(nodo, t, y):
    """Traduce un nodo AST (ya validado por parser_funciones) a sympy.

    Todos los números se vuelven Float, igual que _EnterosAFloat en el parser:
    así no hay enteros de precisión ilimitada ni sympy "simplificando" con
    fracciones exactas.
    """

    if isinstance(nodo, ast.Constant):
        # True/False pasan la validación del parser (bool es subclase de int);
        # igual que allá, aquí no cuentan como números.
        if isinstance(nodo.value, bool):
            raise ErrorFuncion('La función solo puede contener números y operaciones matemáticas.')
        try:
            valor = float(nodo.value)
        except OverflowError:
            valor = math.inf
        if not math.isfinite(valor):
            raise ErrorFuncion('La función contiene un número demasiado grande.')
        return sp.Float(valor)

    if isinstance(nodo, ast.Name):
        if nodo.id == 't':
            return t
        if nodo.id == 'y':
            return y
        if nodo.id == 'e':
            return sp.Float(math.e)
        if nodo.id == 'pi':
            return sp.Float(math.pi)
        raise ErrorFuncion(f'"{nodo.id}" es una función: escríbela con paréntesis, por ejemplo {nodo.id}(t).')

    if isinstance(nodo, ast.UnaryOp):
        operando = _a_sympy(nodo.operand, t, y)
        return -operando if isinstance(nodo.op, ast.USub) else operando

    if isinstance(nodo, ast.BinOp):
        izquierda = _a_sympy(nodo.left, t, y)
        derecha = _a_sympy(nodo.right, t, y)
        operador = nodo.op

        if isinstance(operador, ast.Add):
            return izquierda + derecha
        if isinstance(operador, ast.Sub):
            return izquierda - derecha
        if isinstance(operador, ast.Mult):
            return izquierda * derecha
        if isinstance(operador, ast.Div):
            return izquierda / derecha
        if isinstance(operador, ast.Mod):
            return sp.Mod(izquierda, derecha)
        if isinstance(operador, ast.Pow):
            return _potencia(izquierda, derecha)

    if isinstance(nodo, ast.Call):
        argumentos = [_a_sympy(argumento, t, y) for argumento in nodo.args]
        return _llamar(nodo.func.id, argumentos)

    raise ErrorFuncion('La función contiene una expresión no permitida.')


def crear_expresion_edo(expresion_original):
    """Texto de f(t, y) -> (expresión de sympy, símbolo t, símbolo y)."""

    nodo = _preparar_arbol(expresion_original, variables=('t', 'y'), nombre_funcion='f(t, y)')

    t, y = sp.symbols('t y', real=True)

    try:
        expresion = _a_sympy(nodo, t, y)
    except ZeroDivisionError:
        # sympy lanza esto al dividir números entre cero (p. ej. "1/0").
        raise ErrorFuncion('f(t, y) contiene una división entre cero.')
    except (OverflowError, ValueError, TypeError):
        raise ErrorFuncion('No se pudo interpretar f(t, y). Revisa la sintaxis y los números usados.')

    # Resultados que no son un número real (raíz de un negativo, 1/0, log(0), ...).
    if expresion.has(sp.I, sp.zoo, sp.oo, sp.S.NegativeInfinity, sp.nan):
        raise ErrorFuncion('f(t, y) no produjo un número real (revisa raíces, logaritmos o divisiones entre cero).')

    return expresion, t, y


# ---------------------------------------------------------------------------
# Derivadas y método
# ---------------------------------------------------------------------------

def derivadas_totales(f_expr, t, y, orden):
    """Regresa [F0, F1, ..., F_{orden-1}] con F_{k+1} = dF_k/dt + dF_k/dy · f."""

    derivadas = [f_expr]

    for _ in range(1, orden):
        previa = derivadas[-1]
        siguiente = sp.diff(previa, t) + sp.diff(previa, y) * f_expr

        if siguiente.has(sp.Derivative, sp.DiracDelta):
            raise ErrorTaylor(
                'f(t, y) contiene abs(), floor(), ceil() o % y no se puede derivar tantas veces. '
                'Baja el orden del método de Taylor (con abs() el orden máximo es 2).'
            )

        if sp.count_ops(siguiente) > LIMITE_OPERACIONES:
            raise ErrorTaylor(
                'Las derivadas de f(t, y) crecen demasiado con este orden. '
                'Baja el orden del método de Taylor o simplifica f(t, y).'
            )

        derivadas.append(siguiente)

    return derivadas


def _termino(evaluar, k, h, t_actual, w):
    """(h^(k+1) / (k+1)!) · F_k(t_actual, w), con errores de evaluación en español."""

    # F_0 es f misma; F_k (k ≥ 1) es su k-ésima derivada total.
    nombre = 'f(t, y)' if k == 0 else f'la derivada de orden {k} de f(t, y)'
    punto = f't = {t_actual:g}, y = {w:g}'

    try:
        valor = evaluar(t_actual, w)
        if isinstance(valor, complex):
            raise ErrorTaylor(f'Al evaluar {nombre} en {punto} el resultado no es un número real.')
        termino = (h ** (k + 1) / math.factorial(k + 1)) * valor
    except ZeroDivisionError:
        raise ErrorTaylor(f'División entre cero al evaluar {nombre} en {punto}.')
    except OverflowError:
        raise ErrorTaylor(f'Número demasiado grande al evaluar {nombre} en {punto}.')
    except ValueError:
        raise ErrorTaylor(f'No se pudo evaluar {nombre} en {punto}: fuera del dominio de la función.')

    return float(termino)


def calcular_taylor(f_expr, t, y, t0, tn, n, w0, orden):
    h = (tn - t0) / n
    w = w0

    # Se derivan y se convierten a funciones numéricas UNA sola vez.
    derivadas = derivadas_totales(f_expr, t, y, orden)
    evaluadores = [sp.lambdify((t, y), derivada, modules=['math']) for derivada in derivadas]

    iteraciones = [{'iteracion': 0, 't': t0, 'w': w0}]

    for i in range(1, n + 1):
        t_anterior = t0 + (i - 1) * h

        incremento = 0.0
        for k, evaluar in enumerate(evaluadores):
            incremento += _termino(evaluar, k, h, t_anterior, w)

        w = w + incremento

        if not math.isfinite(w):
            raise ErrorTaylor(
                f'La aproximación se volvió infinita o indefinida en la iteración {i}. '
                'Prueba con más subintervalos o revisa f(t, y).'
            )

        # t se calcula como t0 + i·h (no acumulando t += h) para no arrastrar
        # error de redondeo; en la última iteración se fuerza t = tn exacto.
        t_i = tn if i == n else t0 + i * h

        iteraciones.append({'iteracion': i, 't': t_i, 'w': w})

    return h, iteraciones, w


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        # Estos helpers devuelven (valor, clase_de_error); solo interesa el valor.
        # Importante: NO reasignar ErrorTaylor aquí. Hacerlo dentro de esta
        # función la convierte en variable local y el primer uso truena con
        # UnboundLocalError (500 en vez de un mensaje de error claro).
        t0 = _leer_numero(datos.get('t0'), 'Punto t0', ErrorTaylor)
        tn = _leer_numero(datos.get('tn'), 'Punto tn', ErrorTaylor)
        n = _leer_entero_positivo(datos.get('n'), 'Número de subintervalos', ErrorTaylor)
        w0 = _leer_numero(datos.get('w0'), 'Valor inicial y(t0)', ErrorTaylor)
        orden = _leer_entero_positivo(datos.get('orden'), 'Orden del método de Taylor', ErrorTaylor)

        if orden > ORDEN_MAXIMO:
            raise ErrorTaylor(f'El orden del método de Taylor debe estar entre 1 y {ORDEN_MAXIMO}.')

        if t0 == tn:
            raise ErrorTaylor('Los puntos "t0" y "tn" deben ser distintos.')

        if n > LIMITE_SUBINTERVALOS:
            raise ErrorTaylor(f'El número de subintervalos no puede pasar de {LIMITE_SUBINTERVALOS}.')

        f_expr, t, y = crear_expresion_edo(datos.get('funcion'))
        h, iteraciones, aproximacion = calcular_taylor(f_expr, t, y, t0, tn, n, w0, orden)

        mensaje = (
            f'Aproximación: y({tn:g}) ≈ {aproximacion:.6f} '
            f'(orden {orden}, h = {h:g}, {n} subintervalos)'
        )

        return jsonify({
            'aproximacion': aproximacion,
            'h': h,
            'orden': orden,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
        })
    except (ErrorTaylor, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Taylor: {error}'}), 500