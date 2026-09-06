// Lógica de interfaz para Secante.
// El cálculo real (parseo de f(x) e iteraciones) se hace en el backend
// (Python), este archivo solo lee los inputs, llama a la API y pinta
// la tabla de resultados.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-secante');

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
                formatearNumero(fila.p0),
                formatearNumero(fila.p1),
                formatearNumero(fila.p2),
                formatearNumero(fila.fp2),
                formatearNumero(fila.error),
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
            funcion: document.getElementById('function-input')?.value ?? '',
            a: document.getElementById('point-a')?.value ?? '',
            b: document.getElementById('point-b')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosDesdeInputs();
            const resultado = await llamarApi('/api/secante/calcular', datos);

            pintarTabla(resultado.iteraciones);
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            limpiarTabla();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });
});
