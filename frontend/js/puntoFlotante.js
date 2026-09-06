// Lógica de interfaz para Punto Flotante (IEEE 754).
// Todo el cálculo real se hace en el backend (Python), este archivo solo
// lee los inputs, llama a la API y pinta el resultado.

document.addEventListener('DOMContentLoaded', function () {
    const botonBinarioADecimal = document.getElementById('binary-to-decimal');
    const botonDecimalABinario = document.getElementById('decimal-to-binary');

    function mostrarResultado(texto, esError = false) {
        const resultadoEl = document.getElementById('result');
        const errorEl = document.getElementById('error-message');

        if (!resultadoEl || !errorEl) {
            return;
        }

        resultadoEl.textContent = esError ? '' : texto;
        errorEl.textContent = esError ? texto : '';
    }

    function obtenerBits() {
        const select = document.getElementById('bits-select');
        return Number(select ? select.value : 32);
    }

    botonBinarioADecimal?.addEventListener('click', async function () {
        botonBinarioADecimal.disabled = true;
        try {
            const bits = obtenerBits();
            const binario = document.getElementById('binary-input')?.value ?? '';

            if (!binario.trim()) {
                throw new Error('Ingresa una representación binaria antes de convertir.');
            }

            const resultado = await llamarApi('/api/punto-flotante/binario-a-decimal', { binario, bits });

            if (resultado.especial) {
                mostrarResultado(`Resultado: ${resultado.especial} | Desglose: ${resultado.descripcion}`);
            } else {
                mostrarResultado(`Resultado: ${resultado.decimal} | Desglose (signo | característica | mantisa): ${resultado.descripcion}`);
            }
        } catch (error) {
            mostrarResultado(error.message, true);
        } finally {
            botonBinarioADecimal.disabled = false;
        }
    });

    botonDecimalABinario?.addEventListener('click', async function () {
        botonDecimalABinario.disabled = true;
        try {
            const bits = obtenerBits();
            const valor = document.getElementById('decimal-input')?.value ?? '';

            if (!valor.trim()) {
                throw new Error('Ingresa un valor decimal antes de convertir.');
            }

            const resultado = await llamarApi('/api/punto-flotante/decimal-a-binario', { valor, bits });

            mostrarResultado(
                `Resultado: ${resultado.descripcion} | Binario completo (${resultado.bits} bits): ${resultado.binario}`
            );
        } catch (error) {
            mostrarResultado(error.message, true);
        } finally {
            botonDecimalABinario.disabled = false;
        }
    });
});
