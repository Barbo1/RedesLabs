from lorem_text import lorem
from xmlrcp import connect, XmlRpcException

serv1 = connect('localhost', 8102)
texto_para_enviar = lorem.paragraphs(40)

print(len(texto_para_enviar) == len(serv1.echo(texto_para_enviar)))

print(serv1.ask_pi())

serv1.OPERATIONAL_TIME = 11.5

print(serv1.expensive_time_operation())

