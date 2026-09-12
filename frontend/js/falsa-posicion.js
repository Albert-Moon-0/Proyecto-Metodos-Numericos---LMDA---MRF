// Lógica de interfaz para Falsa Posición.
// El cálculo real (parseo de f(x) e iteraciones) se hace en el backend
// (Python), este archivo solo lee los inputs, llama a la API y pinta
// la tabla de resultados. Las utilidades de tabla/resultado viven en
// comun/tablas-y-recursos.js — cárgalo antes que este archivo en el HTML.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-falsa-posicion');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionIntervalo } = TablasYRecursos;

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionIntervalo();
            const resultado = await llamarApi('/api/falsa-posicion/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.a,
                fila.b,
                fila.c,
                fila.fc,
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