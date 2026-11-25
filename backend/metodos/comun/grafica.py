"""
Utilidades comunes para las gráficas de los métodos de raíces de ecuaciones.

El navegador solo dibuja; aquí se decide QUÉ dibujar: se muestrea f(x) en un
rango, se descartan los puntos donde f no se puede evaluar (polos, raíces de
negativos, etc.) y se calcula un rango vertical razonable.

Uso típico dentro de un método:

    from metodos.comun.grafica import armar_grafica
    respuesta['grafica'] = armar_grafica(f, x_min, x_max, valores_clave=[0, fa, fb])

La respuesta es un dict listo para jsonify:

    {'dominio': {'xMin', 'xMax', 'yMin', 'yMax'},
     'puntos': [{'x': ..., 'y': ...}, ...]}      # y = None donde f no existe

Este archivo no depende de ningún método: si falla, solo se pierde la gráfica
(los métodos lo llaman dentro de un try para no romper el cálculo).
"""

import math

NUM_MUESTRAS = 500


def muestrear(f, x_min, x_max, n=NUM_MUESTRAS):
    """Evalúa f en n+1 puntos equiespaciados. y = None si no se pudo evaluar."""
    puntos = []
    for i in range(n + 1):
        x = x_min + (x_max - x_min) * i / n
        try:
            y = float(f(x))
            if not math.isfinite(y):
                y = None
        except Exception:  # noqa: BLE001 - un punto malo no debe romper la gráfica
            y = None
        puntos.append({'x': x, 'y': y})
    return puntos


def _percentil(valores_ordenados, p):
    if not valores_ordenados:
        return 0.0
    posicion = (len(valores_ordenados) - 1) * p
    inferior = math.floor(posicion)
    superior = math.ceil(posicion)
    peso = posicion - inferior
    return valores_ordenados[inferior] * (1 - peso) + valores_ordenados[superior] * peso


def rango_vertical(puntos, x_a, x_b, valores_clave=()):
    """Rango y que muestra bien la zona [x_a, x_b].

    Se usan los percentiles 2-98 de f dentro de [x_a, x_b] para que una
    asíntota (tan, 1/x) no aplaste el resto de la curva, y siempre se incluyen
    el 0 y los `valores_clave` (f(a), f(b), ...).
    """
    dentro = sorted(
        p['y'] for p in puntos
        if p['y'] is not None and x_a - 1e-12 <= p['x'] <= x_b + 1e-12
    )
    candidatos = [0.0] + [v for v in valores_clave if v is not None and math.isfinite(v)]

    if dentro:
        candidatos += [_percentil(dentro, 0.02), _percentil(dentro, 0.98)]

    y_min, y_max = min(candidatos), max(candidatos)
    if y_max - y_min < 1e-12:
        y_min, y_max = y_min - 1, y_max + 1

    relleno = (y_max - y_min) * 0.12
    return y_min - relleno, y_max + relleno


def armar_grafica(f, a, b, valores_clave=(), margen=0.2, n=NUM_MUESTRAS):
    """Gráfica de f en [a, b] con un margen a cada lado."""
    a, b = min(a, b), max(a, b)
    ancho = b - a
    relleno = max(ancho * margen, 1e-9)
    x_min, x_max = a - relleno, b + relleno

    puntos = muestrear(f, x_min, x_max, n)
    y_min, y_max = rango_vertical(puntos, a, b, valores_clave)

    return {
        'dominio': {'xMin': x_min, 'xMax': x_max, 'yMin': y_min, 'yMax': y_max},
        'puntos': puntos,
    }


# ---------------------------------------------------------------------------
# Métodos que trazan una recta por dos puntos (Falsa Posición, Secante) o una
# sucesión de aproximaciones con tangentes (Newton-Raphson)
# ---------------------------------------------------------------------------
def _evaluar(f, x):
    try:
        y = float(f(x))
        return y if math.isfinite(y) else None
    except Exception:  # noqa: BLE001
        return None


def _grafica_sobre_puntos(f, xs, valores_clave, margen=0.2, n=NUM_MUESTRAS):
    """Curva de f en el rango que cubren los puntos xs (con margen)."""
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        raise ValueError('No hay puntos para graficar.')
    if min(xs) == max(xs):
        centro = min(xs)
        xs = [centro - 1, centro + 1]
    return armar_grafica(f, min(xs), max(xs), valores_clave=valores_clave, margen=margen, n=n)


def armar_grafica_dos_puntos(f, iteraciones, claves=('a', 'b', 'c')):
    """Falsa Posición y Secante: por iteración, la recta que une
    (p, f(p)) y (q, f(q)) y corta el eje x en r.

    `iteraciones` es la lista de dicts que ya arma el método; `claves` son los
    nombres de las columnas p, q, r (por defecto 'a', 'b', 'c').
    Agrega a la gráfica `pasos`: [{p, fp, q, fq, r, fr}, ...].
    """
    kp, kq, kr = claves
    pasos = []
    xs = []
    for it in iteraciones:
        p, q, r = it[kp], it[kq], it[kr]
        pasos.append({
            'p': p, 'fp': _evaluar(f, p),
            'q': q, 'fq': _evaluar(f, q),
            'r': r, 'fr': _evaluar(f, r),
        })
        xs += [p, q, r]

    claves_y = [v for paso in pasos[:6] for v in (paso['fp'], paso['fq'], paso['fr'])]
    grafica = _grafica_sobre_puntos(f, xs[:6] + xs[-3:] if len(xs) > 9 else xs, claves_y)
    grafica['pasos'] = pasos
    return grafica


def _secuencia_x(x0, iteraciones, claves):
    for clave in claves:
        if iteraciones and clave in iteraciones[0]:
            valores = [it[clave] for it in iteraciones]
            break
    else:
        raise KeyError(f'No encontré la columna de x en las iteraciones (probé {claves}).')
    # Si la primera fila ya es x0 (iteración 0), no se repite
    return valores if valores and abs(valores[0] - x0) <= 1e-15 else [x0] + valores


def armar_grafica_sucesion(f, x0, iteraciones, claves=('x', 'xn', 'xi', 'p', 'c', 'aproximacion')):
    """Newton-Raphson: sucesión x0, x1, x2, ... con f(x_k) para dibujar la
    tangente de cada paso (pasa por (x_k, f(x_k)) y por (x_{k+1}, 0)).

    `claves` son los posibles nombres de la columna de x en tus iteraciones;
    se usa la primera que exista. Agrega `pasos`: [{x, fx}, ...].
    """
    xs = _secuencia_x(x0, iteraciones, claves)
    pasos = [{'x': x, 'fx': _evaluar(f, x)} for x in xs]
    grafica = _grafica_sobre_puntos(
        f, xs[:6] + xs[-1:], [p['fx'] for p in pasos[:6]], margen=0.25
    )
    grafica['pasos'] = pasos
    return grafica


# ---------------------------------------------------------------------------
# Steffensen (telaraña + Aitken), Müller (parábola) y Deflación (por etapas)
# ---------------------------------------------------------------------------
def _real(v):
    """Número real a partir de un valor de iteración. Los complejos llegan como
    {'re', 'im'} (así los serializa Müller): si su parte imaginaria es ~0 se
    devuelve la parte real; si no, None."""
    if isinstance(v, dict):
        return v.get('re') if abs(v.get('im', 0.0)) < 1e-12 else None
    return v


def armar_grafica_steffensen(g, iteraciones, claves=('x0', 'x1', 'x2', 'x')):
    """Steffensen: g(x), la recta y = x y, por iteración, la telaraña
    x0 -> x1 = g(x0) -> x2 = g(x1) con el valor de Aitken.
    `claves` = columnas (x0, x1, x2, x_nuevo) de tus iteraciones.
    Agrega `pasos`: [{x0, x1, x2, x}, ...]."""
    k0, k1, k2, kn = claves
    pasos = [{'x0': it[k0], 'x1': it[k1], 'x2': it[k2], 'x': it[kn]} for it in iteraciones]

    xs = [v for paso in pasos[:6] for v in paso.values()] + [pasos[-1]['x']]
    grafica = _grafica_sobre_puntos(g, xs, valores_clave=xs, margen=0.3)

    # El rango vertical debe cubrir también la diagonal y = x en todo el dominio
    d = grafica['dominio']
    d['yMin'] = min(d['yMin'], d['xMin'])
    d['yMax'] = max(d['yMax'], d['xMax'])
    grafica['pasos'] = pasos
    return grafica


def armar_grafica_muller(f, iteraciones, claves=('p0', 'p1', 'p2', 'p3')):
    """Müller: por iteración, la parábola por (p0,f0), (p1,f1), (p2,f2) con sus
    coeficientes a, b, c (P(x) = a(x-p2)² + b(x-p2) + c) y el punto p3 donde
    corta el eje x. Si p3 es complejo la parábola no corta el eje: se manda en
    `p3c` = {re, im}. Si alguno de p0, p1, p2 ya es complejo, `real` = False y
    esa iteración no se puede dibujar en el plano real."""
    k0, k1, k2, k3 = claves
    pasos = []
    xs = []

    for it in iteraciones:
        p0, p1, p2 = _real(it[k0]), _real(it[k1]), _real(it[k2])
        p3_crudo = it[k3]
        p3 = _real(p3_crudo)
        paso = {'real': None not in (p0, p1, p2), 'p0': p0, 'p1': p1, 'p2': p2, 'p3': p3,
                'p3c': p3_crudo if isinstance(p3_crudo, dict) and p3 is None else None}

        if paso['real']:
            f0, f1, f2 = _evaluar(f, p0), _evaluar(f, p1), _evaluar(f, p2)
            paso.update({'f0': f0, 'f1': f1, 'f2': f2, 'f3': _evaluar(f, p3) if p3 is not None else None})
            h0, h1 = p1 - p0, p2 - p1
            if None not in (f0, f1, f2) and h0 and h1 and (h0 + h1):
                d0, d1 = (f1 - f0) / h0, (f2 - f1) / h1
                a = (d1 - d0) / (h1 + h0)
                paso.update({'a': a, 'b': a * h1 + d1, 'c': f2})
            else:
                paso['real'] = False
            xs += [p0, p1, p2]
        if p3 is not None:
            xs.append(p3)
        pasos.append(paso)

    if not xs:
        raise ValueError('Ninguna iteración tiene valores reales para graficar.')

    muestra = [paso['f0'] for paso in pasos[:6] if paso.get('f0') is not None]
    grafica = _grafica_sobre_puntos(f, xs[:24], muestra + [paso['f2'] for paso in pasos[:6] if paso.get('f2') is not None], margen=0.3)
    grafica['pasos'] = pasos
    return grafica


def armar_grafica_deflacion(coeficientes, raices):
    """Deflación: polinomio original, y por cada raíz encontrada (en el orden en
    que se halló) el polinomio que se tenía en ese momento (`coef` de mayor a
    menor grado, o None si ya tiene coeficientes complejos) y la raíz.
    `raices` es la lista que ya devuelve el método (cada una con 'raiz')."""
    def horner(coefs, x):
        r = coefs[0]
        for c in coefs[1:]:
            r = r * x + c
        return r

    etapas = []
    actuales = list(coeficientes)
    for r in raices:
        valor = r['raiz']
        raiz_c = complex(valor['re'], valor['im']) if isinstance(valor, dict) else valor
        reales = all(abs(complex(c).imag) <= 1e-9 * max(1.0, abs(c)) for c in actuales)
        etapas.append({
            'grado': len(actuales) - 1,
            'coef': [complex(c).real for c in actuales] if reales else None,
            'raiz': valor,
            'esReal': _real(valor) is not None,
        })
        if len(actuales) > 1:
            cociente = [actuales[0]]
            for c in actuales[1:]:
                cociente.append(cociente[-1] * raiz_c + c)
            cociente.pop()          # residuo
            actuales = cociente

    reales = [_real(e['raiz']) for e in etapas if e['esReal']]
    if not reales:
        reales = [(e['raiz']['re'] if isinstance(e['raiz'], dict) else e['raiz']) for e in etapas] or [0.0]
    original = [float(c) for c in coeficientes]
    grafica = _grafica_sobre_puntos(lambda x: horner(original, x), reales, [0.0], margen=0.35)
    grafica['etapas'] = etapas
    grafica['coeficientes'] = original
    return grafica


# ---------------------------------------------------------------------------
# Integración numérica: función, nodos y área bajo la curva
# ---------------------------------------------------------------------------
def nodos_equiespaciados(a, b, n):
    """n+1 puntos equiespaciados de a a b (el último es b exacto)."""
    return [b if i == n else a + (b - a) * i / n for i in range(n + 1)]


def armar_grafica_integracion(f, xs, grupo=1):
    """Trapecio / Simpson 1/3 / Simpson 3/8 (simples y compuestos).

    `xs` son TODOS los puntos x de la regla (en la simple: a, a+h, ..., b; en la
    compuesta: los que ingresó el usuario) y `grupo` cuántos subintervalos abarca
    cada aplicación de la regla (trapecio 1, Simpson 1/3 2, Simpson 3/8 3).
    Devuelve la curva y `grupos` = [{xs, fs}, ...]; el navegador dibuja por cada
    grupo el polinomio que pasa por sus nodos (recta, parábola o cúbica) y rellena
    el área bajo él."""
    grupos = []
    for i in range(0, len(xs) - grupo, grupo):
        sub = xs[i:i + grupo + 1]
        grupos.append({'xs': sub, 'fs': [_evaluar(f, x) for x in sub]})

    claves = [v for g in grupos for v in g['fs']]
    grafica = armar_grafica(f, xs[0], xs[-1], valores_clave=claves, margen=0.1)
    grafica['grupos'] = grupos
    return grafica


def armar_grafica_romberg(f, a, b, iteraciones, max_trapecios=128):
    """Romberg: por fila k, los 2^k+1 nodos del trapecio compuesto (columna 0).
    Si 2^k supera `max_trapecios` esa fila no se dibuja (xs = None)."""
    pasos = []
    claves = []
    for it in iteraciones:
        if it['n'] <= max_trapecios:
            xs = nodos_equiespaciados(a, b, it['n'])
            fs = [_evaluar(f, x) for x in xs]
            claves += fs
        else:
            xs = fs = None
        pasos.append({'k': it['k'], 'n': it['n'], 'xs': xs, 'fs': fs})

    grafica = armar_grafica(f, a, b, valores_clave=claves, margen=0.1)
    grafica['pasos'] = pasos
    return grafica