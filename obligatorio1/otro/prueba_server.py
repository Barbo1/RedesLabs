from xmlrcp import Server
from math import pi
from time import sleep


def echo(arg):
    if type(arg) is not str:
        raise TypeError()
    return arg


def ask_pi():
    return pi


def expensive_time_operation():
    sleep(10)
    return 2


servidor = Server(("localhost", 8102))
servidor.add_method(echo)
servidor.add_method(ask_pi)
servidor.add_method(expensive_time_operation)

try:
    servidor.serve()
except Exception as ex:
    print(ex)

servidor.shutdown()
