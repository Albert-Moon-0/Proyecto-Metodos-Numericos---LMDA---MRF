"""
Método: Punto Flotante (IEEE 754)

Convierte números decimales a su representación binaria en punto
flotante y viceversa, siguiendo el estándar IEEE 754 en sus tres
tamaños más comunes: 16 bits (media precisión), 32 bits (precisión
simple) y 64 bits (precisión doble).

Este archivo es independiente del resto de los métodos: si algo falla
aquí, no afecta a Bisección, Secante ni a métodos futuros.
"""

import math
import struct

from flask import Blueprint, jsonify, request

blueprint = Blueprint('punto_flotante', __name__, url_prefix='/api/punto-flotante')

# Formato de empaquetado de Python (struct) y desglose de bits para cada
# tamaño estándar de IEEE 754. Usar struct.pack/unpack garantiza una
# representación 100% conforme al estándar (redondeo, exponente sesgado,
# bit implícito, etc. los maneja la propia biblioteca de Python).
FORMATOS = {
    16: {'struct': '>e', 'bits_signo': 1, 'bits_exponente': 5, 'bits_mantisa': 10},
    32: {'struct': '>f', 'bits_signo': 1, 'bits_exponente': 8, 'bits_mantisa': 23},
    64: {'struct': '>d', 'bits_signo': 1, 'bits_exponente': 11, 'bits_mantisa': 52},
}


class ErrorPuntoFlotante(Exception):
    """Se lanza cuando la entrada del usuario no puede convertirse."""


def _validar_bits(bits):
    try:
        bits = int(bits)
    except (TypeError, ValueError):
        raise ErrorPuntoFlotante('Selecciona una cantidad de bits válida: 16, 32 o 64.')

    if bits not in FORMATOS:
        raise ErrorPuntoFlotante('Selecciona una cantidad de bits válida: 16, 32 o 64.')

    return bits


def decimal_a_binario(valor, bits):
    """Convierte un número decimal a su representación IEEE 754 de `bits` bits."""

    bits = _validar_bits(bits)
    formato = FORMATOS[bits]

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorPuntoFlotante('El valor decimal ingresado no es válido.')

    if math.isnan(numero) or math.isinf(numero):
        raise ErrorPuntoFlotante('Ingresa un valor decimal finito.')

    try:
        empaquetado = struct.pack(formato['struct'], numero)
    except OverflowError as error:
        raise ErrorPuntoFlotante(
            f'El valor excede el rango representable en {bits} bits (IEEE 754).'
        ) from error

    cadena_bits = ''.join(f'{byte:08b}' for byte in empaquetado)

    s = formato['bits_signo']
    e = formato['bits_exponente']
    m = formato['bits_mantisa']

    signo = cadena_bits[:s]
    caracteristica = cadena_bits[s:s + e]
    mantisa = cadena_bits[s + e:s + e + m]

    return {
        'decimal': numero,
        'bits': bits,
        'binario': cadena_bits,
        'signo': signo,
        'caracteristica': caracteristica,
        'mantisa': mantisa,
        'descripcion': f'{signo} | {caracteristica} | {mantisa}',
    }


def binario_a_decimal(cadena_binaria, bits):
    """Convierte una cadena binaria IEEE 754 de `bits` bits a su valor decimal."""

    bits = _validar_bits(bits)
    formato = FORMATOS[bits]

    limpio = ''.join(str(cadena_binaria if cadena_binaria is not None else '').split())

    if not limpio:
        raise ErrorPuntoFlotante('Ingresa una representación binaria antes de convertir.')

    if any(caracter not in '01' for caracter in limpio):
        raise ErrorPuntoFlotante('La representación binaria solo debe contener 0 y 1.')

    if len(limpio) != bits:
        raise ErrorPuntoFlotante(
            f'Se esperaba una cadena de {bits} bits, pero se recibieron {len(limpio)}.'
        )

    s = formato['bits_signo']
    e = formato['bits_exponente']
    m = formato['bits_mantisa']

    signo = limpio[:s]
    caracteristica = limpio[s:s + e]
    mantisa = limpio[s + e:s + e + m]

    entero = int(limpio, 2)
    empaquetado = entero.to_bytes(bits // 8, byteorder='big')
    valor = struct.unpack(formato['struct'], empaquetado)[0]

    especial = None
    if math.isnan(valor):
        especial = 'NaN (no es un número)'
    elif math.isinf(valor):
        especial = 'Infinito positivo' if valor > 0 else 'Infinito negativo'

    return {
        'decimal': None if especial else valor,
        'especial': especial,
        'bits': bits,
        'signo': signo,
        'caracteristica': caracteristica,
        'mantisa': mantisa,
        'descripcion': f'{signo} | {caracteristica} | {mantisa}',
    }


@blueprint.route('/decimal-a-binario', methods=['POST'])
def ruta_decimal_a_binario():
    try:
        datos = request.get_json(force=True, silent=True) or {}
        resultado = decimal_a_binario(datos.get('valor'), datos.get('bits'))
        return jsonify(resultado)
    except ErrorPuntoFlotante as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en Punto Flotante: {error}'}), 500


@blueprint.route('/binario-a-decimal', methods=['POST'])
def ruta_binario_a_decimal():
    try:
        datos = request.get_json(force=True, silent=True) or {}
        resultado = binario_a_decimal(datos.get('binario'), datos.get('bits'))
        return jsonify(resultado)
    except ErrorPuntoFlotante as error:
        return jsonify({'error': str(error)}), 400
    except Exception as error:  # noqa: BLE001 - aislar errores de este método
        return jsonify({'error': f'Error inesperado en Punto Flotante: {error}'}), 500
