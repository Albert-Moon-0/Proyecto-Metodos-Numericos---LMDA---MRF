"""
Punto de entrada del backend.

Este servidor Flask hace dos cosas:
1. Sirve el frontend estático (los archivos HTML/CSS/JS de la carpeta
   `frontend/`) para que puedas abrir el proyecto en el navegador con
   una sola URL.
2. Expone la API en `/api/...` con la lógica de cada método numérico,
   registrada de forma aislada por archivo (ver `metodos/__init__.py`).

Para ejecutarlo:
    cd backend
    pip install -r requirements.txt
    python app.py

Luego abre http://localhost:5000 en el navegador.
"""

import importlib
import logging
import os

from flask import Flask
from flask_cors import CORS

from metodos import MODULOS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('app')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'frontend'))


def registrar_metodos(app):
    """Importa y registra cada método de forma aislada.

    Si un método tiene un error (de sintaxis, de importación, etc.) se
    registra el error en el log pero el resto de los métodos y el
    servidor siguen funcionando con normalidad.
    """

    registrados = []

    for nombre_modulo in MODULOS:
        try:
            modulo = importlib.import_module(f'metodos.{nombre_modulo}')
            app.register_blueprint(modulo.blueprint)
            registrados.append(nombre_modulo)
            logger.info('Método registrado correctamente: %s', nombre_modulo)
        except Exception as error:  # noqa: BLE001 - aislar errores por método
            logger.error('No se pudo registrar el método "%s": %s', nombre_modulo, error)

    return registrados


def crear_app():
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
    CORS(app)

    metodos_activos = registrar_metodos(app)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/api/salud')
    def salud():
        return {'estado': 'ok', 'metodosDisponibles': metodos_activos}

    return app


app = crear_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
