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
│       │   └── parser_funciones.py  # Parser seguro de f(x): trig, e^x, log, algebraicas...
│       ├── punto_flotante.py      # Conversión IEEE 754 (antes "Punto Fijo")
│       ├── biseccion.py           # Método de Bisección
│       └── secante.py             # Método de la Secante
└── frontend/
    ├── index.html
    ├── PuntoFlotante.html
    ├── Biseccion.html
    ├── Secante.html
    ├── FalsaPosicion.html         # Próximamente
    ├── NewtonRaphson.html         # Próximamente
    ├── styles.css
    └── js/
        ├── api.js                 # Helper de conexión con el backend
        ├── puntoFlotante.js
        ├── biseccion.js
        └── secante.js
```

## Cómo ejecutarlo

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Abre **http://localhost:5000** en el navegador. El propio backend sirve el
frontend, así que no necesitas nada más.

(Si prefieres abrir los archivos HTML directamente con doble clic, también
funciona: solo asegúrate de que `python app.py` siga corriendo, ya que
`frontend/js/api.js` llama a `http://localhost:5000` por defecto.)

## Qué cambió respecto a la versión anterior

- **Backend movido de JavaScript a Python** (Flask), con la interfaz en
  HTML/CSS/JavaScript consumiendo esa API por medio de `fetch`.
- **Cada método vive en su propio archivo** (`punto_flotante.py`,
  `biseccion.py`, `secante.py`). `app.py` los registra de forma aislada:
  si un archivo tiene un error, los demás métodos siguen funcionando.
- **Las funciones f(x) ahora aceptan cualquier tipo de expresión**:
  algebraicas (`x**2 - 3`), trigonométricas (`sin(x)`, `cos(x)`, `tan(x)`,
  ...), hiperbólicas (`sinh`, `cosh`, `tanh`), exponenciales con `e`
  (`exp(x)`, `e**x`), logarítmicas (`log`, `ln`, `log10`, `log2`), raíz
  cuadrada (`sqrt`), valor absoluto (`abs`), etc. Esto se validó y evalúa
  de forma segura en el backend (no se usa `eval` sin restricciones).
- **"Punto Fijo" se renombró a "Punto Flotante"**: lo que hacía ese método
  siempre fue una conversión decimal ↔ binario en punto flotante (signo,
  característica/exponente y mantisa), no el método iterativo de punto
  fijo, así que el nombre ahora es el correcto.
- **El selector de bits ahora solo permite 16, 32 o 64**, usando el
  estándar **IEEE 754** real (media precisión, precisión simple y
  precisión doble) a través del módulo `struct` de Python, que garantiza
  una representación 100% conforme al estándar.
- **Bisección ahora muestra dos columnas de error**: el error absoluto
  (mitad del ancho del intervalo, como antes) y el error aproximado
  (variación porcentual entre la aproximación actual y la anterior).
- **Estructura lista para más métodos**: para agregar uno nuevo (por
  ejemplo Falsa Posición o Newton-Raphson) solo hace falta crear su
  archivo en `backend/metodos/`, agregarlo a la lista `MODULOS` en
  `backend/metodos/__init__.py`, y crear su página + script en
  `frontend/`. Ya se dejaron las páginas de Falsa Posición y
  Newton-Raphson como "Próximamente" con esa guía incluida.

## Ejemplos de funciones f(x) admitidas

- `x**2 - 3` o `x^2 - 3`
- `sin(x) + cos(x) - 1`
- `exp(x) - 5` o `e**x - 5`
- `log(x) - 1` (logaritmo natural), `ln(x) - 1`, `log10(x)`, `log2(x)`
- `sqrt(x) - 2`
