// Lógica de interfaz del método de Romberg.
// El cálculo se hace en el backend (metodos/romberg.py, que a su vez reutiliza el
// trapecio compuesto de trapecio_simpsons.py). Aquí se leen los inputs, se llama
// a la API y la tabla se dibuja con TablaPasos (js/tabla-pasos.js).
// Orden de scripts: api.js -> tablas-y-recursos.js -> tabla-pasos.js -> romberg.js

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado } = TablasYRecursos;

    const botonCalcular = document.getElementById('calcular-romberg');
    const contenedorTabla = document.getElementById('steps-sections');

    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    function leerDatos() {
        return {
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            tolerancia: valorDe('tolerance'),
            maxIteraciones: valorDe('max-iterations'),
        };
    }

    // Etiqueta de cada columna: R(k,0) es el trapecio y cada una siguiente
    // elimina un término más del error (O(h²), O(h⁴), O(h⁶)...).
    const SUPERINDICES = '⁰¹²³⁴⁵⁶⁷⁸⁹';
    const superindice = (n) => String(n).replace(/\d/g, (d) => SUPERINDICES[d]);

    function nombreColumna(j) {
        return j === 0 ? 'Trapecio O(h²)' : `R(k,${j}) O(h${superindice(2 * j + 2)})`;
    }

    // Convierte las filas del backend en una sola sección para TablaPasos.
    function construirSeccion(iteraciones) {
        const columnas = iteraciones.length;

        const encabezados = ['k', 'n', 'h'];
        for (let j = 0; j < columnas; j++) {
            encabezados.push(nombreColumna(j));
        }
        encabezados.push('Error');

        const filas = iteraciones.map((fila) => {
            const celdas = [fila.k, fila.n, fila.h];
            for (let j = 0; j < columnas; j++) {
                celdas.push(j <= fila.k ? fila.r[j] : null); // null = celda vacía
            }
            celdas.push(fila.error); // null en k = 0
            return celdas;
        });

        // Diagonal R(k,k): columna k + 3 (k, n y h van antes).
        const resaltar = iteraciones.map((fila) => [fila.k, fila.k + 3]);

        return {
            titulo: 'Resultados por iteración',
            columnas: encabezados,
            filas,
            resaltar,
        };
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/romberg/calcular', leerDatos());
            TablaPasos.pintar(contenedorTabla, [construirSeccion(resultado.iteraciones)]);
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            contenedorTabla.innerHTML = '';
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });
});