from xmlrcp import Server
import time


def suma(a, b):
    time.sleep(1)
    return a + b


servidor = Server(("localhost", 8098))
servidor.add_method(suma)

try:
    servidor.serve()
except Exception as ex:
    print(ex)

servidor.shutdown()
