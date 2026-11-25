// Gráfica de Newton-Raphson: en cada paso se traza la TANGENTE a f en
// (xₖ, f(xₖ)); donde corta el eje x está xₖ₊₁. La pendiente se obtiene de los
// dos puntos (xₖ, f(xₖ)) y (xₖ₊₁, 0), así que no hace falta mandar f'(x).
// Datos: resultado.grafica.pasos = [{x, fx}] (x₀, x₁, x₂, ...)

const GraficaNewton = GraficaIterativa.crear({
    total: (d) => Math.max(d.grafica.pasos.length - 1, 0),
    etiqueta: (k, d) => `Paso ${k + 1} de ${d.grafica.pasos.length - 1}`,

    escena(k, d) {
        const { COLOR, recta, historial } = GraficaComun;
        const g = d.grafica;
        const a = g.pasos[k];          // (xₖ, f(xₖ))
        const b = g.pasos[k + 1];      // (xₖ₊₁, f(xₖ₊₁))
        const arriba = (y) => (y >= 0 ? -10 : 18);

        return {
            dominio: g.dominio,
            curvas: [{ puntos: g.puntos, color: COLOR.acento }],
            rectas: a.fx === null ? [] : [recta(a.x, a.fx, b.x, 0)],      // tangente
            verticales: [
                { x: a.x, y1: 0, y2: a.fx ?? 0, color: COLOR.blanco, discontinua: true },
                { x: b.x, y1: 0, y2: b.fx ?? 0, color: COLOR.acento, discontinua: true },
            ],
            puntos: [
                ...historial(g.pasos.slice(0, k).map((p) => p.x)),
                { x: a.x, y: a.fx, color: COLOR.blanco, radio: 6, etiqueta: `x${subindice(k)}`, dx: 10, dy: arriba(a.fx) },
                { x: b.x, y: 0, color: COLOR.acento, forma: 'rombo', radio: 4, etiqueta: `x${subindice(k + 1)}`, dx: 0, dy: 26, ancla: 'middle' },
                { x: b.x, y: b.fx, color: COLOR.acento, hueco: true, radio: 5 },
            ],
        };
    },

    leyenda(k, d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const a = d.grafica.pasos[k];
        const b = d.grafica.pasos[k + 1];
        const pendiente = a.x !== b.x && a.fx !== null ? a.fx / (a.x - b.x) : null;
        const ultimo = k === d.grafica.pasos.length - 2;

        return [
            linea(
                chip(COLOR.blanco, `x${subindice(k)} = ${num(a.x)}`), ' ', chip(COLOR.gris, `f(x${subindice(k)}) = ${num(a.fx)}`), ' ',
                chip(COLOR.recta, `f′(x${subindice(k)}) ≈ ${num(pendiente)}`), '  La tangente en ese punto es la recta morada.',
            ),
            linea(
                chip(COLOR.acento, `x${subindice(k + 1)} = ${num(b.x)}`), '  ',
                `Donde la tangente corta el eje x: x${subindice(k + 1)} = x${subindice(k)} − f(x${subindice(k)}) / f′(x${subindice(k)}). `,
                ultimo ? 'Último paso mostrado: esa es la aproximación final.' : 'Desde ahí se traza la siguiente tangente.',
            ),
        ];
    },
});

function subindice(n) {
    return String(n).replace(/\d/g, (d) => '₀₁₂₃₄₅₆₇₈₉'[d]);
}
