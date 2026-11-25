// Lógica de interfaz de la Derivación numérica (fórmulas de 2, 3 y 5 puntos).
// El cálculo real se hace en el backend (Python, metodos/derivacion_numerica.py);
// este archivo lee los inputs, llama a la API, pinta el resultado, el
// procedimiento paso a paso (con TablaPasos) y dibuja tres gráficas con el
// módulo grafica.js: f(x) con su recta tangente, la derivada numérica en los
// nodos y (solo con función) el error contra el paso h en escala log-log.
// Orden de scripts: api.js -> tablas-y-recursos.js -> tabla-pasos.js -> grafica.js -> derivacion-numerica.js

document.addEventListener('DOMContentLoaded', function () {
    const { formatearNumero, mostrarResultado } = TablasYRecursos;

    const COLOR_F = '#4fd1c5';
    const COLOR_TANGENTE = '#f6c177';
    const COLOR_EXACTA = '#b892f0';
    const COLOR_NODOS = '#f2a4a0';

    const PISTAS_MODO = {
        tabla: 'Escribe los nodos x y los valores f(x) separados por comas (datos de un experimento, una encuesta o una tabla).',
        funcion: 'Escribe f(x) y un intervalo: se generan los nodos y se compara contra la derivada exacta.',
    };

    const PISTAS_METODO = {
        auto: 'Elige sola la fórmula de mayor orden que cabe en la tabla: 5 puntos si hay datos suficientes, luego 3 y por último 2.',
        '2p': 'f′(x₀) ≈ (f(x₀+h) − f(x₀))/h  (progresiva)  o  (f(x₀) − f(x₀−h))/h  (regresiva).  Error O(h).',
        '2pc': 'f′(x₀) ≈ (f(x₀+h) − f(x₀−h)) / 2h.  Solo dos evaluaciones, pero el error baja a O(h²).',
        '3p': 'Extremos: (−3f₀ + 4f₁ − f₂)/2h y (f₀ − 4f₁ + 3f₂)/2h. Punto medio: (f₂ − f₀)/2h.  Error O(h²).',
        '5p': 'Punto medio: (f₀ − 8f₁ + 8f₃ − f₄)/12h, más cuatro fórmulas descentradas para los bordes.  Error O(h⁴).',
    };

    // Posiciones de x₀ dentro de la ventana de nodos de cada fórmula (k).
    const POSICIONES = {
        '2p': [['auto', 'Automática'], ['0', 'Progresiva'], ['1', 'Regresiva']],
        '3p': [['auto', 'Automática'], ['0', 'Extremo izq.'], ['1', 'Punto medio'], ['2', 'Extremo der.']],
        '5p': [['auto', 'Automática'], ['0', 'Extremo izq.'], ['1', 'Interior izq.'], ['2', 'Punto medio'], ['3', 'Interior der.'], ['4', 'Extremo der.']],
    };

    const EJEMPLOS = {
        tabla: {
            'x-values': '1.0, 1.2, 1.4, 1.6, 1.8',
            'fx-values': '-0.035892, -0.033381, -0.027555, -0.020764, -0.014512',
            'exact-value': '0.033181',
            'point-x0': '1.4',
        },
        funcion: {
            'function-input': 'x**2*sin(x+3)/(1+e**(3*x))',
            'point-a': '1',
            'point-b': '1.8',
            'point-count': '5',
            'point-x0': '1.4',
        },
    };

    const SUPERINDICES = '⁰¹²³⁴⁵⁶⁷⁸⁹';
    const superindice = (n) => String(n).replace(/\d/g, (d) => SUPERINDICES[d]);

    const estado = { modo: 'tabla', metodo: 'auto', k: 'auto', hayResultado: false, ultimo: null };

    const botonCalcular = document.getElementById('calcular-derivacion');
    const botonEjemplo = document.getElementById('cargar-ejemplo');
    const botonCopiar = document.getElementById('copiar-resultado');
    const botonCsv = document.getElementById('descargar-csv');
    const botonesModo = document.querySelectorAll('#mode-selector [data-modo]');
    const botonesMetodo = document.querySelectorAll('#method-selector [data-metodo]');
    const selectorPosicion = document.getElementById('position-selector');
    const campoPosicion = document.getElementById('position-field');
    const selectorNodos = document.getElementById('node-selector');
    const pistaModo = document.getElementById('mode-hint');
    const pistaMetodo = document.getElementById('method-hint');
    const etiquetaX0 = document.getElementById('x0-label');
    const grupoTabla = document.getElementById('group-tabla');
    const grupoFuncion = document.getElementById('group-funcion');

    const resultadoEl = document.getElementById('result');
    const bloqueDetalle = document.getElementById('derivacion-detalle');
    const notaEstimado = document.getElementById('note-estimado');
    const notaExacta = document.getElementById('note-exacta');
    const notaRichardson = document.getElementById('note-richardson');
    const notaOptimos = document.getElementById('note-optimos');
    const notaAviso = document.getElementById('note-aviso');

    const panelPasos = document.getElementById('steps-panel');
    const contenedorPasos = document.getElementById('steps-sections');
    const panelGrafica3 = document.getElementById('graph3-panel');

    // Tres gráficas: cada una con su svg, su marco, su mensaje vacío y su leyenda.
    const graficas = [
        { svg: 'graph-svg', marco: 'graph-frame', vacio: 'graph-empty', leyenda: 'graph-legend' },
        { svg: 'graph2-svg', marco: 'graph2-frame', vacio: 'graph2-empty', leyenda: 'graph2-legend' },
        { svg: 'graph3-svg', marco: 'graph3-frame', vacio: null, leyenda: 'graph3-legend' },
    ].map((g) => ({
        control: GraficaSVG.montar(document.getElementById(g.svg)),
        marco: document.getElementById(g.marco),
        vacio: g.vacio ? document.getElementById(g.vacio) : null,
        leyenda: document.getElementById(g.leyenda),
    }));

    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    function leerDatos() {
        return {
            modo: estado.modo,
            metodo: estado.metodo,
            k: estado.k,
            xs: valorDe('x-values'),
            fs: valorDe('fx-values'),
            exacto: valorDe('exact-value'),
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            puntos: valorDe('point-count'),
            x0: valorDe('point-x0'),
        };
    }

    // ---------------------------------------------------------------
    // Selectores (modo, fórmula y posición)
    // ---------------------------------------------------------------
    function marcarActivo(botones, esActivo) {
        botones.forEach((boton) => {
            const activo = esActivo(boton);
            boton.classList.toggle('is-active', activo);
            boton.setAttribute('aria-pressed', String(activo));
        });
    }

    function aplicarModo(modo) {
        estado.modo = modo;
        marcarActivo(botonesModo, (b) => b.dataset.modo === modo);
        grupoTabla.hidden = modo !== 'tabla';
        grupoFuncion.hidden = modo !== 'funcion';
        pistaModo.textContent = PISTAS_MODO[modo];
        etiquetaX0.textContent = modo === 'tabla'
            ? 'Nodo x₀ donde derivar (debe ser uno de los x)'
            : 'Nodo x₀ donde derivar (vacío = nodo central)';
    }

    function pintarPosiciones() {
        const opciones = POSICIONES[estado.metodo];
        campoPosicion.hidden = !opciones;
        selectorPosicion.innerHTML = '';
        (opciones || []).forEach(([valor, texto]) => {
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'segmented__btn' + (valor === estado.k ? ' is-active' : '');
            boton.dataset.k = valor;
            boton.setAttribute('aria-pressed', String(valor === estado.k));
            boton.textContent = texto;
            selectorPosicion.appendChild(boton);
        });
    }

    function aplicarMetodo(metodo) {
        estado.metodo = metodo;
        estado.k = 'auto';
        marcarActivo(botonesMetodo, (b) => b.dataset.metodo === metodo);
        pistaMetodo.textContent = PISTAS_METODO[metodo];
        pintarPosiciones();
    }

    function recalcularSiHayResultado() {
        if (estado.hayResultado) {
            botonCalcular.click();
        }
    }

    botonesModo.forEach((boton) => {
        boton.addEventListener('click', function () {
            if (boton.dataset.modo === estado.modo) {
                return;
            }
            aplicarModo(boton.dataset.modo);
            limpiarSalida();
        });
    });

    botonesMetodo.forEach((boton) => {
        boton.addEventListener('click', function () {
            if (boton.dataset.metodo === estado.metodo) {
                return;
            }
            aplicarMetodo(boton.dataset.metodo);
            recalcularSiHayResultado();
        });
    });

    selectorPosicion.addEventListener('click', function (evento) {
        const boton = evento.target.closest('[data-k]');
        if (!boton || boton.dataset.k === estado.k) {
            return;
        }
        estado.k = boton.dataset.k;
        pintarPosiciones();
        recalcularSiHayResultado();
    });

    selectorNodos.addEventListener('click', function (evento) {
        const boton = evento.target.closest('[data-x]');
        if (!boton) {
            return;
        }
        document.getElementById('point-x0').value = boton.dataset.x;
        botonCalcular.click();
    });

    botonEjemplo?.addEventListener('click', function () {
        Object.entries(EJEMPLOS[estado.modo]).forEach(([id, valor]) => {
            document.getElementById(id).value = valor;
        });
        botonCalcular.click();
    });

    // ---------------------------------------------------------------
    // Pintado de resultados
    // ---------------------------------------------------------------
    function crear(clase, ...contenido) {
        const el = document.createElement('span');
        el.className = clase;
        el.append(...contenido);
        return el;
    }

    function cifras(valor) {
        return String(Number(valor.toPrecision(8)));
    }

    function cientifico(valor) {
        return Number(valor).toExponential(3);
    }

    function pintarResultado(r) {
        const p = r.principal;
        resultadoEl.replaceChildren(
            crear('rg-etiqueta', `f′(${formatearNumero(r.x0)}) ≈`),
            crear('rg-valor', cifras(p.valor)),
            crear('rg-detalle', `${p.metodo} · ${p.posicion} · h = ${formatearNumero(r.h)} · orden O(h${superindice(p.orden)}) · E = ${p.errorFormula}`),
        );
    }

    function nota(elemento, texto) {
        elemento.textContent = texto || '';
        elemento.hidden = !texto;
    }

    function pintarNotas(r) {
        const p = r.principal;

        nota(notaEstimado, p.errorEstimado === null || p.errorEstimado === undefined ? '' :
            `Error estimado ≈ ${cientifico(p.errorEstimado)}  (diferencia contra la fórmula de un orden menor; no necesita la derivada exacta).`);

        nota(notaExacta, r.exacta === null || r.exacta === undefined ? '' :
            `f′(x₀) exacta = ${cifras(r.exacta)}   ·   error real = ${cientifico(p.errorReal)}`);

        nota(notaRichardson, !r.richardson ? '' :
            `Con Richardson: f′(x₀) ≈ ${cifras(r.richardson.valor)}   ·   error = ${cientifico(r.richardson.error)}`);

        nota(notaOptimos, !r.optimos ? '' :
            'Mejor h observado — ' + r.optimos.map((o) => `${o.metodo}: ${Number(o.h).toExponential(0)}`).join(' · '));

        nota(notaAviso, r.aviso);
    }

    function pintarNodos(r) {
        selectorNodos.innerHTML = '';
        r.nodos.forEach((nodo) => {
            const boton = document.createElement('button');
            boton.type = 'button';
            const activo = nodo.i === r.indice;
            boton.className = 'segmented__btn' + (activo ? ' is-active' : '');
            boton.dataset.x = String(nodo.x);
            boton.setAttribute('aria-pressed', String(activo));
            boton.title = `f′(${formatearNumero(nodo.x)}) ≈ ${formatearNumero(nodo.derivada)}`;
            boton.textContent = formatearNumero(nodo.x);
            selectorNodos.appendChild(boton);
        });
    }

    function mostrarGrafica(g, config) {
        g.control.dibujar(config);
        GraficaSVG.pintarLeyenda(g.leyenda, g.control.leyenda());
        if (g.vacio) {
            g.vacio.hidden = true;
        }
        g.marco.hidden = false;
    }

    function dibujar(r) {
        const gr = r.grafica;
        const xMin = r.nodos[0].x;
        const xMax = r.nodos[r.nodos.length - 1].x;
        const principal = { x: r.x0, y: gr.nodos[r.indice].y, color: COLOR_TANGENTE, radio: 6, etiqueta: 'x₀' };

        // 1) f(x) y recta tangente (numérica y, si se conoce, exacta)
        const series1 = [
            { puntos: gr.puntosF, color: COLOR_F, ancho: 2.5, etiqueta: r.modo === 'funcion' ? 'f(x) original' : 'f(x) por los datos' },
            { puntos: gr.tangenteNumerica, color: COLOR_TANGENTE, ancho: 2.25, etiqueta: 'tangente numérica', defineEscala: false },
        ];
        if (gr.tangenteExacta) {
            series1.push({ puntos: gr.tangenteExacta, color: COLOR_EXACTA, ancho: 2, discontinua: true, etiqueta: 'tangente exacta', defineEscala: false });
        }
        mostrarGrafica(graficas[0], {
            series: series1,
            marcadores: [...gr.nodos.map((n) => ({ ...n, color: COLOR_NODOS, etiqueta: 'nodos (xᵢ, f(xᵢ))' })), principal],
            xMin,
            xMax,
            descripcion: 'Gráfica de f(x) y de la recta tangente en x0 calculada con la derivada numérica',
        });

        // 2) f′(x) numérica en los nodos contra la exacta
        const series2 = [];
        if (gr.derivadaExacta) {
            series2.push({ puntos: gr.derivadaExacta, color: COLOR_EXACTA, ancho: 2.5, etiqueta: 'f′(x) exacta' });
        }
        series2.push({ puntos: gr.derivadaNumerica, color: COLOR_TANGENTE, ancho: 2, discontinua: !!gr.derivadaExacta, etiqueta: 'f′(xᵢ) numérica' });
        mostrarGrafica(graficas[1], {
            series: series2,
            marcadores: gr.derivadaNumerica.map((n) => ({ ...n, color: COLOR_NODOS, etiqueta: 'f′ en los nodos' })),
            xMin,
            xMax,
            descripcion: 'Derivada numérica en cada nodo comparada con la derivada exacta',
        });

        // 3) error vs. h (solo con función): log10(h) contra log10(error)
        panelGrafica3.hidden = !gr.analisisH;
        if (gr.analisisH) {
            mostrarGrafica(graficas[2], {
                series: [
                    { puntos: gr.analisisH.adelante, color: COLOR_NODOS, ancho: 2.25, etiqueta: '2 pts progresiva O(h)' },
                    { puntos: gr.analisisH.centrada, color: COLOR_F, ancho: 2.25, etiqueta: '2 pts centrada O(h²)' },
                    { puntos: gr.analisisH.cinco, color: COLOR_EXACTA, ancho: 2.25, etiqueta: '5 pts centrada O(h⁴)' },
                ],
                descripcion: 'Logaritmo del error contra el logaritmo del paso h para tres fórmulas',
            });
        }
    }

    function limpiarSalida() {
        estado.hayResultado = false;
        estado.ultimo = null;
        mostrarResultado('');
        resultadoEl.replaceChildren();
        bloqueDetalle.hidden = true;
        panelPasos.hidden = true;
        panelGrafica3.hidden = true;
        graficas.forEach((g) => {
            g.control.limpiar();
            g.marco.hidden = true;
            if (g.vacio) {
                g.vacio.hidden = false;
            }
            GraficaSVG.limpiarLeyenda(g.leyenda);
        });
    }

    // ---------------------------------------------------------------
    // Exportar
    // ---------------------------------------------------------------
    function textoCsv(r) {
        const conExacta = r.exacta !== null && r.exacta !== undefined;
        const filas = [['i', 'x', 'f(x)', "f'(x)", 'formula', "f''(x)", ...(conExacta ? ["f'(x) exacta", 'error'] : [])]];
        r.nodos.forEach((n) => {
            filas.push([n.i, n.x, n.fx, n.derivada, n.formula, n.segunda ?? '', ...(conExacta ? [n.exacta, n.error] : [])]);
        });
        return filas.map((fila) => fila.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    }

    async function copiar(boton, texto) {
        const original = boton.textContent;
        try {
            await navigator.clipboard.writeText(texto);
            boton.textContent = 'Copiado';
        } catch (error) {
            boton.textContent = 'No se pudo copiar';
        }
        setTimeout(() => { boton.textContent = original; }, 1500);
    }

    botonCopiar?.addEventListener('click', function () {
        if (estado.ultimo) {
            copiar(botonCopiar, estado.ultimo.mensaje);
        }
    });

    botonCsv?.addEventListener('click', function () {
        if (!estado.ultimo) {
            return;
        }
        const blob = new Blob(['\ufeff' + textoCsv(estado.ultimo)], { type: 'text/csv;charset=utf-8' });
        const enlace = document.createElement('a');
        enlace.href = URL.createObjectURL(blob);
        enlace.download = 'derivacion-numerica.csv';
        enlace.click();
        URL.revokeObjectURL(enlace.href);
    });

    // ---------------------------------------------------------------
    // Calcular
    // ---------------------------------------------------------------
    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/derivacion-numerica/calcular', leerDatos());

            mostrarResultado('');
            pintarResultado(resultado);
            pintarNotas(resultado);
            pintarNodos(resultado);
            bloqueDetalle.hidden = false;

            TablaPasos.pintar(contenedorPasos, resultado.pasos);
            panelPasos.hidden = false;

            dibujar(resultado);
            estado.ultimo = resultado;
            estado.hayResultado = true;
        } catch (error) {
            limpiarSalida();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    aplicarModo('tabla');
    aplicarMetodo('auto');
    limpiarSalida();
});