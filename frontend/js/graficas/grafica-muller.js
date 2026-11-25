// Gráfica de Müller: la parábola P(x) = a(x − p₂)² + b(x − p₂) + c que pasa por
// (p₀, f₀), (p₁, f₁) y (p₂, f₂); donde corta el eje x está la nueva aproximación p₃.
// Si el discriminante es negativo la parábola no toca el eje: p₃ es complejo y
// se explica en la leyenda. Si p₀, p₁ o p₂ ya son complejos, esa iteración no
// se puede dibujar en el plano real y solo se muestran los valores.
// Datos: resultado.grafica.pasos = [{real, p0..p3, p3c, f0..f3, a, b, c}]
//   (comun/grafica.py -> armar_grafica_muller)

const GraficaMuller = GraficaIterativa.crear({
    total: (d) => d.grafica.pasos.length,
    etiqueta: (k, d) => `Iteración ${k + 1} de ${d.grafica.pasos.length}`,

    escena(k, d) {
        const { COLOR } = GraficaComun;
        const g = d.grafica;
        const s = g.pasos[k];
        const dom = g.dominio;
        const base = { dominio: dom, curvas: [{ puntos: g.puntos, color: COLOR.acento }] };

        if (!s.real) {
            return { ...base, textos: [{ x: (dom.xMin + dom.xMax) / 2, y: (dom.yMin + dom.yMax) / 2,
                texto: 'Esta iteración usa valores complejos: no se puede dibujar en el plano real', ancla: 'middle' }] };
        }

        // Parábola muestreada sobre todo el dominio
        const parabola = [];
        const n = 240;
        for (let i = 0; i <= n; i += 1) {
            const x = dom.xMin + ((dom.xMax - dom.xMin) * i) / n;
            const t = x - s.p2;
            parabola.push({ x, y: s.a * t * t + s.b * t + s.c });
        }

        const arriba = (y) => (y >= 0 ? -10 : 18);
        const puntos = [
            ...g.pasos.slice(0, k).filter((p) => p.p3 !== null).map((p) => ({ x: p.p3, y: 0, color: COLOR.gris, radio: 2.5 })),
            { x: s.p0, y: s.f0, color: COLOR.blanco, radio: 5, etiqueta: 'p₀', dx: 0, dy: arriba(s.f0), ancla: 'middle' },
            { x: s.p1, y: s.f1, color: COLOR.blanco, radio: 5, etiqueta: 'p₁', dx: 0, dy: arriba(s.f1), ancla: 'middle' },
            { x: s.p2, y: s.f2, color: COLOR.blanco, radio: 5, etiqueta: 'p₂', dx: 0, dy: arriba(s.f2), ancla: 'middle' },
        ];
        const verticales = [];
        if (s.p3 !== null) {
            puntos.push({ x: s.p3, y: 0, color: COLOR.acento, forma: 'rombo', radio: 4, etiqueta: 'p₃', dx: 0, dy: (s.f3 ?? 1) < 0 ? -14 : 26, ancla: 'middle' });
            if (s.f3 !== null) {
                puntos.push({ x: s.p3, y: s.f3, color: COLOR.acento, hueco: true, radio: 5 });
                verticales.push({ x: s.p3, y1: 0, y2: s.f3, color: COLOR.acento, discontinua: true });
            }
        }

        return { ...base, curvas: [...base.curvas, { puntos: parabola, color: COLOR.recta, ancho: 1.75 }], verticales, puntos };
    },

    leyenda(k, d) {
        const { COLOR, num, chip, linea } = GraficaComun;
        const s = d.grafica.pasos[k];

        if (!s.real) {
            return [linea('Los puntos de esta iteración son complejos, así que la parábola no se dibuja en el plano real.')];
        }

        const l1 = linea(
            chip(COLOR.blanco, `p₀ = ${num(s.p0)}`), ' ', chip(COLOR.blanco, `p₁ = ${num(s.p1)}`), ' ', chip(COLOR.blanco, `p₂ = ${num(s.p2)}`),
            '  La parábola morada pasa por los tres puntos.',
        );
        const l2 = linea(chip(COLOR.recta, `a = ${num(s.a)}   b = ${num(s.b)}   c = ${num(s.c)}`), '  ');
        if (s.p3 !== null) {
            l2.append(chip(COLOR.acento, `p₃ = ${num(s.p3)}`), ' donde la parábola corta el eje x.');
        } else if (s.p3c) {
            l2.append(chip(COLOR.acento, `p₃ = ${num(s.p3c.re)} ${s.p3c.im < 0 ? '−' : '+'} ${num(Math.abs(s.p3c.im))}i`),
                ' La parábola no corta el eje x (discriminante negativo): la nueva aproximación es compleja.');
        }
        return [l1, l2];
    },
});
