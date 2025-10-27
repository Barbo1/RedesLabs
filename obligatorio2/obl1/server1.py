from xmlrcp import Server


def multiplicacion(arg1, arg2):
    if type(arg1) not in [float, int] or type(arg2) not in [float, int]:
        raise TypeError()
    return (arg1 * arg2)


def suma(arg1, arg2):
    return arg1 + arg2


def division(divid, divis):
    if type(divid) not in [float, int] or type(divis) not in [float, int]:
        raise TypeError()
    div = divid / divis
    return div


servidor = Server(("150.150.0.2", 8080))
servidor.add_method(suma)
servidor.add_method(division)
servidor.add_method(multiplicacion)

try:
    servidor.serve()
except Exception as ex:
    print(ex)

servidor.shutdown()
