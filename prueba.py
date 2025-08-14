from xmlrcp import Server


def suma(a, b):
    return a + b


servidor = Server(("localhost", 8080))
servidor.add_method(suma)

servidor.serve()
