// Recursos de interfaz compartidos entre los métodos (Bisección, Secante, ...).
// Cada archivo de método solo debe encargarse de leer sus inputs propios,
// llamar a la API y decidir cómo se arma cada fila de la tabla; todo lo
// repetido (formatear números, pintar la tabla, mostrar resultado/error,
// leer los campos comunes de función + intervalo) vive aquí.

(function (global) {
    function formatearNumero(numero) {
        if (numero === null || numero === undefined) {
            return '—';
        }
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

    // iteraciones: arreglo de filas devuelto por la API.
    // obtenerCeldas: función (fila) => arreglo de valores en el orden de las
    // columnas de la tabla. Cada valor se formatea con formatearNumero.
    function pintarTabla(iteraciones, obtenerCeldas) {
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

            obtenerCeldas(fila).forEach((valor) => {
                const td = document.createElement('td');
                td.textContent = formatearNumero(valor);
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

    // Campos comunes a los métodos que piden f(x) + intervalo [a, b]
    // (Bisección, Secante). Si un método futuro usa otros campos
    // (por ejemplo un único punto inicial), léelo aparte en ese archivo.
    function leerDatosFuncionIntervalo() {
        return {
            funcion: document.getElementById('function-input')?.value ?? '',
            a: document.getElementById('point-a')?.value ?? '',
            b: document.getElementById('point-b')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }
    
    // Campos comunes a los métodos que piden g(x) + un único punto
    // inicial x0 (Punto Fijo, Steffensen).
    function leerDatosFuncionPuntoInicial() {
        return {
            funcion: document.getElementById('function-input')?.value ?? '',
            x0: document.getElementById('point-x0')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }

     // Campos comunes a los métodos que piden f(x) + tres aproximaciones
    // iniciales p0, p1, p2 (Müller).
    function leerDatosFuncionTresPuntos() {
        return {
            funcion: document.getElementById('function-input')?.value ?? '',
            p0: document.getElementById('point-p0')?.value ?? '',
            p1: document.getElementById('point-p1')?.value ?? '',
            p2: document.getElementById('point-p2')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }

    // Campos para métodos que piden un polinomio (coeficientes) + tres
    // aproximaciones iniciales p0, p1, p2 (Deflación).
    function leerDatosPolinomioTresPuntos() {
        return {
            coeficientes: document.getElementById('coefficients-input')?.value ?? '',
            p0: document.getElementById('point-p0')?.value ?? '',
            p1: document.getElementById('point-p1')?.value ?? '',
            p2: document.getElementById('point-p2')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }

    // (Metodo Euler EDO, Metodo Taylor EDO). Si un método futuro usa otros campos
    function leerDatosEDO() {
    return {
        funcion: document.getElementById('function-input')?.value ?? '',
        t0: document.getElementById('point-t0')?.value ?? '',
        tn: document.getElementById('point-tn')?.value ?? '',
        n: document.getElementById('no-subintervalos')?.value ?? '',
        w0: document.getElementById('w0')?.value ?? '',
    };
}
    // (Metodo Euler EDO, Metodo Taylor EDO). Si un método futuro usa otros campos
    function leerDatosEDO_Taylor() {
    return {
        funcion: document.getElementById('function-input')?.value ?? '',
        t0: document.getElementById('point-t0')?.value ?? '',
        tn: document.getElementById('point-tn')?.value ?? '',
        n: document.getElementById('no-subintervalos')?.value ?? '',
        w0: document.getElementById('w0')?.value ?? '',
        orden: document.getElementById('orden-taylor')?.value ?? '',
    };
}

    global.TablasYRecursos = {
        formatearNumero,
        limpiarTabla,
        pintarTabla,
        mostrarResultado,
        leerDatosFuncionIntervalo,
        leerDatosFuncionPuntoInicial,
        leerDatosFuncionTresPuntos,
        leerDatosPolinomioTresPuntos,
        leerDatosEDO,
        leerDatosEDO_Taylor,
    };
})(typeof window !== 'undefined' ? window : globalThis);