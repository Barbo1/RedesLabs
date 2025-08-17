from socket import socket, AF_INET, SOCK_STREAM, timeout
from .xmlrpc_utilities import write_xmlrpc_request, read_xmlrpc_response
from .http_utilities import wrap_http_request, unwrap_http_response


class ClientException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code
        super().__init__("")


class Client(object):
    # User agent del cliente.
    user_agent = "Agente"

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
            sock.settimeout(self.SIMPLE_OP)
            data = write_xmlrpc_request(tuple(args), method)
            data = wrap_http_request(data, self.user_agent)
            size = 0
            msglen = len(data)
            try:
                while size < msglen:
                    size += sock.send(data[size:])
            except timeout:
                pass
            except Exception:
                print("ha ocurrido un error.")
                sock.close()
                return

            # recepcion de datos.
            data = b""
            try:
                sock.settimeout(self.COMPLEX_OP)
                while True:
                    res = sock.recv(self.buffer_receptor)
                    if not res:
                        break
                    data += res
            except timeout:
                pass
            except Exception:
                print("Ha ocurrido un error.")
                sock.close()
                return

            # cierre de socket cliente.
            sock.close()

            # retorno de información.
            try:
                data = unwrap_http_response(data)
                data = read_xmlrpc_response(data)
            except Exception:
                raise ClientException(
                    code=0,
                    message="La respuesta no es un XMLRPC response."
                )

            if data["type"]:
                raise ClientException(
                    code=data["faultCode"],
                    message=data["faultString"]
                )
            else:
                data = data["data"][0]

            return data

        return ret


def connect(address, port):
    return Client(address, port)
