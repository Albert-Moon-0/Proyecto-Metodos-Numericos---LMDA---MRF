// Lógica de interfaz para el Spline cúbico natural.
// El cálculo real se hace en el backend (Python, metodos/spline_cubico.py);
// este archivo lee los inputs, llama a la API, pinta las fórmulas de cada
// tramo, las tablas del procedimiento (tabla-pasos.js) y dibuja f(x) junto
// con los splines (grafica.js).
// Cárgalo después de api.js, tablas-y-recursos.js, grafica.js y tabla-pasos.js.

document.addEventListener('DOMContentLoaded', function () {
    const { formatearNumero, mostrarResultado } = TablasYRecursos;

    const COLOR_F = '#4fd1c5';
    // Los tramos alternan de color para distinguir dónde cambia de spline.
    const COLORES_SPLINE = ['#b892f0', '#e879f9'];
    const COLOR_NODOS = '#f2a4a0';
    const COLOR_EVALUACION = '#f6c177';
    const SUBINDICES = '₀₁₂₃₄₅₆₇₈₉';

    const botonCalcular = document.getElementById('calcular-spline');
    const botonCopiar = document.getElementById('copiar-splines');
    const bloqueResultado = document.getElementById('spline-detalle');
    const splinesEl = document.getElementById('spline-output');
    const evaluacionEl = document.getElementById('evaluation-output');
    const errorMaxEl = document.getElementById('max-error-output');

    const graficaVacia = document.getElementById('graph-empty');
    const marcoGrafica = document.getElementById('graph-frame');
    const leyenda = document.getElementById('graph-legend');

    const panelPasos = document.getElementById('steps-panel');
    const seccionesPasos = document.getElementById('steps-sections');

    const grafica = GraficaSVG.montar(document.getElementById('graph-svg'));

    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    function leerDatos() {
        return {
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            puntos: valorDe('point-count'),
            xEvaluar: valorDe('evaluate-x'),
        };
    }

    function subindice(numero) {
        return String(numero).replace(/\d/g, (d) => SUBINDICES[Number(d)]);
    }

    function textoEvaluacion(ev) {
        if (!ev) {
            return '';
        }

        let texto = `S(${formatearNumero(ev.x)}) = ${formatearNumero(ev.s)}  (tramo S${subindice(ev.tramo)})`;
        if (ev.f !== null && ev.f !== undefined) {
            texto += `   ·   f(${formatearNumero(ev.x)}) = ${formatearNumero(ev.f)}`;
            texto += `   ·   |error| = ${Number(ev.error.toPrecision(4))}`;
        }
        return texto;
    }

    function dibujar(resultado) {
        const series = [
            { puntos: resultado.grafica.puntosF, color: COLOR_F, ancho: 2.5, etiqueta: 'f(x) original' },
        ];

        resultado.grafica.tramosS.forEach((puntos, j) => {
            series.push({
                puntos,
                color: COLORES_SPLINE[j % COLORES_SPLINE.length],
                ancho: 2.25,
                discontinua: true,
                etiqueta: j === 0 ? 'S(x) spline cúbico' : undefined,
            });
        });

        const marcadores = resultado.nodos.map((n) => ({
            x: n.x, y: n.fx, color: COLOR_NODOS, etiqueta: 'nodos (xⱼ, f(xⱼ))',
        }));

        const ev = resultado.evaluacion;
        if (ev) {
            marcadores.push({
                x: ev.x, y: ev.s, color: COLOR_EVALUACION, radio: 6, etiqueta: `S(${formatearNumero(ev.x)})`,
            });
        }

        grafica.dibujar({
            series,
            marcadores,
            xMin: resultado.a,
            xMax: resultado.b,
            descripcion: 'Gráfica de la función original y de los splines cúbicos',
        });

        GraficaSVG.pintarLeyenda(leyenda, grafica.leyenda());
        graficaVacia.hidden = true;
        marcoGrafica.hidden = false;
    }

    function limpiarSalida() {
        mostrarResultado('');
        bloqueResultado.hidden = true;
        panelPasos.hidden = true;
        marcoGrafica.hidden = true;
        graficaVacia.hidden = false;
        grafica.limpiar();
        GraficaSVG.limpiarLeyenda(leyenda);
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/spline-cubico/calcular', leerDatos());

            mostrarResultado(resultado.mensaje);

            splinesEl.textContent = resultado.formulas.join('\n\n');
            evaluacionEl.textContent = textoEvaluacion(resultado.evaluacion);
            evaluacionEl.hidden = !resultado.evaluacion;

            const errorMax = resultado.errorMaximo;
            errorMaxEl.textContent = errorMax === null || errorMax === undefined
                ? ''
                : `Error máximo observado |f(x) − S(x)| en [a, b]: ${Number(errorMax.toPrecision(4))}`;

            bloqueResultado.hidden = false;
            TablaPasos.pintar(seccionesPasos, resultado.pasos);
            panelPasos.hidden = false;
            dibujar(resultado);
        } catch (error) {
            limpiarSalida();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    botonCopiar?.addEventListener('click', async function () {
        const texto = splinesEl.textContent;
        if (!texto) {
            return;
        }

        const textoOriginal = botonCopiar.textContent;
        try {
            await navigator.clipboard.writeText(texto);
            botonCopiar.textContent = 'Copiado';
        } catch (error) {
            botonCopiar.textContent = 'No se pudo copiar';
        }
        setTimeout(() => { botonCopiar.textContent = textoOriginal; }, 1500);
    });

    limpiarSalida();
});