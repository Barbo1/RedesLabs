import socket
from xmlrpc.client import loads
from threading import Thread
from . import http_utilities
from . import xmlrpc_utilities
from . import socket_functions


class Server(object):
    # Socket mediante el cual acepta conexiones.
    sock = None

    # Numero de mensajes que pueden haber en la cola de entrada.
    queue_length = 5

    # Largo del buffer que acepta un mensaje.
    buffer_size = 1024

    # Tiempo en milisegundos que espera antes de retornar timeout.
    SIMPLE_OP = 0.575

    # Nombre asociado al servidor, utilizado en la HTTP response.
    SERVER_NAME = "PythonPrueba/1.1.1"

    def __init__(self, info):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(info)
        self.sock.listen(self.queue_length)

    def handler(self, conn):
        conn.settimeout(self.SIMPLE_OP)

        # recepción y procesamiento de datos.
        readed = socket_functions.read_socket(conn, self.buffer_size)
        if not readed["status"]:
            conn.close()
            return
        http_req = readed["data"]

        # Descompresion de HTTP.
        code = 200
        try:
            data = http_utilities.unwrap_http_request(http_req)
        except http_utilities.HTTPException as ex:
            data = "".encode()
            code = ex.value
        else:

            # Descompresion de XML_RPC.
            try:
                xml_rpc = loads(data)
            except Exception:
                data = xmlrpc_utilities.write_xmlrpc_error(1)
            else:
                method = xml_rpc[1]
                params = xml_rpc[0]

                # validar que el metodo exista.
                try:
                    method = getattr(self, method)
                except AttributeError:
                    data = xmlrpc_utilities.write_xmlrpc_error(2)
                else:

                    # validar que se puede obtener el resultado.
                    try:
                        data = method(*params)
                        data = xmlrpc_utilities.write_xmlrpc_response(data)
                    except TypeError:
                        data = xmlrpc_utilities.write_xmlrpc_error(3)
                    except Exception:
                        data = xmlrpc_utilities.write_xmlrpc_error(4)

        # Envio de data.
        data = http_utilities.wrap_http_response(data, code, self.SERVER_NAME)
        socket_functions.send_socket(conn, data)

        conn.close()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
                th = Thread(target=self.handler, args=(conn, ))
                th.start()
            except KeyboardInterrupt:
                return

    def add_method(self, function):
        setattr(self, function.__name__, function)

    def shutdown(self):
        self.sock.shutdown(socket.SHUT_RDWR)
