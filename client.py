from xmlrcp import connect, XmlRpcException


def test_client():
    serv1 = connect('localhost', 8099)
    serv2 = connect('localhost', 8100)

    print()
    print()
    print('==========================================================')
    print('Iniciando pruebas de casos sin errores SERVER 1.')

    result = serv1.suma(1, 2)
    assert result == 3
    print(f'La funcion suma con (1,2) devuelve {result} correctamente.')

    result = serv1.suma(5, 5)
    assert result == 10
    print(f'La funcion suma con (5,5) devuelve {result} correctamente.')

    result = serv1.multiplicacion(10, 100)
    assert result == 1000
    print(f'La funcion multiplicacion con (10, 100) devuelve {result} correctamente.')

    result = serv1.division(1, 4)
    assert result == 0.25
    print(f'La funcion division con (1, 4) devuelve {result} correctamente.')

    result = serv1.division(4, 2)
    assert result == 2.0
    print(f'La funcion division con (4, 2) devuelve {result} correctamente.')
    print()
    print()
    print('==========================================================')
    print('Iniciando pruebas de casos sin errores SERVER 2.')

    ret = serv2.sustituir_caracter('Hola, como estas?', 'a', '5')
    result = ret["texto_sustituido"]
    ocurrencias = ret["ocurrencias"]
    assert result == 'Hol5, como est5s?', f"Texto incorrecto: {result}"
    assert ocurrencias == 2, f"Número de ocurrencias incorrecto: {ocurrencias}"
    print('La sustitución se realizó correctamente.')

    result = serv2.potencia(2, 3)
    assert result == 8
    print(f'La funcion potencia con (2,3) devuelve {result} correctamente.')

    result = serv2.dot_prod([1, 2, 3], [4, 5, 6])
    assert result == 32
    print(f'La funcion dot_prod con ([1, 2, 3], [4, 5, 6]) devuelve {result} correctamente.')

    print()
    print()
    print('==========================================================')
    print('Iniciando pruebas de casos con errores SERVER 1.')
    try:
        serv1.division()
    except XmlRpcException as e:
        assert e.code == 3
        print('Llamada incorrecta sin parámetros. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')

    try:
        serv1.multiplicacion('str1', 'str2')
    except XmlRpcException as e:
        assert e.code == 3
        print('Llamada con parametros incorrectos. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')

    try:
        serv1.division(50, 0)
    except XmlRpcException as e:
        assert e.code == 4
        print('Llamada con divisor nulo. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')

    print()
    print()
    print('==========================================================')
    print('Iniciando pruebas de casos con errores SERVER 2.')
    try:
        serv2.dot_prod([2, 3, 4])
    except XmlRpcException as e:
        assert e.code == 3
        print('Llamada con menos cantidad de parámetros. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')

    try:
        serv2.dot_prod([2, 3, 4], [2, 3, 4], [2, 3, 4])
    except XmlRpcException as e:
        assert e.code == 3
        print('Llamada con más cantidad de parámetros. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')

    try:
        serv2.matrix_sum([[1, 2], [3, 4]], [[5, 6], [7, 8]])
    except XmlRpcException as e:
        assert e.code == 2
        print('Metodo no existente. ', end="")
        print('Genera excepción necesaria con el mensaje:')
        print(e.message)
    else:
        print('ERROR: No lanzó excepción o no es la excepción correcta.')


if __name__ == "__main__":
    test_client()
