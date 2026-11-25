// Piezas compartidas por las gráficas de los métodos de raíces:
// colores, formato de números, "chips" de la leyenda y la recta por dos puntos
// (la secante de Falsa Posición / Secante y la tangente de Newton son la misma
// mecánica: una recta que pasa por dos puntos y corta el eje x).
// Orden de scripts: grafica-svg.js -> grafica-comun.js -> grafica-iterativa.js -> grafica-<método>.js

const GraficaComun = (function () {
    const COLOR = {
        neg: '#f2a4a0',      // f < 0
        pos: '#86d9a0',      // f > 0
        acento: '#4fd1c5',   // curva f(x)
        gris: '#8b96a8',
        recta: '#b892f0',    // secante / tangente
        blanco: '#e6e9ef',
    };

    const num = (v) => (v === null || v === undefined ? '—' : GraficaSvg.formato(v).replace('-', '−'));
    const colorSigno = (v) => (v < 0 ? COLOR.neg : COLOR.pos);
    const textoSigno = (v) => (v < 0 ? '−' : '+');

    function chip(color, texto) {
        const c = document.createElement('span');
        c.className = 'graph-chip';
        c.style.setProperty('--chip', color);
        c.textContent = texto;
        return c;
    }

    // Párrafo de leyenda: acepta textos y nodos (chips) mezclados
    function linea(...partes) {
        const p = document.createElement('p');
        p.className = 'graph-legend__linea';
        p.append(...partes);
        return p;
    }

    // Recta infinita por (x1,y1) y (x2,y2): entra en escena.rectas
    const recta = (x1, y1, x2, y2, extra = {}) => ({ x1, y1, x2, y2, color: COLOR.recta, ...extra });

    // Puntos anteriores de la sucesión, pequeños y sobre el eje x
    const historial = (xs) => xs.map((x) => ({ x, y: 0, color: COLOR.gris, radio: 2.5 }));

    return { COLOR, num, colorSigno, textoSigno, chip, linea, recta, historial };
})();

// ---------------------------------------------------------------------------
// Integración: polígono del área bajo una curva muestreada entre x1 y x2.
// Los bordes usan los valores exactos f1 = f(x1) y f2 = f(x2).
// ---------------------------------------------------------------------------
GraficaComun.areaBajoCurva = function (puntos, x1, x2, f1, f2) {
    const dentro = puntos.filter((p) => p.y !== null && p.x > x1 && p.x < x2);
    return [{ x: x1, y: 0 }, { x: x1, y: f1 }, ...dentro, { x: x2, y: f2 }, { x: x2, y: 0 }];
};

// Polinomio de Lagrange que pasa por (xs[i], fs[i]), evaluado en x
GraficaComun.lagrange = function (xs, fs, x) {
    let suma = 0;
    for (let i = 0; i < xs.length; i += 1) {
        let t = fs[i];
        for (let j = 0; j < xs.length; j += 1) {
            if (j !== i) {
                t *= (x - xs[j]) / (xs[i] - xs[j]);
            }
        }
        suma += t;
    }
    return suma;
};