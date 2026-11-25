// Gráfica de Romberg: la columna 0 de la tabla es el trapecio compuesto con
// 2^k subintervalos. El deslizador recorre k = 0, 1, 2, ...: se ve cómo los
// trapecios (morado) se pegan al área real (verde-azulado) al duplicar n. La
// leyenda da R(k,0) y la mejor aproximación R(k,k) tras la extrapolación de
// Richardson. Si 2^k es demasiado grande para dibujar, solo se muestra la curva.
// Datos: resultado.grafica = { dominio, puntos, pasos: [{k, n, xs, fs}] }
//   (comun/grafica.py -> armar_grafica_romberg) y resultado.iteraciones (r, error)
// Requiere: grafica-integracion.js (dibuja los polígonos).

const GraficaRomberg = GraficaIterativa.crear({
    total: (d) => d.grafica.pasos.length,
    etiqueta: (k, d) => `k = ${d.grafica.pasos[k].k} · n = ${d.grafica.pasos[k].n}`,

    escena(k, d) {
        const { COLOR } = GraficaComun;
        const g = d.grafica;
        const paso = g.pasos[k];

        if (!paso.xs) {
            return {
                dominio: g.dominio,
                curvas: [{ puntos: g.puntos, color: COLOR.acento }],
                textos: [{ x: (g.dominio.xMin + g.dominio.xMax) / 2, y: g.dominio.yMax - (g.dominio.yMax - g.dominio.yMin) * 0.06,
                    texto: `${paso.n} trapecios: demasiados para dibujar`, ancla: 'middle' }],
            };
        }

        const grupos = [];
        for (let i = 0; i < paso.xs.length - 1; i += 1) {
            grupos.push({ xs: [paso.xs[i], paso.xs[i + 1]], fs: [paso.fs[i], paso.fs[i + 1]] });
        }
        return GraficaIntegracion.escenaGrupos(g, grupos, { etiquetarNodos: paso.n <= 8 });
    },

    leyenda(k, d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const fila = d.iteraciones[k];
        const l1 = linea(
            chip(COLOR.recta, `R(${fila.k},0) = trapecio con n = ${fila.n}:  ${num(fila.r[0])}`), ' ',
            chip(COLOR.blanco, `h = ${num(fila.h)}`),
        );
        const l2 = fila.k === 0
            ? linea('Primera fila: un solo trapecio; todavía no hay extrapolación.')
            : linea(
                chip(COLOR.acento, `R(${fila.k},${fila.k}) = ${num(fila.r[fila.k])}`),
                `  mejor aproximación tras extrapolar (Richardson). Error ≈ ${fila.error === null ? '—' : fila.error.toExponential(2)}`,
            );
        return [l1, l2];
    },
});
