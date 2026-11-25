// Gráfica de Steffensen: la curva g(x), la recta y = x y la "telaraña" del punto
// fijo  x₀ → x₁ = g(x₀) → x₂ = g(x₁). Con esos tres valores se calcula la
// extrapolación de Aitken (rombo sobre la diagonal), que es el nuevo x₀.
// Datos: resultado.grafica.pasos = [{x0, x1, x2, x}]  (comun/grafica.py -> armar_grafica_steffensen)

const GraficaSteffensen = GraficaIterativa.crear({
    total: (d) => d.grafica.pasos.length,
    etiqueta: (k, d) => `Iteración ${k + 1} de ${d.grafica.pasos.length}`,

    escena(k, d) {
        const { COLOR } = GraficaComun;
        const g = d.grafica;
        const s = g.pasos[k];
        const dom = g.dominio;
        const tela = { color: COLOR.blanco, ancho: 1.5, discontinua: true };
        const arriba = (y) => (y >= s.x0 ? -10 : 18);

        return {
            dominio: dom,
            curvas: [{ puntos: g.puntos, color: COLOR.acento }],
            // y = x
            rectas: [{ x1: dom.xMin, y1: dom.xMin, x2: dom.xMax, y2: dom.xMax, color: COLOR.gris, ancho: 1.5 }],
            // telaraña: (x0,x0) → (x0,x1) → (x1,x1) → (x1,x2) → (x2,x2)
            segmentos: [
                { x1: s.x0, y1: s.x0, x2: s.x0, y2: s.x1, ...tela },
                { x1: s.x0, y1: s.x1, x2: s.x1, y2: s.x1, ...tela },
                { x1: s.x1, y1: s.x1, x2: s.x1, y2: s.x2, ...tela },
                { x1: s.x1, y1: s.x2, x2: s.x2, y2: s.x2, ...tela },
            ],
            puntos: [
                ...g.pasos.slice(0, k).map((p) => ({ x: p.x, y: p.x, color: COLOR.gris, radio: 2.5 })),
                { x: s.x0, y: s.x0, color: COLOR.blanco, radio: 5, etiqueta: 'x₀', dx: 8, dy: 16 },
                { x: s.x1, y: s.x1, color: COLOR.blanco, radio: 5, etiqueta: 'x₁', dx: 8, dy: 16 },
                { x: s.x2, y: s.x2, color: COLOR.blanco, radio: 5, etiqueta: 'x₂', dx: 8, dy: arriba(s.x2) },
                { x: s.x, y: s.x, color: COLOR.recta, forma: 'rombo', radio: 5, etiqueta: 'Aitken', dx: 10, dy: -12 },
            ],
        };
    },

    leyenda(k, d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const s = d.grafica.pasos[k];
        const ultimo = k === d.grafica.pasos.length - 1;
        return [
            linea(
                chip(COLOR.blanco, `x₀ = ${num(s.x0)}`), ' ',
                chip(COLOR.blanco, `x₁ = g(x₀) = ${num(s.x1)}`), ' ',
                chip(COLOR.blanco, `x₂ = g(x₁) = ${num(s.x2)}`),
                '  La telaraña salta entre la curva y la diagonal y = x.',
            ),
            linea(
                chip(COLOR.recta, `x = x₀ − (x₁ − x₀)² / (x₂ − 2x₁ + x₀) = ${num(s.x)}`), '  ',
                ultimo ? 'Última iteración mostrada: ese valor es la raíz aproximada.' : 'Ese valor de Aitken es el x₀ de la siguiente iteración.',
            ),
        ];
    },
});
