"""
Método: Punto Fijo

Busca un punto fijo de g(x) (es decir, un valor p tal que g(p) = p) por
iteración simple: p_{n+1} = g(p_n), comenzando en una aproximación
inicial p0. El problema de encontrar una raíz de f(x) = 0 se transforma
primero, a mano, en un problema equivalente x = g(x); g(x) es lo que el
usuario ingresa aquí.

Además de la tabla de iteraciones, este método evalúa sobre un intervalo
[a, b] dado por el usuario los dos criterios del teorema de existencia y
unicidad del punto fijo:

  1. Mapeo:       g(x) ∈ [a, b] para todo x ∈ [a, b]      (existencia)
  2. Contracción: |g'(x)| ≤ k < 1 para todo x ∈ [a, b]     (unicidad y
                                                             convergencia)

g'(x) se calcula de forma simbólica (exacta) con `comun/derivador.py`.
También se generan puntos muestreados de g(x), |g'(x)| y la recta
identidad y = x para que el frontend dibuje la gráfica de análisis.

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Punto Flotante, Bisección, Secante, Falsa Posición,
Newton-Raphson ni a métodos futuros.
"""

import math

from flask import Blueprint, jsonify, request

from metodos.comun.derivador import ErrorDerivada, crear_funcion_y_derivada
from metodos.comun.parser_funciones import ErrorFuncion

blueprint = Blueprint('punto_fijo', __name__, url_prefix='/api/punto-fijo')

NUM_MUESTRAS_GRAFICA = 250


class ErrorPuntoFijo(Exception):
    """Se lanza cuando la entrada del usuario no es válida o el método no puede continuar."""


def _leer_numero(valor, nombre_campo):
    if valor is None or str(valor).strip() == '':
        raise ErrorPuntoFijo(f'El campo "{nombre_campo}" debe ser un número válido.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorPuntoFijo(f'El campo "{nombre_campo}" debe ser un número válido.')

    if not math.isfinite(numero):
        raise ErrorPuntoFijo(f'El campo "{nombre_campo}" debe ser un número finito.')

    return numero


def _leer_entero_positivo(valor, nombre_campo):
    numero = _leer_numero(valor, nombre_campo)
    if not float(numero).is_integer() or numero <= 0:
        raise ErrorPuntoFijo(f'El campo "{nombre_campo}" debe ser un entero positivo.')
    return int(numero)


def calcular_punto_fijo(g, p0, tolerancia, max_iteraciones):
    iteraciones = []
    p1 = p0

    for i in range(1, max_iteraciones + 1):
        gp0 = g(p0)
        p1 = gp0

        error_absoluto = abs(p1 - p0)
        error_aproximado = abs(error_absoluto / p1) * 100 if p1 != 0 else None

        iteraciones.append({
            'iteracion': i,
            'p0': p0,
            'gp0': gp0,
            'p1': p1,
            'errorAbsoluto': error_absoluto,
            'errorAproximado': error_aproximado,
        })

        if error_absoluto < tolerancia:
            return p1, iteraciones, True

        p0 = p1

    return p1, iteraciones, False


def analizar_intervalo_y_graficar(g, g_prima, a, b):
    """Evalúa los criterios de existencia/unicidad en [a, b] y arma los
    puntos muestreados para la gráfica (g, |g'| y la recta y = x)."""

    ancho = b - a
    relleno = max(ancho * 0.35, 0.5)
    dominio_x_min = a - relleno
    dominio_x_max = b + relleno

    puntos_g = []
    puntos_derivada_abs = []

    valores_g = []
    valores_derivada_abs = []

    fallos_en_intervalo = 0
    muestras_en_intervalo = 0

    for indice in range(NUM_MUESTRAS_GRAFICA + 1):
        x = dominio_x_min + (dominio_x_max - dominio_x_min) * indice / NUM_MUESTRAS_GRAFICA
        dentro_del_intervalo = a - 1e-9 <= x <= b + 1e-9

        try:
            y_g = g(x)
            puntos_g.append({'x': x, 'y': y_g})
            valores_g.append(y_g)
            if dentro_del_intervalo:
                muestras_en_intervalo += 1
        except ErrorFuncion:
            if dentro_del_intervalo:
                fallos_en_intervalo += 1
                muestras_en_intervalo += 1

        try:
            y_dp = abs(g_prima(x))
            puntos_derivada_abs.append({'x': x, 'y': y_dp})
            valores_derivada_abs.append(y_dp)
        except ErrorFuncion:
            pass

    if muestras_en_intervalo == 0:
        raise ErrorPuntoFijo('No se pudo evaluar g(x) en ningún punto del intervalo [a, b].')

    # --- Criterio 1: mapeo g([a, b]) ⊆ [a, b] ---
    valores_g_en_intervalo = [
        punto['y'] for punto in puntos_g
        if a - 1e-9 <= punto['x'] <= b + 1e-9
    ]

    if fallos_en_intervalo > 0:
        cumple_mapeo = False
        g_min = min(valores_g_en_intervalo) if valores_g_en_intervalo else None
        g_max = max(valores_g_en_intervalo) if valores_g_en_intervalo else None
    elif valores_g_en_intervalo:
        g_min = min(valores_g_en_intervalo)
        g_max = max(valores_g_en_intervalo)
        margen = max(abs(a), abs(b), 1.0) * 1e-6
        cumple_mapeo = (g_min >= a - margen) and (g_max <= b + margen)
    else:
        cumple_mapeo = False
        g_min = None
        g_max = None

    # --- Criterio 2: contracción |g'(x)| <= k < 1 ---
    derivadas_en_intervalo = [
        punto['y'] for punto in puntos_derivada_abs
        if a - 1e-9 <= punto['x'] <= b + 1e-9
    ]

    if derivadas_en_intervalo:
        k_max = max(derivadas_en_intervalo)
        cumple_contraccion = k_max < 1
    else:
        k_max = None
        cumple_contraccion = False

    cumple_ambos = cumple_mapeo and cumple_contraccion

    if cumple_ambos:
        mensaje_analisis = (
            f'Se cumplen los dos criterios en [{a:g}, {b:g}]: existe un único punto fijo '
            f'y la iteración converge a él (k ≈ {k_max:.4f}).'
        )
    else:
        razones = []
        if not cumple_mapeo:
            razones.append('g(x) no se mantiene dentro de [a, b] en todo el intervalo')
        if not cumple_contraccion:
            k_texto = f'k ≈ {k_max:.4f}' if k_max is not None else 'k desconocida'
            razones.append(f'|g\'(x)| no es menor que 1 en todo el intervalo ({k_texto})')
        mensaje_analisis = (
            'No se puede garantizar existencia y unicidad del punto fijo con este g(x) '
            f'en [{a:g}, {b:g}]: ' + '; '.join(razones) + '.'
        )

    # --- Datos para la gráfica ---
    valores_y_relevantes = list(valores_g) + list(valores_derivada_abs) + [a, b, 1.0]
    dominio_y_min = min(valores_y_relevantes + [dominio_x_min])
    dominio_y_max = max(valores_y_relevantes + [dominio_x_max])
    relleno_y = max((dominio_y_max - dominio_y_min) * 0.1, 0.5)

    return {
        'a': a,
        'b': b,
        'cumpleMapeo': cumple_mapeo,
        'gMin': g_min,
        'gMax': g_max,
        'cumpleContraccion': cumple_contraccion,
        'kMax': k_max,
        'cumpleAmbos': cumple_ambos,
        'mensaje': mensaje_analisis,
        'grafica': {
            'puntosG': puntos_g,
            'puntosDerivadaAbs': puntos_derivada_abs,
            'dominio': {
                'xMin': dominio_x_min,
                'xMax': dominio_x_max,
                'yMin': dominio_y_min - relleno_y,
                'yMax': dominio_y_max + relleno_y,
            },
        },
    }


@blueprint.route('/calcular', methods=['POST'])
def calcular():
    try:
        datos = request.get_json(force=True, silent=True) or {}

        p0 = _leer_numero(datos.get('p0'), 'Aproximación inicial p0')
        tolerancia = _leer_numero(datos.get('tolerancia'), 'Error máximo')
        max_iteraciones = _leer_entero_positivo(datos.get('maxIteraciones'), 'Iteraciones máximas')
        a = _leer_numero(datos.get('a'), 'Punto a')
        b = _leer_numero(datos.get('b'), 'Punto b')

        if tolerancia <= 0:
            raise ErrorPuntoFijo('El error máximo debe ser mayor que cero.')

        if a >= b:
            raise ErrorPuntoFijo('El intervalo no es válido: "a" debe ser menor que "b".')

        g, g_prima = crear_funcion_y_derivada(datos.get('funcion'))

        raiz, iteraciones, convergio = calcular_punto_fijo(g, p0, tolerancia, max_iteraciones)
        analisis = analizar_intervalo_y_graficar(g, g_prima, a, b)

        mensaje = (
            f'Punto fijo aproximado: x ≈ {raiz:.6f} ({len(iteraciones)} iteraciones)'
            if convergio
            else f'No se alcanzó la tolerancia tras {len(iteraciones)} iteraciones. '
                 f'Mejor aproximación: x ≈ {raiz:.6f}'
        )

        return jsonify({
            'raiz': raiz,
            'convergio': convergio,
            'mensaje': mensaje,
            'iteraciones': iteraciones,
            'analisisIntervalo': analisis,
        })
    except (ErrorPuntoFijo, ErrorDerivada, ErrorFuncion) as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en el método de Punto Fijo: {error}'}), 500
