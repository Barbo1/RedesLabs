import xml.etree.ElementTree as ET
from xmlrpc.client import dumps, loads


# funcion que retorna un XMLRPC el resultado de una operacion.
def write_xmlrpc_request(params, method):
    return dumps(params, methodname=method).encode()


# funcion que retorna un XMLRPC con el resultado de una operacion.
def write_xmlrpc_response(result):
    ret = "<?xml version='1.0'?><methodResponse>".encode()
    ret += dumps((result,), methodname="").encode()
    ret += "</methodResponse>".encode()
    return ret


# funcion que retorna un XMLRPC erroneo con el codigo y mensaje
# de error correspondiente.
def write_xmlrpc_error(code):
    ret = ET.Element("methodResponse")
    body = ET.SubElement(ret, "fault")
    body = ET.SubElement(body, "value")
    body = ET.SubElement(body, "struct")

    mem = ET.SubElement(body, "member")
    ET.SubElement(mem, "name").text = "faultCode"
    ET.SubElement(ET.SubElement(mem, "value"), "int").text = str(code)

    mem = ET.SubElement(body, "member")
    ET.SubElement(mem, "name").text = "faultString"
    mem = ET.SubElement(ET.SubElement(mem, "value"), "string")

    if code == 1:
        mem.text = "Error parseo de XML."
    elif code == 2:
        mem.text = "No existe el método invocado."
    elif code == 3:
        mem.text = "Error en parámetros del método invocado."
    elif code == 4:
        mem.text = "Error interno en la ejecución del método."
    elif code == 5:
        mem.text = "Otros errores."

    return ET.tostring(ret, encoding="utf-8", xml_declaration=True)


def validate_single(elem, name):
    if len(elem) != 1 or elem.tag != name:
        raise Exception()


def charge_value(value):
    if len(value) == 0:
        return value.text
    elif len(value) >= 2 or len(value[0]) >= 1:
        raise Exception()
    elif value[0].tag == "string":
        return value[0].text
    elif value[0].tag in ["i4", "int"]:
        return int(value[0].text)
    else:
        raise Exception()


# lee mensaje XMLRPC response y retorna los datos y tipo de mensaje.
def read_xmlrpc_response(data):
    data = ET.fromstring(data)
    validate_single(data, "methodResponse")

    data = data[0]
    ret = {"type": True}
    if data.tag == "fault":
        data = data[0]
        validate_single(data, "value")

        data = data[0]
        if len(data) != 2 or data.tag != "struct":
            raise Exception()

        dic = {}
        for elem in data:
            if elem.tag != "member" or len(elem) != 2:
                raise Exception()
            dic.update({
                elem.find("name").text: charge_value(elem.find("value"))
            })
        ret.update(dic)

    elif data.tag == "params":
        elem = data[0]
        validate_single(elem, "param")

        elem = elem[0]
        validate_single(elem, "value")

        data = loads(ET.tostring(data))[0]
        if not data:
            raise Exception()

        ret["type"] = False
        ret["data"] = data
    else:
        raise Exception()

    return ret


# lee mensaje XMLRPC response y retorna los datos y tipo de mensaje.
def read_xmlrpc_request(data):
    elem = ET.fromstring(data)
    if len(elem) != 2:
        raise Exception()
    if elem.find("methodName") is None:
        raise Exception()
    if elem.find("params") is None:
        raise Exception()

    method = elem.find("methodName")
    if len(method) != 0:
        raise Exception()
    method = method.text

    params = elem.find("params")
    params = loads(ET.tostring(params))[0]

    return {
        "method": method,
        "params": params
    }
