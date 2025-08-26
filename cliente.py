from xmlrcp import connect, ClientException

address = 'localhost'
port = 8098

client = connect(address, port)

print(client.suma(1, 2))

try:
    print(client.suma(2))
except ClientException as e:
    print("Error " + str(e.code) + ": " + e.message)

try:
    print(client.hola(2))
except ClientException as e:
    print("Error " + str(e.code) + ": " + e.message)
