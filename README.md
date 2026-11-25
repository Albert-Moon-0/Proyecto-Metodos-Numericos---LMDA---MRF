# Proyecto Métodos Numéricos — LMDA · MRF

Backend en **Python (Flask)** + Frontend en **HTML/CSS/JavaScript**.

## Estructura

```
proyecto-metodos-numericos/
├── .gitignore
├── backend/
│   ├── app.py                     # Servidor Flask (API + sirve el frontend)
│   ├── requirements.txt
│   └── metodos/
│       ├── __init__.py            # Registro central de métodos (lista MODULOS)
│       ├── comun/
│       │   ├── parser_funciones.py  # Parser seguro de f(x): trig, e^x, log, algebraicas...
│       │   └── derivador.py         # Derivada simbólica exacta (Newton-Raphson, Punto Fijo, ...)
│       ├── punto_flotante.py      # Conversión IEEE 754
│       ├── biseccion.py           # Bisección
│       ├── secante.py             # Secante
│       ├── falsa_posicion.py      # Falsa Posición
│       ├── newton_raphson.py      # Newton-Raphson
│       ├── punto_fijo.py          # Punto Fijo (con análisis de existencia/unicidad)
│       ├── steffenson.py          # Steffensen (aceleración de Aitken)
│       ├── muller.py              # Müller (raíces reales y complejas)
│       ├── deflacion.py           # Deflación (todas las raíces de un polinomio)
│       ├── trapecio_simpsons.py   # Trapecio, Simpson 1/3 y 3/8 (simples y compuestas)
│       ├── derivacion_numerica.py # Derivación numérica: 2, 3 y 5 puntos (tabla o f(x))
│       ├── euler.py               # Euler para EDO de valor inicial
│       └── taylor.py              # Taylor de orden p para EDO de valor inicial
└── frontend/
    ├── index.html                 # Menú por módulos
    ├── styles.css
    ├── PuntoFlotante.html, Biseccion.html, Secante.html, FalsaPosicion.html,
    │   NewtonRaphson.html, PuntoFijo.html, Steffenson.html, Muller.html,
    │   Deflacion.html, TrapecioYSimpsons.html, DerivacionNumerica.html,
    │   MétodoEuler.html, MetodoTaylor.html
    └── js/
        ├── api.js                   # Helper de conexión con el backend
        ├── tablas-y-recursos.js     # Utilidades compartidas de tabla/resultado
        ├── index.js
        └── un script por método (biseccion.js, secante.js, ..., taylor.js)
```

## Cómo ejecutarlo

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Abre **http://localhost:5000** en el navegador. El propio backend sirve el
frontend, así que no necesitas nada más.

## Métodos incluidos

- **Punto Flotante (IEEE 754)** — conversión decimal ↔ binario en 16/32/64 bits.
- **Bisección** — con error absoluto y error aproximado.
- **Secante**
- **Falsa Posición**
- **Newton-Raphson** — la derivada f'(x) se calcula de forma **simbólica y
  exacta** (no numérica) a partir del texto de f(x), con `comun/derivador.py`.
- **Punto Fijo** — itera p_{n+1} = g(p_n) y además, sobre un intervalo [a, b]
  que ingresa el usuario, evalúa los dos criterios del teorema de existencia
  y unicidad:
  1. **Mapeo**: g(x) ∈ [a, b] para todo x ∈ [a, b].
  2. **Contracción**: |g'(x)| ≤ k < 1 para todo x ∈ [a, b].

  Debajo de la tabla se dibuja una gráfica con g(x), |g'(x)| y la recta
  identidad y = x, junto con un recuadro punteado que marca el intervalo
  [a, b] × [a, b] (igual que en el análisis gráfico clásico de punto fijo).

- **Steffensen** — acelera Punto Fijo con el proceso Δ² de Aitken a partir de un
  único valor inicial.
- **Müller** — usa 3 aproximaciones iniciales y una parábola; encuentra raíces
  reales y complejas.
- **Deflación** — obtiene todas las raíces de un polinomio (división sintética).
- **Trapecio y Simpson (1/3 y 3/8)** — integración numérica, en versión simple
  y compuesta.
- **Derivación numérica** — aproxima f'(x₀) con fórmulas de 2, 3 y 5 puntos
  (progresiva, regresiva, centrada y descentradas) a partir de datos
  tabulados o de una f(x). Elige automáticamente la fórmula de mayor orden,
  compara todas las fórmulas aplicables, estima el error aunque no se conozca
  f'(x), y con función compara contra la derivada exacta simbólica
  (`comun/derivador.py`), aplica extrapolación de Richardson y estudia el
  paso h (error de truncamiento vs. redondeo). Dibuja f(x) con su recta
  tangente, la derivada en los nodos y la curva error-vs-h.
- **Euler** — EDO de valor inicial: w_{i+1} = w_i + h·f(t_i, w_i).
- **Taylor** — EDO de valor inicial con serie de Taylor de orden p.

## Estructura lista para más métodos

Para agregar un método nuevo: crea su archivo en `backend/metodos/` con un
`Blueprint` de Flask, agrégalo a la lista `MODULOS` en
`backend/metodos/__init__.py`, y crea su página + script en `frontend/`.
Cada método está aislado en su propio archivo: un error en uno no afecta
a los demás.

## Ejemplos de funciones admitidas

- `x**2 - 3` o `x^2 - 3`
- `sin(x) + cos(x) - 1`
- `exp(x) - 5` o `e**x - 5`
- `log(x) - 1` (logaritmo natural), `ln(x) - 1`, `log10(x)`, `log2(x)`
- `sqrt(x) - 2`

(Newton-Raphson y Punto Fijo requieren además que la función tenga
derivada simbólica soportada: algebraica, trigonométrica, hiperbólica,
exponencial o logarítmica — no admiten `abs`, `floor` ni `ceil`.)
