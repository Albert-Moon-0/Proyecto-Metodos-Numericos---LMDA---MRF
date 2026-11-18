// Módulo reutilizable para pintar el "procedimiento paso a paso" de un método.
// Recibe una lista de secciones (normalmente tomadas de la respuesta del backend)
// y crea, por cada una, un título, una descripción, fórmulas opcionales y una tabla.
//
//   <div id="steps-sections"></div>
//   <script src="js/api.js"></script>
//   <script src="js/tablas-y-recursos.js"></script>
//   <script src="js/tabla-pasos.js"></script>
//
//   TablaPasos.pintar(document.getElementById('steps-sections'), [
//       {
//           titulo: '1. Sistema A·c = B',           // obligatorio
//           descripcion: 'Texto explicativo',        // opcional
//           formulas: ['S₀(x) = …'],                 // opcional: líneas en monoespaciado
//           columnas: ['j', 'xⱼ', 'aⱼ'],            // si va vacío no se dibuja la tabla
//           filas: [[0, -3, 2.2685], [1, -2, null]], // null = celda vacía; texto = tal cual
//           resaltar: [[0, 2]],                      // celdas [fila, columna] resaltadas
//           nota: 'Texto al final',                  // opcional
//       },
//   ]);
//
// Usa las clases de layout-grafica.css (.steps-section, .steps-table, ...).
// Cárgalo después de tablas-y-recursos.js.

(function (global) {
    function texto(clase, contenido, etiqueta) {
        const el = document.createElement(etiqueta || 'p');
        el.className = clase;
        el.textContent = contenido;
        return el;
    }

    function formato(valor) {
        return typeof valor === 'string' ? valor : TablasYRecursos.formatearNumero(valor);
    }

    function crearTabla(seccion) {
        const envoltura = document.createElement('div');
        envoltura.className = 'table-wrap';

        const tabla = document.createElement('table');
        tabla.className = 'steps-table';

        const cabecera = document.createElement('thead');
        const filaCabecera = document.createElement('tr');
        seccion.columnas.forEach((nombre) => {
            const th = document.createElement('th');
            th.textContent = nombre;
            filaCabecera.appendChild(th);
        });
        cabecera.appendChild(filaCabecera);

        const resaltadas = new Set((seccion.resaltar || []).map(([i, j]) => `${i},${j}`));
        const cuerpo = document.createElement('tbody');
        seccion.filas.forEach((fila, i) => {
            const tr = document.createElement('tr');
            fila.forEach((valor, j) => {
                const td = document.createElement('td');
                if (valor === null || valor === undefined) {
                    td.className = 'is-empty';
                } else {
                    td.textContent = formato(valor);
                }
                if (resaltadas.has(`${i},${j}`)) {
                    td.classList.add('is-highlight');
                }
                tr.appendChild(td);
            });
            cuerpo.appendChild(tr);
        });

        tabla.append(cabecera, cuerpo);
        envoltura.appendChild(tabla);
        return envoltura;
    }

    function crearSeccion(seccion) {
        const contenedor = document.createElement('section');
        contenedor.className = 'steps-section';

        contenedor.appendChild(texto('subsection__title', seccion.titulo, 'h3'));

        if (seccion.descripcion) {
            contenedor.appendChild(texto('steps-description', seccion.descripcion));
        }

        if ((seccion.formulas || []).length) {
            const lista = document.createElement('ul');
            lista.className = 'steps-formulas';
            seccion.formulas.forEach((linea) => {
                const item = document.createElement('li');
                item.textContent = linea;
                lista.appendChild(item);
            });
            contenedor.appendChild(lista);
        }

        if ((seccion.columnas || []).length) {
            contenedor.appendChild(crearTabla(seccion));
        }

        if (seccion.nota) {
            contenedor.appendChild(texto('result-note', seccion.nota));
        }

        return contenedor;
    }

    function pintar(contenedor, secciones) {
        contenedor.innerHTML = '';
        secciones.forEach((seccion) => contenedor.appendChild(crearSeccion(seccion)));
    }

    global.TablaPasos = { crearSeccion, pintar };
})(window);