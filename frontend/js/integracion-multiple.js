// Interfaz de la integración múltiple (integral doble con trapecio compuesto).
// El cálculo se hace en el backend (metodos/integracion_multiple.py); aquí se
// elige cómo está delimitada la región (intervalos o funciones), se leen los
// campos que corresponden, se llama a la API y se muestra el resultado.
// Las utilidades compartidas viven en tablas-y-recursos.js — cárgalo antes.

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado } = TablasYRecursos;

    const estado = { tipo: 'intervalos' };

    const PISTAS = {
        intervalos: 'Rectángulo [a, b] × [c, d]:   I = ∫ₐᵇ [ ∫ f(x, y) dy ] dx,   con y entre c y d.',
        funciones: 'Región entre curvas:   I = ∫ₐᵇ [ ∫ f(x, y) dy ] dx,   con y entre f₁(x) y f₂(x).',
    };


    const botonesTipo = Array.from(document.querySelectorAll('.segmented__btn[data-grupo="tipo"]'));
    const botonCalcular = document.getElementById('calcular-integracion-multiple');
    const pista = document.getElementById('formula-hint');

    const camposIntervalos = ['campo-c', 'campo-d'].map((id) => document.getElementById(id));
    const camposFunciones = ['campo-f1', 'campo-f2'].map((id) => document.getElementById(id));

    const valorDe = (id) => document.getElementById(id)?.value ?? '';

    function actualizarVista() {
        camposIntervalos.forEach((campo) => { campo.hidden = estado.tipo !== 'intervalos'; });
        camposFunciones.forEach((campo) => { campo.hidden = estado.tipo !== 'funciones'; });
        pista.textContent = PISTAS[estado.tipo];
        mostrarResultado('');
    }

    botonesTipo.forEach((boton) => {
        boton.addEventListener('click', () => {
            estado.tipo = boton.dataset.valor;

            botonesTipo.forEach((otro) => {
                const activo = otro === boton;
                otro.classList.toggle('is-active', activo);
                otro.setAttribute('aria-pressed', String(activo));
            });

            actualizarVista();
        });
    });

    // Solo se envían los campos del tipo elegido: c y d con intervalos,
    // f1 y f2 con funciones.
    function leerDatosIntegracionMultiple() {
        const datos = {
            tipo: estado.tipo,
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            n: valorDe('subint-n'),
            m: valorDe('subint-m'),
        };

        if (estado.tipo === 'intervalos') {
            datos.c = valorDe('point-c');
            datos.d = valorDe('point-d');
        } else {
            datos.f1 = valorDe('function-f1');
            datos.f2 = valorDe('function-f2');
        }

        return datos;
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/integracion_multiple/calcular', leerDatosIntegracionMultiple());
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    actualizarVista();
});