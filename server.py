import socket
import json
import sys
from HttpMessage import HttpMessage

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 proxy.py <config_file>")
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