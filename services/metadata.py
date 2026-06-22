import re
import xml.etree.ElementTree as ET
from utils import RE_METADATA

def extract_metadata(text):
    return [
        {"field": f, "cho": c, "value": v}
        for f, c, v in RE_METADATA.findall(text or "")
    ]

def get_memory_title(text, fallback):
    match = re.search(r"<dc[:_]title>(.*?)</dc[:_]title>", text or "")
    return match.group(1) if match else fallback

def build_rdf_block(metadata):
    if not metadata:
        return ""

    root = ET.Element("rdf:RDF")
    desc = ET.SubElement(root, "rdf:Description")

    for field, value in metadata.items():
        tag = field.replace(":", "_")
        ET.SubElement(desc, tag).text = value

    return ET.tostring(root, encoding="unicode") + "\n\n"