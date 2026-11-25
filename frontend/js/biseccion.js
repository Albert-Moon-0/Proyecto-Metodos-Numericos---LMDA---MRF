// Lógica de interfaz para Bisección.
// El cálculo real (parseo de f(x) e iteraciones) se hace en el backend
// (Python), este archivo solo lee los inputs, llama a la API, pinta
// la tabla de resultados y la gráfica (js/grafica-biseccion.js).

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-biseccion');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionIntervalo } = TablasYRecursos;
 
    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionIntervalo();
            const resultado = await llamarApi('/api/biseccion/calcular', datos);
 
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
            GraficaBiseccion.mostrar(resultado);
        } catch (error) {
            limpiarTabla();
            mostrarResultado(error.message, true);
            GraficaBiseccion.limpiar();
        } finally {
            botonCalcular.disabled = false;
        }
    });
});