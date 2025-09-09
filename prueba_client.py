from lorem_text import lorem
from xmlrcp import connect, XmlRpcException

serv1 = connect('localhost', 8101)
texto_para_enviar = lorem.paragraphs(40)

print(len(texto_para_enviar) == len(serv1.echo(texto_para_enviar)))

print(serv1.ask_pi())
