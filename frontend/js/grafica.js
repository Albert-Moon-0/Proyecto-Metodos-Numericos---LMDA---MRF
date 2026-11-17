// Módulo de gráficas SVG reutilizable (sin librerías externas).
//
// Cualquier método que necesite graficar (Lagrange, splines, integración,
// EDOs, ...) puede usarlo así:
//
//   <svg id="graph-svg" class="graph-svg"></svg>
//   <div id="graph-legend" class="graph-legend"></div>
//   <script src="js/grafica.js"></script>
//
//   const grafica = GraficaSVG.montar(document.getElementById('graph-svg'));
//   grafica.dibujar({
//       series: [
//           { puntos: [{x: 0, y: 1}, {x: 1, y: 2}, null, {x: 3, y: 0}],  // null corta la línea
//             color: '#4fd1c5', ancho: 2.25, etiqueta: 'f(x)' },
//           { puntos: [...], color: '#b892f0', discontinua: true, etiqueta: 'P(x)',
//             defineEscala: false },   // false: no estira el eje Y si la curva se dispara
//       ],
//       marcadores: [{ x: 1, y: 2, color: '#f2a4a0', etiqueta: 'nodos' }],
//   });
//   GraficaSVG.pintarLeyenda(document.getElementById('graph-legend'), grafica.leyenda());
//
// - Es responsiva: el viewBox se ajusta al ancho real del contenedor (se
//   redibuja sola al girar el celular o cambiar el tamaño de la ventana).
// - Rangos opcionales: xMin, xMax, yMin, yMax (si no se dan, se calculan).
// - Colores en hexadecimal (el SVG no lee las variables CSS de la página).

(function (global) {
    const NS = 'http://www.w3.org/2000/svg';

    const TEMA = {
        marco: 'rgba(148, 163, 184, 0.30)',
        rejilla: 'rgba(148, 163, 184, 0.10)',
        eje: 'rgba(148, 163, 184, 0.45)',
        texto: '#8b96a8',
        fuente: "'JetBrains Mono', ui-monospace, monospace",
    };

    let contadorClip = 0;

    function crear(nombre, atributos, texto) {
        const el = document.createElementNS(NS, nombre);
        Object.entries(atributos || {}).forEach(([clave, valor]) => el.setAttribute(clave, valor));
        if (texto !== undefined) {
            el.textContent = texto;
        }
        return el;
    }

    // ---------------------------------------------------------------
    // Escalas y marcas "bonitas" (1, 2, 5 × 10^k)
    // ---------------------------------------------------------------
    function pasoBonito(rango, objetivo) {
        const bruto = rango / Math.max(objetivo, 1);
        const potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
        const fraccion = bruto / potencia;
        const base = fraccion <= 1 ? 1 : fraccion <= 2 ? 2 : fraccion <= 5 ? 5 : 10;
        return base * potencia;
    }

    function marcas(min, max, objetivo) {
        const paso = pasoBonito(max - min, objetivo);
        const inicio = Math.ceil(min / paso - 1e-9) * paso;
        const lista = [];
        for (let v = inicio; v <= max + paso * 1e-9; v += paso) {
            lista.push(Math.abs(v) < paso * 1e-9 ? 0 : v);
        }
        return { lista, paso };
    }

    function textoMarca(valor, paso) {
        const decimales = Math.max(0, Math.min(8, -Math.floor(Math.log10(paso) + 1e-9)));
        const texto = valor.toFixed(decimales);
        return Math.abs(valor) >= 1e6 ? valor.toExponential(1) : texto;
    }

    // ---------------------------------------------------------------
    // Rangos automáticos
    // ---------------------------------------------------------------
    function puntosValidos(serie) {
        return (serie.puntos || []).filter((p) => p && Number.isFinite(p.x) && Number.isFinite(p.y));
    }

    function calcularRangos(config) {
        const series = config.series || [];
        const marcadores = (config.marcadores || []).filter((m) => Number.isFinite(m.x) && Number.isFinite(m.y));

        const todos = [];
        series.forEach((s) => todos.push(...puntosValidos(s)));
        todos.push(...marcadores);

        let xMin = config.xMin;
        let xMax = config.xMax;
        if (!Number.isFinite(xMin) || !Number.isFinite(xMax)) {
            const xs = todos.map((p) => p.x);
            xMin = Math.min(...xs);
            xMax = Math.max(...xs);
        }

        let yMin = config.yMin;
        let yMax = config.yMax;
        if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) {
            // Las series con defineEscala = false (p. ej. un polinomio que se
            // dispara entre nodos) solo estiran el eje Y hasta cierto punto.
            const base = [...marcadores];
            series.filter((s) => s.defineEscala !== false).forEach((s) => base.push(...puntosValidos(s)));
            if (base.length === 0) {
                base.push(...todos);
            }

            let bajo = Math.min(...base.map((p) => p.y));
            let alto = Math.max(...base.map((p) => p.y));
            const amplitud = alto - bajo || Math.abs(alto) || 1;

            series.filter((s) => s.defineEscala === false).forEach((s) => {
                puntosValidos(s).forEach((p) => {
                    if (p.y >= bajo - amplitud && p.y <= alto + amplitud) {
                        bajo = Math.min(bajo, p.y);
                        alto = Math.max(alto, p.y);
                    }
                });
            });

            const margen = (alto - bajo || 1) * 0.1;
            yMin = bajo - margen;
            yMax = alto + margen;
        }

        if (xMax === xMin) {
            xMin -= 1;
            xMax += 1;
        }
        if (yMax === yMin) {
            yMin -= 1;
            yMax += 1;
        }

        return { xMin, xMax, yMin, yMax };
    }

    // ---------------------------------------------------------------
    // Dibujo
    // ---------------------------------------------------------------
    // Une los puntos en tramos continuos (los null parten la línea).
    function tramos(puntos, sx, sy) {
        const resultado = [];
        let actual = [];

        (puntos || []).forEach((p) => {
            if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                actual.push(`${sx(p.x).toFixed(2)},${sy(p.y).toFixed(2)}`);
            } else if (actual.length) {
                resultado.push(actual);
                actual = [];
            }
        });
        if (actual.length) {
            resultado.push(actual);
        }
        return resultado;
    }

    function dibujarEn(svg, config, id) {
        const ancho = Math.max(Math.round(svg.getBoundingClientRect().width) || 640, 240);
        const alto = Math.round(Math.max(240, Math.min(ancho * 0.7, 520)));
        const compacto = ancho < 420;

        const margen = { izq: compacto ? 40 : 52, der: 14, sup: 14, inf: 30 };
        const areaAncho = ancho - margen.izq - margen.der;
        const areaAlto = alto - margen.sup - margen.inf;

        svg.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
        svg.setAttribute('role', 'img');
        svg.innerHTML = '';

        const { xMin, xMax, yMin, yMax } = calcularRangos(config);
        const sx = (x) => margen.izq + ((x - xMin) / (xMax - xMin)) * areaAncho;
        const sy = (y) => margen.sup + (1 - (y - yMin) / (yMax - yMin)) * areaAlto;

        const idClip = `grafica-clip-${id}`;
        const defs = crear('defs');
        const clip = crear('clipPath', { id: idClip });
        clip.appendChild(crear('rect', { x: margen.izq, y: margen.sup, width: areaAncho, height: areaAlto }));
        defs.appendChild(clip);
        svg.appendChild(defs);

        // Rejilla y marcas
        const marcasX = marcas(xMin, xMax, compacto ? 4 : 7);
        const marcasY = marcas(yMin, yMax, compacto ? 5 : 7);

        marcasX.lista.forEach((v) => {
            const x = sx(v);
            svg.appendChild(crear('line', { x1: x, y1: margen.sup, x2: x, y2: margen.sup + areaAlto, stroke: TEMA.rejilla }));
            svg.appendChild(crear('text', {
                x, y: margen.sup + areaAlto + 17, 'text-anchor': 'middle',
                fill: TEMA.texto, 'font-size': 11, 'font-family': TEMA.fuente,
            }, textoMarca(v, marcasX.paso)));
        });

        marcasY.lista.forEach((v) => {
            const y = sy(v);
            svg.appendChild(crear('line', { x1: margen.izq, y1: y, x2: margen.izq + areaAncho, y2: y, stroke: TEMA.rejilla }));
            svg.appendChild(crear('text', {
                x: margen.izq - 6, y: y + 4, 'text-anchor': 'end',
                fill: TEMA.texto, 'font-size': 11, 'font-family': TEMA.fuente,
            }, textoMarca(v, marcasY.paso)));
        });

        // Ejes en x = 0 y y = 0 cuando están dentro de la vista
        if (yMin < 0 && yMax > 0) {
            svg.appendChild(crear('line', { x1: margen.izq, y1: sy(0), x2: margen.izq + areaAncho, y2: sy(0), stroke: TEMA.eje, 'stroke-width': 1.25 }));
        }
        if (xMin < 0 && xMax > 0) {
            svg.appendChild(crear('line', { x1: sx(0), y1: margen.sup, x2: sx(0), y2: margen.sup + areaAlto, stroke: TEMA.eje, 'stroke-width': 1.25 }));
        }

        // Series (recortadas al área de trazado)
        const capa = crear('g', { 'clip-path': `url(#${idClip})` });
        (config.series || []).forEach((serie) => {
            tramos(serie.puntos, sx, sy).forEach((tramo) => {
                const atributos = {
                    points: tramo.join(' '),
                    fill: 'none',
                    stroke: serie.color || '#4fd1c5',
                    'stroke-width': serie.ancho || 2.25,
                    'stroke-linejoin': 'round',
                    'stroke-linecap': 'round',
                };
                if (serie.discontinua) {
                    atributos['stroke-dasharray'] = '7 5';
                }
                capa.appendChild(crear('polyline', atributos));
            });
        });
        svg.appendChild(capa);

        // Marcadores (nodos)
        (config.marcadores || []).forEach((m) => {
            if (!Number.isFinite(m.x) || !Number.isFinite(m.y)) {
                return;
            }
            const x = sx(m.x);
            const y = sy(m.y);
            if (x < margen.izq - 1 || x > margen.izq + areaAncho + 1 || y < margen.sup - 1 || y > margen.sup + areaAlto + 1) {
                return;
            }
            svg.appendChild(crear('circle', {
                cx: x, cy: y, r: m.radio || 4.5,
                fill: m.color || '#f2a4a0', stroke: '#0a0d12', 'stroke-width': 1.5,
            }));
        });

        // Marco del área de trazado
        svg.appendChild(crear('rect', {
            x: margen.izq, y: margen.sup, width: areaAncho, height: areaAlto,
            fill: 'none', stroke: TEMA.marco,
        }));

        if (config.descripcion) {
            svg.setAttribute('aria-label', config.descripcion);
        }
    }

    // Leyenda: [{ etiqueta, color, tipo: 'linea' | 'discontinua' | 'punto' }]
    function pintarLeyenda(contenedor, items) {
        if (!contenedor) {
            return;
        }
        contenedor.innerHTML = '';

        items.forEach((item) => {
            const fila = document.createElement('span');
            fila.className = 'graph-legend__item';

            const muestra = document.createElement('span');
            muestra.className = 'graph-legend__swatch';
            muestra.style.background = item.color;

            if (item.tipo === 'punto') {
                muestra.style.borderRadius = '50%';
            } else if (item.tipo === 'discontinua') {
                muestra.style.background = 'transparent';
                muestra.style.border = `2px dashed ${item.color}`;
                muestra.style.width = '1.1rem';
                muestra.style.height = '0';
                muestra.style.borderWidth = '2px 0 0 0';
                muestra.style.borderRadius = '0';
            } else if (item.tipo !== 'punto') {
                muestra.style.width = '1.1rem';
                muestra.style.height = '3px';
            }

            fila.append(muestra, document.createTextNode(item.etiqueta));
            contenedor.appendChild(fila);
        });
    }

    function limpiarLeyenda(contenedor) {
        if (contenedor) {
            contenedor.innerHTML = '';
        }
    }

    // Prepara un <svg> y devuelve su controlador. Se redibuja solo cuando
    // cambia el ancho del contenedor (celular girado, ventana redimensionada).
    function montar(svg) {
        contadorClip += 1;
        const id = contadorClip;
        let configActual = null;
        let anchoPrevio = 0;
        let temporizador = null;

        function redibujar() {
            if (configActual) {
                dibujarEn(svg, configActual, id);
            }
        }

        function alCambiarTamano() {
            const ancho = Math.round(svg.getBoundingClientRect().width);
            if (ancho === anchoPrevio) {
                return;
            }
            anchoPrevio = ancho;
            clearTimeout(temporizador);
            temporizador = setTimeout(redibujar, 80);
        }

        if (typeof ResizeObserver !== 'undefined') {
            new ResizeObserver(alCambiarTamano).observe(svg);
        } else {
            window.addEventListener('resize', alCambiarTamano);
        }

        return {
            dibujar(config) {
                configActual = config;
                anchoPrevio = Math.round(svg.getBoundingClientRect().width);
                dibujarEn(svg, config, id);
            },
            limpiar() {
                configActual = null;
                svg.innerHTML = '';
            },
            leyenda() {
                if (!configActual) {
                    return [];
                }
                const items = [];
                (configActual.series || []).forEach((s) => {
                    if (s.etiqueta) {
                        items.push({ etiqueta: s.etiqueta, color: s.color || '#4fd1c5', tipo: s.discontinua ? 'discontinua' : 'linea' });
                    }
                });
                (configActual.marcadores || []).forEach((m, i, todos) => {
                    if (m.etiqueta && todos.findIndex((o) => o.etiqueta === m.etiqueta) === i) {
                        items.push({ etiqueta: m.etiqueta, color: m.color || '#f2a4a0', tipo: 'punto' });
                    }
                });
                return items;
            },
        };
    }

    global.GraficaSVG = { montar, pintarLeyenda, limpiarLeyenda, calcularRangos };
})(typeof window !== 'undefined' ? window : globalThis);