from socket import socket, SHUT_RDWR, AF_INET, SOCK_STREAM, timeout
import xml.etree.ElementTree as ET
from xmlrpc.client import loads, dumps
from threading import Thread
import re


SERVER_NAME = "PythonPrueba/1.1.1"
LF_CHAR = chr(10)
CR_CHAR = chr(13)
SP_CHAR = chr(32)
CR_NUM = 13
LF_NUM = 10
SP_NUM = 32
HEAD_SEPARATOR_NUM = ord(":")


http_methods = [
    "GET", "POST", "PUT", "DELETE", "HEAD",
    "PATCH", "OPTIONS", "CONNECT", "TRACE"
]

headers = [
    "Accept", "Accept-Charset", "Accept-Encoding",
    "Accept-Language", "Authorization", "Expect", "From",
    "Host", "If-Match", "If-Modified-Since", "If-None-Match",
    "If-Range", "If-Unmodified-Since", "Max-Forwards", "Proxy-Authorization",
    "Range", "Referer", "TE", "User-Agent", "Content-Length", "Connection",
    "Date", "Host", "User-Agent", "Content-Type"
]

necessary_headers = ["Content-Type", "Host", "User-Agent", "Content-Length"]


class HTTPException(Exception):
    def __init__(self, value):
        self.value = value
        super().__init__(f"HTTP code {value}")


def read_chars_until(data, pos, char):
    try:
        new_pos = data.index(char, pos)
    except Exception:
        raise HTTPException(400)
    read = "".join([chr(x) for x in data[pos:new_pos]])
    return [read, new_pos + 1]


def read_header(data, pos):
    # reading header name
    ret = read_chars_until(data, pos, HEAD_SEPARATOR_NUM)
    header = ret[0]
    pos = ret[1]
    if header not in headers:
        raise HTTPException(400)
    pos = ret[1]
    if data[pos] != SP_NUM:
        raise HTTPException(400)
    pos += 1

    # reading header value
    ret = read_chars_until(data, pos, CR_NUM)

    # reading the lf
    pos = ret[1]
    if data[pos] != LF_NUM:
        raise HTTPException(400)

    return [{header: ret[0]}, pos + 1]


# funcion que discecciona el POST HTTP request en el mensaje XML RPC,
# lanzando error en caso de que sea necesario.
def unwrap_http(data):
    data = [ord(char) for char in list(data)]
    pos = 0

    # reading method
    ret = read_chars_until(data, pos, SP_NUM)
    method = ret[0]
    if method not in http_methods:
        raise HTTPException(400)
    elif method != "POST":
        raise HTTPException(405)
    pos = ret[1]

    # reading url
    ret = read_chars_until(data, pos, SP_NUM)
    pos = ret[1]

    # reading version
    ret = read_chars_until(data, pos, CR_NUM)
    version = ret[0]
    if re.fullmatch(r"HTTP/\d\.\d", version):
        version = float(version[-3:])
        if version > 1.1:
            raise HTTPException(505)
    else:
        raise HTTPException(400)

    pos = ret[1]
    if data[pos] != LF_NUM:
        raise HTTPException(400)
    pos += 1

    # lectura de los headers.
    headers_info = {}
    while data[pos] != CR_NUM or data[pos + 1] != LF_NUM:
        ret = read_header(data, pos)
        pos = ret[1]
        headers_info.update(ret[0])

    pos += 2
    ret = "".join([chr(x) for x in data[pos:]])

    # comprobacion del headers necesarios.
    for header in necessary_headers:
        if header not in headers_info:
            raise HTTPException(400)

    # comprobacion de informacion de los campos.
    # tipo del contenido.
    if headers_info["Content-Type"] != "text/xml":
        raise HTTPException(415)
    # largo del contenido.
    try:
        length = int(headers_info["Content-Length"])
        if len(ret) != length:
            raise HTTPException(400)
    except Exception:
        raise HTTPException(400)

    return ret


# funcion que crea un HTTP response para el mensaje XML RPC.
def wrap_http(data, code=201, version=1.1):
    version = min(version, 1.1)

    phrase = ""
    if code == 200:
        phrase = "OK"
    elif code == 201:
        phrase = "Created"
    elif code == 400:
        phrase = "Bad Request"
    elif code == 404:
        phrase = "Not Found"
    elif code == 405:
        phrase = "Method Not Allowed"
    elif code == 415:
        phrase = "Unsupported Media Type"
    elif code == 500:
        phrase = "Internal Server Error"
    elif code == 505:
        phrase = "HTTP Version Not Supported"

    finish_line = CR_CHAR + LF_CHAR

    ret = "HTTP" + str(version) + " " + code + " " + phrase + finish_line
    ret += "Server: " + SERVER_NAME + finish_line
    ret += "Content-Length: " + str(len(data)) + finish_line
    ret += "Content-Type: text/xml" + finish_line
    ret += finish_line
    ret += data
    return ret


# funcion que retorna un xml rpc el resultado de una operacion.
def get_xml_rpc_right(result):
    ret = "<methodResponse>" + dumps((result,)) + "</methodResponse>"
    return ET.tostring(ret, encoding="utf-8", xml_declaration=True),


# funcion que retorna un xml rpc erroneo con el codigo y mensaje
# de error correspondiente.
def get_xml_rpc_error(code):
    ret = ET.Element("methodResponse")
    body = ET.SubElement(ret, "fault")
    body = ET.SubElement(body, "value")
    body = ET.SubElement(body, "struct")

    mem = ET.SubElement(body, "member")
    ET.SubElement(mem, "name").text = "faultCode"
    ET.SubElement(ET.SubElement(mem, "value"), "int").text = str(code)

    mem = ET.SubElement(body, "member")
    ET.SubElement(mem, "name").text = "faultString"
    mem = ET.SubElement(ET.SubElement(mem, "value"), "string")

    if code == 1:
        mem.text = "Erro parseo de XML."
    elif code == 2:
        mem.text = "No existe el método invocado."
    elif code == 3:
        mem.text = "Error en parámetros del método invocado."
    elif code == 4:
        mem.text = "Error interno en la ejecución del método."
    elif code == 5:
        mem.text = "Otros errores."

    return ET.tostring(ret, encoding="utf-8", xml_declaration=True),


class Server(object):
    sock = None             # Socket mediante el cual acepta conexiones.
    queue_length = 5        # Numero de mensajes que pueden haber en la cola de entrada.
    buffer_receptor = 128   # Largo del buffer que acepta un mensaje.
    SIMPLE_OP = 0.575       # Tiempo en milisegundos que espera antes de retornar timeout.

    def __init__(self, info):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.bind(info)
        self.sock.listen(self.queue_length)

    def handler(self, conn):

        # recepcion de datos
        http_req = ""
        try:
            # recepción y procesamiento de datos.
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
        http_req = http_req.decode()

        # Descompresion de HTTP(falta)
        try:
            data = unwrap_http(http_req)
        except HTTPException as ex:
            data = wrap_http("", ex.value)
        else:

            # Descompresion de XML_RPC.
            try:
                xml_rpc = loads(data)
            except Exception:
                data = wrap_http(get_xml_rpc_error(1))
            else:
                method = xml_rpc[1]
                params = xml_rpc[0]

                # validar que el metodo exista.
                try:
                    method = getattr(self, method)
                except AttributeError:
                    data = wrap_http(get_xml_rpc_error(2))
                else:

                    # validar que se puede obtener el resultado.
                    try:
                        data = method(*params)
                    except TypeError:
                        data = wrap_http(get_xml_rpc_error(3))
                    except Exception:
                        data = wrap_http(get_xml_rpc_error(4))
                    else:
                        data = wrap_http(get_xml_rpc_right(data))

        # envìo de data.
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
