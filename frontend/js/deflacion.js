// Lógica de interfaz para Deflación.
// El cálculo real (Müller + división sintética sobre los coeficientes)
// se hace en el backend (Python); este archivo solo lee los inputs,
// llama a la API y pinta la tabla de raíces encontradas. A diferencia
// de los demás métodos, la tabla aquí no es "iteración por iteración"
// de una sola raíz, sino una fila por cada raíz del polinomio.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-deflacion');
    const { pintarTabla, limpiarTabla, mostrarResultado, leerDatosPolinomioTresPuntos } = TablasYRecursos;

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatosPolinomioTresPuntos();
            const resultado = await llamarApi('/api/deflacion/calcular', datos);

            pintarTabla(resultado.raices, (fila) => [
                fila.numero,
                fila.grado,
                fila.raiz,
                fila.iteraciones,
                fila.residuo,
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