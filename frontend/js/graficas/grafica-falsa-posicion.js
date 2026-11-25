// Gráfica de Falsa Posición: la recta (secante) que une (a, f(a)) y (b, f(b)),
// su corte con el eje x (= c) y el cambio de signo que decide qué extremo se reemplaza.
// Datos: resultado.grafica = { dominio, puntos, pasos: [{p, fp, q, fq, r, fr}] }
//   (p = a, q = b, r = c; los arma comun/grafica.py -> armar_grafica_dos_puntos)

const GraficaFalsaPosicion = GraficaIterativa.crear({
    total: (d) => d.grafica.pasos.length,
    etiqueta: (k, d) => `Iteración ${k + 1} de ${d.grafica.pasos.length}`,

    escena(k, d) {
        const { COLOR, colorSigno, textoSigno, recta } = GraficaComun;
        const g = d.grafica;
        const s = g.pasos[k];
        const primero = g.pasos[0];
        const arriba = (y) => (y >= 0 ? -10 : 18);
        
        return {
            dominio: g.dominio,
            bandas: [
                { x1: primero.p, x2: primero.q, color: COLOR.gris, opacidad: 0.06 },
                { x1: s.p, x2: s.q, color: COLOR.acento, opacidad: 0.14 },
            ],
            curvas: [{ puntos: g.puntos, color: COLOR.acento }],
            rectas: [recta(s.p, s.fp, s.q, s.fq)],
            verticales: [{ x: s.r, y1: 0, y2: s.fr, color: COLOR.acento, discontinua: true }],
            puntos: [
                { x: s.p, y: s.fp, color: colorSigno(s.fp), radio: 6, etiqueta: `a  (${textoSigno(s.fp)})`, dx: -10, dy: arriba(s.fp), ancla: 'end' },
                { x: s.q, y: s.fq, color: colorSigno(s.fq), radio: 6, etiqueta: `b  (${textoSigno(s.fq)})`, dx: 10, dy: arriba(s.fq) },
                { x: s.r, y: 0, color: COLOR.blanco, forma: 'rombo', radio: 4, etiqueta: 'c', dx: 0, dy: 26, ancla: 'middle' },
                { x: s.r, y: s.fr, color: COLOR.acento, hueco: true, radio: 5 },
            ],
        };
    },

    leyenda(k, d) {
        const { COLOR, num, colorSigno, textoSigno, chip, linea } = GraficaComun;
        const s = d.grafica.pasos[k];
        const sig = d.grafica.pasos[k + 1];

        const l1 = linea(
            chip(colorSigno(s.fp), `f(a) = ${num(s.fp)}  (${textoSigno(s.fp)})`), ' ',
            chip(colorSigno(s.fq), `f(b) = ${num(s.fq)}  (${textoSigno(s.fq)})`),
            '  La recta que une ambos puntos corta el eje x en c.',
        );
        const l2 = linea(chip(COLOR.blanco, `c = ${num(s.r)}`), ' ', chip(colorSigno(s.fr), `f(c) = ${num(s.fr)}  (${textoSigno(s.fr)})`), '  ');
        if (sig) {
            l2.append(sig.p === s.r
                ? `f(c) tiene el signo de f(a): c reemplaza a a → nuevo intervalo [${num(sig.p)}, ${num(sig.q)}].`
                : `f(c) tiene el signo de f(b): c reemplaza a b → nuevo intervalo [${num(sig.p)}, ${num(sig.q)}].`);
        } else {
            l2.append('Última iteración mostrada: c es la raíz aproximada.');
        }
        return [l1, l2];
    },
});
