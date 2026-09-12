// Lógica de interfaz para Secante.
// El cálculo real (parseo de f(x) e iteraciones) se hace en el backend
// (Python), este archivo solo lee los inputs, llama a la API y pinta
// la tabla de resultados.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-secante');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionIntervalo } = TablasYRecursos;
 
    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionIntervalo();
            const resultado = await llamarApi('/api/secante/calcular', datos);
 
            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.p0,
                fila.p1,
                fila.p2,
                fila.fp2,
                fila.error,
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