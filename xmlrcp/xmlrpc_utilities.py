import xml.etree.ElementTree as ET
from xmlrpc.client import dumps


# funcion que retorna un xml rpc el resultado de una operacion.
def get_xml_rpc_response(result):
    ret = "<methodResponse>" + dumps((result,)) + "</methodResponse>"
    return ET.tostring(ret, encoding="utf-8", xml_declaration=True),


# funcion que retorna un xml rpc erroneo con el codigo y mensaje
# de error correspondiente.
def get_xml_rpc_error(code):
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
