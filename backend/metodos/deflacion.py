"""
Método: Deflación (todas las raíces de un polinomio)

Se usa para obtener TODAS las raíces de un polinomio F(x), no solo una.
Si δ es una raíz de F(x), entonces

    F(x) / (x - δ) = W(x)

donde W(x) es un polinomio de un grado menor (división sintética /
Horner). Repitiendo el proceso sobre W(x) —encontrar una raíz, dividir,
repetir— cada paso reduce el grado en 1 hasta quedarse con un polinomio
de grado 1 o 2, que se resuelve directo.

Aquí la raíz de cada paso se consigue reutilizando el método de Müller
(metodos/muller.py) sobre el polinomio actual, partiendo siempre de los
mismos tres puntos iniciales p0, p1, p2 que da el usuario. Como Müller
puede converger a raíces complejas, la deflación también puede
encontrar pares de raíces complejas conjugadas (algo que Bisección,
Secante o Falsa Posición no pueden hacer).

A diferencia de los demás métodos del proyecto, aquí la función no se
escribe como texto libre (f(x) = ...) sino como una lista de
coeficientes del polinomio, de mayor a menor grado — así la evaluación
se hace con el esquema de Horner (pura aritmética +,-,*), que funciona
igual de bien con números reales o complejos sin depender de
metodos/comun/parser_funciones.py.

Este archivo es independiente del resto de los métodos salvo por su
dependencia explícita de metodos/muller.py: si algo falla en Bisección,
Secante, Falsa Posición o Steffensen, no afecta a Deflación.
"""

import cmath
import math
import re

from flask import Blueprint, jsonify, request

from metodos.muller import ErrorMuller, calcular_muller

blueprint = Blueprint('deflacion', __name__, url_prefix='/api/deflacion')


class ErrorDeflacion(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorDeflacion(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorDeflacion(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorDeflacion(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorDeflacion(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def _leer_coeficientes(texto):
    if texto is None or str(texto).strip() == '':
        raise ErrorDeflacion('Ingresa los coeficientes del polinomio, de mayor a menor grado.')

    partes = [p for p in re.split(r'[,\s]+', str(texto).strip()) if p != '']

    try:
        coeficientes = [float(p) for p in partes]
    except ValueError:
        raise ErrorDeflacion('Los coeficientes deben ser números separados por comas o espacios (ej. 3, -14, -8, 64).')

    # Quita ceros a la izquierda para quedarse con el grado real del polinomio.
    while len(coeficientes) > 1 and coeficientes[0] == 0:
        coeficientes.pop(0)

    if len(coeficientes) < 2:
        raise ErrorDeflacion('El polinomio debe tener al menos grado 1 (dos coeficientes, ej. "2, -4").')

    return coeficientes


def _evaluar_horner(coeficientes, x):
    resultado = coeficientes[0]
    for coef in coeficientes[1:]:
        resultado = resultado * x + coef
    return resultado


def deflactar(coeficientes, raiz):
    """División sintética de `coeficientes` entre (x - raiz).
    Regresa (cociente, residuo); el residuo debería ser ~0 si `raiz`
    de verdad es una raíz del polinomio."""
    cociente = [coeficientes[0]]
    for coef in coeficientes[1:]:
        cociente.append(cociente[-1] * raiz + coef)
    residuo = cociente.pop()
    return cociente, residuo


def _simplificar(valor, tolerancia_imaginaria=1e-9):
    """Si un número complejo tiene parte imaginaria ~0, lo regresa como real."""
    if isinstance(valor, complex) and abs(valor.imag) < tolerancia_imaginaria:
        return valor.real
    return valor


def _resolver_cuadratica(a, b, c):
    discriminante = b * b - 4 * a * c
    if isinstance(discriminante, complex) or discriminante < 0:
        raiz_discriminante = cmath.sqrt(discriminante)
    else:
        raiz_discriminante = math.sqrt(discriminante)

    r1 = (-b + raiz_discriminante) / (2 * a)
    r2 = (-b - raiz_discriminante) / (2 * a)
    return [_simplificar(r1), _simplificar(r2)]


def _valor_json(valor):
    if isinstance(valor, complex):
        return {'re': valor.real, 'im': valor.imag}
    return valor


def encontrar_todas_las_raices(coeficientes, p0, p1, p2, tolerancia, max_iteraciones):
    actuales = list(coeficientes)
    raices = []

    # Mientras el polinomio actual tenga grado > 2, se busca una raíz con
    # Müller y se deflacta. Grado 1 y 2 se resuelven directo (más simple
    # y más robusto que forzar a Müller con muy pocos coeficientes).
    while len(actuales) - 1 > 2:
        grado_actual = len(actuales) - 1

        def f(x, coefs=actuales):
            return _evaluar_horner(coefs, x)

        try:
            raiz, iteraciones, convergio = calcular_muller(f, p0, p1, p2, tolerancia, max_iteraciones)
        except ErrorMuller as error:
            raise ErrorDeflacion(
                f'No se pudo encontrar una raíz del polinomio de grado {grado_actual}: {error}'
            )

        if not convergio:
            raise ErrorDeflacion(
                f'Müller no alcanzó la tolerancia buscando una raíz del polinomio de grado {grado_actual} '
                f'tras {len(iteraciones)} iteraciones. Prueba con otros puntos p0, p1, p2 o más iteraciones.'
            )

        raiz = _simplificar(raiz)
        nuevos_coeficientes, residuo = deflactar(actuales, raiz)

        raices.append({
            'numero': len(raices) + 1,
            'grado': grado_actual,
            'raiz': _valor_json(raiz),
            'iteraciones': len(iteraciones),
            'residuo': _valor_json(_simplificar(residuo)),
        })

        actuales = nuevos_coeficientes

    grado_final = len(actuales) - 1

    if grado_final == 2:
        a, b, c = actuales
        for raiz in _resolver_cuadratica(a, b, c):
            raices.append({
                'numero': len(raices) + 1,
                'grado': 2,
                'raiz': _valor_json(raiz),
                'iteraciones': 0,
                'residuo': _valor_json(0.0),
            })
    elif grado_final == 1:
        a, b = actuales
        raices.append({
            'numero': len(raices) + 1,
            'grado': 1,
            'raiz': _valor_json(-b / a),
            'iteraciones': 0,
            'residuo': _valor_json(0.0),
        })

    return raices


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        coeficientes = _leer_coeficientes(datos.get('coeficientes'))
        p0 = _leer_numero(datos.get('p0'), 'Punto p0')
        p1 = _leer_numero(datos.get('p1'), 'Punto p1')
        p2 = _leer_numero(datos.get('p2'), 'Punto p2')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')

        if len({p0, p1, p2}) < 3:
            raise ErrorDeflacion('Los puntos p0, p1 y p2 deben ser distintos entre sí.')

        if tolerancia <= 0:
            raise ErrorDeflacion('El error máximo debe ser mayor que cero.')

        grado_original = len(coeficientes) - 1
        raices = encontrar_todas_las_raices(coeficientes, p0, p1, p2, tolerancia, max_iteraciones)

        mensaje = f'Se encontraron {len(raices)} raíces de un polinomio de grado {grado_original}.'

        return jsonify({
            'grado': grado_original,
            'mensaje': mensaje,
            'raices': raices,
        })
    except (ErrorDeflacion, ErrorMuller) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Deflación: {error}'}), 500