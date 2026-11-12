"""
Parser seguro de funciones matemáticas f(x) y f(t, y).

Este módulo es utilizado por todos los métodos que necesitan evaluar una
función ingresada por el usuario como texto (Bisección, Secante y
cualquier método futuro). No es un "método numérico" en sí mismo, por eso
vive en `comun/` y no junto a los archivos de cada método.

Hay dos puntos de entrada, que comparten validación, funciones permitidas
y evaluación:
- `crear_funcion(texto)`      -> f(x)       (raíces, integración, ...)
- `crear_funcion_edo(texto)`  -> f(t, y)    (ecuaciones diferenciales: Euler, ...)

Soporta:
- Operaciones algebraicas: + - * / ** (también se acepta "^" como potencia)
- Funciones trigonométricas: sin, cos, tan, asin, acos, atan
- Funciones hiperbólicas: sinh, cosh, tanh
- Exponencial y logaritmos: exp, log (natural), ln (alias de log), log10, log2
- Raíz cuadrada, valor absoluto, piso y techo: sqrt, abs, fabs, floor, ceil
- Constantes: e, pi

Ejemplos válidos de f(x): "x**2 - 3", "x^2 - 3", "sin(x) + cos(x)",
"exp(x) - 5", "e**x - 5", "log(x) + 1", "sqrt(x) - 2".
Ejemplos válidos de f(t, y): "y - t**2 + 1", "t*exp(3*t) - 2*y",
"sin(t) + cos(y)".
"""

import ast
import copy
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

LONGITUD_MAXIMA = 300


class ErrorFuncion(Exception):
    """Se lanza cuando la función ingresada por el usuario no es válida."""


class _EnterosAFloat(ast.NodeTransformer):
    """Convierte las constantes enteras en float.

    Sin esto, algo como 9**9**9**9 se evalúa con enteros de Python (de
    precisión ilimitada) y deja el servidor calculando "para siempre".
    Con floats, esa misma expresión falla al instante con OverflowError.
    Se aplica solo al compilar (sobre una copia), nunca al árbol que
    devuelve `_preparar_arbol`, para no alterar la derivación simbólica.
    """

    def visit_Constant(self, nodo):
        if isinstance(nodo.value, int) and not isinstance(nodo.value, bool):
            return ast.copy_location(ast.Constant(float(nodo.value)), nodo)
        return nodo


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


def _preparar_arbol(expresion_original, variables=('x',), nombre_funcion='f(x)'):
    """Convierte el texto de la función en un nodo AST validado (sin compilar).

    Reutilizado por `crear_funcion`, `crear_funcion_edo` y por
    `comun.derivador` (para derivar simbólicamente antes de compilar).

    `variables` son los nombres de variable permitidos además de las
    funciones y constantes: ('x',) para f(x), ('t', 'y') para f(t, y).
    """

    expresion = str(expresion_original if expresion_original is not None else '').strip()

    if not expresion:
        raise ErrorFuncion(f'Ingresa una función {nombre_funcion}.')

    if len(expresion) > LONGITUD_MAXIMA:
        raise ErrorFuncion(f'La función es demasiado larga (máximo {LONGITUD_MAXIMA} caracteres).')

    expresion_python = expresion.replace('^', '**')

    try:
        arbol = ast.parse(expresion_python, mode='eval')
    except SyntaxError as error:
        raise ErrorFuncion('No se pudo interpretar la función. Revisa la sintaxis.') from error

    _validar_nodo(arbol)

    nombres_validos = set(variables) | set(FUNCIONES_PERMITIDAS) | set(CONSTANTES_PERMITIDAS)
    identificadores = {nodo.id for nodo in ast.walk(arbol) if isinstance(nodo, ast.Name)}
    no_permitidos = identificadores - nombres_validos
    if no_permitidos:
        nombre = sorted(no_permitidos)[0]
        variables_texto = ' y '.join(f'"{variable}"' for variable in variables)
        raise ErrorFuncion(
            f'"{nombre}" no es un nombre válido en {nombre_funcion}. '
            f'Usa {variables_texto}, funciones (sin, cos, tan, exp, log, ln, sqrt, ...) y las constantes e, pi.'
        )

    return arbol.body


def _compilar_codigo(nodo_expresion):
    """Compila un nodo AST (ya validado) a código evaluable.

    Trabaja sobre una copia: el nodo original queda intacto, así que quien
    lo reutilice (p. ej. el derivador) sigue viendo los enteros originales.
    """

    copia = _EnterosAFloat().visit(copy.deepcopy(nodo_expresion))
    envoltura = ast.Expression(body=copia)
    ast.fix_missing_locations(envoltura)

    return compile(envoltura, '<funcion>', 'eval')


def _entorno_base():
    entorno = dict(FUNCIONES_PERMITIDAS)
    entorno.update(CONSTANTES_PERMITIDAS)
    return entorno


def _evaluar(codigo, entorno, llamada, punto):
    """Evalúa el código con un entorno restringido y valida que el resultado
    sea un número real finito.

    `llamada` es cómo se muestra la evaluación en los mensajes (p. ej. "f(2)"
    o "f(0.5, 1)") y `punto` es el valor de las variables ("x = 2" o
    "t = 0.5, y = 1").
    """

    try:
        resultado = eval(codigo, {'__builtins__': {}}, entorno)  # noqa: S307 - entorno restringido
    except ZeroDivisionError as error:
        raise ErrorFuncion(f'División entre cero al evaluar {llamada}.') from error
    except OverflowError as error:
        raise ErrorFuncion(f'{llamada} produjo un número demasiado grande.') from error
    except ValueError as error:
        raise ErrorFuncion(f'No se pudo evaluar {llamada}: fuera del dominio de la función.') from error
    except ErrorFuncion:
        raise
    except Exception as error:
        raise ErrorFuncion(f'No se pudo evaluar la función en {punto}.') from error

    if isinstance(resultado, bool) or not isinstance(resultado, (int, float)):
        raise ErrorFuncion(f'{llamada} no produjo un número válido. Revisa la función.')

    if not math.isfinite(resultado):
        raise ErrorFuncion(f'{llamada} no produjo un número finito. Revisa la función.')

    return float(resultado)


def _compilar_desde_nodo(nodo_expresion):
    """Compila un nodo AST (ya validado) en una función Python f(x) evaluable de forma segura."""

    codigo = _compilar_codigo(nodo_expresion)
    entorno_base = _entorno_base()

    def f(valor):
        entorno = dict(entorno_base)
        entorno['x'] = valor
        return _evaluar(codigo, entorno, f'f({valor})', f'x = {valor}')

    return f


def crear_funcion(expresion_original):
    """Convierte el texto de f(x) en una función Python evaluable de forma segura."""

    nodo = _preparar_arbol(expresion_original)
    return _compilar_desde_nodo(nodo)


def crear_funcion_edo(expresion_original):
    """Convierte el texto de f(t, y) en una función Python f(t, y) -> float,
    para ecuaciones diferenciales dy/dt = f(t, y)."""

    nodo = _preparar_arbol(expresion_original, variables=('t', 'y'), nombre_funcion='f(t, y)')
    codigo = _compilar_codigo(nodo)
    entorno_base = _entorno_base()

    def f(t, y):
        entorno = dict(entorno_base)
        entorno['t'] = t
        entorno['y'] = y
        return _evaluar(codigo, entorno, f'f({t:g}, {y:g})', f't = {t:g}, y = {y:g}')

    return f

def _leer_numero(valor, nombre_campo, Error):
    if valor is None or str(valor).strip() == '':
        raise Error(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise Error(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise Error(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo, Error):
    numero = _leer_numero(valor, nombre_campo, Error)
    if not float(numero).is_integer() or numero <= 0:
        raise Error(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)