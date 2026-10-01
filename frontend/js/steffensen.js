// Lógica de interfaz para Steffensen.
// El cálculo real (parseo de g(x) y la extrapolación de Aitken) se hace
// en el backend (Python), este archivo solo lee los inputs, llama a la
// API y pinta la tabla de resultados. Las utilidades de tabla/resultado
// viven en comun/tablas-y-recursos.js — cárgalo antes que este archivo.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-steffensen');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionPuntoInicial } = TablasYRecursos;

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionPuntoInicial();
            const resultado = await llamarApi('/api/steffensen/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.x0,
                fila.x1,
                fila.x2,
                fila.x,
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