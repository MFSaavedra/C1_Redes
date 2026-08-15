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
             user_name = config.get("user", "Nombre por defecto")
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
         
         message = HttpMessage.receive(new_socket)

         if message:
             print("Request en crudo:")
             print(message.raw)

             print(f' -> Se ha recibido el siguiente mensaje: {message.start_line} {message.headers}')

             response = HttpMessage.response(
                 200, "OK", "<html><body><h1>webiwabo</h1></body></html>",
                 extra_headers={"X-ElQuePregunta": user_name})
             new_socket.sendall(response.to_bytes())

         new_socket.close()
         print(f"conexión con {new_socket_address} ha sido cerrada")
 