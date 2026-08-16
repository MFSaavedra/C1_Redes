import os
import socket
import json
import sys
from HttpMessage import HttpMessage

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 server.py <config_file>")
        sys.exit(1)

    config_path = sys.argv[1]
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            user_name = config.get("user_name", "Nombre por defecto")
            user_email = config.get("user", "")
            blocked_domains = config.get("blocked", [])
            forbidden_words = config.get("forbidden_words", [])
    except Exception as e:
        print(f"Error al leer el archivo de configuración: {e}")
        sys.exit(1)

    listen_address = ('0.0.0.0', 8000)
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.bind(listen_address)
    listen_socket.listen(3)

    print(f"Proxy HTTP escuchando en http://{listen_address[0]}:{listen_address[1]}")

    while True:
        client_socket, client_address = listen_socket.accept()
        print(f"\n-> Conexión recibida desde cliente: {client_address}")

        try:
            request_msg = HttpMessage.receive(client_socket)
            if not request_msg:
                client_socket.close()
                continue

            path = request_msg.start_line.get("path", "/")

            if path == "/gato.jpg":
                if os.path.exists("gato.jpg"):
                    with open("gato.jpg", "rb") as f:
                        image_data = f.read()
                    response_msg = HttpMessage(
                        start_line={"version": "HTTP/1.1", "status_code": 200, "reason": "OK"},
                        headers={"Content-Type": "image/jpeg", "Content-Length": str(len(image_data))},
                        body=image_data
                    )
                    client_socket.sendall(response_msg.to_bytes())
                client_socket.close()
                continue

            headers = request_msg.headers
            host_header = headers.get("Host") or headers.get("host")

            if not host_header:
                print("No se encontró el header Host en la petición.")
                client_socket.close()
                continue

            if ":" in host_header:
                server_host, server_port = host_header.split(":", 1)
                server_port = int(server_port)
            else:
                server_host = host_header
                server_port = 80

            if path.startswith("http://") or path.startswith("https://"):
                full_url = path
            else:
                full_url = f"{server_host}{path}"

            is_blocked = False
            for blocked in blocked_domains:
                if blocked in full_url:
                    is_blocked = True
                    break

            if is_blocked:
                print(f"-> [403 FORBIDDEN] Solicitud bloqueada hacia: {full_url}")
                
                html_body = (
                    "<html><body>"
                    "<h1>403 Forbidden - Acceso Prohibido</h1>"
                    "<p>El acceso a esta ruta esta bloqueado por el proxy.</p>"
                    "<img src='/gato.jpg' alt='Acceso Denegado'>"
                    "</body></html>"
                )
                html_bytes = html_body.encode("utf-8")

                forbidden_msg = HttpMessage(
                    start_line={"version": "HTTP/1.1", "status_code": 403, "reason": "Forbidden"},
                    headers={
                        "Content-Type": "text/html; charset=utf-8",
                        "Content-Length": str(len(html_bytes))
                    },
                    body=html_bytes
                )
                
                client_socket.sendall(forbidden_msg.to_bytes())
                client_socket.close()
                continue

            print(f"-> Reenviando mensaje a servidor destino: {server_host}:{server_port}")

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server_host, server_port))
            server_socket.sendall(request_msg.to_bytes())
            response_msg = HttpMessage.receive(server_socket)
            server_socket.close()

            if response_msg:
                client_socket.sendall(response_msg.to_bytes())

        except Exception as e:
            print(f"-> Error durante el procesamiento: {e}")
        finally:
            client_socket.close()