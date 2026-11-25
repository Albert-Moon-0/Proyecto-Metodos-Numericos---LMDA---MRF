// Controlador de gráficas "iteración por iteración": deslizador + botón Animar
// + leyenda. No sabe qué método es: cada método le da tres funciones.
//
//   const GraficaX = GraficaIterativa.crear({
//       total:   (resultado) => número de pasos que se pueden mostrar,
//       escena:  (k, resultado) => escena para GraficaSvg.dibujar (paso k, desde 0),
//       leyenda: (k, resultado) => [párrafos]  (usa GraficaComun.linea / chip),
//   });
//   GraficaX.mostrar(resultado);   GraficaX.limpiar();
//
// Ids que espera el HTML: graph-empty, graph-frame, graph-svg, graph-controls,
// graph-play, graph-iter, graph-iter-texto, graph-legend.
// El resultado debe traer `grafica` (ver comun/grafica.py).

const GraficaIterativa = (function () {
    const $ = (id) => document.getElementById(id);

    function crear({ total, escena, leyenda, etiqueta }) {
        let datos = null;
        let temporizador = null;

        const cuantos = () => (datos ? total(datos) : 0);

        function mostrarPaso(k) {
            GraficaSvg.dibujar($('graph-svg'), escena(k, datos));
            $('graph-legend').replaceChildren(...leyenda(k, datos));
            $('graph-iter-texto').textContent = etiqueta ? etiqueta(k, datos) : `Paso ${k + 1} de ${cuantos()}`;
            $('graph-iter').value = String(k + 1);
        }

        function detener() {
            if (temporizador) {
                clearInterval(temporizador);
                temporizador = null;
            }
            if ($('graph-play')) {
                $('graph-play').textContent = '▶ Animar';
            }
        }

        function animar() {
            if (temporizador) {
                detener();
                return;
            }
            let k = 0;
            mostrarPaso(0);
            $('graph-play').textContent = '❚❚ Pausa';
            temporizador = setInterval(() => {
                k += 1;
                if (k >= cuantos()) {
                    detener();
                    return;
                }
                mostrarPaso(k);
            }, 1000);
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
            datos = resultado && resultado.grafica ? resultado : null;
            if (!datos || cuantos() < 1) {
                limpiar();
                return;
            }
            $('graph-empty').hidden = true;
            $('graph-frame').hidden = false;
            $('graph-controls').hidden = false;
            $('graph-iter').min = '1';
            $('graph-iter').max = String(cuantos());
            mostrarPaso(cuantos() - 1);          // arranca en el último paso
        }

        document.addEventListener('DOMContentLoaded', () => {
            $('graph-iter')?.addEventListener('input', (e) => {
                detener();
                if (datos) { mostrarPaso(Number(e.target.value) - 1); }
            });
            $('graph-play')?.addEventListener('click', () => { if (datos) { animar(); } });
        });

        return { mostrar, limpiar };
    }

    return { crear };
})();
