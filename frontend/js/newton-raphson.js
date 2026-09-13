// Lógica de interfaz para Newton-Raphson.
// El cálculo real (parseo de f(x), derivada simbólica e iteraciones) se
// hace en el backend (Python); este archivo solo lee los inputs, llama
// a la API y pinta la tabla usando las utilidades de
// comun/tablas-y-recursos.js.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-newton');
    const { pintarTabla, limpiarTabla, mostrarResultado } = TablasYRecursos;

    function leerDatos() {
        return {
            funcion: document.getElementById('function-input')?.value ?? '',
            p0: document.getElementById('p0-input')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
        };
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatos();
            const resultado = await llamarApi('/api/newton-raphson/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.p0,
                fila.fp0,
                fila.dfp0,
                fila.p1,
                fila.errorAbsoluto,
                fila.errorAproximado,
            ]);
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            limpiarTabla();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });
});
