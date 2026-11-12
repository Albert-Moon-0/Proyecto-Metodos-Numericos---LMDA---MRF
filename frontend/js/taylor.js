// Lógica de interfaz para Taylor.
// El cálculo real (parseo de f(t, y) y las iteraciones) se hace en el
// backend (Python); este archivo solo lee los inputs, llama a la API y
// pinta la tabla de resultados. Las utilidades de tabla/resultado viven
// en tablas-y-recursos.js — cárgalo antes que este archivo en el HTML.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-taylor');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosEDO_Taylor } = TablasYRecursos;

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosEDO_Taylor();
            const resultado = await llamarApi('/api/taylor/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.t,
                fila.w,
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