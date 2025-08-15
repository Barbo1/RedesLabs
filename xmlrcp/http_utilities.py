import re

LF_CHAR = chr(10)
CR_CHAR = chr(13)
SP_CHAR = chr(32)
CR_NUM = 13
LF_NUM = 10
SP_NUM = 32
CL_NUM = ord(":")
HTTP_METHODS = [
    "GET", "POST", "PUT", "DELETE", "HEAD",
    "PATCH", "OPTIONS", "CONNECT", "TRACE"
]
HEADERS = [
    "Accept", "Accept-Charset", "Accept-Encoding",
    "Accept-Language", "Authorization", "Expect", "From",
    "Host", "If-Match", "If-Modified-Since", "If-None-Match",
    "If-Range", "If-Unmodified-Since", "Max-Forwards", "Proxy-Authorization",
    "Range", "Referer", "TE", "User-Agent", "Content-Length", "Connection",
    "Date", "Host", "User-Agent", "Content-Type"
]
NECESSARY_HEADERS = ["Content-Type", "Host", "User-Agent", "Content-Length"]


class HTTPException(Exception):
    def __init__(self, value):
        self.value = value
        super().__init__(f"HTTP code {value}")


# Lee caracteres hasta que llege al caracter 'char'.
def read_chars_until(data, pos, char):
    try:
        new_pos = data.index(char, pos)
    except Exception:
        raise HTTPException(400)
    read = "".join([chr(x) for x in data[pos:new_pos]])
    return [read, new_pos + 1]


def read_header(data, pos):
    # Leyendo nombre del header
    ret = read_chars_until(data, pos, CL_NUM)
    header = ret[0]
    pos = ret[1]
    if header not in HEADERS:
        raise HTTPException(400)
    pos = ret[1]
    if data[pos] != SP_NUM:
        raise HTTPException(400)
    pos += 1

    # Leyendo valor del header
    ret = read_chars_until(data, pos, CR_NUM)

    # Leer el caracter lf final de la linea.
    pos = ret[1]
    if data[pos] != LF_NUM:
        raise HTTPException(400)

    return [{header: ret[0]}, pos + 1]


# Funcion que discecciona el POST HTTP request en el mensaje XML RPC,
# Lanzando error en caso de que sea necesario.
def unwrap_http(data):
    data = [ord(char) for char in list(data)]
    pos = 0

    # Lectura y validacion de metodo utilizado.
    ret = read_chars_until(data, pos, SP_NUM)
    method = ret[0]
    if method not in HTTP_METHODS:
        raise HTTPException(400)
    elif method != "POST":
        raise HTTPException(501)
    pos = ret[1]

    # Lectura de url.
    ret = read_chars_until(data, pos, SP_NUM)
    pos = ret[1]

    # Lectura y validacion de version de HTTP.
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

    # Lectura de los headers.
    headers_info = {}
    while data[pos] != CR_NUM or data[pos + 1] != LF_NUM:
        ret = read_header(data, pos)
        pos = ret[1]
        headers_info.update(ret[0])

    pos += 2
    ret = "".join([chr(x) for x in data[pos:]])

    # Comprobacion del headers necesarios.
    for header in NECESSARY_HEADERS:
        if header not in headers_info:
            raise HTTPException(400)

    # Comprobacion de informacion de los campos.
    # Tipo del contenido.
    if headers_info["Content-Type"] != "text/xml":
        raise HTTPException(415)
    # Largo del contenido.
    try:
        length = int(headers_info["Content-Length"])
        if len(ret) != length:
            raise HTTPException(400)
    except Exception:
        raise HTTPException(400)

    return ret


# funcion que crea un HTTP response para el mensaje XML RPC.
def wrap_http_response(data, code, server_name):
    phrase = ""
    if code == 200:
        phrase = "OK"
    elif code == 201:
        phrase = "Created"
    elif code == 400:
        phrase = "Bad Request"
    elif code == 404:
        phrase = "Not Found"
    elif code == 415:
        phrase = "Unsupported Media Type"
    elif code == 500:
        phrase = "Internal Server Error"
    elif code == 505:
        phrase = "HTTP Version Not Supported"
    elif code == 501:
        phrase = "Not Implemented"

    finish_line = CR_CHAR + LF_CHAR

    ret = "HTTP/1.1 " + str(code) + " " + phrase + finish_line
    ret += "Server: " + server_name + finish_line
    ret += "Content-Length: " + str(len(data)) + finish_line
    ret += "Content-Type: text/xml" + finish_line
    ret += "Last-Modified: text/xml" + finish_line
    ret += finish_line
    ret = ret.encode()
    ret += data
    return ret


# funcion que crea un HTTP reques para el mensaje XML RPC.
def wrap_http_request(data, code, host, client_name):
    finish_line = CR_CHAR + LF_CHAR

    ret = "POST / HTTP/1.1" + finish_line
    ret += "Host: Servidor.com" + finish_line
    ret += "Connection: close" + finish_line
    ret += "User-Agent: " + client_name + finish_line
    ret += "Accept-Language: es" + finish_line
    ret += "Content-Type: text/xml" + finish_line
    ret += "Content-Length: " + str(len(data)) + finish_line
    ret += finish_line
    ret = ret.encode()
    ret += data
    return ret
