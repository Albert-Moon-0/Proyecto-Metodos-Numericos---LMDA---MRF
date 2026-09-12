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
import sys
import threading
import webbrowser

from flask import Flask
from flask_cors import CORS

from metodos import MODULOS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('app')

# NUEVO: detectar si estamos corriendo como .exe empaquetado (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # carpeta temporal donde PyInstaller extrae los datos
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'frontend'))


def registrar_metodos(app):
    registrados = []
    for nombre_modulo in MODULOS:
        try:
            modulo = importlib.import_module(f'metodos.{nombre_modulo}')
            app.register_blueprint(modulo.blueprint)
            registrados.append(nombre_modulo)
            logger.info('Método registrado correctamente: %s', nombre_modulo)
        except Exception as error:  # noqa: BLE001
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


# NUEVO: abrir el navegador automáticamente medio segundo después de arrancar
def abrir_navegador():
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        # Dentro del .exe: sin debug/reloader, y abrimos el navegador solos
        threading.Timer(0.75, abrir_navegador).start()
        app.run(host='localhost', port=5000, debug=False)
    else:
        # Modo desarrollo normal en VS Code
        app.run(host='localhost', port=5000, debug=True)