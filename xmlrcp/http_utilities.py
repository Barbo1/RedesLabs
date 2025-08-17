import re
import datetime as dt

LF_CHAR = chr(10)
CR_CHAR = chr(13)
SP_CHAR = chr(32)
FINISH_LINE = CR_CHAR + LF_CHAR
LF_NUM = 10
CR_NUM = 13
SP_NUM = 32
CL_NUM = ord(":")

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]

GENERAL_HEADERS = ["Connection", "Content-Type", "Content-Length"]

REQUEST_HEADERS = [
    "Host", "User-Agent", "Accept-Language", "Cookies", "Accept"
] + GENERAL_HEADERS
NECESSARY_REQUEST_HEADERS = [
    "Content-Type", "Host", "User-Agent", "Content-Length"
]

RESPONSE_HEADERS = [
    "Server", "Date", "Last-Modified", "Set-Cookie"
] + GENERAL_HEADERS
NECESSARY_RESPONSE_HEADERS = ["Content-Type", "Content-Length"]


class HTTPException(Exception):
    def __init__(self, value):
        self.value = value
        super().__init__(f"HTTP code {value}")


def current_time():
    date = dt.datetime.now(tz=dt.timezone.utc)
    date = date.strftime("%a, %d %b %Y %H:%M:%S")
    date += " GMT"
    return date


# Lee caracteres hasta que llege al caracter 'char'.
def read_chars_until(data, pos, char):
    try:
        new_pos = data.index(char, pos)
    except Exception:
        raise HTTPException(400)
    read = "".join([chr(x) for x in data[pos:new_pos]])
    return [read, new_pos + 1]


def read_header(data, pos, headers):
    # Leyendo nombre del header
    ret = read_chars_until(data, pos, CL_NUM)
    header = ret[0]
    pos = ret[1]
    if header not in headers:
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


def read_validate_headers(data, pos, headers, necessary_headers):
    # Lectura de los headers.
    headers_info = {}
    while data[pos] != CR_NUM or data[pos + 1] != LF_NUM:
        ret = read_header(data, pos, headers)
        pos = ret[1]
        headers_info.update(ret[0])

    pos += 2
    ret = "".join([chr(x) for x in data[pos:]])

    # Comprobacion del headers necesarios.
    for header in necessary_headers:
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


# Funcion que discecciona el POST HTTP response en el mensaje XML RPC,
# Lanzando error en caso de que sea necesario. Los datos tienen que
# ser pasados en Bytes.
def unwrap_http_response(data):
    data = [int(char) for char in data]
    pos = 0

    # Lectura y validacion de version de HTTP.
    ret = read_chars_until(data, pos, SP_NUM)
    version = ret[0]
    if re.fullmatch(r"HTTP/\d\.\d", version):
        version = float(version[-3:])
        if version > 1.1:
            raise HTTPException(505)
    else:
        raise HTTPException(400)
    pos = ret[1]

    # Lectura de codigo.
    ret = read_chars_until(data, pos, SP_NUM)
    code = ret[0]
    code = int(code)
    if code > 600 or code < 100:
        raise Exception()
    pos = ret[1]

    # Lectura de frase.
    ret = read_chars_until(data, pos, CR_NUM)
    pos = ret[1]
    if data[pos] != LF_NUM:
        raise HTTPException(400)
    pos += 1

    return read_validate_headers(
        data,
        pos,
        RESPONSE_HEADERS,
        NECESSARY_RESPONSE_HEADERS
    )


# Funcion que discecciona el POST HTTP request en el mensaje XML RPC,
# Lanzando error en caso de que sea necesario. Los datos tienen que
# ser pasados en Bytes.
def unwrap_http_request(data):
    data = [int(char) for char in data]
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

    return read_validate_headers(
        data,
        pos,
        REQUEST_HEADERS,
        NECESSARY_REQUEST_HEADERS
    )


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

    print()
    print(data)
    print(len(data))
    print()


    ret = "HTTP/1.1 " + str(code) + " " + phrase + FINISH_LINE
    ret += "Server: " + server_name + FINISH_LINE
    ret += "Content-Length: " + str(len(data)) + FINISH_LINE
    ret += "Content-Type: text/xml" + FINISH_LINE
    ret += "Date: " + current_time() + FINISH_LINE
    ret += FINISH_LINE
    ret = ret.encode()
    ret += data
    return ret


# funcion que crea un HTTP reques para el mensaje XML RPC.
def wrap_http_request(data, user_agent):
    ret = "POST / HTTP/1.1" + FINISH_LINE
    ret += "Host: Servidor.com" + FINISH_LINE
    ret += "Connection: close" + FINISH_LINE
    ret += "User-Agent: " + user_agent + FINISH_LINE
    ret += "Accept-Language: en" + FINISH_LINE
    ret += "Content-Type: text/xml" + FINISH_LINE
    ret += "Content-Length: " + str(len(data)) + FINISH_LINE
    ret += FINISH_LINE
    ret = ret.encode()
    ret += data
    return ret
