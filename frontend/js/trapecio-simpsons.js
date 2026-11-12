// Lógica de interfaz para Trapecio, Simpson 1/3 y Simpson 3/8 (simples y compuestos).
// El cálculo real se hace en el backend (Python, metodos/trapecio_simpsons.py);
// este archivo maneja los selectores, la lista dinámica de puntos x, lee los
// inputs, llama a la API y muestra el resultado. Una sola página y un solo
// endpoint cubren las 6 combinaciones (tipo × regla).
// Las utilidades compartidas viven en tablas-y-recursos.js — cárgalo antes.

document.addEventListener('DOMContentLoaded', function () {
    const { mostrarResultado } = TablasYRecursos;

    // Mismo tope que LIMITE_SUBINTERVALOS en trapecio_simpsons.py.
    const MAX_SUBINTERVALOS = 200;

    const estado = { tipo: 'simple', regla: 'trapecio' };

    const PISTAS = {
        simple: {
            trapecio: 'Trapecio simple:  I ≈ (b − a)/2 · [ f(a) + f(b) ]',
            simpson13: 'Simpson 1/3 simple:  I ≈ h/3 · [ f(a) + 4f(a+h) + f(b) ],  con h = (b − a)/2',
            simpson38: 'Simpson 3/8 simple:  I ≈ 3h/8 · [ f(a) + 3f(a+h) + 3f(a+2h) + f(b) ],  con h = (b − a)/3',
        },
        compuesto: {
            trapecio: 'Trapecio compuesto: suma la regla del trapecio en cada subintervalo [xᵢ, xᵢ₊₁]. '
                + 'Acepta cualquier cantidad de puntos, incluso espaciados de forma irregular.',
            simpson13: 'Simpson 1/3 compuesto: aplica Simpson 1/3 cada 2 subintervalos. '
                + 'Necesita n par (cantidad impar de puntos) y puntos equiespaciados.',
            simpson38: 'Simpson 3/8 compuesto: aplica Simpson 3/8 cada 3 subintervalos. '
                + 'Necesita n múltiplo de 3 y puntos equiespaciados.',
        },
    };

    const botonesSeleccion = Array.from(document.querySelectorAll('.segmented__btn'));
    const panelSimple = document.getElementById('inputs-simple');
    const panelCompuesto = document.getElementById('inputs-compuesto');
    const pista = document.getElementById('formula-hint');
    const botonCalcular = document.getElementById('calcular-integral');
    const botonGenerar = document.getElementById('generar-puntos');

    function valorDe(id) {
        return document.getElementById(id)?.value ?? '';
    }

    // ---------------------------------------------------------------
    // Lista dinámica de campos numéricos (agregar, quitar, renumerar).
    // Está escrita sin depender de esta página para poder moverla a
    // tablas-y-recursos.js cuando otro módulo (interpolación, splines)
    // también necesite una lista de puntos.
    // ---------------------------------------------------------------
    const SUBINDICES = '₀₁₂₃₄₅₆₇₈₉';
    const subindice = (n) => String(n).replace(/\d/g, (d) => SUBINDICES[d]);

    function crearListaDinamica({ contenedor, botonAgregar, prefijo, minimo, maximo, inicial }) {
        function filas() {
            return Array.from(contenedor.querySelectorAll('.point-item'));
        }

        function renumerar() {
            const total = filas().length;

            filas().forEach((fila, i) => {
                const campo = fila.querySelector('input');
                const quitar = fila.querySelector('.point-item__remove');

                campo.placeholder = `${prefijo}${subindice(i)}`;
                campo.setAttribute('aria-label', `Valor ${prefijo}${i}`);
                quitar.setAttribute('aria-label', `Quitar ${prefijo}${i}`);
                quitar.disabled = total <= minimo;
            });

            botonAgregar.disabled = total >= maximo;
        }

        function agregar(valor = '') {
            if (filas().length >= maximo) {
                return null;
            }

            const fila = document.createElement('div');
            fila.className = 'point-item';

            const campo = document.createElement('input');
            campo.type = 'text';
            campo.inputMode = 'decimal';
            campo.autocomplete = 'off';
            campo.value = valor;

            const quitar = document.createElement('button');
            quitar.type = 'button';
            quitar.className = 'point-item__remove';
            quitar.textContent = '×';
            quitar.addEventListener('click', () => {
                if (filas().length > minimo) {
                    fila.remove();
                    renumerar();
                }
            });

            fila.append(campo, quitar);
            contenedor.appendChild(fila);
            renumerar();
            return campo;
        }

        function establecerValores(valores) {
            contenedor.innerHTML = '';
            valores.forEach((valor) => agregar(valor));
            while (filas().length < minimo) {
                agregar();
            }
            renumerar();
        }

        function obtenerValores() {
            return filas().map((fila) => fila.querySelector('input').value);
        }

        botonAgregar.addEventListener('click', () => agregar()?.focus());

        establecerValores(Array(inicial).fill(''));

        return { agregar, establecerValores, obtenerValores };
    }

    const lista = crearListaDinamica({
        contenedor: document.getElementById('lista-x'),
        botonAgregar: document.getElementById('agregar-punto'),
        prefijo: 'x',
        minimo: 2,
        maximo: MAX_SUBINTERVALOS + 1,
        inicial: 3,
    });

    // ---------------------------------------------------------------
    // Selectores (tipo y regla)
    // ---------------------------------------------------------------
    function actualizarVista() {
        panelSimple.hidden = estado.tipo !== 'simple';
        panelCompuesto.hidden = estado.tipo !== 'compuesto';
        pista.textContent = PISTAS[estado.tipo][estado.regla];
        mostrarResultado('');
    }

    function seleccionar(grupo, valor) {
        estado[grupo] = valor;

        botonesSeleccion
            .filter((boton) => boton.dataset.grupo === grupo)
            .forEach((boton) => {
                const activo = boton.dataset.valor === valor;
                boton.classList.toggle('is-active', activo);
                boton.setAttribute('aria-pressed', String(activo));
            });

        actualizarVista();
    }

    botonesSeleccion.forEach((boton) => {
        boton.addEventListener('click', () => seleccionar(boton.dataset.grupo, boton.dataset.valor));
    });

    // ---------------------------------------------------------------
    // Generar puntos equiespaciados a partir de x₀, xₙ y n
    // ---------------------------------------------------------------
    function leerNumeroCampo(id, nombre) {
        const texto = valorDe(id).trim();
        const numero = Number(texto);

        if (texto === '' || !Number.isFinite(numero)) {
            throw new Error(`El campo "${nombre}" debe ser un número válido.`);
        }
        return numero;
    }

    // Quita el ruido de punto flotante: 0.30000000000000004 -> "0.3".
    const formatear = (numero) => String(Number(numero.toPrecision(12)));

    botonGenerar.addEventListener('click', function () {
        try {
            const a = leerNumeroCampo('gen-x0', 'Punto inicial x₀');
            const b = leerNumeroCampo('gen-xn', 'Punto final xₙ');
            const n = leerNumeroCampo('gen-n', 'Número de subintervalos n');

            if (!Number.isInteger(n) || n < 1) {
                throw new Error('El número de subintervalos n debe ser un entero positivo.');
            }
            if (n > MAX_SUBINTERVALOS) {
                throw new Error(`El número de subintervalos no puede pasar de ${MAX_SUBINTERVALOS}.`);
            }
            if (a >= b) {
                throw new Error('El punto inicial x₀ debe ser menor que el punto final xₙ.');
            }

            const paso = (b - a) / n;
            const valores = Array.from({ length: n + 1 }, (_, i) => formatear(i === n ? b : a + i * paso));

            lista.establecerValores(valores);
            mostrarResultado('');
        } catch (error) {
            mostrarResultado(error.message, true);
        }
    });

    // ---------------------------------------------------------------
    // Calcular
    // ---------------------------------------------------------------
    function leerDatos() {
        const datos = {
            funcion: valorDe('function-input'),
            tipo: estado.tipo,
            regla: estado.regla,
        };

        if (estado.tipo === 'simple') {
            datos.x0 = valorDe('point-x0');
            datos.xn = valorDe('point-xn');
        } else {
            datos.xs = lista.obtenerValores();
        }

        return datos;
    }

    botonCalcular?.addEventListener('click', async function () {
        botonCalcular.disabled = true;
        try {
            const resultado = await llamarApi('/api/trapecio_simpsons/calcular', leerDatos());
            mostrarResultado(resultado.mensaje);
        } catch (error) {
            mostrarResultado(error.message, true);
        } finally {
            botonCalcular.disabled = false;
        }
    });

    actualizarVista();
});