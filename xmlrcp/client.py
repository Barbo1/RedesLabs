from socket import socket, AF_INET, SOCK_STREAM, timeout
from xmlrpc.client import loads
from .xmlrpc_utilities import get_xml_rpc_request


class ClientException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code
        super().__init__("")


class Client(object):
    # Socket mediante el cual acepta conexiones.
    jsonrpc_version = "2.0"

    # Largo del buffer que acepta un mensaje.
    buffer_receptor = 128

    # IP mediante la cual se realiza la conexión.
    address = None

    # Puerto mediante el cual se realiza la conexión.
    port = None

    # Tiempo en milisegundos antes de timeout(cuando espera para enviar).
    SIMPLE_OP = 0.575

    # Tiempo en milisegundos antes de timeout(cuando espera el resultado).
    COMPLEX_OP = 1.437

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

            # Creación del socket cliente.
            sock = socket(AF_INET, SOCK_STREAM)
            sock.connect((self.address, self.port))

            # Envio de datos.
            try:
                sock.settimeout(self.SIMPLE_OP)
                data = get_xml_rpc_request(tuple(args), method)
                data = data.encode()
                size = 0
                msglen = len(data)
                while size < msglen:
                    size += sock.send(data[size:])
            except timeout:
                pass
            except Exception:
                print("ha ocurrido un error.")
                sock.close()
                return

            print("CLIENT | REQUEST: " + data)

            # recepcion de datos.
            data = ""
            try:
                sock.settimeout(self.COMPLEX_OP)
                while True:
                    res = sock.recv(self.buffer_receptor)
                    if not res:
                        break
                    data += res.decode()
            except timeout:
                pass
            except Exception:
                print("Ha ocurrido un error.")
                sock.close()
                return

            # cierre de socket cliente.
            sock.close()

            print("CLIENT | RESPONSE: " + data)

            # retorno de información.
            if not data:
                raise ClientException(code=0, message="El mensaje esta vacio.")

            try:
                data = loads(data)
            except Exeception:
                raise ClientException(code=0, message="El mensaje esta vacio.")

        return ret


def connect(address, port):
    return Client(address, port)
