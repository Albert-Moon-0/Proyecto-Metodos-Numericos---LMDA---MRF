// Gráfica de Trapecio / Simpson 1/3 / Simpson 3/8 (simples y compuestos) y base
// de la de Romberg. Muestra:
//   - la función f(x) y, rellena en verde-azulado, el ÁREA REAL bajo la curva;
//   - los puntos dados (xᵢ, f(xᵢ)) con una línea punteada hasta el eje x;
//   - en morado, el área que calcula la regla: trapecios (recta), parábolas
//     (Simpson 1/3) o cúbicas (Simpson 3/8) por los nodos de cada grupo.
// Donde ambas áreas no coinciden se ve el error de la aproximación.
//
// Datos: resultado.grafica = { dominio, puntos, grupos: [{xs, fs}] }
//   (comun/grafica.py -> armar_grafica_integracion)
// Ids del HTML: graph-empty, graph-frame, graph-svg, graph-legend.
// Requiere: grafica-svg.js, grafica-comun.js.

const GraficaIntegracion = (function () {
    const $ = (id) => document.getElementById(id);

    // Escena para una lista de grupos [{xs, fs}] (reutilizada por Romberg)
    function escenaGrupos(g, grupos, { etiquetarNodos = true } = {}) {
        const { COLOR, areaBajoCurva, lagrange } = GraficaComun;
        const poligonosReales = [];
        const poligonosRegla = [];
        const puntos = [];
        const verticales = [];

        grupos.forEach((grupo) => {
            const { xs, fs } = grupo;
            if (fs.some((v) => v === null)) {
                return;
            }
            const x1 = xs[0];
            const x2 = xs[xs.length - 1];

            poligonosReales.push({ puntos: areaBajoCurva(g.puntos, x1, x2, fs[0], fs[fs.length - 1]),
                color: COLOR.acento, opacidad: 0.16 });

            // Polinomio por los nodos del grupo (2 puntos = recta: bastan los extremos)
            const muestras = xs.length === 2 ? 2 : 48;
            const curva = [];
            for (let i = 0; i < muestras; i += 1) {
                const x = x1 + ((x2 - x1) * i) / (muestras - 1);
                curva.push({ x, y: xs.length === 2 ? fs[i] : lagrange(xs, fs, x) });
            }
            poligonosRegla.push({ puntos: [{ x: x1, y: 0 }, ...curva, { x: x2, y: 0 }],
                color: COLOR.recta, opacidad: 0.3, borde: COLOR.recta, anchoBorde: 1.5 });
        });

        // Nodos: sin repetir los extremos compartidos entre grupos
        const vistos = new Set();
        let indice = 0;
        grupos.forEach((grupo) => {
            grupo.xs.forEach((x, i) => {
                if (vistos.has(x)) { return; }
                vistos.add(x);
                const fx = grupo.fs[i];
                if (fx === null) { return; }
                verticales.push({ x, y1: 0, y2: fx, color: COLOR.gris, discontinua: true });
                puntos.push({
                    x, y: fx, color: COLOR.blanco, radio: 3.5,
                    etiqueta: etiquetarNodos ? `x${indiceSub(indice)}` : undefined,
                    dx: 0, dy: fx >= 0 ? -10 : 18, ancla: 'middle',
                });
                indice += 1;
            });
        });

        return {
            dominio: g.dominio,
            poligonos: [...poligonosReales, ...poligonosRegla],
            verticales,
            curvas: [{ puntos: g.puntos, color: COLOR.acento, ancho: 2.25 }],
            puntos,
        };
    }

    function indiceSub(n) {
        return String(n).replace(/\d/g, (d) => '₀₁₂₃₄₅₆₇₈₉'[d]);
    }

    const NOMBRES = { trapecio: 'trapecios', simpson13: 'parábolas (Simpson 1/3)', simpson38: 'cúbicas (Simpson 3/8)' };

    function leyenda(d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const forma = NOMBRES[d.regla] || 'la regla';
        return [
            linea(
                chip(COLOR.acento, 'Área real bajo f(x)'), ' ',
                chip(COLOR.recta, `Área de la regla: ${forma}`), ' ',
                chip(COLOR.blanco, `${new Set(d.grafica.grupos.flatMap((gr) => gr.xs)).size} puntos`),
            ),
            linea(`Aproximación: ∫ f(x) dx ≈ ${num(d.aproximacion)}.  `,
                'Donde el morado se separa de la curva está el error de la regla.'),
        ];
    }

    function mostrar(resultado) {
        if (!resultado || !resultado.grafica || !resultado.grafica.grupos?.length) {
            limpiar();
            return;
        }
        $('graph-empty').hidden = true;
        $('graph-frame').hidden = false;
        GraficaSvg.dibujar($('graph-svg'), escenaGrupos(resultado.grafica, resultado.grafica.grupos,
            { etiquetarNodos: resultado.grafica.grupos.length <= 8 }));
        $('graph-legend').replaceChildren(...leyenda(resultado));
    }

    function limpiar() {
        $('graph-svg')?.replaceChildren();
        $('graph-legend')?.replaceChildren();
        if ($('graph-frame')) { $('graph-frame').hidden = true; }
        if ($('graph-empty')) { $('graph-empty').hidden = false; }
    }

    return { mostrar, limpiar, escenaGrupos };
})();
