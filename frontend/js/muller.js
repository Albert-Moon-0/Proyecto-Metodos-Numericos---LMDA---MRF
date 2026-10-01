// Lógica de interfaz para Müller.
// El cálculo real (parseo de f(x), aritmética real/compleja) se hace en
// el backend (Python); este archivo solo lee los inputs, llama a la API
// y pinta la tabla. p0..p3 y f(p3) pueden venir como número o como
// {re, im} cuando el backend encuentra una aproximación compleja —
// pintarTabla/formatearNumero (en tablas-y-recursos.js) ya saben
// mostrar ambos casos.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-muller');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionTresPuntos } = TablasYRecursos;

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionTresPuntos();
            const resultado = await llamarApi('/api/muller/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.p0,
                fila.p1,
                fila.p2,
                fila.p3,
                fila.fp3,
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