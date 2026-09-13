"""
Derivador simbólico de funciones f(x).

Construye la derivada exacta (no numérica) de una función ingresada como
texto, reutilizando el mismo parser seguro de `parser_funciones.py`. Se
usa en Newton-Raphson (necesita f'(x) para cada iteración) y en Punto
Fijo (necesita g'(x) para verificar el criterio de convergencia
|g'(x)| < 1 y para graficarla).

No es un "método numérico" en sí mismo, por eso vive en `comun/` igual
que el parser.

Reglas de derivación soportadas: suma, resta, producto, cociente,
potencia (regla de la potencia, regla exponencial o regla general según
corresponda), y las funciones de `FUNCIONES_PERMITIDAS` que tienen
derivada elemental conocida (trigonométricas, hiperbólicas, exp, log,
ln, log10, log2, sqrt, asin, acos, atan).
"""

import ast
import math

from metodos.comun.parser_funciones import (
    ErrorFuncion,
    FUNCIONES_PERMITIDAS,
    _compilar_desde_nodo,
    _preparar_arbol,
    _validar_nodo,
)


class ErrorDerivada(ErrorFuncion):
    """Se lanza cuando no se puede construir la derivada de la función."""


def _contiene_x(nodo):
    return any(isinstance(n, ast.Name) and n.id == 'x' for n in ast.walk(nodo))


def _const(valor):
    return ast.Constant(value=valor)


def _bin(izquierda, operador, derecha):
    return ast.BinOp(left=izquierda, op=operador, right=derecha)


def _neg(nodo):
    return ast.UnaryOp(op=ast.USub(), operand=nodo)


def _llamada(nombre, argumento):
    return ast.Call(func=ast.Name(id=nombre, ctx=ast.Load()), args=[argumento], keywords=[])


def derivar(nodo):
    """Devuelve el nodo AST de la derivada de `nodo` respecto a x."""

    if isinstance(nodo, ast.Constant):
        return _const(0)

    if isinstance(nodo, ast.Name):
        return _const(1) if nodo.id == 'x' else _const(0)

    if isinstance(nodo, ast.UnaryOp):
        if isinstance(nodo.op, ast.USub):
            return _neg(derivar(nodo.operand))
        if isinstance(nodo.op, ast.UAdd):
            return derivar(nodo.operand)
        raise ErrorDerivada('No se pudo derivar la función: operador unario no soportado.')

    if isinstance(nodo, ast.BinOp):
        izquierda, derecha = nodo.left, nodo.right
        d_izquierda, d_derecha = derivar(izquierda), derivar(derecha)

        if isinstance(nodo.op, ast.Add):
            return _bin(d_izquierda, ast.Add(), d_derecha)

        if isinstance(nodo.op, ast.Sub):
            return _bin(d_izquierda, ast.Sub(), d_derecha)

        if isinstance(nodo.op, ast.Mult):
            return _bin(
                _bin(d_izquierda, ast.Mult(), derecha),
                ast.Add(),
                _bin(izquierda, ast.Mult(), d_derecha),
            )

        if isinstance(nodo.op, ast.Div):
            numerador = _bin(
                _bin(d_izquierda, ast.Mult(), derecha),
                ast.Sub(),
                _bin(izquierda, ast.Mult(), d_derecha),
            )
            denominador = _bin(derecha, ast.Mult(), derecha)
            return _bin(numerador, ast.Div(), denominador)

        if isinstance(nodo.op, ast.Pow):
            x_en_base = _contiene_x(izquierda)
            x_en_exponente = _contiene_x(derecha)

            if x_en_exponente and not x_en_base:
                # a^v  ->  a^v * ln(a) * v'
                return _bin(
                    _bin(nodo, ast.Mult(), _llamada('log', izquierda)),
                    ast.Mult(),
                    d_derecha,
                )

            if x_en_base and not x_en_exponente:
                # u^n  ->  n * u^(n-1) * u'
                exponente_menos_uno = _bin(derecha, ast.Sub(), _const(1))
                return _bin(
                    _bin(derecha, ast.Mult(), _bin(izquierda, ast.Pow(), exponente_menos_uno)),
                    ast.Mult(),
                    d_izquierda,
                )

            if x_en_base and x_en_exponente:
                # u^v  ->  u^v * (v' * ln(u) + v * u'/u)
                termino_1 = _bin(d_derecha, ast.Mult(), _llamada('log', izquierda))
                termino_2 = _bin(derecha, ast.Mult(), _bin(d_izquierda, ast.Div(), izquierda))
                return _bin(nodo, ast.Mult(), _bin(termino_1, ast.Add(), termino_2))

            return _const(0)

        raise ErrorDerivada('No se pudo derivar la función: operador no soportado.')

    if isinstance(nodo, ast.Call):
        nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else None
        if nombre not in FUNCIONES_PERMITIDAS:
            raise ErrorDerivada(f'"{nombre}" no es una función derivable soportada.')

        argumento = nodo.args[0]
        d_argumento = derivar(argumento)

        def cadena(externa):
            return _bin(externa, ast.Mult(), d_argumento)

        if nombre == 'sin':
            return cadena(_llamada('cos', argumento))
        if nombre == 'cos':
            return cadena(_neg(_llamada('sin', argumento)))
        if nombre == 'tan':
            return cadena(_bin(_const(1), ast.Div(), _bin(_llamada('cos', argumento), ast.Pow(), _const(2))))
        if nombre == 'exp':
            return cadena(_llamada('exp', argumento))
        if nombre in ('log', 'ln'):
            return cadena(_bin(_const(1), ast.Div(), argumento))
        if nombre == 'log10':
            return cadena(_bin(_const(1), ast.Div(), _bin(argumento, ast.Mult(), _const(math.log(10)))))
        if nombre == 'log2':
            return cadena(_bin(_const(1), ast.Div(), _bin(argumento, ast.Mult(), _const(math.log(2)))))
        if nombre == 'sqrt':
            return cadena(_bin(_const(1), ast.Div(), _bin(_const(2), ast.Mult(), _llamada('sqrt', argumento))))
        if nombre == 'asin':
            radical = _llamada('sqrt', _bin(_const(1), ast.Sub(), _bin(argumento, ast.Pow(), _const(2))))
            return cadena(_bin(_const(1), ast.Div(), radical))
        if nombre == 'acos':
            radical = _llamada('sqrt', _bin(_const(1), ast.Sub(), _bin(argumento, ast.Pow(), _const(2))))
            return cadena(_neg(_bin(_const(1), ast.Div(), radical)))
        if nombre == 'atan':
            return cadena(_bin(_const(1), ast.Div(), _bin(_const(1), ast.Add(), _bin(argumento, ast.Pow(), _const(2)))))
        if nombre == 'sinh':
            return cadena(_llamada('cosh', argumento))
        if nombre == 'cosh':
            return cadena(_llamada('sinh', argumento))
        if nombre == 'tanh':
            return cadena(_bin(_const(1), ast.Div(), _bin(_llamada('cosh', argumento), ast.Pow(), _const(2))))

        raise ErrorDerivada(
            f'"{nombre}(...)" no tiene una derivada elemental soportada. '
            'Usa funciones trigonométricas, hiperbólicas, exp, log/ln, log10, log2 o sqrt.'
        )

    raise ErrorDerivada('No se pudo derivar la función: expresión no soportada.')


def crear_funcion_y_derivada(expresion_original):
    """A partir del texto de f(x), devuelve (f, f_prima) como funciones Python evaluables."""

    nodo = _preparar_arbol(expresion_original)
    f = _compilar_desde_nodo(nodo)

    nodo_derivada = derivar(nodo)
    _validar_nodo(ast.Expression(body=nodo_derivada))
    f_prima = _compilar_desde_nodo(nodo_derivada)

    return f, f_prima
