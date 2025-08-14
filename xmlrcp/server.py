from socket import socket, SHUT_RDWR, AF_INET, SOCK_STREAM, timeout
from xmlrpc.client import loads
from threading import Thread
from .http_utilities import unwrap_http, wrap_http_response, HTTPException
from .xmlrpc_utilities import get_xml_rpc_error, get_xml_rpc_response


class Server(object):
    # Socket mediante el cual acepta conexiones.
    sock = None

    # Numero de mensajes que pueden haber en la cola de entrada.
    queue_length = 5

    # Largo del buffer que acepta un mensaje.
    buffer_receptor = 128

    # Tiempo en milisegundos que espera antes de retornar timeout.
    SIMPLE_OP = 0.575

    # Nombre asociado al servidor, utilizado en la HTTP response.
    SERVER_NAME = "PythonPrueba/1.1.1"

    def __init__(self, info):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.bind(info)
        self.sock.listen(self.queue_length)

    def handler(self, conn):

        # recepción y procesamiento de datos.
        http_req = ""
        try:
            while True:
                res = conn.recv(self.buffer_receptor).decode()
                if not res:
                    break
                http_req += res
        except timeout:
            pass
        except Exception:
            print("ha ocurrido un error.")
            conn.close()
            return

        # Descompresion de HTTP.
        code = 200
        try:
            data = unwrap_http(http_req)
        except HTTPException as ex:
            data = ""
            code = ex.value
        else:

            # Descompresion de XML_RPC.
            try:
                print(data)
                xml_rpc = loads(data)
            except Exception:
                data = get_xml_rpc_error(1)
            else:
                method = xml_rpc[1]
                params = xml_rpc[0]

                # validar que el metodo exista.
                try:
                    method = getattr(self, method)
                except AttributeError:
                    data = get_xml_rpc_error(2)
                else:

                    # validar que se puede obtener el resultado.
                    try:
                        data = method(*params)
                        data = get_xml_rpc_response(data)
                    except TypeError:
                        data = get_xml_rpc_error(3)
                    except Exception:
                        data = get_xml_rpc_error(4)

        # Wrapping data en un http response.
        data = wrap_http_response(data, code, self.SERVER_NAME)

        # Envio de data.
        try:
            size = 0
            msglen = len(data)
            while size < msglen:
                size += conn.send(data[size:])
        except timeout:
            pass
        except Exception:
            print("ha ocurrido un error.")
            conn.close()
            return

        conn.close()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
                conn.settimeout(self.SIMPLE_OP)
                th = Thread(target=self.handler, args=(conn, ))
                th.start()
            except KeyboardInterrupt:
                return

    def add_method(self, function):
        setattr(self, function.__name__, function)

    def shutdown(self):
        self.sock.shutdown(SHUT_RDWR)
