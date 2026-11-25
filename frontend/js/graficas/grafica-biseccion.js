// Gráfica de Bisección: muestra f(x), el intervalo [a, b] de cada iteración y
// el CAMBIO DE SIGNO (f(a) en un color, f(b) en el otro), el punto medio c y,
// al final, la raíz. Un deslizador recorre las iteraciones (y un botón las anima).
//
// Usa grafica-svg.js (motor) y los datos que manda biseccion.py:
//   resultado.grafica      -> { dominio, puntos }  (curva f(x) muestreada)
//   resultado.iteraciones  -> a, b, c, fa, fb, fc por iteración
//
// Uso desde biseccion.js:   GraficaBiseccion.mostrar(resultado)  /  .limpiar()
// Orden de scripts: grafica-svg.js -> grafica-biseccion.js -> biseccion.js

const GraficaBiseccion = (function () {
    const NEG = '#f2a4a0';      // f < 0
    const POS = '#86d9a0';      // f > 0
    const ACENTO = '#4fd1c5';
    const GRIS = '#8b96a8';

    const $ = (id) => document.getElementById(id);
    let datos = null;           // último resultado
    let temporizador = null;

    const colorSigno = (v) => (v < 0 ? NEG : POS);
    const textoSigno = (v) => (v < 0 ? '−' : '+');
    const num = (v) => GraficaSvg.formato(v).replace('-', '−');

    // ---------------------------------------------------------------
    // Escena de una iteración
    // ---------------------------------------------------------------
    function escenaIteracion(k) {
        const { grafica, iteraciones, raiz, convergio } = datos;
        const it = iteraciones[k];
        const inicial = iteraciones[0];
        const esUltima = k === iteraciones.length - 1;
        const arriba = (y) => (y >= 0 ? -10 : 18);

        const puntos = [];

        // Puntos medios de iteraciones anteriores: pequeños, sobre el eje x
        for (let j = 0; j < k; j += 1) {
            puntos.push({ x: iteraciones[j].c, y: 0, color: GRIS, radio: 2.5 });
        }

        puntos.push(
            { x: it.a, y: it.fa, color: colorSigno(it.fa), radio: 6, etiqueta: `a  (${textoSigno(it.fa)})`, dx: -10, dy: arriba(it.fa), ancla: 'end' },
            { x: it.b, y: it.fb, color: colorSigno(it.fb), radio: 6, etiqueta: `b  (${textoSigno(it.fb)})`, dx: 10, dy: arriba(it.fb) },
            { x: it.c, y: it.fc, color: ACENTO, hueco: true, radio: 6, etiqueta: 'c', dx: 0, dy: it.fc >= 0 ? -12 : 20, ancla: 'middle' },
        );

        if (esUltima && convergio) {
            puntos.push({ x: raiz, y: 0, color: '#e6e9ef', forma: 'rombo', radio: 5, etiqueta: `x ≈ ${num(raiz)}`, dx: 0, dy: 26, ancla: 'middle' });
        }

        return {
            dominio: grafica.dominio,
            bandas: [
                { x1: inicial.a, x2: inicial.b, color: GRIS, opacidad: 0.06 },
                { x1: it.a, x2: it.b, color: ACENTO, opacidad: 0.14 },
            ],
            verticales: [
                { x: it.a, y1: 0, y2: it.fa, color: colorSigno(it.fa), discontinua: true },
                { x: it.b, y1: 0, y2: it.fb, color: colorSigno(it.fb), discontinua: true },
                { x: it.c, y1: 0, y2: it.fc, color: ACENTO, discontinua: true },
            ],
            curvas: [{ puntos: grafica.puntos, color: ACENTO, ancho: 2.25 }],
            puntos,
        };
    }

    // ---------------------------------------------------------------
    // Texto bajo la gráfica: explica el cambio de signo de la iteración
    // ---------------------------------------------------------------
    function chip(color, texto) {
        const c = document.createElement('span');
        c.className = 'graph-chip';
        c.style.setProperty('--chip', color);
        c.textContent = texto;
        return c;
    }

    function pintarLeyenda(k) {
        const { iteraciones } = datos;
        const it = iteraciones[k];
        const siguiente = iteraciones[k + 1];

        const linea1 = document.createElement('p');
        linea1.className = 'graph-legend__linea';
        linea1.append(
            `Iteración ${it.iteracion} de ${iteraciones.length}:  `,
            chip(colorSigno(it.fa), `f(a) = ${num(it.fa)}  (${textoSigno(it.fa)})`), ' ',
            chip(colorSigno(it.fb), `f(b) = ${num(it.fb)}  (${textoSigno(it.fb)})`),
            '  → signos opuestos: hay una raíz en [a, b].',
        );

        const linea2 = document.createElement('p');
        linea2.className = 'graph-legend__linea';
        linea2.append(chip(ACENTO, `c = ${num(it.c)}`), ' ', chip(colorSigno(it.fc), `f(c) = ${num(it.fc)}  (${textoSigno(it.fc)})`), '  ');
        if (siguiente) {
            const cambiaA = siguiente.a === it.c;
            linea2.append(cambiaA
                ? `f(c) tiene el signo de f(a): c reemplaza a a → nuevo intervalo [${num(siguiente.a)}, ${num(siguiente.b)}].`
                : `f(c) tiene el signo de f(b): c reemplaza a b → nuevo intervalo [${num(siguiente.a)}, ${num(siguiente.b)}].`);
        } else {
            linea2.append(datos.convergio ? 'Se alcanzó la tolerancia: c es la raíz aproximada.' : 'Se llegó al máximo de iteraciones.');
        }

        $('graph-legend').replaceChildren(linea1, linea2);
    }

    function mostrarIteracion(k) {
        GraficaSvg.dibujar($('graph-svg'), escenaIteracion(k));
        pintarLeyenda(k);
        $('graph-iter-texto').textContent = `Iteración ${k + 1} de ${datos.iteraciones.length}`;
        $('graph-iter').value = String(k + 1);
    }

    // ---------------------------------------------------------------
    // Controles
    // ---------------------------------------------------------------
    function detener() {
        if (temporizador) {
            clearInterval(temporizador);
            temporizador = null;
        }
        const boton = $('graph-play');
        if (boton) {
            boton.textContent = '▶ Animar';
        }
    }

    function animar() {
        if (temporizador) {
            detener();
            return;
        }
        let k = 0;
        mostrarIteracion(0);
        $('graph-play').textContent = '❚❚ Pausa';
        temporizador = setInterval(() => {
            k += 1;
            if (k >= datos.iteraciones.length) {
                detener();
                return;
            }
            mostrarIteracion(k);
        }, 900);
    }

    function limpiar() {
        detener();
        datos = null;
        $('graph-svg')?.replaceChildren();
        $('graph-legend')?.replaceChildren();
        if ($('graph-frame')) { $('graph-frame').hidden = true; }
        if ($('graph-controls')) { $('graph-controls').hidden = true; }
        if ($('graph-empty')) { $('graph-empty').hidden = false; }
    }

    function mostrar(resultado) {
        detener();
        if (!resultado || !resultado.grafica || !resultado.iteraciones?.length) {
            limpiar();
            return;
        }
        datos = resultado;
        $('graph-empty').hidden = true;
        $('graph-frame').hidden = false;
        $('graph-controls').hidden = false;

        const control = $('graph-iter');
        control.min = '1';
        control.max = String(resultado.iteraciones.length);
        mostrarIteracion(resultado.iteraciones.length - 1);   // arranca en el resultado final
    }

    document.addEventListener('DOMContentLoaded', () => {
        $('graph-iter')?.addEventListener('input', (e) => {
            detener();
            if (datos) { mostrarIteracion(Number(e.target.value) - 1); }
        });
        $('graph-play')?.addEventListener('click', () => { if (datos) { animar(); } });
    });

    return { mostrar, limpiar };
})();
