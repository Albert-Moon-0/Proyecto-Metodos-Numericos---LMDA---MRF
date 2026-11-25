// Gráfica de la Secante: la recta que pasa por (xₙ₋₁, f(xₙ₋₁)) y (xₙ, f(xₙ))
// corta el eje x en xₙ₊₁. A diferencia de Falsa Posición no hay intervalo ni
// cambio de signo: siempre se quedan los dos puntos más recientes.
// Datos: resultado.grafica.pasos = [{p, fp, q, fq, r, fr}]  (p = xₙ₋₁, q = xₙ, r = xₙ₊₁)

const GraficaSecante = GraficaIterativa.crear({
    total: (d) => d.grafica.pasos.length,
    etiqueta: (k, d) => `Iteración ${k + 1} de ${d.grafica.pasos.length}`,

    escena(k, d) {
        const { COLOR, recta, historial } = GraficaComun;
        const g = d.grafica;
        const s = g.pasos[k];
        const arriba = (y) => (y >= 0 ? -10 : 18);

        return {
            dominio: g.dominio,
            curvas: [{ puntos: g.puntos, color: COLOR.acento }],
            rectas: [recta(s.p, s.fp, s.q, s.fq)],
            verticales: [{ x: s.r, y1: 0, y2: s.fr, color: COLOR.acento, discontinua: true }],
            puntos: [
                ...historial(g.pasos.slice(0, k).map((paso) => paso.r)),
                { x: s.p, y: s.fp, color: COLOR.gris, radio: 5, etiqueta: 'xₙ₋₁', dx: -10, dy: arriba(s.fp), ancla: 'end' },
                { x: s.q, y: s.fq, color: COLOR.blanco, radio: 6, etiqueta: 'xₙ', dx: 10, dy: arriba(s.fq) },
                { x: s.r, y: 0, color: COLOR.acento, forma: 'rombo', radio: 4, etiqueta: 'xₙ₊₁', dx: 0, dy: 26, ancla: 'middle' },
                { x: s.r, y: s.fr, color: COLOR.acento, hueco: true, radio: 5 },
            ],
        };
    },

    leyenda(k, d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const s = d.grafica.pasos[k];
        const ultimo = k === d.grafica.pasos.length - 1;

        return [
            linea(
                chip(COLOR.gris, `xₙ₋₁ = ${num(s.p)}`), ' ', chip(COLOR.blanco, `xₙ = ${num(s.q)}`),
                '  La secante por (xₙ₋₁, f(xₙ₋₁)) y (xₙ, f(xₙ)) corta el eje x en xₙ₊₁.',
            ),
            linea(
                chip(COLOR.acento, `xₙ₊₁ = ${num(s.r)}`), ' ', chip(COLOR.gris, `f(xₙ₊₁) = ${num(s.fr)}`), '  ',
                ultimo ? 'Última iteración mostrada: xₙ₊₁ es la raíz aproximada.' : 'Se descarta xₙ₋₁ y se repite con xₙ y xₙ₊₁.',
            ),
        ];
    },
});
