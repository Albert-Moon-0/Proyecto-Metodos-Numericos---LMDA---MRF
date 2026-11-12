// Lógica del índice: módulos desplegables tipo acordeón.
// - Al abrir un módulo se cierra el que estuviera abierto.
// - Click sobre el módulo abierto lo cierra.
// - El contador ("3 métodos" / "Próximamente") se calcula solo a partir de
//   las tarjetas .method-card que haya dentro de cada módulo, así que
//   al agregar un enlace en el HTML no hay que tocar nada aquí.
// - Si la URL trae un hash (index.html#raices) ese módulo se abre al cargar:
//   útil para que el "Volver al proyecto" de cada método regrese a su módulo.

document.addEventListener('DOMContentLoaded', function () {
    const modulos = Array.from(document.querySelectorAll('.module'));

    function textoContador(cantidad) {
        if (cantidad === 0) {
            return 'Próximamente';
        }
        return cantidad === 1 ? '1 método' : `${cantidad} métodos`;
    }

    function actualizarContador(modulo) {
        const contador = modulo.querySelector('.module__count');
        const cantidad = modulo.querySelectorAll('.method-card').length;

        contador.textContent = textoContador(cantidad);
        contador.classList.toggle('is-empty', cantidad === 0);
    }

    function establecerEstado(modulo, abierto) {
        const boton = modulo.querySelector('.module__header');
        modulo.classList.toggle('is-open', abierto);
        boton.setAttribute('aria-expanded', String(abierto));
    }

    function abrir(modulo) {
        modulos.forEach((otro) => {
            if (otro !== modulo) {
                establecerEstado(otro, false);
            }
        });
        establecerEstado(modulo, true);
    }

    function alternar(modulo) {
        if (modulo.classList.contains('is-open')) {
            establecerEstado(modulo, false);
        } else {
            abrir(modulo);
        }
    }

    modulos.forEach((modulo) => {
        actualizarContador(modulo);
        establecerEstado(modulo, false);

        modulo.querySelector('.module__header').addEventListener('click', () => alternar(modulo));
    });

    // Navegación con teclado entre cabeceras: flechas arriba/abajo, Inicio y Fin.
    const cabeceras = modulos.map((modulo) => modulo.querySelector('.module__header'));

    cabeceras.forEach((cabecera, indice) => {
        cabecera.addEventListener('keydown', (evento) => {
            let destino = null;

            if (evento.key === 'ArrowDown') {
                destino = cabeceras[(indice + 1) % cabeceras.length];
            } else if (evento.key === 'ArrowUp') {
                destino = cabeceras[(indice - 1 + cabeceras.length) % cabeceras.length];
            } else if (evento.key === 'Home') {
                destino = cabeceras[0];
            } else if (evento.key === 'End') {
                destino = cabeceras[cabeceras.length - 1];
            }

            if (destino) {
                evento.preventDefault();
                destino.focus();
            }
        });
    });

    const idEnUrl = window.location.hash.replace('#', '');
    const moduloEnUrl = modulos.find((modulo) => modulo.id === idEnUrl);

    if (moduloEnUrl) {
        abrir(moduloEnUrl);
    }
});
