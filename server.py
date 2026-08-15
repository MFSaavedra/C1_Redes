import socket
import json
import sys
from utils import build_HTTP_response, receive_full_message, parse_HTTP_message, create_HTTP_message

if __name__ == "__main__":
     if len(sys.argv) < 2:
         print("Uso: python3 server.py <config_file>")
         sys.exit(1)

     config_path = sys.argv[1]
     try:
         with open(config_path, "r", encoding="utf-8") as f:
             config = json.load(f)
             user_name = config.get("user_name", "Nombre por defecto")
     except Exception as e:
         print(f"Error al leer el archivo de configuración: {e}")
         sys.exit(1)

     new_socket_address = ('0.0.0.0', 8000)

     print('Creando socket - Servidor')
     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     server_socket.bind(new_socket_address)
     server_socket.listen(3)
 
     print('... Esperando clientes')
     print(f' -> Servidor escuchando en http://{new_socket_address[0]}:{new_socket_address[1]}')

     while True:
         new_socket, new_socket_address = server_socket.accept()
         print(f' -> Se ha establecido una conexión con {new_socket_address}')
         
         recv_message = receive_full_message(new_socket)

         if recv_message:
             print("Request en crudo:")
             print(recv_message)

             parsed_message = parse_HTTP_message(recv_message)
             print(f' -> Se ha recibido el siguiente mensaje: {parsed_message}')

             response = build_HTTP_response(200, "OK", "<html><body><h1>webiwabo</h1></body></html>", user_name=user_name)
             new_socket.sendall(response)

         new_socket.close()
         print(f"conexión con {new_socket_address} ha sido cerrada")
 