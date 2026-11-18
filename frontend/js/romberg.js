// Lógica de interfaz para Romberg.
// El cálculo real (parseo de f(x) e iteraciones) se hace en el backend
// (Python), este archivo solo lee los inputs, llama a la API y pinta
// la tabla de resultados.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-romberg');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosFuncionIntervalo } = TablasYRecursos;
 
    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosFuncionIntervalo();
            const resultado = await llamarApi('/api/romberg/calcular', datos);
 
            pintarTabla(resultado.n, (fila) => [
                fila.n,
                fila.Trapecio,
                fila.h4,
                fila.h6,
                fila.h8,
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
