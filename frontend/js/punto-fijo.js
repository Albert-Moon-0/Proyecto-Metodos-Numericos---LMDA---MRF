// Lógica de interfaz para Punto Fijo.
// El cálculo real (iteraciones, derivada simbólica g'(x) y el muestreo
// de puntos para graficar) se hace en el backend (Python); este archivo
// lee los inputs, llama a la API, pinta la tabla (usando
// comun/tablas-y-recursos.js), pinta el panel de criterios de
// existencia/unicidad y dibuja la gráfica SVG de g(x), |g'(x)| y y = x.

document.addEventListener('DOMContentLoaded', function () {
    const botonCalcular = document.getElementById('calcular-punto-fijo');
    const { pintarTabla, limpiarTabla, mostrarResultado, formatearNumero } = TablasYRecursos;

    function leerDatos() {
        return {
            funcion: document.getElementById('function-input')?.value ?? '',
            p0: document.getElementById('p0-input')?.value ?? '',
            tolerancia: document.getElementById('tolerance')?.value ?? '',
            maxIteraciones: document.getElementById('max-iterations')?.value ?? '',
            a: document.getElementById('point-a')?.value ?? '',
            b: document.getElementById('point-b')?.value ?? '',
        };
    }

    // ---------- Panel de criterios de existencia / unicidad ----------

    function limpiarAnalisis() {
        const lista = document.getElementById('criteria-list');
        const resumen = document.getElementById('analysis-summary');
        if (lista) lista.innerHTML = '';
        if (resumen) {
            resumen.textContent = '';
            resumen.className = '';
        }
    }

    function pintarCriterios(analisis) {
        const lista = document.getElementById('criteria-list');
        const resumen = document.getElementById('analysis-summary');
        if (!lista || !resumen) return;

        lista.innerHTML = '';

        const itemMapeo = document.createElement('div');
        itemMapeo.className = `criteria-item ${analisis.cumpleMapeo ? 'criteria-item--ok' : 'criteria-item--fail'}`;
        const rangoTexto = (analisis.gMin !== null && analisis.gMax !== null)
            ? `g(x) toma valores entre ${formatearNumero(analisis.gMin)} y ${formatearNumero(analisis.gMax)} en [a, b].`
            : 'g(x) no pudo evaluarse en todo el intervalo.';
        itemMapeo.innerHTML = `
            <span class="criteria-item__icon">${analisis.cumpleMapeo ? '✓' : '✕'}</span>
            <span class="criteria-item__text"><strong>Existencia (mapeo):</strong> g(x) ∈ [a, b] para todo x ∈ [a, b]. ${rangoTexto}</span>
        `;
        lista.appendChild(itemMapeo);

        const itemContraccion = document.createElement('div');
        itemContraccion.className = `criteria-item ${analisis.cumpleContraccion ? 'criteria-item--ok' : 'criteria-item--fail'}`;
        const kTexto = analisis.kMax !== null
            ? `máximo de |g'(x)| en [a, b] ≈ ${formatearNumero(analisis.kMax)}.`
            : 'no se pudo calcular |g\'(x)| en el intervalo.';
        itemContraccion.innerHTML = `
            <span class="criteria-item__icon">${analisis.cumpleContraccion ? '✓' : '✕'}</span>
            <span class="criteria-item__text"><strong>Unicidad (contracción):</strong> |g'(x)| ≤ k &lt; 1 para todo x ∈ [a, b]; ${kTexto}</span>
        `;
        lista.appendChild(itemContraccion);

        resumen.textContent = analisis.mensaje;
        resumen.className = `analysis-summary ${analisis.cumpleAmbos ? 'analysis-summary--ok' : 'analysis-summary--fail'}`;
    }

    // ---------- Gráfica SVG ----------

    const NS = 'http://www.w3.org/2000/svg';
    const MARGEN = { izq: 46, der: 18, sup: 18, inf: 34 };
    const ANCHO_VB = 640;
    const ALTO_VB = 420;

    function crearElemento(nombre, atributos) {
        const el = document.createElementNS(NS, nombre);
        Object.entries(atributos).forEach(([clave, valor]) => el.setAttribute(clave, valor));
        return el;
    }

    function limpiarGrafica() {
        const svg = document.getElementById('graph-svg');
        if (svg) svg.innerHTML = '';
    }

    function dibujarGrafica(analisis) {
        const svg = document.getElementById('graph-svg');
        if (!svg) return;
        svg.innerHTML = '';

        const dominio = analisis.grafica.dominio;
        const { xMin, xMax, yMin, yMax } = dominio;
        const anchoGraf = ANCHO_VB - MARGEN.izq - MARGEN.der;
        const altoGraf = ALTO_VB - MARGEN.sup - MARGEN.inf;

        const sx = (x) => MARGEN.izq + ((x - xMin) / (xMax - xMin)) * anchoGraf;
        const sy = (y) => MARGEN.sup + (1 - (y - yMin) / (yMax - yMin)) * altoGraf;

        // Fondo del área de trazado
        svg.appendChild(crearElemento('rect', {
            x: MARGEN.izq, y: MARGEN.sup, width: anchoGraf, height: altoGraf,
            fill: 'none', stroke: 'rgba(148, 163, 184, 0.18)',
        }));

        // Ejes (si el 0 cae dentro del dominio visible)
        if (yMin <= 0 && yMax >= 0) {
            svg.appendChild(crearElemento('line', {
                x1: sx(xMin), y1: sy(0), x2: sx(xMax), y2: sy(0),
                stroke: 'rgba(148, 163, 184, 0.35)', 'stroke-width': 1,
            }));
        }
        if (xMin <= 0 && xMax >= 0) {
            svg.appendChild(crearElemento('line', {
                x1: sx(0), y1: sy(yMin), x2: sx(0), y2: sy(yMax),
                stroke: 'rgba(148, 163, 184, 0.35)', 'stroke-width': 1,
            }));
        }

        // Umbral |g'(x)| = 1
        if (yMin <= 1 && yMax >= 1) {
            const y1 = sy(1);
            const linea = crearElemento('line', {
                x1: sx(xMin), y1, x2: sx(xMax), y2: y1,
                stroke: '#f2a4a0', 'stroke-width': 1.25, 'stroke-dasharray': '5 4', opacity: 0.85,
            });
            svg.appendChild(linea);
        }

        // Recta identidad y = x
        svg.appendChild(crearElemento('line', {
            x1: sx(xMin), y1: sy(xMin), x2: sx(xMax), y2: sy(xMax),
            stroke: '#8b96a8', 'stroke-width': 1.5,
        }));

        // Cuadro punteado del intervalo [a, b] x [a, b]
        const { a, b } = analisis;
        const corners = [[a, a], [a, b], [b, b], [b, a]].map(([px, py]) => `${sx(px)},${sy(py)}`).join(' ');
        svg.appendChild(crearElemento('polygon', {
            points: corners, fill: 'none', stroke: '#e6e9ef',
            'stroke-width': 1.25, 'stroke-dasharray': '4 3', opacity: 0.8,
        }));

        // Curva |g'(x)|
        const puntosDerivada = analisis.grafica.puntosDerivadaAbs
            .map((p) => `${sx(p.x)},${sy(p.y)}`).join(' ');
        if (puntosDerivada) {
            svg.appendChild(crearElemento('polyline', {
                points: puntosDerivada, fill: 'none', stroke: '#b892f0', 'stroke-width': 2,
            }));
        }

        // Curva g(x)
        const puntosG = analisis.grafica.puntosG.map((p) => `${sx(p.x)},${sy(p.y)}`).join(' ');
        if (puntosG) {
            svg.appendChild(crearElemento('polyline', {
                points: puntosG, fill: 'none', stroke: '#4fd1c5', 'stroke-width': 2.25,
            }));
        }

        // Marcas y etiquetas de a y b sobre el eje x
        [a, b].forEach((valor) => {
            svg.appendChild(crearElemento('line', {
                x1: sx(valor), y1: sy(yMin), x2: sx(valor), y2: sy(yMin) + 5,
                stroke: 'var(--text-secondary)', 'stroke-width': 1,
            }));
            const etiqueta = crearElemento('text', {
                x: sx(valor), y: ALTO_VB - 10, fill: '#8b96a8',
                'font-size': 11, 'font-family': 'JetBrains Mono, monospace', 'text-anchor': 'middle',
            });
            etiqueta.textContent = formatearNumero(valor);
            svg.appendChild(etiqueta);
        });
    }

    // ---------- Envío del formulario ----------

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const datos = leerDatos();
            const resultado = await llamarApi('/api/punto-fijo/calcular', datos);

            pintarTabla(resultado.iteraciones, (fila) => [
                fila.iteracion,
                fila.p0,
                fila.gp0,
                fila.p1,
                fila.errorAbsoluto,
                fila.errorAproximado,
            ]);
            mostrarResultado(resultado.mensaje);
            pintarCriterios(resultado.analisisIntervalo);
            dibujarGrafica(resultado.analisisIntervalo);
        } catch (error) {
            limpiarTabla();
            limpiarAnalisis();
            limpiarGrafica();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });
});
