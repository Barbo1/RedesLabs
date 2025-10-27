import socket
import re
from xmlrcp import read_xmlrpc_response, unwrap_http_response, wrap_http_request, HTTPException


def test_cliente_maligno():
    xml_rpc_mal_formado = [
        'hoasongoansre',
        '<hola><value><string>Esto es un string</string></value></hola>',
        '{"jsonrpc": "2.0", "params": [1, 2, 3], "id": 1}',
        '<?xml version="1.0"?><methodCall><methodName>examples.getStateName</methodName> <params> <param><param> <value><i4>41</i4></value> </param> </params></methodCall>',
    ]

    http_mal_formado = [
        ('hoasongoansre', 400),
        ('POST /RPC2 HTTP/1.0\r\nUser-Agent: Frontier/5.1.2 (WinNT)\r\nHost: betty.userland.com\r\nContent-Type: text/xml\r\n\r\n<?xml version="1.0"?><methodCall><methodName>examples.getStateName</methodName><params><param><value><i4>41</i4></value></param></params></methodCall>', 400)
    ]

    for message in xml_rpc_mal_formado:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(('150.150.0.2', 8080))
        except ConnectionRefusedError:
            print("No se pudo conectar con el servidor.")
        data = wrap_http_request(message.encode(), "Agente")
        conn.sendall(data)
        response = conn.recv(1024)
        conn.close()
        try:
            data = unwrap_http_response(response)
            data = read_xmlrpc_response(data)

            if data["type"]:
                assert int(data["faultCode"]) == 1
                print('El XML-RPC es un fault. ', end="")
                print('Genera excepción necesaria con el mensaje:')
                print(data["faultString"])
            else:
                print('ERROR: No lanzó excepción o no es la excepción correcta.')
        except Exception:
            print("El response no esta bien formado.")

    for message, code in http_mal_formado:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(('100.100.0.2', 8080))
        except ConnectionRefusedError:
            print("No se pudo conectar con el servidor.")
        conn.sendall(message.encode())
        response = conn.recv(1024)
        conn.close()

        resp_code = int(re.search(r"\d{3}", response.decode()).group(0))
        if int(resp_code) == code:
            print(f'El HTTP corresponde a un error {code}. ', end="")
            print('Genera excepción necesaria.')
        else:
            print('ERROR: HTTP mal formado.')


if __name__ == "__main__":
    test_cliente_maligno()
