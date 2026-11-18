// Interfaz de la cuadratura adaptativa.
// TODO el cálculo (y el árbol completo) viene del backend
// (metodos/cuadratura_adaptativa.py). Aquí solo se leen los inputs, se llama a
// la API y se dibuja el árbol con Cytoscape.js.
//
// Cada nodo del árbol se dibuja como una tabla de 2 filas × 2 columnas:
//
//     ┌─────┬──────────────────────┐
//     │  E  │ S(a, c)              │   (1,1) símbolo E     (1,2) fórmula con los puntos
//     │     │ + S(c, b)            │
//     ├─────┼──────────────────────┤
//     │ 0.01│ Error aprox = 0.0012 │   (2,1) valor de E    (2,2) error aprox y criterio 15E
//     │     │ < 15E = 0.15  ✓      │
//     └─────┴──────────────────────┘
//
// La tabla se genera como imagen SVG (data URI) usada de fondo del nodo, así
// sale idéntica en pantalla y en el PNG exportado.
// Orden de scripts: api.js -> tablas-y-recursos.js -> vendor/cytoscape.min.js -> este archivo.

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado } = TablasYRecursos;

    // ---------------------------------------------------------------
    // Medidas y colores (iguales a las variables de styles.css)
    // ---------------------------------------------------------------
    const NODO_ANCHO = 300;
    const NODO_ALTO = 100;
    const COLUMNA_1 = 86;           // ancho de la columna izquierda (E y su valor)
    const SEPARACION_X = 40;        // espacio horizontal entre nodos
    const SEPARACION_Y = 70;        // espacio vertical entre niveles

    const COLOR = {
        fondo: '#0a0d12',
        nodo: '#121722',
        texto: '#e6e9ef',
        tenue: '#8b96a8',
        rejilla: 'rgba(148,163,184,0.35)',
        aceptado: '#4fd1c5',        // --accent
        dividido: '#e6c07b',
        limite: '#f2a4a0',          // --error
        arista: '#566074',
    };

    const ESTADOS = {
        aceptado: { color: COLOR.aceptado, simbolo: '✓', texto: '' },
        dividido: { color: COLOR.dividido, simbolo: '✗', texto: ' dividir' },
        limite: { color: COLOR.limite, simbolo: '✗', texto: ' nivel máx.' },
    };

    const MONO = 'ui-monospace, Menlo, Consolas, DejaVu Sans Mono, monospace';

    // ---------------------------------------------------------------
    // Formato de números
    // ---------------------------------------------------------------
    function formatear(numero, cifras = 6) {
        if (numero === 0) {
            return '0';
        }
        const absoluto = Math.abs(numero);
        if (absoluto < 1e-5 || absoluto >= 1e7) {
            return Number(numero.toExponential(cifras - 1)).toExponential().replace('e+', 'e');
        }
        return String(Number(numero.toPrecision(cifras)));
    }

    function escapar(texto) {
        return String(texto).replace(/[&<>"']/g, (c) => (
            { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
        ));
    }

    // ---------------------------------------------------------------
    // Imagen SVG de un nodo (tabla 2×2)
    // ---------------------------------------------------------------
    function svgNodo(nodo) {
        const estado = ESTADOS[nodo.estado] || ESTADOS.dividido;
        const mitad = NODO_ALTO / 2;
        const centroC1 = COLUMNA_1 / 2;
        const xC2 = COLUMNA_1 + 14;

        const texto = (x, y, contenido, { tam = 12, color = COLOR.texto, ancla = 'start', familia = MONO, estilo = 'normal' } = {}) =>
            `<text x="${x}" y="${y}" font-size="${tam}" fill="${color}" text-anchor="${ancla}" ` +
            `font-family="${familia}" font-style="${estilo}">${escapar(contenido)}</text>`;

        const puntoA = formatear(nodo.a);
        const puntoC = formatear(nodo.c);
        const puntoB = formatear(nodo.b);
        const comparacion = nodo.cumple ? '<' : '≥';

        return (
            `<svg xmlns="http://www.w3.org/2000/svg" width="${NODO_ANCHO}" height="${NODO_ALTO}" viewBox="0 0 ${NODO_ANCHO} ${NODO_ALTO}">` +
            `<rect x="1" y="1" width="${NODO_ANCHO - 2}" height="${NODO_ALTO - 2}" rx="10" fill="${COLOR.nodo}" stroke="${estado.color}" stroke-width="2"/>` +
            `<line x1="${COLUMNA_1}" y1="1" x2="${COLUMNA_1}" y2="${NODO_ALTO - 1}" stroke="${COLOR.rejilla}"/>` +
            `<line x1="1" y1="${mitad}" x2="${NODO_ANCHO - 1}" y2="${mitad}" stroke="${COLOR.rejilla}"/>` +
            // (1,1) símbolo E
            texto(centroC1, mitad / 2 + 8, 'E', { tam: 24, ancla: 'middle', familia: 'Georgia, Times New Roman, serif', estilo: 'italic' }) +
            // (1,2) fórmula S(a, c) + S(c, b) con los puntos reales
            texto(xC2, mitad / 2 - 3, `S(${puntoA}, ${puntoC})`, { tam: 12 }) +
            texto(xC2, mitad / 2 + 14, `+ S(${puntoC}, ${puntoB})`, { tam: 12 }) +
            // (2,1) valor de E de este intervalo
            texto(centroC1, mitad + mitad / 2 + 4, formatear(nodo.E, 5), { tam: 12, ancla: 'middle' }) +
            // (2,2) error aproximado y criterio contra 15E
            texto(xC2, mitad + mitad / 2 - 3, `Error aprox = ${formatear(nodo.errorAprox, 5)}`, { tam: 12, color: COLOR.tenue }) +
            texto(xC2, mitad + mitad / 2 + 14, `${comparacion} 15E = ${formatear(nodo.umbral, 5)} ${estado.simbolo}${estado.texto}`, { tam: 12, color: estado.color }) +
            '</svg>'
        );
    }

    const aDataUri = (svg) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);

    // ---------------------------------------------------------------
    // Posiciones: hojas en fila, cada padre centrado sobre sus hijos
    // ---------------------------------------------------------------
    function calcularPosiciones(nodos) {
        const porId = new Map(nodos.map((nodo) => [nodo.id, nodo]));
        const columna = new Map();
        let siguienteHoja = 0;

        function colocar(nodo) {
            if (!nodo.hijos.length) {
                columna.set(nodo.id, siguienteHoja++);
                return;
            }
            nodo.hijos.forEach((idHijo) => colocar(porId.get(idHijo)));
            const [izquierdo, derecho] = nodo.hijos.map((idHijo) => columna.get(idHijo));
            columna.set(nodo.id, (izquierdo + derecho) / 2);
        }

        colocar(nodos[0]);

        const posiciones = new Map();
        nodos.forEach((nodo) => {
            posiciones.set(nodo.id, {
                x: columna.get(nodo.id) * (NODO_ANCHO + SEPARACION_X),
                y: nodo.nivel * (NODO_ALTO + SEPARACION_Y),
            });
        });
        return posiciones;
    }

    function construirElementos(nodos) {
        const posiciones = calcularPosiciones(nodos);
        const elementos = [];

        nodos.forEach((nodo) => {
            elementos.push({
                group: 'nodes',
                data: { id: nodo.id, imagen: aDataUri(svgNodo(nodo)) },
                position: posiciones.get(nodo.id),
            });
        });

        const porId = new Map(nodos.map((nodo) => [nodo.id, nodo]));
        nodos.forEach((nodo) => {
            nodo.hijos.forEach((idHijo) => {
                const hijo = porId.get(idHijo);
                elementos.push({
                    group: 'edges',
                    data: {
                        id: `${nodo.id}-${idHijo}`,
                        source: nodo.id,
                        target: idHijo,
                        etiqueta: `[${formatear(hijo.a)}, ${formatear(hijo.b)}]`,
                    },
                });
            });
        });

        return elementos;
    }

    // ---------------------------------------------------------------
    // Cytoscape
    // ---------------------------------------------------------------
    const contenedor = document.getElementById('arbol-cy');
    const mensajeVacio = document.getElementById('arbol-vacio');
    const botonCalcular = document.getElementById('calcular-adaptativa');
    const botonAjustar = document.getElementById('ajustar-arbol');
    const botonDescargar = document.getElementById('descargar-arbol');

    const cy = cytoscape({
        container: contenedor,
        elements: [],
        wheelSensitivity: 0.25,
        minZoom: 0.03,
        maxZoom: 3,
        boxSelectionEnabled: false,
        autoungrabify: true, // los nodos no se arrastran; solo se mueve la vista
        style: [
            {
                selector: 'node',
                style: {
                    shape: 'round-rectangle',
                    width: NODO_ANCHO,
                    height: NODO_ALTO,
                    'background-opacity': 0,
                    'background-image': 'data(imagen)',
                    'background-fit': 'cover',
                    'background-clip': 'node',
                    'border-width': 0,
                },
            },
            {
                selector: 'edge',
                style: {
                    'curve-style': 'taxi',
                    'taxi-direction': 'downward',
                    'taxi-turn': '50%',
                    width: 1.5,
                    'line-color': COLOR.arista,
                    label: 'data(etiqueta)',
                    'font-family': MONO,
                    'font-size': 12,
                    color: COLOR.tenue,
                    'text-background-color': COLOR.fondo,
                    'text-background-opacity': 1,
                    'text-background-padding': 3,
                },
            },
        ],
    });

    function ajustarVista() {
        cy.resize();
        cy.fit(undefined, 30);
    }

    function dibujarArbol(nodos) {
        cy.elements().remove();
        cy.add(construirElementos(nodos));
        mensajeVacio.hidden = true;
        botonAjustar.disabled = false;
        botonDescargar.disabled = false;
        ajustarVista();
    }

    function limpiarArbol() {
        cy.elements().remove();
        mensajeVacio.hidden = false;
        botonAjustar.disabled = true;
        botonDescargar.disabled = true;
    }

    // ---------------------------------------------------------------
    // Descargar PNG (el árbol completo, no solo la parte visible)
    // ---------------------------------------------------------------
    const DIMENSION_MAXIMA_PNG = 12000; // los navegadores fallan con lienzos más grandes

    botonDescargar.addEventListener('click', function () {
        const caja = cy.elements().boundingBox();
        const mayor = Math.max(caja.w, caja.h, 1);
        const escala = Math.min(2, DIMENSION_MAXIMA_PNG / mayor);

        const imagen = cy.png({ full: true, scale: escala, bg: COLOR.fondo, output: 'base64uri' });

        const enlace = document.createElement('a');
        enlace.href = imagen;
        enlace.download = 'cuadratura-adaptativa.png';
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();
    });

    botonAjustar.addEventListener('click', ajustarVista);
    window.addEventListener('resize', () => {
        if (!botonAjustar.disabled) {
            ajustarVista();
        }
    });

    // ---------------------------------------------------------------
    // Calcular
    // ---------------------------------------------------------------
    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    function leerDatos() {
        return {
            funcion: valorDe('function-input'),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
            tolerancia: valorDe('tolerance'),
            nivelMaximo: valorDe('max-level'),
        };
    }

    botonCalcular.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/cuadratura_adaptativa/calcular', leerDatos());
            dibujarArbol(resultado.nodos);
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            limpiarArbol();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });
});