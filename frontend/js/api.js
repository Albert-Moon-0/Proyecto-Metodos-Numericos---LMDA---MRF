// Configuración de conexión con el backend en Python (Flask).
//
// Si abres estos archivos HTML directamente con doble clic (file://),
// o los sirves con otra herramienta (Live Server, etc.), deja esta
// URL apuntando al backend Flask (por defecto corre en el puerto 5000).
//
// Si en cambio abres el proyecto a través del propio backend
// (http://localhost:5000), esta misma URL sigue funcionando porque
// apunta al mismo servidor.
// Si abren la web desde ngrok, usa la URL de ngrok automáticamente. 
// Si la abren en local (Live Server), usa localhost:5000
const API_BASE_URL = window.location.hostname.includes('ngrok') 
    ? window.location.origin 
    : 'http://localhost:5000';

/**
 * Hace un POST en formato JSON hacia el backend y devuelve la respuesta
 * ya parseada. Si el backend responde con un error (400/500), lanza un
 * Error con el mensaje que envió el backend.
 */
async function llamarApi(ruta, cuerpo) {
    let respuesta;

    try {
        respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cuerpo),
        });
    } catch (error) {
        throw new Error(
            'No se pudo conectar con el backend. ¿Está corriendo "python app.py" en ' +
            API_BASE_URL + '?'
        );
    }

    const datos = await respuesta.json().catch(() => ({}));

    if (!respuesta.ok) {
        throw new Error(datos.error || 'Ocurrió un error al comunicarse con el servidor.');
    }

    return datos;
}
