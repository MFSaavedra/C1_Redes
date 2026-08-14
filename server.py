import socket
from utils import receive_full_message, parse_HTTP_message, create_HTTP_message

if __name__ == "__main__":
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

             reconstructed_message = create_HTTP_message(parsed_message)
             print(f' -> Se ha reconstruido el mensaje: {reconstructed_message}')

         new_socket.close()
         print(f"conexión con {new_socket_address} ha sido cerrada")
 