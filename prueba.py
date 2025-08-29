from datetime import datetime
import xml.etree.ElementTree as ET
import base64


# Computa la lectura de valores en un xml con estructura XMLRPC.
# Solamente funciona para las etiquetas 'value'.
def read_value(value):
    if len(value) == 0:
        return value.text
    elif len(value) == 1:
        if value[0].tag == "struct":
            ret = {}
            for elem in value[0]:
                if elem.tag != "member" or len(elem) != 2:
                    raise Exception()
                name = elem.find("name")
                value = elem.find("value")
                if len(name) != 0:
                    raise Exception()
                ret.update({name.text: read_value(value)})
            return ret
        if value[0].tag == "array" and len(value[0]) == 1 and value[0][0].tag == "data":
            ret = []
            for elem in value[0][0]:
                if elem.tag != "value":
                    raise Exception()
                ret.append(read_value(elem))
            return ret
        elif len(value[0]) == 0:
            if value[0].tag == "string":
                return value[0].text
            elif value[0].tag in ["i4", "int"]:
                return int(value[0].text)
            elif value[0].tag == "boolean":
                if value[0].text == "true":
                    return True
                elif value[0].text == "false":
                    return False
            elif value[0].tag == "double":
                return float(value[0].text)
            elif value[0].tag == "dateTime.iso8601":
                return datetime.fromisoformat(value[0].text)
            elif value[0].tag == "base64":
                ret = value[0].text.encode()
                base64.b64decode(ret)   # lanza error si no es base64.
                return ret

    raise Exception()


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


# lee mensaje XMLRPC response y retorna los datos y tipo de mensaje, donde
# False representa un response correcto y True representa un falut.
def read_xmlrpc_response(data):
    data = ET.fromstring(data)
    validate_single(data, "methodResponse")

    data = data[0]
    ret = {}
    if data.tag == "fault":
        data = data[0]
        ret = read_value(data)

        if type(ret["faultCode"]) is not int:
            raise Exception()
        if type(ret["faultString"]) is not str:
            raise Exception()
        if len(ret) != 2:
            raise Exception()

        ret["type"] = True

    elif data.tag == "params":
        elem = data[0]
        if len(elem) != 1 or elem.tag != "param":
            raise Exception()

        ret["type"] = False
        ret["data"] = read_value(elem[0])
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
    params_list = []
    for param in params:
        if param.tag != "param" or len(param) != 1 or param[0].tag != "value":
            raise Exception()
        params_list.append(read_value(param[0]))

    return {
        "method": method,
        "params": params_list
    }


a = ET.tostring(ET.parse("prueba.xml").getroot())
readed = read_xmlrpc_response(a)
print(readed)
