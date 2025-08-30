import xml.etree.ElementTree as ET
from datetime import datetime
import base64


# -------------------
# |     Escritura   |
# |       de        |
# |     Mensajes    |
# -------------------


# Retorna un string que representa un valor en formato XMLRCP.
# returna una etiqueta 'value'.
def write_value(info):
    if type(info) is str:
        ret = "<string>" + info + "</string>"
    elif type(info) is int:
        ret = "<int>" + str(info) + "</int>"
    elif type(info) is bool:
        ret = "<boolean>" + str(info).lower() + "</boolean>"
    elif type(info) is float:
        ret = "<double>" + str(info) + "</double>"
    elif type(info) is datetime:
        ret = "<dateTime.iso8601>" + info.isoformat() + "</dateTime.iso8601>"
    elif type(info) is bytes:
        ret = "<base64>" + info.decode() + "</base64>"
    elif type(info) is dict:
        ret = "<struct>"
        for key in info:
            ret += "<member><name>" + key + "</name>"
            ret += write_value(info[key])
            ret += "</member>"
        ret += "</struct>"
    elif type(info) in [list, tuple]:
        ret = ""
        for key in info:
            ret += write_value(info[key])
        ret = "<array><data>" + ret + "</data></array>"
    else:
        raise Exception()
    return "<value>" + ret + "</value>"


# funcion que retorna un XMLRPC que representa una consulta de
# una operacion.
def write_xmlrpc_request(params, method):
    ret = '<?xml version="1.0"?><methodCall>'
    ret += '<methodName>' + method + '</methodName>'
    ret += '<params>'
    for param in params:
        ret += '<param>' + write_value(param) + '</param>'
    ret += '</params>'
    ret += '</methodCall>'
    return ret.encode()


# funcion que retorna un XMLRPC con el resultado de una operacion.
def write_xmlrpc_response(result):
    ret = "<?xml version='1.0'?><methodResponse>"
    ret += '<params><param>' + write_value(result) + '</param></params>'
    ret += "</methodResponse>"
    return ret.encode()


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


# -------------------
# |     Lectura     |
# |       de        |
# |     Mensajes    |
# -------------------


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


# lee mensaje XMLRPC response y retorna los datos y tipo de mensaje, donde
# False representa un response correcto y True representa un falut.
def read_xmlrpc_response(data):
    data = ET.fromstring(data)
    if len(data) != 1 or data.tag != "methodResponse":
        raise Exception()

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


# lee mensaje XMLRPC request y retorna los el nombre del
# metodo y una lista con los parametros de ejecucion.
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
