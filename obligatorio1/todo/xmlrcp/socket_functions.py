import socket
import re

LF_CHAR = chr(10)
CR_CHAR = chr(13)
SP_CHAR = chr(32)
FINISH_LINE = CR_CHAR + LF_CHAR
HDR_END = FINISH_LINE + FINISH_LINE

def read_socket(conn, buffer_size):
    http_req = b""
    status = True
    content_length = 0
    try:
        buf = bytearray()
        header_bytes = b""
        rest = b""
        while True:
            rec = conn.recv(buffer_size)
            if not rec:
                break

            buf += rec

            end = buf.find(HDR_END)
            if end != -1:
                header_bytes = bytes(buf[:end + len(HDR_END)])
                rest = bytes(buf[end + len(HDR_END):])
                break  # tenemos headers

        regex = re.compile(rb"(?i)\bcontent-length:\s*(\d+)\b")
        match = regex.search(header_bytes)
        if match:
            content_length = int(match.group(1))
        body = bytearray(rest)

        while len(body) < content_length:
            rec = conn.recv(min(buffer_size, content_length - len(body)))
            if not rec:
                # conexión cerrada antes de tiempo
                break
            body += rec

        http_req = header_bytes + bytes(body)

    except socket.timeout:
        pass
    except socket.error as ex:
        print(ex)
        status = False
    return {"status": status, "data": http_req}


def send_socket(conn, data):
    status = True
    size = 0
    msglen = len(data)
    try:
        while size < msglen:
            size += conn.send(data[size:])
    except socket.error as ex:
        status = False
        print(ex)
    return {"status": status}
