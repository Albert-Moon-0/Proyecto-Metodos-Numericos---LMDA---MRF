// Interfaz de la cuadratura gaussiana (Gauss-Legendre), simple y compuesta.
//
// Los nodos tᵢ y pesos cᵢ de cada grado viven en el backend
// (metodos/cuadratura_gaussiana.py, tabla CONSTANTES) y se piden una sola vez
// a /constantes: así hay una única fuente de verdad. Con ellos esta página
// dibuja la fórmula del grado elegido (antes de calcular) y, al calcular,
// muestra solo el resultado.
//
// La fórmula se arma con elementos HTML (<var>, <sub>, fracciones, ∫ y Σ con
// límites; estilos en styles-gauss-agregar.css) para que los símbolos y
// subíndices se lean bien. No hace falta ninguna librería.
// Orden de scripts: api.js -> tablas-y-recursos.js -> este archivo.

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado } = TablasYRecursos;

    const estado = { tipo: 'simple', grado: 3 };
    let constantes = null; // { "2": { nodos, pesos, exactoHasta }, ... }

    const botonesTipo = Array.from(document.querySelectorAll('.segmented__btn[data-grupo="tipo"]'));
    const selectorGrado = document.getElementById('selector-grado');
    const campoSubintervalos = document.getElementById('campo-subintervalos');
    const botonCalcular = document.getElementById('calcular-gauss');
    const contenedorFormula = document.getElementById('formula-contenido');
    const tituloFormula = document.getElementById('formula-title');
    const notaExactitud = document.getElementById('formula-exactitud');
    const resultadoEl = document.getElementById('result');

    const valorDe = (id) => document.getElementById(id)?.value ?? '';

    // ---------------------------------------------------------------
    // Constructores de HTML para la notación matemática
    // ---------------------------------------------------------------
    function el(etiqueta, clase, ...hijos) {
        const nodo = document.createElement(etiqueta);
        if (clase) {
            nodo.className = clase;
        }
        nodo.append(...hijos.flat(Infinity));
        return nodo;
    }

    const v = (texto) => el('var', '', texto);                                  // variable en cursiva
    const sub = (...contenido) => el('sub', '', ...contenido);                  // subíndice
    const indice = (letra, ...contenido) => [v(letra), sub(...contenido)];      // cᵢ, tᵢ, xᵢ...
    const fraccion = (arriba, abajo) => el('span', 'mf-frac', el('span', '', arriba), el('span', '', abajo));
    const bMenosA = () => [v('b'), ' − ', v('a')];

    // ∫ con límites a (abajo) y b (arriba)
    const integral = () => el('span', 'mf-int',
        el('span', 'mf-int__signo', '∫'),
        el('span', 'mf-int__arriba', v('b')),
        el('span', 'mf-int__abajo', v('a')));

    // Σ con límites k = 1 (abajo) y m (arriba)
    const sumatoria = () => el('span', 'mf-sum',
        el('span', 'mf-sum__arriba', v('m')),
        el('span', 'mf-sum__signo', 'Σ'),
        el('span', 'mf-sum__abajo', v('k'), ' = 1'));

    // f(xᵢ) en la simple, f(xₖ,ᵢ) en la compuesta
    function fDeX(i) {
        const subindice = estado.tipo === 'simple' ? [String(i)] : [v('k'), ',', String(i)];
        return [v('f'), '(', v('x'), sub(...subindice), ')'];
    }

    // Un término "+ c f(x)" que no se parte entre líneas
    function termino(coeficiente, i, esPrimero) {
        return el('span', 'mf-termino', esPrimero ? '' : '+ ', coeficiente, ' ', fDeX(i));
    }

    // 10 decimales y signo "−" real, para que las columnas alineen.
    function fijo(numero) {
        const texto = Math.abs(numero).toFixed(10);
        return numero < 0 ? `−${texto}` : texto;
    }

    // "∫ f(x) dx ≈ " (siempre igual)
    const cabeceraIntegral = () => [integral(), ' ', v('f'), '(', v('x'), ') d', v('x'), el('span', 'mf-op', '≈')];

    // Factor delante del corchete: (b − a)/2 en la simple; Σ (h/2) en la compuesta
    function factor() {
        return estado.tipo === 'simple'
            ? [fraccion(bMenosA(), '2'), el('span', 'mf-op', '·')]
            : [sumatoria(), fraccion(v('h'), '2'), el('span', 'mf-op', '·')];
    }

    // Lista de términos del corchete. `coeficiente(i)` devuelve cᵢ simbólico o su valor.
    // Con más de 5 puntos la versión simbólica se abrevia con "…".
    function terminos(n, coeficiente, abreviar) {
        const todos = Array.from({ length: n }, (_, i) => i + 1);
        const mostrados = abreviar && n > 5 ? [1, 2, null, n] : todos;

        return mostrados.map((i, posicion) => (
            i === null
                ? el('span', 'mf-termino', '+ … ')
                : termino(coeficiente(i), i, posicion === 0)
        ));
    }

    const corchete = (...contenido) => [el('span', 'mf-corchete', '['), ...contenido, el('span', 'mf-corchete', ']')];

    // ---------------------------------------------------------------
    // Bloques de la fórmula
    // ---------------------------------------------------------------
    function bloque(etiqueta, ...contenido) {
        return el('div', 'formula-bloque',
            etiqueta ? el('p', 'formula-etiqueta', etiqueta) : '',
            ...contenido);
    }

    function bloqueGeneral(n) {
        const simbolico = (i) => indice('c', String(i));
        return bloque('Fórmula',
            el('div', 'mf', cabeceraIntegral(), factor(), corchete(terminos(n, simbolico, true))));
    }

    function bloqueNodos() {
        // Definición de los puntos xᵢ a partir de los nodos tᵢ
        const lineas = estado.tipo === 'simple'
            ? [[indice('x', 'i'), ' = ', fraccion(bMenosA(), '2'), ' ', indice('t', 'i'), ' + ', fraccion([v('a'), ' + ', v('b')], '2')]]
            : [
                [v('h'), ' = ', fraccion(bMenosA(), v('m'))],
                [v('x'), sub(v('k'), ',', v('i')), ' = ', v('a'), ' + (', v('k'), ' − ½) ', v('h'), ' + ', fraccion(v('h'), '2'), ' ', indice('t', 'i')],
            ];
        return bloque('Donde', ...lineas.map((linea) => el('div', 'mf mf--medio', linea)));
    }

    function bloqueSustituido(n) {
        const datos = constantes[String(n)];
        const conValor = (i) => el('span', 'mf-num', fijo(datos.pesos[i - 1]));
        return bloque(`Con las constantes de n = ${n}`,
            el('div', 'mf', factor(), corchete(terminos(n, conValor, false))));
    }

    function bloqueTabla(n) {
        const datos = constantes[String(n)];

        const encabezado = el('tr', '',
            el('th', '', v('i')),
            el('th', '', indice('t', 'i'), el('span', 'tabla-constantes__rotulo', ' nodo')),
            el('th', '', indice('c', 'i'), el('span', 'tabla-constantes__rotulo', ' peso')));

        const filas = datos.nodos.map((t, i) => el('tr', '',
            el('td', '', String(i + 1)),
            el('td', '', fijo(t)),
            el('td', '', fijo(datos.pesos[i]))));

        return bloque('Nodos y pesos',
            el('table', 'tabla-constantes', el('thead', '', encabezado), el('tbody', '', ...filas)));
    }

    function pintarFormula() {
        if (!constantes) {
            return;
        }
        const n = estado.grado;

        tituloFormula.textContent = `Fórmula · grado n = ${n}`;
        notaExactitud.textContent = `Exacta para polinomios de grado ≤ ${constantes[String(n)].exactoHasta}`;

        contenedorFormula.replaceChildren(
            bloqueGeneral(n),
            bloqueNodos(),
            bloqueSustituido(n),
            bloqueTabla(n),
        );
    }

    // ---------------------------------------------------------------
    // Selectores
    // ---------------------------------------------------------------
    function marcarActivo(botones, valor) {
        botones.forEach((boton) => {
            const activo = boton.dataset.valor === String(valor);
            boton.classList.toggle('is-active', activo);
            boton.setAttribute('aria-pressed', String(activo));
        });
    }

    function actualizarVista() {
        campoSubintervalos.hidden = estado.tipo !== 'compuesto';
        mostrarResultado('');
        pintarFormula();
    }

    botonesTipo.forEach((boton) => {
        boton.addEventListener('click', () => {
            estado.tipo = boton.dataset.valor;
            marcarActivo(botonesTipo, estado.tipo);
            actualizarVista();
        });
    });

    function crearBotonesGrado() {
        selectorGrado.innerHTML = '';
        Object.keys(constantes)
            .map(Number)
            .sort((a, b) => a - b)
            .forEach((grado) => {
                const boton = document.createElement('button');
                boton.type = 'button';
                boton.className = 'segmented__btn';
                boton.dataset.grupo = 'grado';
                boton.dataset.valor = String(grado);
                boton.setAttribute('aria-pressed', 'false');
                boton.textContent = String(grado);
                boton.addEventListener('click', () => {
                    estado.grado = grado;
                    marcarActivo(Array.from(selectorGrado.children), grado);
                    actualizarVista();
                });
                selectorGrado.appendChild(boton);
            });
        marcarActivo(Array.from(selectorGrado.children), estado.grado);
    }

    // ---------------------------------------------------------------
    // Resultado: solo el valor, grande, y una línea tenue con el método usado
    // ---------------------------------------------------------------
    function formatoResultado(numero) {
        const absoluto = Math.abs(numero);
        if (absoluto !== 0 && (absoluto < 1e-4 || absoluto >= 1e9)) {
            return numero.toExponential(8).replace('e+', 'e').replace('-', '−');
        }
        return fijoLibre(numero, absoluto >= 1e6 ? 6 : 10);
    }

    function fijoLibre(numero, decimales) {
        const texto = Math.abs(numero).toFixed(decimales);
        return numero < 0 ? `−${texto}` : texto;
    }

    function mostrarResultadoGauss(resultado) {
        mostrarResultado(''); // limpia el texto y el mensaje de error

        const detalle = resultado.tipo === 'simple'
            ? `Gauss-Legendre simple · n = ${resultado.grado}`
            : `Gauss-Legendre compuesta · n = ${resultado.grado} · m = ${resultado.subintervalos}`;

        resultadoEl.replaceChildren(
            el('span', 'rg-etiqueta', integral(), ' ', v('f'), '(', v('x'), ') d', v('x'), ' ≈'),
            el('span', 'rg-valor', formatoResultado(resultado.aproximacion)),
            el('span', 'rg-detalle', detalle),
        );
    }

    // ---------------------------------------------------------------
    // Calcular
    // ---------------------------------------------------------------
    function leerDatos() {
        const datos = {
            funcion: valorDe('function-input'),
            tipo: estado.tipo,
            grado: String(estado.grado),
            a: valorDe('point-a'),
            b: valorDe('point-b'),
        };
        if (estado.tipo === 'compuesto') {
            datos.subintervalos = valorDe('subintervalos');
        }
        return datos;
    }

    botonCalcular.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/cuadratura_gaussiana/calcular', leerDatos());
            mostrarResultadoGauss(resultado);
        } catch (error) {
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    // ---------------------------------------------------------------
    // Inicio: cargar las constantes del backend
    // ---------------------------------------------------------------
    (async function iniciar() {
        try {
            const respuesta = await llamarApi('/api/cuadratura_gaussiana/constantes', {});
            constantes = respuesta.grados;
            if (!constantes[String(estado.grado)]) {
                estado.grado = Number(Object.keys(constantes)[0]);
            }
            crearBotonesGrado();
            actualizarVista();
        } catch (error) {
            mostrarResultado(`No se pudieron cargar las constantes del método: ${error.message}`, true);
        }
    })();
});