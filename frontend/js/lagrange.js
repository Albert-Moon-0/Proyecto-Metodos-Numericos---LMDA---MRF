// Lógica de interfaz para la Interpolación polinomial (Lagrange, Neville y
// Diferencias divididas).
// El cálculo real se hace en el backend (Python, metodos/lagrange.py);
// este archivo lee los inputs, llama a la API, pinta las formas del
// polinomio, la tabla del procedimiento paso a paso y dibuja las gráficas de
// f(x) y P(x) con el módulo grafica.js.
// Cárgalo después de api.js, tablas-y-recursos.js y grafica.js.

document.addEventListener('DOMContentLoaded', function () {
    const { formatearNumero, mostrarResultado } = TablasYRecursos;

    const COLOR_F = '#4fd1c5';
    const COLOR_P = '#b892f0';
    const COLOR_NODOS = '#f2a4a0';
    const COLOR_EVALUACION = '#f6c177';

    const PISTAS = {
        lagrange: 'P(x) = Σ f(xᵢ)·Lᵢ(x), con Lᵢ(x) = Π (x − xⱼ)/(xᵢ − xⱼ), j ≠ i.',
        neville: 'Qᵢ,ⱼ = [(x − xᵢ₋ⱼ)·Qᵢ,ⱼ₋₁ − (x − xᵢ)·Qᵢ₋₁,ⱼ₋₁] / (xᵢ − xᵢ₋ⱼ). Evalúa P en un valor x sin armar el polinomio.',
        diferencias: 'P(x) = f[x₀] + f[x₀,x₁](x − x₀) + f[x₀,x₁,x₂](x − x₀)(x − x₁) + …',
    };

    const estado = { metodo: 'lagrange', hayResultado: false };

    const botonCalcular = document.getElementById('calcular-lagrange');
    const botonCopiar = document.getElementById('copiar-polinomio');
    const botonesMetodo = document.querySelectorAll('#method-selector [data-metodo]');
    const pistaMetodo = document.getElementById('method-hint');
    const etiquetaEvaluar = document.getElementById('evaluate-label');
    const entradaEvaluar = document.getElementById('evaluate-x');

    const bloqueResultado = document.getElementById('lagrange-detalle');
    const bloqueForma = document.getElementById('method-form');
    const tituloForma = document.getElementById('method-form-title');
    const formaEl = document.getElementById('method-form-output');
    const polinomioEl = document.getElementById('polynomial-output');
    const evaluacionEl = document.getElementById('evaluation-output');
    const errorMaxEl = document.getElementById('max-error-output');

    const graficaVacia = document.getElementById('graph-empty');
    const marcoGrafica = document.getElementById('graph-frame');
    const leyenda = document.getElementById('graph-legend');

    const panelPasos = document.getElementById('steps-panel');
    const tituloPasos = document.getElementById('steps-heading');
    const descripcionPasos = document.getElementById('steps-description');
    const formulasPasos = document.getElementById('steps-formulas');
    const cabeceraPasos = document.getElementById('steps-head');
    const cuerpoPasos = document.getElementById('steps-body');
    const resumenPasos = document.getElementById('steps-summary');

    const grafica = GraficaSVG.montar(document.getElementById('graph-svg'));

    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    function leerDatos() {
        return {
            metodo: estado.metodo,
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            puntos: valorDe('point-count'),
            xEvaluar: valorDe('evaluate-x'),
        };
    }

    // ---------------------------------------------------------------
    // Selector de método
    // ---------------------------------------------------------------
    function aplicarMetodo(metodo) {
        estado.metodo = metodo;

        botonesMetodo.forEach((boton) => {
            const activo = boton.dataset.metodo === metodo;
            boton.classList.toggle('is-active', activo);
            boton.setAttribute('aria-pressed', String(activo));
        });

        pistaMetodo.textContent = PISTAS[metodo];

        const obligatorio = metodo === 'neville';
        etiquetaEvaluar.textContent = obligatorio ? 'Evaluar P(x) en (obligatorio)' : 'Evaluar P(x) en (opcional)';
        entradaEvaluar.placeholder = obligatorio ? 'Ejemplo: 1.5 (requerido)' : 'Ejemplo: 1.5';
    }

    botonesMetodo.forEach((boton) => {
        boton.addEventListener('click', function () {
            if (boton.dataset.metodo === estado.metodo) {
                return;
            }
            aplicarMetodo(boton.dataset.metodo);

            // Si ya había un resultado en pantalla, se recalcula con el nuevo método.
            if (estado.hayResultado) {
                botonCalcular.click();
            }
        });
    });

    // ---------------------------------------------------------------
    // Pintado de resultados
    // ---------------------------------------------------------------
    function celda(valor) {
        const td = document.createElement('td');
        if (valor === null || valor === undefined) {
            td.className = 'is-empty';
        } else {
            td.textContent = formatearNumero(valor);
        }
        return td;
    }

    function pintarPasos(pasos) {
        tituloPasos.textContent = pasos.titulo;
        descripcionPasos.textContent = pasos.descripcion;

        formulasPasos.innerHTML = '';
        (pasos.formulas || []).forEach((texto) => {
            const item = document.createElement('li');
            item.textContent = texto;
            formulasPasos.appendChild(item);
        });
        formulasPasos.hidden = !(pasos.formulas || []).length;

        cabeceraPasos.innerHTML = '';
        const filaCabecera = document.createElement('tr');
        pasos.columnas.forEach((nombre) => {
            const th = document.createElement('th');
            th.textContent = nombre;
            filaCabecera.appendChild(th);
        });
        cabeceraPasos.appendChild(filaCabecera);

        const resaltadas = new Set((pasos.resaltar || []).map(([i, j]) => `${i},${j}`));
        cuerpoPasos.innerHTML = '';
        pasos.filas.forEach((fila, i) => {
            const tr = document.createElement('tr');
            fila.forEach((valor, j) => {
                const td = celda(valor);
                if (resaltadas.has(`${i},${j}`)) {
                    td.classList.add('is-highlight');
                }
                tr.appendChild(td);
            });
            cuerpoPasos.appendChild(tr);
        });

        resumenPasos.textContent = pasos.resumen || '';
        resumenPasos.hidden = !pasos.resumen;
        panelPasos.hidden = false;
    }

    function textoEvaluacion(ev) {
        if (!ev) {
            return '';
        }

        let texto = `P(${formatearNumero(ev.x)}) = ${formatearNumero(ev.p)}`;
        if (ev.f !== null && ev.f !== undefined) {
            texto += `   ·   f(${formatearNumero(ev.x)}) = ${formatearNumero(ev.f)}`;
            texto += `   ·   |error| = ${Number(ev.error.toPrecision(4))}`;
        }
        if (ev.fueraDeIntervalo) {
            texto += '   (fuera de [a, b]: es una extrapolación, el error suele crecer)';
        }
        return texto;
    }

    function dibujar(resultado) {
        const marcadores = resultado.nodos.map((n) => ({
            x: n.x, y: n.fx, color: COLOR_NODOS, etiqueta: 'nodos (xᵢ, f(xᵢ))',
        }));

        const ev = resultado.evaluacion;
        if (ev) {
            marcadores.push({
                x: ev.x, y: ev.p, color: COLOR_EVALUACION, radio: 6, etiqueta: `P(${formatearNumero(ev.x)})`,
            });
        }

        grafica.dibujar({
            series: [
                { puntos: resultado.grafica.puntosF, color: COLOR_F, ancho: 2.5, etiqueta: 'f(x) original' },
                // defineEscala: false -> si P(x) se dispara entre nodos, no aplasta la gráfica de f(x)
                { puntos: resultado.grafica.puntosP, color: COLOR_P, ancho: 2.25, discontinua: true, etiqueta: 'P(x) polinomio', defineEscala: false },
            ],
            marcadores,
            xMin: resultado.a,
            xMax: resultado.b,
            descripcion: 'Gráfica de la función original y de su polinomio de interpolación',
        });

        GraficaSVG.pintarLeyenda(leyenda, grafica.leyenda());
        graficaVacia.hidden = true;
        marcoGrafica.hidden = false;
    }

    function limpiarSalida() {
        estado.hayResultado = false;
        mostrarResultado('');
        bloqueResultado.hidden = true;
        panelPasos.hidden = true;
        marcoGrafica.hidden = true;
        graficaVacia.hidden = false;
        grafica.limpiar();
        GraficaSVG.limpiarLeyenda(leyenda);
    }

    // ---------------------------------------------------------------
    // Eventos
    // ---------------------------------------------------------------
    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/lagrange/calcular', leerDatos());

            mostrarResultado(resultado.mensaje);

            if (resultado.formaMetodo) {
                tituloForma.textContent = resultado.formaMetodo.etiqueta;
                formaEl.textContent = resultado.formaMetodo.texto;
                bloqueForma.hidden = false;
            } else {
                bloqueForma.hidden = true;
            }

            polinomioEl.textContent = `P(x) = ${resultado.polinomio}`;
            polinomioEl.dataset.expresion = resultado.polinomio;
            evaluacionEl.textContent = textoEvaluacion(resultado.evaluacion);
            evaluacionEl.hidden = !resultado.evaluacion;

            const errorMax = resultado.errorMaximo;
            errorMaxEl.textContent = errorMax === null || errorMax === undefined
                ? ''
                : `Error máximo observado |f(x) − P(x)| en [a, b]: ${Number(errorMax.toPrecision(4))}`;

            bloqueResultado.hidden = false;
            pintarPasos(resultado.pasos);
            dibujar(resultado);
            estado.hayResultado = true;
        } catch (error) {
            limpiarSalida();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    botonCopiar?.addEventListener('click', async function () {
        const expresion = polinomioEl.dataset.expresion;
        if (!expresion) {
            return;
        }

        const textoOriginal = botonCopiar.textContent;
        try {
            await navigator.clipboard.writeText(expresion);
            botonCopiar.textContent = 'Copiado';
        } catch (error) {
            botonCopiar.textContent = 'No se pudo copiar';
        }
        setTimeout(() => { botonCopiar.textContent = textoOriginal; }, 1500);
    });

    aplicarMetodo('lagrange');
    limpiarSalida();
});