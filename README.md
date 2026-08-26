# CC4303 — Actividad 1: servidor HTTP y proxy

Actividad 1 del curso **Redes (CC4303)**, DCC — Universidad de Chile.
El objetivo es implementar HTTP a mano sobre sockets: primero un servidor
que responde peticiones, y luego un proxy que se interpone entre el navegador y
el servidor de origen, pudiendo bloquear dominios, agregar headers y censurar
palabras en las respuestas.

**Restricción:** solo se permite la librería `socket`. No se usa
`http.server`, `http.client`, `requests` ni `urllib`; el parseo, el framing y la
construcción de los mensajes HTTP están escritos en `HttpMessage.py`.
También se utiliza `json` y `sys` para leer la configuración y manejar argumentos de línea de comandos.

Integrantes: María Moya G., M. Fernando Saavedra.

## Ramas

| Rama | Parte | Contenido |
|---|---|---|
| `Parte_1` | Parte 1 | Servidor HTTP: escucha en el puerto 8000, parsea la request y responde un `200 OK` con HTML mínimo y el header `X-ElQuePregunta`. |
| `feature/proxy` | Parte 2 | Proxy HTTP completo (rama por defecto). Parte de la Parte 1 y agrega el reenvío al servidor de origen, el bloqueo de dominios, la inyección del header y el reemplazo de palabras. |

## Ejecución

```bash
python3 server.py config.json
```

Queda escuchando en `0.0.0.0:8000` (en la VM se accede como `IP_VM:8000`).
Pruebas con `curl`, atravesando el proxy con `-x`:

```bash
curl example.com -x IP_VM:8000                     # debe verse igual que sin proxy
curl cc4303.bachmann.cl -x IP_VM:8000              # muestra el nombre inyectado
curl cc4303.bachmann.cl/replace -x IP_VM:8000      # palabras prohibidas reemplazadas
curl cc4303.bachmann.cl/secret -x IP_VM:8000       # 403 + imagen local
```

También funciona configurando el proxy HTTP del navegador en `IP_VM:8000`.
HTTPS está fuera del alcance de la actividad.

### Configuración

`config.json` controla el comportamiento del proxy:

```json
{
  "user_name": "Nombre Apellido",
  "blocked": ["www.dcc.uchile.cl", "cc4303.bachmann.cl/secret"],
  "forbidden_words": [{"proxy": "[REDACTED]"}]
}
```

- `user_name`: valor que se envía en el header `X-ElQuePregunta`.
- `blocked`: dominios o rutas prohibidas; basta que la cadena esté contenida en la URL pedida.
- `forbidden_words`: pares palabra → reemplazo que se aplican al body de la respuesta.

## Archivos

- **`HttpMessage.py`** — toda la lógica de protocolo. La clase `HttpMessage` representa
  un mensaje (request o response) ya parseado, con `start_line`, `headers`, `body` en
  bytes y los bytes originales en `raw`.
- **`server.py`** — el driver: lee la configuración, acepta conexiones y ejecuta el
  flujo del proxy.
- **`gato.jpg`** — imagen servida localmente en la página de bloqueo.
- **`Informe/`** — informe LaTeX de la actividad (`main.tex`).
- **`client.py`** — cliente TCP del módulo 1, no forma parte del proxy.

## Implementación

### Recepción con buffer pequeño

`HttpMessage._read_raw` lee en dos fases, que es lo que permite que el buffer sea más
chico que el mensaje:

1. Se llama a `recv` acumulando bytes hasta que aparece `\r\n\r\n`, el fin de los
   headers. Así el tamaño del buffer no limita el tamaño del área de headers.
2. Se busca `Content-Length` en el bloque de headers y se sigue leyendo hasta
   completar esa cantidad de bytes de body.

El buffer se ajusta con el parámetro `buff_size` de `HttpMessage.receive`
(4096 por defecto); bajarlo a un valor como 50 sirve para probar el caso en que ni
siquiera los headers caben en una lectura.

`to_bytes` hace el camino inverso y, si el mensaje declara `Content-Length`, **lo recalcula**
al serializar, porque
el reemplazo de palabras cambia el largo del body y reenviar el valor original dejaría
un mensaje inconsistente.

### Flujo del proxy

El proxy actúa como servidor frente al cliente y como cliente frente al servidor de
origen, con tres sockets: el de escucha, el aceptado hacia el cliente y el que se abre
hacia el destino. Por cada petición:

1. Si la ruta termina en `/gato.jpg`, responde la imagen local y termina (la pide el
   navegador a raíz de la página de bloqueo, y no existe en el servidor de origen).
2. Obtiene el destino desde el header `Host`, separando el puerto si viene explícito y
   asumiendo el 80 en caso contrario. `socket.connect` acepta el nombre de dominio, así
   que la resolución DNS la hace la librería.
3. Si la URL contiene algún dominio de `blocked`, responde un `403 Forbidden` generado
   localmente, con un HTML que referencia `/gato.jpg`. El socket hacia el destino nunca
   se abre, de modo que el servidor prohibido no recibe la petición.
4. Si no está bloqueado, agrega el header `X-ElQuePregunta` a la petición y la reenvía.
5. Sobre el body de la respuesta aplica los reemplazos de `forbidden_words` y se lo
   entrega al cliente.

### Limitación conocida

El framing asume `Content-Length`. Una respuesta con `Transfer-Encoding: chunked` o que
delimite el body cerrando la conexión se trunca a lo que haya llegado en la primera
lectura.
