// Gráfica de Deflación: el polinomio original (tenue) y, en cada etapa, el
// polinomio que se tiene en ese momento (brillante) con la raíz que se encontró.
// Las raíces ya halladas quedan marcadas sobre el eje x. Las raíces complejas no
// están en el plano real: se muestran en la leyenda, y si el polinomio de una
// etapa ya tiene coeficientes complejos solo se dibuja el original.
// Datos: resultado.grafica = { dominio, puntos, coeficientes, etapas: [{grado, coef, raiz, esReal}] }
//   (comun/grafica.py -> armar_grafica_deflacion)

const GraficaDeflacion = (function () {
    const horner = (coefs, x) => coefs.reduce((acc, c) => acc * x + c);

    function textoRaiz(raiz) {
        const { num } = GraficaComun;
        if (raiz !== null && typeof raiz === 'object') {
            return `${num(raiz.re)} ${raiz.im < 0 ? '−' : '+'} ${num(Math.abs(raiz.im))}i`;
        }
        return num(raiz);
    }

    return GraficaIterativa.crear({
        total: (d) => d.grafica.etapas.length,
        etiqueta: (k, d) => `Raíz ${k + 1} de ${d.grafica.etapas.length}`,

        escena(k, d) {
            const { COLOR } = GraficaComun;
            const g = d.grafica;
            const e = g.etapas[k];
            const dom = g.dominio;
            const curvas = [{ puntos: g.puntos, color: e.coef ? COLOR.gris : COLOR.acento, ancho: e.coef ? 1.5 : 2.25 }];

            if (e.coef && e.grado < g.coeficientes.length - 1) {
                const puntos = [];
                for (let i = 0; i <= 300; i += 1) {
                    const x = dom.xMin + ((dom.xMax - dom.xMin) * i) / 300;
                    puntos.push({ x, y: horner(e.coef, x) });
                }
                curvas.push({ puntos, color: COLOR.acento });
            } else if (e.coef) {
                curvas[0].color = COLOR.acento;
                curvas[0].ancho = 2.25;
            }

            const puntos = [];
            g.etapas.forEach((otra, i) => {
                if (!otra.esReal || i === k) { return; }
                puntos.push({ x: otra.raiz, y: 0, color: i < k ? COLOR.acento : COLOR.gris, hueco: i > k, radio: 4 });
            });
            if (e.esReal) {
                puntos.push({ x: e.raiz, y: 0, color: COLOR.blanco, forma: 'rombo', radio: 5,
                    etiqueta: `x ≈ ${GraficaComun.num(e.raiz)}`, dx: 0, dy: -14, ancla: 'middle' });
            }

            const textos = e.esReal ? [] : [{ x: (dom.xMin + dom.xMax) / 2, y: dom.yMax - (dom.yMax - dom.yMin) * 0.06,
                texto: 'Raíz compleja: no está en el eje real', ancla: 'middle' }];

            return { dominio: dom, curvas, puntos, textos };
        },

        leyenda(k, d) {
            const { COLOR, chip, linea } = GraficaComun;
            const e = d.grafica.etapas[k];
            const l1 = linea(
                `Polinomio de grado ${e.grado}  →  `,
                chip(e.esReal ? COLOR.acento : COLOR.recta, `raíz = ${textoRaiz(e.raiz)}`),
            );
            const l2 = linea(
                e.esReal ? 'Se divide el polinomio entre (x − raíz) y queda uno de un grado menos.'
                    : 'Es una raíz compleja: se divide igualmente y el polinomio que queda tiene coeficientes complejos.',
                e.coef ? '' : ' (Este polinomio ya tiene coeficientes complejos: se muestra solo el original.)',
            );
            return [l1, l2];
        },
    });
})();
