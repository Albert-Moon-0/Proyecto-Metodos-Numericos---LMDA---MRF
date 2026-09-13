# Proyecto Métodos Numéricos — LMDA · MRF

Backend en **Python (Flask)** + Frontend en **HTML/CSS/JavaScript**.

## Estructura

```
proyecto-metodos-numericos/
├── backend/
│   ├── app.py                     # Servidor Flask (API + sirve el frontend)
│   ├── requirements.txt
│   └── metodos/
│       ├── __init__.py            # Registro central de métodos (ver abajo)
│       ├── comun/
│       │   ├── parser_funciones.py  # Parser seguro de f(x): trig, e^x, log, algebraicas...
│       │   └── derivador.py         # Derivada simbólica exacta (usada por Newton-Raphson y Punto Fijo)
│       ├── punto_flotante.py      # Conversión IEEE 754 (antes "Punto Fijo")
│       ├── biseccion.py           # Método de Bisección
│       ├── secante.py             # Método de la Secante
│       ├── falsa_posicion.py      # Método de la Falsa Posición
│       ├── newton_raphson.py      # Método de Newton-Raphson
│       └── punto_fijo.py          # Método de Punto Fijo (con análisis de existencia/unicidad)
└── frontend/
    ├── index.html
    ├── PuntoFlotante.html
    ├── Biseccion.html
    ├── Secante.html
    ├── FalsaPosicion.html
    ├── NewtonRaphson.html
    ├── PuntoFijo.html
    ├── styles.css
    └── js/
        ├── api.js                   # Helper de conexión con el backend
        ├── tablas-y-recursos.js     # Utilidades compartidas de tabla/resultado
        ├── puntoFlotante.js
        ├── biseccion.js
        ├── secante.js
        ├── falsa-posicion.js
        ├── newton-raphson.js
        └── punto-fijo.js
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
