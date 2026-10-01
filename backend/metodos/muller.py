"""
Método: Müller (raíces reales y complejas)

Requiere 3 aproximaciones iniciales p0, p1, p2 a una raíz r. Se ajusta
la parábola P(x) = a(x-p2)² + b(x-p2) + c que pasa por (p0,f0), (p1,f1)
y (p2,f2); la intersección de esa parábola con el eje X da la nueva
aproximación p3. El proceso se repite con el corrimiento p0←p1, p1←p2,
p2←p3.

a, b y c se obtienen aquí con diferencias divididas (forma estándar,
equivalente a resolver a mano el sistema 3x3 del apunte, pero con
menos riesgo de un error de álgebra):

    h0 = p1-p0,  h1 = p2-p1
    δ0 = (f1-f0)/h0,  δ1 = (f2-f1)/h1
    a = (δ1-δ0)/(h1+h0)
    b = a·h1 + δ1
    c = f2

y luego, como en el apunte:

    p3 = p2 - 2c / (b + signo(b)·√(b²-4ac))

usando siempre el denominador de mayor magnitud entre (b+√Δ) y (b-√Δ)
para evitar cancelación numérica.

Lo que distingue a Müller de los demás métodos del proyecto: si el
discriminante b²-4ac sale negativo, la raíz cuadrada (y por lo tanto
p3) se vuelve un número COMPLEJO — así es como el método encuentra
raíces complejas incluso partiendo de valores iniciales reales. Por
eso aquí se usa el tipo `complex` de Python y, cuando hace falta,
`cmath.sqrt` en vez de `math.sqrt`.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Bisección, Secante, Falsa Posición, Steffensen ni a
métodos futuros.
"""

import cmath
import math

from flask import Blueprint, jsonify, request

from metodos.comun.parser_funciones import ErrorFuncion, crear_funcion

blueprint = Blueprint('muller', __name__, url_prefix='/api/muller')


class ErrorMuller(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorMuller(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorMuller(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorMuller(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorMuller(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def _evaluar(f, punto):
    """Evalúa f en `punto` (real o complejo) y traduce el error típico de
    un parser que no soporta complejos en un mensaje claro para el usuario."""
    try:
        return f(punto)
    except (TypeError, ValueError) as error:
        if isinstance(punto, complex) and abs(punto.imag) > 0:
            raise ErrorMuller(
                'Müller llegó a una aproximación compleja (posible raíz compleja), pero f(x) no se '
                'pudo evaluar en un número complejo. Revisa metodos/comun/parser_funciones.py: necesita '
                'usar "cmath" (o un evaluador compatible con complejos) en vez de "math" para que este '
                'método pueda encontrar raíces complejas.'
            ) from error
        raise


def _valor_json(valor):
    """Convierte un número (real o complejo) a algo serializable en JSON."""
    if isinstance(valor, complex):
        return {'re': valor.real, 'im': valor.imag}
    return valor


def _formatear_valor(valor):
    if isinstance(valor, complex):
        signo = '+' if valor.imag >= 0 else '-'
        return f'{valor.real:.6f} {signo} {abs(valor.imag):.6f}i'
    return f'{valor:.6f}'


def calcular_muller(f, p0, p1, p2, tolerancia, max_iteraciones):
    iteraciones = []
    p3 = p2

    for i in range(1, max_iteraciones + 1):
        f0 = _evaluar(f, p0)
        f1 = _evaluar(f, p1)
        f2 = _evaluar(f, p2)

        h0 = p1 - p0
        h1 = p2 - p1

        if h0 == 0 or h1 == 0 or (h1 + h0) == 0:
            raise ErrorMuller('Las tres aproximaciones iniciales deben ser distintas entre sí.')

        delta0 = (f1 - f0) / h0
        delta1 = (f2 - f1) / h1

        a = (delta1 - delta0) / (h1 + h0)
        b = a * h1 + delta1
        c = f2

        if a == 0 and b == 0:
            raise ErrorMuller('La parábola se degenera (a = b = 0); prueba con otras aproximaciones iniciales.')

        discriminante = b * b - 4 * a * c

        # Si el discriminante es negativo, su raíz cuadrada ya es un número
        # complejo: aquí es donde Müller "se asoma" a las raíces complejas.
        if isinstance(discriminante, complex) or discriminante < 0:
            raiz_discriminante = cmath.sqrt(discriminante)
        else:
            raiz_discriminante = math.sqrt(discriminante)

        denominador_mas = b + raiz_discriminante
        denominador_menos = b - raiz_discriminante

        # Se toma el denominador de mayor magnitud (equivale a elegir el
        # signo igual al de b) para evitar cancelación numérica.
        if abs(denominador_mas) >= abs(denominador_menos):
            denominador = denominador_mas
        else:
            denominador = denominador_menos

        if denominador == 0:
            raise ErrorMuller('El denominador de la fórmula de Müller dio cero; no se puede continuar.')

        p3 = p2 - (2 * c) / denominador

        # Si la parte imaginaria es prácticamente cero, se regresa a número
        # real: evita arrastrar aritmética compleja (y la dependencia de
        # que f(x) la soporte) cuando en realidad la raíz es real.
        if isinstance(p3, complex) and abs(p3.imag) < 1e-12:
            p3 = p3.real

        f3 = _evaluar(f, p3)

        error_absoluto = abs(p3 - p2)
        error_aproximado = error_absoluto / abs(p3) if p3 != 0 else error_absoluto

        iteraciones.append({
            'iteracion': i,
            'p0': _valor_json(p0),
            'p1': _valor_json(p1),
            'p2': _valor_json(p2),
            'p3': _valor_json(p3),
            'fp3': _valor_json(f3),
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if abs(f3) == 0 or error_aproximado < tolerancia:
            return p3, iteraciones, True

        p0, p1, p2 = p1, p2, p3

    return p3, iteraciones, False


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        p0 = _leer_numero(datos.get('p0'), 'Punto p0')
        p1 = _leer_numero(datos.get('p1'), 'Punto p1')
        p2 = _leer_numero(datos.get('p2'), 'Punto p2')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if len({p0, p1, p2}) < 3:
            raise ErrorMuller('Los puntos p0, p1 y p2 deben ser distintos entre sí.')

        if tolerancia <= 0:
            raise ErrorMuller('El error máximo debe ser mayor que cero.')

        f = crear_funcion(datos.get('funcion'))
        raiz, iteraciones, convergio = calcular_muller(f, p0, p1, p2, tolerancia, max_iteraciones)

        mensaje = (
            f'Raíz aproximada: x ≈ {_formatear_valor(raiz)} ({len(iteraciones)} iteraciones)'
            if convergio
            else f'No se alcanzó la tolerancia tras {len(iteraciones)} iteraciones. '
                 f'Mejor aproximación: x ≈ {_formatear_valor(raiz)}'
        )

        return jsonify({
            'raiz': _valor_json(raiz),
            'convergio': convergio,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
        })
    except (ErrorMuller, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Müller: {error}'}), 500