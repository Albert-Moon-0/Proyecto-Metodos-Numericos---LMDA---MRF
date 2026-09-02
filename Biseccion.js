(function (global) {
    function limpiarTexto(texto) {
        return String(texto).trim().replace(/\s+/g, '');
    }

    // Nombres permitidos dentro de la expresión: la variable "x" y las
    // funciones/constantes estáticas de Math (sin, cos, sqrt, PI, etc.).
    // Cualquier otro identificador (por ejemplo, un objeto o función global)
    // se rechaza para que la expresión solo pueda hacer cálculo matemático.
    const NOMBRES_PERMITIDOS = new Set([
        'x',
        ...Object.getOwnPropertyNames(Math)
    ]);

    // Convierte el texto de la función (ej. "x**2 - 3" o "x^2 - 3") en f(x) evaluable.
    // Se restringe a caracteres típicos de una expresión matemática y, además,
    // se verifica que cada identificador usado esté en NOMBRES_PERMITIDOS.
    function crearFuncion(expresionOriginal) {
        const expresion = String(expresionOriginal).trim();

        if (!expresion) {
            throw new Error('Ingresa una función f(x).');
        }

        if (!/^[0-9x.+\-*/^(),\s a-zA-Z]+$/.test(expresion)) {
            throw new Error('La función contiene caracteres no permitidos.');
        }

        const identificadores = expresion.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || [];
        const noPermitido = identificadores.find((nombre) => !NOMBRES_PERMITIDOS.has(nombre));

        if (noPermitido) {
            throw new Error(`"${noPermitido}" no es un nombre válido en f(x). Usa "x" y funciones de Math (sin, cos, sqrt, ...).`);
        }

        const expresionJS = expresion.replace(/\^/g, '**');

        let evaluador;
        try {
            evaluador = new Function('x', `with (Math) { return (${expresionJS}); }`);
        } catch (error) {
            throw new Error('No se pudo interpretar la función. Revisa la sintaxis.');
        }

        return function (valor) {
            let resultado;
            try {
                resultado = evaluador(valor);
            } catch (error) {
                throw new Error('No se pudo evaluar la función en x = ' + valor + '.');
            }

            if (typeof resultado !== 'number' || !Number.isFinite(resultado)) {
                throw new Error(`f(${valor}) no produjo un número válido. Revisa la función.`);
            }

            return resultado;
        };
    }

    function leerNumero(valor, nombreCampo) {
        const limpio = limpiarTexto(valor);
        const numero = Number(limpio);

        if (limpio === '' || !Number.isFinite(numero)) {
            throw new Error(`El campo "${nombreCampo}" debe ser un número válido.`);
        }

        return numero;
    }

    function leerEnteroPositivo(valor, nombreCampo) {
        const numero = leerNumero(valor, nombreCampo);

        if (!Number.isInteger(numero) || numero <= 0) {
            throw new Error(`El campo "${nombreCampo}" debe ser un entero positivo.`);
        }

        return numero;
    }

    function biseccion(f, a, b, tolerancia, maxIteraciones) {
        if (f(a) * f(b) >= 0) {
            throw new Error('El intervalo no es válido: f(a) y f(b) deben tener signos opuestos.');
        }

        const iteraciones = [];
        let c = a;

        for (let i = 1; i <= maxIteraciones; i += 1) {
            c = (a + b) / 2;
            const fc = f(c);
            const error = (b - a) / 2;

            iteraciones.push({ iteracion: i, a, b, c, fc, error });

            if (fc === 0 || error < tolerancia) {
                return { raiz: c, iteraciones, convergio: true };
            }

            if (f(a) * fc < 0) {
                b = c;
            } else {
                a = c;
            }
        }

        return { raiz: c, iteraciones, convergio: false };
    }

    function formatearNumero(numero) {
        if (!Number.isFinite(numero)) {
            return String(numero);
        }
        return Number(numero.toFixed(6)).toString();
    }

    function limpiarTabla() {
        const cuerpo = document.getElementById('result-table-body');
        if (cuerpo) {
            cuerpo.innerHTML = '';
        }
    }

    function pintarTabla(iteraciones) {
        const cuerpo = document.getElementById('result-table-body');
        if (!cuerpo) {
            return;
        }

        cuerpo.innerHTML = '';

        iteraciones.forEach((fila, indice) => {
            const tr = document.createElement('tr');

            if (indice === iteraciones.length - 1) {
                tr.classList.add('is-final');
            }

            const celdas = [
                fila.iteracion,
                formatearNumero(fila.a),
                formatearNumero(fila.b),
                formatearNumero(fila.c),
                formatearNumero(fila.fc),
                formatearNumero(fila.error)
            ];

            celdas.forEach((valor) => {
                const td = document.createElement('td');
                td.textContent = valor;
                tr.appendChild(td);
            });

            cuerpo.appendChild(tr);
        });
    }

    function mostrarResultado(texto, esError = false) {
        const resultadoEl = document.getElementById('result');
        const errorEl = document.getElementById('error-message');

        if (!resultadoEl || !errorEl) {
            return;
        }

        resultadoEl.textContent = esError ? '' : texto;
        errorEl.textContent = esError ? texto : '';
    }

    function leerDatosDesdeInputs() {
        return {
            expresion: document.getElementById('function-input')?.value ?? '',
            a: document.getElementById('point-a')?.value ?? '',
            b: document.getElementById('point-b')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? ''
        };
    }

    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', function () {
            const botonCalcular = document.getElementById('calcular-biseccion');

            botonCalcular?.addEventListener('click', function () {
                try {
                    const datos = leerDatosDesdeInputs();

                    const a = leerNumero(datos.a, 'Punto a');
                    const b = leerNumero(datos.b, 'Punto b');
                    const tolerancia = leerNumero(datos.tolerancia, 'Error máximo');
                    const maxIteraciones = leerEnteroPositivo(datos.maxIteraciones, 'Iteraciones máximas');

                    if (a === b) {
                        throw new Error('Los puntos "a" y "b" deben ser distintos.');
                    }

                    if (tolerancia <= 0) {
                        throw new Error('El error máximo debe ser mayor que cero.');
                    }

                    const f = crearFuncion(datos.expresion);
                    const { raiz, iteraciones, convergio } = biseccion(f, a, b, tolerancia, maxIteraciones);

                    pintarTabla(iteraciones);

                    const mensaje = convergio
                        ? `Raíz aproximada: x ≈ ${formatearNumero(raiz)} (${iteraciones.length} iteraciones)`
                        : `No se alcanzó la tolerancia tras ${iteraciones.length} iteraciones. Mejor aproximación: x ≈ ${formatearNumero(raiz)}`;

                    mostrarResultado(mensaje);
                } catch (error) {
                    limpiarTabla();
                    mostrarResultado(error.message, true);
                }
            });
        });
    }

    const api = {
        limpiarTexto,
        crearFuncion,
        biseccion,
        formatearNumero
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }

    global.Biseccion = api;
})(typeof window !== 'undefined' ? window : globalThis);