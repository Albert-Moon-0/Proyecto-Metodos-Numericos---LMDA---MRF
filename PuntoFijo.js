(function (global) {
    function limpiarTexto(texto) {
        return String(texto).trim().replace(/\s+/g, '');
    }

    function decimalABinario(valor, esINT) {
        const numero = Number(valor);
        const res=0, medionum=0, resultado = '';
        if(numero === 0){
            return '0';
        }
        while(numero!==0){
            res=numero%2;
            medionum=Math.floor(numero/2);
            numero=medionum;
            resultado=res+resultado;
        }
        if(esINT)
            resultado = resultado.split('').reverse().join('');
        return resultado;
    }

    function normalizarBinario(numeroStr) {
        const partes = numeroStr.split('.');
        const entera = partes[0] || "";
        const fraccionaria = partes[1] || "";

        let bitsCombinados = entera + fraccionaria;
        if (bitsCombinados === "" || parseInt(bitsCombinados, 2) === 0) {
            return { mantisa: "0.0", exponente: 0 };
        }

        let exponente = 0;

        if (parseInt(entera, 2) > 0) {
            exponente = entera.length - 1;
        } else {
            const primerUno = fraccionaria.indexOf('1');
            exponente = -(primerUno + 1);
            bitsCombinados = fraccionaria.slice(primerUno);
        }

        const mantisaEntera = bitsCombinados[0];
        const mantisaFraccion = bitsCombinados.slice(1);
        
        let mantisaFinal = mantisaEntera;
        if (mantisaFraccion.length > 0) {
            mantisaFinal += "." + mantisaFraccion;
        }

        // Retornamos un objeto con los dos valores
        return { mantisa: mantisaFinal, exponente: exponente };
        }

    function validarBits(totalBits, characteristicBits, mantissaBits) {
        totalBits = Number(totalBits);
        characteristicBits = Number(characteristicBits);
        mantissaBits = Number(mantissaBits);

        if (!Number.isInteger(totalBits) || totalBits <= 0) {
            throw new Error('El número total de bits debe ser un entero positivo.');
        }

        if (!Number.isInteger(characteristicBits) || characteristicBits <= 0) {
            throw new Error('Los bits de la característica deben ser un entero positivo.');
        }

        if (!Number.isInteger(mantissaBits) || mantissaBits < 0) {
            throw new Error('Los bits de la mantisa deben ser un entero mayor o igual a cero.');
        }

        if (totalBits < characteristicBits + mantissaBits + 1) {
            throw new Error('La suma de la característica y la mantisa debe ser menor que el total de bits.');
        }

        return { totalBits, characteristicBits, mantissaBits };
    }







    function decimalAFijo(value, totalBits, characteristicBits, mantissaBits) {
    const numero = Number(value);

    if (!Number.isFinite(numero)) {
        throw new Error('El valor decimal ingresado no es válido.');
    }

    const { totalBits: total, characteristicBits: k, mantissaBits: m } = validarBits(totalBits, characteristicBits, mantissaBits);
    const signBit = numero < 0 ? '1' : '0';
    const absoluto = Math.abs(numero);

    if (absoluto === 0) {
        return {
            decimal: 0,
            binario: '0'.repeat(total),
            signo: '0',
            caracteristica: '0'.repeat(k),
            mantisa: '0'.repeat(m),
            descripcion: '0'
        };
    }
    // Separamos la parte entera y fraccionaria 
    const partes = absoluto.toString().split('.');
    const entera = partes[0] || "0";
    const fraccionaria = partes[1] || "";

    // Convertimos ambas partes a binario 
    const enteraBinaria = decimalABinario(entera, true);
    const fraccBinaria = decimalABinario(fraccionaria, false); 

    // Usamos 'let' en lugar de 'const' para poder modificar x
    let x = enteraBinaria + '.' + fraccBinaria;
    x = x.slice((m + 1) * -1).padStart(m + 1, '0');

    // Normalizamos para hallar la mantisa y el exponente real
    const { mantisa: mantisaBinaria, exponente } = normalizarBinario(x);
    
    const exponenteBias = exponente + (2 ** (k - 1) - 1);
    
    const bitsCaracteristica = decimalABinario(exponenteBias, true).padStart(k, '0');
    
    const mantisaLimpia = mantisaBinaria.replace('.', '').padEnd(m, '0');
    const representacion = signBit + bitsCaracteristica + mantisaLimpia;

    return {
        decimal: numero,
        binario: representacion,
        signo: signBit,
        caracteristica: bitsCaracteristica,
        mantisa: mantisaBinaria,
        descripcion: `${signBit} | ${bitsCaracteristica} | ${mantisaBinaria}`
    };
}












    function binarioAFijo(bits, totalBits, characteristicBits, mantissaBits) {
        const limpio = limpiarTexto(bits).replace(/[^01]/g, '');
        const { totalBits: total, characteristicBits: k, mantissaBits: m } = validarBits(totalBits, characteristicBits, mantissaBits);

        if (limpio.length !== total) {
            throw new Error(`Se esperaba una cadena de ${total} bits, pero se recibieron ${limpio.length}.`);
        }

        const signo = parseInt(limpio[0], 2);
        const bitsCaracteristica = limpio.slice(1, 1 + k);
        const bitsMantisa = limpio.slice(1 + k, total);
        const bias = 2 ** (k - 1) - 1;
        const exponente = parseInt(bitsCaracteristica, 2);

        if (exponente === 0 && bitsMantisa === '0'.repeat(m)) {
            return 0;
        }

        if (exponente === 2 ** k - 1) {
            throw new Error('La representación ingresada corresponde a un valor infinito o NaN, no admite cálculo en este método.');
        }

        let mantisa = 1;
        for (let i = 0; i < bitsMantisa.length; i += 1) {
            mantisa += Number(bitsMantisa[i]) / (2 ** (i + 1));
        }

        const valor = mantisa * (2 ** (exponente - bias));
        return signo === 1 ? -valor : valor;
    }

    function decimalABinarioFijo(value, totalBits, characteristicBits, mantissaBits) {
        return decimalAFijo(value, totalBits, characteristicBits, mantissaBits);
    }

    function binarioADecimalFijo(bits, totalBits, characteristicBits, mantissaBits) {
        return binarioAFijo(bits, totalBits, characteristicBits, mantissaBits);
    }

    function convertirBinarioFijo(bits, totalBits, characteristicBits, mantissaBits) {
        const entrada = limpiarTexto(bits);

        if (entrada.includes('.')) {
            const [parteEntera, parteDecimal] = entrada.split('.');
            const entero = parteEntera && parteEntera !== '-' ? parteEntera : '0';
            const sign = entrada.startsWith('-') ? -1 : 1;
            const valorEntero = entero === '0' ? 0 : parseInt(entero, 2);
            let valorDecimal = 0;

            if (parteDecimal) {
                for (let i = 0; i < parteDecimal.length; i += 1) {
                    valorDecimal += Number(parteDecimal[i]) / (2 ** (i + 1));
                }
            }

            return sign * (valorEntero + valorDecimal);
        }

        return binarioAFijo(entrada, totalBits, characteristicBits, mantissaBits);
    }

    function convertirDecimalABinarioFijo(valor, totalBits, characteristicBits, mantissaBits) {
        const numero = Number(valor);
        if (!Number.isFinite(numero)) {
            throw new Error('El valor decimal no es válido.');
        }

        const { totalBits: total, characteristicBits: k, mantissaBits: m } = validarBits(totalBits, characteristicBits, mantissaBits);
        const sign = numero < 0 ? '1' : '0';
        const absoluto = Math.abs(numero);

        if (absoluto === 0) {
            return { binario: '0'.repeat(total), descripcion: '0 | ' + '0'.repeat(k) + ' | ' + '0'.repeat(m) };
        }

        const bias = 2 ** (k - 1) - 1;
        const exp = Math.floor(Math.log2(absoluto));
        const exponenteBias = exp + bias;

        if (exponenteBias < 0 || exponenteBias >= 2 ** k) {
            throw new Error('El número excede el rango de bits configurado.');
        }

        const normalizado = absoluto / (2 ** exp);
        const mantisaFraccion = normalizado - 1;

        let mantisa = '';
        let fraccion = mantisaFraccion;

        for (let i = 0; i < m; i += 1) {
            fraccion *= 2;
            if (fraccion >= 1) {
                mantisa += '1';
                fraccion -= 1;
            } else {
                mantisa += '0';
            }
        }

        const expBits = exponenteBias.toString(2).padStart(k, '0');
        const resultado = sign + expBits + mantisa;

        return {
            binario: resultado,
            descripcion: `${sign} | ${expBits} | ${mantisa}`
        };
    }

    function mostrarResultado(texto, esError = false) {
        const resultadoEl = document.getElementById('result');
        const errorEl = document.getElementById('error-message');

        if (!resultadoEl || !errorEl) {
            return;
        }

        resultadoEl.textContent = esError ? '' : texto;
        errorEl.textContent = esError ? texto : '';
    }

    function leerDatosDesdeInputs() {
        const totalBits = document.getElementById('total-bits')?.value ?? '';
        const characteristicBits = document.getElementById('characteristic-bits')?.value ?? '';
        const mantissaBits = document.getElementById('mantissa-bits')?.value ?? '';
        return { totalBits, characteristicBits, mantissaBits };
    }

    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', function () {
            const botonBinarioADecimal = document.getElementById('binary-to-decimal');
            const botonDecimalABinario = document.getElementById('decimal-to-binary');

            botonBinarioADecimal?.addEventListener('click', function () {
                try {
                    const data = leerDatosDesdeInputs();
                    const entrada = limpiarTexto(document.getElementById('binary-input')?.value ?? '');

                    if (!entrada) {
                        throw new Error('Ingresa una representación binaria antes de convertir.');
                    }

                    const resultado = convertirBinarioFijo(entrada, data.totalBits, data.characteristicBits, data.mantissaBits);
                    mostrarResultado(`Resultado: ${resultado}`);
                } catch (error) {
                    mostrarResultado(error.message, true);
                }
            });

            botonDecimalABinario?.addEventListener('click', function () {
                try {
                    const data = leerDatosDesdeInputs();
                    const valor = document.getElementById('decimal-input')?.value ?? '';

                    if (!valor) {
                        throw new Error('Ingresa un valor decimal antes de convertir.');
                    }

                    const resultado = convertirDecimalABinarioFijo(valor, data.totalBits, data.characteristicBits, data.mantissaBits);
                    mostrarResultado(`Resultado: ${resultado.descripcion} | Binario completo: ${resultado.binario}`);
                } catch (error) {
                    mostrarResultado(error.message, true);
                }
            });
        });
    }

    const api = {
        limpiarTexto,
        validarBits,
        decimalAFijo,
        binarioAFijo,
        decimalABinarioFijo,
        binarioADecimalFijo,
        convertirBinarioFijo,
        convertirDecimalABinarioFijo
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }

    global.PuntoFijo = api;
})(typeof window !== 'undefined' ? window : globalThis);
