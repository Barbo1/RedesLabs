from xmlrcp import Server
from math import pi


def echo(arg):
    if type(arg) is not str:
        raise TypeError()
    return arg


def ask_pi():
    return pi


servidor = Server(("localhost", 8101))
servidor.add_method(echo)
servidor.add_method(ask_pi)

try:
    servidor.serve()
except Exception as ex:
    print(ex)

servidor.shutdown()
