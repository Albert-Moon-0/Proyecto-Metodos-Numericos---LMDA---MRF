// Interfaz de Runge-Kutta (órdenes 2 a 6) y Runge-Kutta-Fehlberg.
//
// Todo el cálculo vive en el backend (metodos/runge_kutta.py). Aquí solo se
// leen los campos, se llama a la API y se dibuja:
//   - el panel "Fórmulas": las K del método elegido (aparecen al elegir el
//     método, antes de calcular) y, tras calcular, los valores del primer paso;
//   - la tabla de iteraciones, con o sin columnas K;
//   - en Fehlberg: wᵢ, w̃ᵢ, R, q, la barra de q (q < 1 / q ≥ 1) y las etiquetas
//     de paso aceptado / rechazado.
// Orden de scripts: api.js -> tablas-y-recursos.js -> este archivo.

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado, formatearNumero } = TablasYRecursos;

    const estado = { familia: 'rk', orden: 'rk4', henk: 'si', criterio: 'R', vistak: 'si' };
    let ultimoResultado = null;
    let formulas = null;

    const $ = (id) => document.getElementById(id);
    const botonCalcular = $('calcular-rk');
    const contenedorK = $('k-contenido');
    const tabla = $('rk-table');
    const resumen = $('rkf-resumen');

    const valorDe = (id) => $(id)?.value ?? '';
    const claveMetodo = () => (estado.familia === 'rkf' ? 'rkf45' : estado.orden);

    // ---------------------------------------------------------------
    // Utilidades de DOM y de formato
    // ---------------------------------------------------------------
    function el(etiqueta, clase, ...hijos) {
        const nodo = document.createElement(etiqueta);
        if (clase) {
            nodo.className = clase;
        }
        nodo.append(...hijos.flat(Infinity));
        return nodo;
    }

    const SUBS = '₀₁₂₃₄₅₆₇₈₉';
    const sub = (n) => String(n).replace(/\d/g, (d) => SUBS[d]);

    // "1/2·K₁" -> fracción apilada; el resto del texto queda igual.
    function conFracciones(texto) {
        const partes = [];
        let ultimo = 0;
        texto.replace(/(\d+)\/(\d+)/g, (coincide, num, den, posicion) => {
            partes.push(texto.slice(ultimo, posicion));
            partes.push(el('span', 'rk-frac', el('span', '', num), el('span', '', den)));
            ultimo = posicion + coincide.length;
            return coincide;
        });
        partes.push(texto.slice(ultimo));
        return partes;
    }

    // Número con signo "−" real y 6 decimales (como el resto de la app).
    const num = (x) => {
        const texto = formatearNumero(x);
        return texto.startsWith('-') ? `−${texto.slice(1)}` : texto;
    };
    const exp = (x) => (x === null || x === undefined ? '—' : x.toExponential(3).replace('e+', 'e').replace(/-/g, '−'));

    // ---------------------------------------------------------------
    // Panel de fórmulas
    // ---------------------------------------------------------------
    function lineaFormula(nombre, formula, claseExtra = '') {
        return el('div', `k-linea ${claseExtra}`.trim(),
            el('span', 'k-linea__nombre', nombre),
            el('span', 'k-linea__formula', conFracciones(formula)));
    }

    function bloqueFormulas(datos) {
        const bloques = [];
        const esRkf = datos.tipo === 'rkf';

        bloques.push(el('div', 'k-bloque',
            el('p', 'formula-etiqueta', esRkf ? 'Las seis K (incluyen h)' : 'Las K de este método'),
            ...datos.definiciones.map((d) => lineaFormula(`K${sub(d.nombre.slice(1))}`, d.formula))));

        if (esRkf) {
            bloques.push(el('div', 'k-bloque',
                el('p', 'formula-etiqueta', 'Aproximaciones'),
                lineaFormula('wᵢ₊₁', datos.formulaW.split(' = ')[1], 'k-linea--w'),
                lineaFormula('w̃ᵢ₊₁', datos.formulaWTilde.split(' = ')[1], 'k-linea--w'),
                el('p', 'k-nota', 'wᵢ₊₁ es de orden 4 y w̃ᵢ₊₁ de orden 5; usan las mismas K.')));

            bloques.push(el('div', 'k-bloque',
                el('p', 'formula-etiqueta', 'Control del paso'),
                lineaFormula('R', '|w̃ᵢ₊₁ − wᵢ₊₁| / h'),
                lineaFormula('q', '(TOL / 2R)^(1/4)'),
                el('ul', 'k-reglas',
                    el('li', '', el('b', 'k-q-no', 'q < 1'), ' → el paso se reduce: h ← q·h'),
                    el('li', '', el('b', 'k-q-si', 'q ≥ 1'), ' → el paso se conserva o crece: h ← q·h'),
                    el('li', '', 'q se limita entre 0.1 y 4, y h entre hₘᵢₙ y hₘₐₓ.'))));
        } else {
            bloques.push(el('div', 'k-bloque',
                el('p', 'formula-etiqueta', 'Aproximación'),
                lineaFormula('wᵢ₊₁', datos.formulaW.split(' = ')[1], 'k-linea--w')));
        }
        return bloques;
    }

    // Primer paso con números (solo Runge-Kutta, que sí guarda t y y de cada K)
    function bloquePrimerPaso(resultado) {
        if (!resultado || !resultado.paso1) {
            return null;
        }
        const conArgumentos = resultado.tipo === 'rk';
        const encabezado = el('tr', '',
            el('th', '', 'K'),
            conArgumentos ? [el('th', '', 't'), el('th', '', 'y')] : '',
            el('th', '', 'Valor'));

        const filas = resultado.paso1.map((k) => el('tr', '',
            el('td', '', `K${sub(k.nombre.slice(1))}`),
            conArgumentos ? [el('td', '', num(k.t)), el('td', '', num(k.y))] : '',
            el('td', 'is-valor', num(k.valor))));

        return el('div', 'k-bloque',
            el('p', 'formula-etiqueta', 'Primer paso (i = 0)'),
            el('div', 'table-wrap',
                el('table', 'k-tabla', el('thead', '', encabezado), el('tbody', '', ...filas))));
    }

    function pintarFormulas() {
        if (!formulas) {
            contenedorK.replaceChildren(el('p', 'k-nota', 'Cargando fórmulas…'));
            return;
        }
        const hijos = bloqueFormulas(formulas);
        const paso = ultimoResultado && ultimoResultado.metodo === formulas.metodo
            ? bloquePrimerPaso(ultimoResultado) : null;
        if (paso) {
            hijos.push(paso);
        }
        contenedorK.replaceChildren(...hijos);
    }

    async function cargarFormulas() {
        formulas = null;
        pintarFormulas();
        try {
            formulas = await llamarApi('/api/runge_kutta/formulas', {
                metodo: claveMetodo(),
                hEnK: estado.henk === 'si',
            });
        } catch (error) {
            contenedorK.replaceChildren(el('p', 'k-nota', `No se pudieron cargar las fórmulas: ${error.message}`));
            return;
        }
        pintarFormulas();
    }

    // ---------------------------------------------------------------
    // Tabla de Runge-Kutta (paso fijo)
    // ---------------------------------------------------------------
    function pintarTablaRk(resultado) {
        const nK = resultado.definiciones.length;
        const conK = estado.vistak === 'si';

        const columnasK = conK ? Array.from({ length: nK }, (_, j) => el('th', 'is-k', `K${sub(j + 1)}`)) : [];
        tabla.tHead.replaceChildren(el('tr', '',
            el('th', '', 'i'), el('th', '', 'tᵢ'), columnasK, el('th', '', 'wᵢ ≈ y(tᵢ)')));

        const filas = resultado.iteraciones.map((fila, indice) => {
            const celdasK = conK
                ? Array.from({ length: nK }, (_, j) => el('td', 'is-k', fila.k ? num(fila.k[j]) : '—'))
                : [];
            const tr = el('tr', indice === resultado.iteraciones.length - 1 ? 'is-final' : '',
                el('td', '', String(fila.iteracion)), el('td', '', num(fila.t)), celdasK, el('td', 'is-w', num(fila.w)));
            return tr;
        });
        tabla.tBodies[0].replaceChildren(...filas);
        resumen.hidden = true;
        resumen.replaceChildren();
    }

    // ---------------------------------------------------------------
    // Tabla de Fehlberg (paso variable)
    // ---------------------------------------------------------------
    const Q_MIN = 0.1;
    const Q_MAX = 4;

    // Barra de q en escala logarítmica entre 0.1 y 4, con marca en q = 1.
    function barraQ(q, qUsado) {
        const posicion = (v) => (Math.log10(v) - Math.log10(Q_MIN)) / (Math.log10(Q_MAX) - Math.log10(Q_MIN));
        const valor = q === null ? Q_MAX : q;
        const recortado = Math.min(Math.max(valor, Q_MIN), Q_MAX);
        const menor = valor < 1;

        const relleno = el('span', `qbar__fill ${menor ? 'is-menor' : 'is-mayor'}`);
        relleno.style.width = `${(posicion(recortado) * 100).toFixed(1)}%`;
        const marca = el('span', 'qbar__uno');
        marca.style.left = `${(posicion(1) * 100).toFixed(1)}%`;

        const texto = q === null ? '∞' : q.toFixed(4);
        return el('div', 'qcelda',
            el('span', 'qbar', relleno, marca),
            el('span', `qcelda__texto ${menor ? 'is-menor' : 'is-mayor'}`,
                `${texto} `, el('em', '', menor ? '< 1' : '≥ 1')));
    }

    function pintarTablaRkf(resultado) {
        const conK = estado.vistak === 'si';
        const columnasK = conK ? Array.from({ length: 6 }, (_, j) => el('th', 'is-k', `K${sub(j + 1)}`)) : [];

        tabla.tHead.replaceChildren(el('tr', '',
            el('th', '', 'Intento'), el('th', '', 'tᵢ'), el('th', '', 'h'), columnasK,
            el('th', '', 'wᵢ₊₁'), el('th', '', 'w̃ᵢ₊₁'), el('th', '', 'R'), el('th', '', 'q'),
            el('th', '', 'Estado'), el('th', '', 'h siguiente')));

        const nodos = resultado.iteraciones.map((fila, indice) => {
            if (indice === 0) {
                return el('tr', 'is-inicial',
                    el('td', '', '0'), el('td', '', num(fila.t)), el('td', '', '—'),
                    conK ? Array.from({ length: 6 }, () => el('td', 'is-k', '—')) : [],
                    el('td', 'is-w', num(fila.w)), el('td', '', '—'), el('td', '', '—'), el('td', '', '—'),
                    el('td', '', 'Condición inicial'), el('td', '', '—'));
            }
            const aceptado = fila.aceptado;
            const flecha = fila.q !== null && fila.q < 1 ? '↓' : '↑';
            return el('tr', aceptado ? 'is-aceptado' : 'is-rechazado',
                el('td', '', String(fila.intento)),
                el('td', '', num(fila.tIntento)),
                el('td', '', num(fila.h)),
                conK ? fila.k.map((k) => el('td', 'is-k', num(k))) : [],
                el('td', 'is-w', num(fila.w)),
                el('td', 'is-w', num(fila.wTilde)),
                el('td', '', exp(fila.R)),
                el('td', 'is-q', barraQ(fila.q, fila.qUsado)),
                el('td', '', el('span', `estado ${aceptado ? 'estado--ok' : 'estado--no'}`,
                    aceptado ? '✓ Aceptado' : '✗ Rechazado')),
                el('td', '', `${flecha} ${num(fila.hSiguiente)}`));
        });
        // Última fila aceptada: resaltar como resultado final
        for (let i = nodos.length - 1; i > 0; i -= 1) {
            if (resultado.iteraciones[i].aceptado) {
                nodos[i].classList.add('is-final');
                break;
            }
        }
        tabla.tBodies[0].replaceChildren(...nodos);

        // Tira de intentos: un cuadro por intento, verde = aceptado, rojo = rechazado
        const chips = resultado.iteraciones.slice(1).map((fila) => {
            const chip = el('span', `chip ${fila.aceptado ? 'chip--ok' : 'chip--no'}`, String(fila.intento));
            chip.title = `Intento ${fila.intento}: h = ${num(fila.h)}, R = ${exp(fila.R)}, `
                + `q = ${fila.q === null ? '∞' : fila.q.toFixed(3)} → ${fila.aceptado ? 'aceptado' : 'rechazado'}`;
            return chip;
        });
        resumen.replaceChildren(
            el('p', 'rkf-resumen__texto',
                el('b', 'k-q-si', `${resultado.aceptados} aceptados`), ' · ',
                el('b', 'k-q-no', `${resultado.rechazados} rechazados`), ' · ',
                `${resultado.iteraciones.length - 1} intentos`),
            el('div', 'rkf-resumen__chips', ...chips));
        resumen.hidden = false;
    }

    function pintarTabla() {
        if (!ultimoResultado) {
            tabla.tHead.replaceChildren();
            tabla.tBodies[0].replaceChildren();
            resumen.hidden = true;
            return;
        }
        tabla.classList.toggle('rk-table--rkf', ultimoResultado.tipo === 'rkf');
        (ultimoResultado.tipo === 'rkf' ? pintarTablaRkf : pintarTablaRk)(ultimoResultado);
    }

    // ---------------------------------------------------------------
    // Selectores
    // ---------------------------------------------------------------
    function marcar(grupo) {
        document.querySelectorAll(`.segmented__btn[data-grupo="${grupo}"]`).forEach((boton) => {
            const activo = boton.dataset.valor === estado[grupo];
            boton.classList.toggle('is-active', activo);
            boton.setAttribute('aria-pressed', String(activo));
        });
    }

    function actualizarCampos() {
        const esRkf = estado.familia === 'rkf';
        $('campo-orden').hidden = esRkf;
        $('campo-henk').hidden = esRkf;       // Fehlberg usa siempre K con h
        $('campo-n').hidden = esRkf;
        $('campos-rkf').hidden = !esRkf;
    }

    document.querySelectorAll('.segmented__btn').forEach((boton) => {
        boton.addEventListener('click', () => {
            const { grupo, valor } = boton.dataset;
            estado[grupo] = valor;
            marcar(grupo);

            if (grupo === 'vistak') {
                pintarTabla();
                return;
            }
            if (grupo === 'criterio') {
                return;
            }
            if (grupo === 'familia') {
                // Fehlberg tiene muchas columnas: arranca sin K (se pueden activar)
                estado.vistak = valor === 'rkf' ? 'no' : 'si';
                marcar('vistak');
            }
            // Cambió el método: se limpia el resultado y se muestran sus K
            ultimoResultado = null;
            mostrarResultado('');
            pintarTabla();
            actualizarCampos();
            cargarFormulas();
        });
    });

    // ---------------------------------------------------------------
    // Calcular
    // ---------------------------------------------------------------
    function leerDatos() {
        const datos = {
            funcion: valorDe('function-input'),
            metodo: claveMetodo(),
            t0: valorDe('point-t0'),
            tn: valorDe('point-tn'),
            w0: valorDe('w0'),
        };
        if (estado.familia === 'rkf') {
            datos.tol = valorDe('tol');
            datos.hmax = valorDe('hmax');
            datos.hmin = valorDe('hmin');
            datos.criterio = estado.criterio;
        } else {
            datos.n = valorDe('no-subintervalos');
            datos.hEnK = estado.henk === 'si';
        }
        return datos;
    }

    botonCalcular.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/runge_kutta/calcular', leerDatos());
            ultimoResultado = resultado;
            pintarFormulas();
            pintarTabla();
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            ultimoResultado = null;
            pintarTabla();
            pintarFormulas();
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    actualizarCampos();
    cargarFormulas();
});