from xmlrcp import Server


def potencia(num1, num2):
    return pow(num1, num2)


def sustituir_caracter(texto, caracter_a_remplazar, nuevo_caracter):
    ocurrencias = texto.count(caracter_a_remplazar)
    texto_sustituido = texto.replace(caracter_a_remplazar, nuevo_caracter)
    return {"texto_sustituido": texto_sustituido, "ocurrencias": ocurrencias}


def dot_prod(v1, v2):
    if type(v1) is not list or type(v2) is not list or len(v1) != len(v2):
        raise TypeError()
    for elem in v1:
        if type(elem) not in [int, float]:
            raise TypeError()
    for elem in v2:
        if type(elem) not in [int, float]:
            raise TypeError()

    ret = 0
    for e1, e2 in zip(v1, v2):
        ret += e1 * e2
    return ret


servidor = Server(("100.100.0.2", 8080))
servidor.add_method(potencia)
servidor.add_method(sustituir_caracter)
servidor.add_method(dot_prod)

try:
    servidor.serve()
except Exception as ex:
    print(ex)

servidor.shutdown()
