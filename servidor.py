from xmlrcp import Server


def suma(a, b):
    return a + b


servidor = Server(("localhost", 8093))
servidor.add_method(suma)

try:
    servidor.serve()
except Exception:
    servidor.shutdown()
