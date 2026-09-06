"""
Parser seguro de funciones matemáticas f(x).

Este módulo es utilizado por todos los métodos que necesitan evaluar una
función ingresada por el usuario como texto (Bisección, Secante y
cualquier método futuro). No es un "método numérico" en sí mismo, por eso
vive en `comun/` y no junto a los archivos de cada método.

Soporta:
- Operaciones algebraicas: + - * / ** (también se acepta "^" como potencia)
- Funciones trigonométricas: sin, cos, tan, asin, acos, atan
- Funciones hiperbólicas: sinh, cosh, tanh
- Exponencial y logaritmos: exp, log (natural), ln (alias de log), log10, log2
- Raíz cuadrada, valor absoluto, piso y techo: sqrt, abs, fabs, floor, ceil
- Constantes: e, pi

Ejemplos válidos de f(x): "x**2 - 3", "x^2 - 3", "sin(x) + cos(x)",
"exp(x) - 5", "e**x - 5", "log(x) + 1", "sqrt(x) - 2".
"""

import ast
import math

FUNCIONES_PERMITIDAS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    'exp': math.exp,
    'log': math.log,
    'ln': math.log,
    'log10': math.log10,
    'log2': math.log2,
    'sqrt': math.sqrt,
    'abs': abs,
    'fabs': math.fabs,
    'floor': math.floor,
    'ceil': math.ceil,
}

CONSTANTES_PERMITIDAS = {
    'e': math.e,
    'pi': math.pi,
}

NOMBRES_PERMITIDOS = {'x'} | set(FUNCIONES_PERMITIDAS) | set(CONSTANTES_PERMITIDAS)

_NODOS_PERMITIDOS = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)


class ErrorFuncion(Exception):
    """Se lanza cuando la función f(x) ingresada por el usuario no es válida."""


def _validar_nodo(nodo):
    if not isinstance(nodo, _NODOS_PERMITIDOS):
        raise ErrorFuncion(f'La función contiene una expresión no permitida ({type(nodo).__name__}).')

    if isinstance(nodo, ast.Constant) and not isinstance(nodo.value, (int, float)):
        raise ErrorFuncion('La función solo puede contener números y operaciones matemáticas.')

    if isinstance(nodo, ast.Call):
        if not isinstance(nodo.func, ast.Name) or nodo.func.id not in FUNCIONES_PERMITIDAS:
            nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else '?'
            raise ErrorFuncion(f'"{nombre}" no es una función matemática permitida.')
        if nodo.keywords:
            raise ErrorFuncion('No se permiten argumentos con nombre en las funciones.')

    for hijo in ast.iter_child_nodes(nodo):
        _validar_nodo(hijo)


def crear_funcion(expresion_original):
    """Convierte el texto de f(x) en una función Python evaluable de forma segura."""

    expresion = str(expresion_original if expresion_original is not None else '').strip()

    if not expresion:
        raise ErrorFuncion('Ingresa una función f(x).')

    expresion_python = expresion.replace('^', '**')

    try:
        arbol = ast.parse(expresion_python, mode='eval')
    except SyntaxError as error:
        raise ErrorFuncion('No se pudo interpretar la función. Revisa la sintaxis.') from error

    _validar_nodo(arbol)

    identificadores = {nodo.id for nodo in ast.walk(arbol) if isinstance(nodo, ast.Name)}
    no_permitidos = identificadores - NOMBRES_PERMITIDOS
    if no_permitidos:
        nombre = sorted(no_permitidos)[0]
        raise ErrorFuncion(
            f'"{nombre}" no es un nombre válido en f(x). '
            'Usa "x", funciones (sin, cos, tan, exp, log, ln, sqrt, ...) y las constantes e, pi.'
        )

    codigo = compile(arbol, '<f(x)>', 'eval')
    entorno_base = dict(FUNCIONES_PERMITIDAS)
    entorno_base.update(CONSTANTES_PERMITIDAS)

    def f(valor):
        entorno = dict(entorno_base)
        entorno['x'] = valor
        try:
            resultado = eval(codigo, {'__builtins__': {}}, entorno)  # noqa: S307 - entorno restringido
        except ZeroDivisionError as error:
            raise ErrorFuncion(f'División entre cero al evaluar f({valor}).') from error
        except ValueError as error:
            raise ErrorFuncion(f'No se pudo evaluar f({valor}): fuera del dominio de la función.') from error
        except ErrorFuncion:
            raise
        except Exception as error:
            raise ErrorFuncion(f'No se pudo evaluar la función en x = {valor}.') from error

        if isinstance(resultado, bool) or not isinstance(resultado, (int, float)):
            raise ErrorFuncion(f'f({valor}) no produjo un número válido. Revisa la función.')

        if not math.isfinite(resultado):
            raise ErrorFuncion(f'f({valor}) no produjo un número finito. Revisa la función.')

        return float(resultado)

    return f
