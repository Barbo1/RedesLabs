import socket


def read_socket(conn, buffer_size):
    http_req = b""
    status = True
    try:
        while True:
            rec = conn.recv(buffer_size)
            if not rec:
                break
            http_req += rec
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
