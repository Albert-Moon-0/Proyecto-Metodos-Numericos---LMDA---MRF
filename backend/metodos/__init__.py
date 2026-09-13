"""
Registro central de métodos numéricos.

Cada método vive en su propio archivo dentro de esta carpeta
(por ejemplo `biseccion.py`, `secante.py`, `punto_flotante.py`) y expone
un Blueprint de Flask llamado `blueprint`. `app.py` registra cada uno
de forma aislada: si un método tiene un error de importación o de
sintaxis, los demás métodos siguen funcionando con normalidad.

Cómo agregar un método nuevo en el futuro (por ejemplo Newton-Raphson):

1. Crea `metodos/newton_raphson.py`.
2. Dentro de ese archivo define un `Blueprint` de Flask llamado `blueprint`
   con su propio `url_prefix` (por ejemplo '/api/newton-raphson').
3. Si el método necesita evaluar f(x), reutiliza
   `metodos.comun.parser_funciones.crear_funcion`.
4. Agrega el nombre del archivo (sin ".py") a la lista MODULOS de abajo.
5. Crea su página en `frontend/` (HTML) y su script en `frontend/js/`.

No hace falta tocar nada más: `app.py` lo registrará automáticamente.
"""

MODULOS = [
    'punto_flotante',
    'biseccion',
    'secante',
    'falsa_posicion',
    'newton_raphson',
    'punto_fijo',
]
