// Motor de gráficas SVG reutilizable (sin librerías).
//
// Dibuja en un <svg> una escena descrita con un objeto simple; cada método
// arma su escena en su propio archivo (grafica-biseccion.js, ...) y llama a
//
//     GraficaSvg.dibujar(svgElemento, escena);
//
// Escena:
//   dominio:      { xMin, xMax, yMin, yMax }                (obligatorio)
//   bandas:       [{ x1, x2, color, opacidad }]             zonas sombreadas verticales
//   curvas:       [{ puntos: [{x, y|null}], color, ancho, discontinua }]
//   horizontales: [{ y, color, discontinua, etiqueta }]
//   verticales:   [{ x, y1, y2, color, discontinua }]       y1/y2 opcionales (segmento)
//   poligonos:    [{ puntos: [{x, y}], color, opacidad, borde, anchoBorde }]  áreas rellenas
//   segmentos:    [{ x1, y1, x2, y2, color, ancho, discontinua }]  segmento FINITO entre dos puntos
//   rectas:       [{ x1, y1, x2, y2, color, ancho, discontinua }]  recta INFINITA por dos puntos
//                 (secante, tangente...). Se recorta al área de la gráfica.
//   puntos:       [{ x, y, color, hueco, radio, forma, etiqueta, dx, dy }]
//                 forma: 'circulo' (def.) | 'rombo' | 'cruz'
//   textos:       [{ x, y, texto, color, ancla }]           coordenadas de la gráfica
//
// Los tramos donde y es null o cae fuera del rango se cortan (así una
// asíntota no dibuja una línea vertical falsa).

const GraficaSvg = (function () {
    const NS = 'http://www.w3.org/2000/svg';
    const ANCHO = 640;
    const ALTO = 420;
    const M = { izq: 52, der: 18, sup: 18, inf: 34 };
    const COLOR_TEXTO = '#8b96a8';
    const COLOR_EJE = 'rgba(148, 163, 184, 0.45)';
    const COLOR_REJILLA = 'rgba(148, 163, 184, 0.10)';

    let contadorClip = 0;

    function nodo(nombre, atributos = {}, texto) {
        const el = document.createElementNS(NS, nombre);
        Object.entries(atributos).forEach(([k, v]) => {
            if (v !== undefined && v !== null) {
                el.setAttribute(k, v);
            }
        });
        if (texto !== undefined) {
            el.textContent = texto;
        }
        return el;
    }

    // Formato corto: 0.5, 1.25, 3e-5, 1200
    function formato(n) {
        if (n === 0 || Math.abs(n) < 1e-12) {
            return '0';
        }
        const a = Math.abs(n);
        if (a >= 1e5 || a < 1e-3) {
            return n.toExponential(1).replace('e+', 'e');
        }
        return String(Number(n.toPrecision(4)));
    }

    // Marcas "bonitas" (1, 2, 5 × 10^k)
    function marcas(min, max, cantidad) {
        const rango = max - min;
        if (!(rango > 0)) {
            return [min];
        }
        const bruto = rango / cantidad;
        const potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
        const f = bruto / potencia;
        const paso = (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * potencia;
        const lista = [];
        for (let v = Math.ceil(min / paso) * paso; v <= max + paso * 1e-9; v += paso) {
            lista.push(Math.abs(v) < paso * 1e-9 ? 0 : v);
        }
        return lista;
    }

    function dibujar(svg, escena) {
        if (!svg || !escena || !escena.dominio) {
            return;
        }
        const { xMin, xMax, yMin, yMax } = escena.dominio;
        const anchoG = ANCHO - M.izq - M.der;
        const altoG = ALTO - M.sup - M.inf;

        const sx = (x) => M.izq + ((x - xMin) / (xMax - xMin)) * anchoG;
        const sy = (y) => M.sup + (1 - (y - yMin) / (yMax - yMin)) * altoG;
        const dentroY = (y) => y !== null && y !== undefined && Number.isFinite(y) && y >= yMin && y <= yMax;

        svg.replaceChildren();
        svg.setAttribute('viewBox', `0 0 ${ANCHO} ${ALTO}`);
        svg.setAttribute('role', 'img');

        const idClip = `gsvg-clip-${contadorClip += 1}`;
        const defs = nodo('defs');
        defs.appendChild(nodo('clipPath', { id: idClip },)).appendChild(
            nodo('rect', { x: M.izq, y: M.sup, width: anchoG, height: altoG }));
        svg.appendChild(defs);

        // Rejilla y marcas
        const rejilla = nodo('g');
        marcas(xMin, xMax, 7).forEach((v) => {
            rejilla.appendChild(nodo('line', { x1: sx(v), y1: M.sup, x2: sx(v), y2: M.sup + altoG, stroke: COLOR_REJILLA }));
            rejilla.appendChild(nodo('text', {
                x: sx(v), y: ALTO - 12, fill: COLOR_TEXTO, 'font-size': 11,
                'font-family': 'JetBrains Mono, monospace', 'text-anchor': 'middle',
            }, formato(v)));
        });
        marcas(yMin, yMax, 6).forEach((v) => {
            rejilla.appendChild(nodo('line', { x1: M.izq, y1: sy(v), x2: M.izq + anchoG, y2: sy(v), stroke: COLOR_REJILLA }));
            rejilla.appendChild(nodo('text', {
                x: M.izq - 6, y: sy(v) + 4, fill: COLOR_TEXTO, 'font-size': 11,
                'font-family': 'JetBrains Mono, monospace', 'text-anchor': 'end',
            }, formato(v)));
        });
        svg.appendChild(rejilla);
        svg.appendChild(nodo('rect', {
            x: M.izq, y: M.sup, width: anchoG, height: altoG, fill: 'none', stroke: COLOR_REJILLA,
        }));

        // Ejes x = 0 e y = 0 (si caen dentro)
        if (yMin <= 0 && yMax >= 0) {
            svg.appendChild(nodo('line', { x1: M.izq, y1: sy(0), x2: M.izq + anchoG, y2: sy(0), stroke: COLOR_EJE, 'stroke-width': 1.25 }));
        }
        if (xMin <= 0 && xMax >= 0) {
            svg.appendChild(nodo('line', { x1: sx(0), y1: M.sup, x2: sx(0), y2: M.sup + altoG, stroke: COLOR_EJE, 'stroke-width': 1.25 }));
        }

        // Todo lo que se dibuja dentro del área, recortado
        const g = nodo('g', { 'clip-path': `url(#${idClip})` });
        svg.appendChild(g);

        (escena.bandas || []).forEach((b) => {
            g.appendChild(nodo('rect', {
                x: sx(Math.min(b.x1, b.x2)), y: M.sup,
                width: Math.abs(sx(b.x2) - sx(b.x1)), height: altoG,
                fill: b.color || '#4fd1c5', opacity: b.opacidad ?? 0.12,
            }));
        });

        (escena.poligonos || []).forEach((pol) => {
            const validos = pol.puntos.filter((q) => q.y !== null && q.y !== undefined && Number.isFinite(q.y));
            if (validos.length < 3) {
                return;
            }
            g.appendChild(nodo('polygon', {
                points: validos.map((q) => `${sx(q.x).toFixed(2)},${sy(q.y).toFixed(2)}`).join(' '),
                fill: pol.color || '#4fd1c5', 'fill-opacity': pol.opacidad ?? 0.25,
                stroke: pol.borde || 'none', 'stroke-width': pol.anchoBorde || 1.25, 'stroke-linejoin': 'round',
            }));
        });

        (escena.horizontales || []).forEach((h) => {
            g.appendChild(nodo('line', {
                x1: M.izq, y1: sy(h.y), x2: M.izq + anchoG, y2: sy(h.y),
                stroke: h.color || COLOR_EJE, 'stroke-width': 1.25,
                'stroke-dasharray': h.discontinua ? '5 4' : undefined,
            }));
        });

        (escena.verticales || []).forEach((v) => {
            const y1 = v.y1 === undefined ? yMin : v.y1;
            const y2 = v.y2 === undefined ? yMax : v.y2;
            g.appendChild(nodo('line', {
                x1: sx(v.x), y1: sy(y1), x2: sx(v.x), y2: sy(y2),
                stroke: v.color || COLOR_EJE, 'stroke-width': v.ancho || 1.25,
                'stroke-dasharray': v.discontinua ? '5 4' : undefined,
            }));
        });

        (escena.segmentos || []).forEach((t) => {
            g.appendChild(nodo('line', {
                x1: sx(t.x1), y1: sy(t.y1), x2: sx(t.x2), y2: sy(t.y2),
                stroke: t.color || '#e6e9ef', 'stroke-width': t.ancho || 1.5,
                'stroke-dasharray': t.discontinua ? '5 4' : undefined,
            }));
        });

        (escena.rectas || []).forEach((r) => {
            let xa = xMin;
            let xb = xMax;
            let ya;
            let yb;
            if (r.x1 === r.x2) {
                xa = xb = r.x1;
                ya = yMin;
                yb = yMax;
            } else {
                const m = (r.y2 - r.y1) / (r.x2 - r.x1);
                ya = r.y1 + m * (xa - r.x1);
                yb = r.y1 + m * (xb - r.x1);
            }
            if (![ya, yb].every(Number.isFinite)) {
                return;
            }
            g.appendChild(nodo('line', {
                x1: sx(xa), y1: sy(ya), x2: sx(xb), y2: sy(yb),
                stroke: r.color || '#b892f0', 'stroke-width': r.ancho || 1.75,
                'stroke-dasharray': r.discontinua ? '6 4' : undefined,
            }));
        });

        (escena.curvas || []).forEach((curva) => {
            // Se parte la polilínea donde no hay valor o se sale del rango.
            let tramo = [];
            const tramos = [tramo];
            curva.puntos.forEach((p) => {
                if (dentroY(p.y)) {
                    tramo.push(`${sx(p.x).toFixed(2)},${sy(p.y).toFixed(2)}`);
                } else if (tramo.length) {
                    tramo = [];
                    tramos.push(tramo);
                }
            });
            tramos.filter((t) => t.length > 1).forEach((t) => {
                g.appendChild(nodo('polyline', {
                    points: t.join(' '), fill: 'none', stroke: curva.color || '#4fd1c5',
                    'stroke-width': curva.ancho || 2.25, 'stroke-linejoin': 'round',
                    'stroke-dasharray': curva.discontinua ? '6 4' : undefined,
                }));
            });
        });

        // Puntos y etiquetas van sin recorte para que no se corten los rótulos
        const capaPuntos = nodo('g');
        svg.appendChild(capaPuntos);

        (escena.puntos || []).forEach((p) => {
            // Un punto fuera de la ventana (iteración que se disparó) no se dibuja
            if (!(p.x >= xMin && p.x <= xMax && p.y >= yMin && p.y <= yMax)) {
                return;
            }
            const cx = sx(p.x);
            const cy = sy(p.y);
            const r = p.radio || 5;
            const color = p.color || '#e6e9ef';
            const relleno = p.hueco ? '#0a0d12' : color;

            if (p.forma === 'rombo') {
                capaPuntos.appendChild(nodo('path', {
                    d: `M${cx} ${cy - r - 2} L${cx + r + 2} ${cy} L${cx} ${cy + r + 2} L${cx - r - 2} ${cy} Z`,
                    fill: relleno, stroke: color, 'stroke-width': 2,
                }));
            } else if (p.forma === 'cruz') {
                capaPuntos.appendChild(nodo('path', {
                    d: `M${cx - r} ${cy - r} L${cx + r} ${cy + r} M${cx - r} ${cy + r} L${cx + r} ${cy - r}`,
                    stroke: color, 'stroke-width': 2.25, fill: 'none', 'stroke-linecap': 'round',
                }));
            } else {
                capaPuntos.appendChild(nodo('circle', {
                    cx, cy, r, fill: relleno, stroke: color, 'stroke-width': 2,
                }));
            }

            if (p.etiqueta) {
                capaPuntos.appendChild(nodo('text', {
                    x: cx + (p.dx ?? 9), y: cy + (p.dy ?? -9), fill: color, 'font-size': 12,
                    'font-weight': 500, 'font-family': 'JetBrains Mono, monospace',
                    'text-anchor': p.ancla || 'start',
                    'paint-order': 'stroke', stroke: '#0a0d12', 'stroke-width': 3, 'stroke-linejoin': 'round',
                }, p.etiqueta));
            }
        });

        (escena.textos || []).forEach((t) => {
            capaPuntos.appendChild(nodo('text', {
                x: sx(t.x), y: sy(t.y), fill: t.color || COLOR_TEXTO, 'font-size': 11,
                'font-family': 'JetBrains Mono, monospace', 'text-anchor': t.ancla || 'start',
            }, t.texto));
        });
    }

    return { dibujar, formato };
})();