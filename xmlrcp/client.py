import socket
from . import http_utilities
from . import xmlrpc_utilities
from . import socket_functions

FORMAT_ERROR = "La respuesta no es un XMLRPC response."
CONNECTION_ERROR = "Hubo un problema en la conexion con el servidor."


class ClientException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__("")


class Client(object):
    # User agent del cliente.
    user_agent = "Agente"

    # Largo del buffer que acepta un mensaje.
    buffer_size = 1024

    # IP mediante la cual se realiza la conexión.
    address = None

    # Puerto mediante el cual se realiza la conexión.
    port = None

    # Tiempo en milisegundos antes de timeout(cuando espera para enviar).
    SIMPLE_OP = 0.575

    # Tiempo en milisegundos antes de timeout(cuando espera el resultado).
    COMPLEX_OP = 2.437

    def __init__(self, address, port):
        self.address = address
        self.port = port

    def __getattr__(self, method):
        if method == "":
            raise AttributeError("No hay nombre para el metodo.")

        def ret(*args):

            # Validación de parametros
            if self.address is None:
                raise TypeError("Direccion no encontrada.")

            elif self.port is None:
                raise TypeError("Puerto no encontrada.")

            # Creacion de data.
            data = xmlrpc_utilities.write_xmlrpc_request(tuple(args), method)
            data = http_utilities.wrap_http_request(data, self.user_agent)

            # Creación del socket cliente.
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try:
                sock.connect((self.address, self.port))
                sock.settimeout(self.SIMPLE_OP)

                # Envio de datos.
                sended = socket_functions.send_socket(sock, data)
                if not sended["status"]:
                    sock.close()
                    return

                # recepcion de datos.
                sock.settimeout(self.COMPLEX_OP)
                readed = socket_functions.read_socket(sock, self.buffer_size)
                if not readed["status"]:
                    sock.close()
                    return
                data = readed["data"]

                # cierre de socket cliente.
                sock.close()
            except ConnectionError:
                raise ConnectionError(CONNECTION_ERROR)

            # retorno de información.
            try:
                data = http_utilities.unwrap_http_response(data)
                data = xmlrpc_utilities.read_xmlrpc_response(data)
            except Exception:
                raise SyntaxError(FORMAT_ERROR)

            if data["type"]:
                raise ClientException(data["faultCode"], data["faultString"])
            else:
                data = data["data"][0]

            return data

        return ret


def connect(address, port):
    return Client(address, port)
