import xml.etree.ElementTree as ET
from utils import MetadataType
from services.metadata import extract_metadata

def export_cho_rdf(cho):
    """Export CHO-linked metadata as RDF/XML"""
    if not cho:
        return ""
    
    root = ET.Element("rdf:RDF")
    root.set("xmlns:rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    root.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")
    root.set("xmlns:dcterms", "http://purl.org/dc/terms/")
    root.set("xmlns:oaf", "http://www.openarchives.org/OAI/2.0/oai_dc/")
    root.set("xmlns:rdaGr2", "http://RDVocab.info/GRupElmComps/")
    
    desc = ET.SubElement(root, "rdf:Description")
    desc.set("rdf:about", f"http://example.org/cho/{cho.custom_id}")
    
    # Add CHO properties
    ET.SubElement(desc, "rdf:type").text = "CHO"
    ET.SubElement(desc, "dc:identifier").text = cho.custom_id
    ET.SubElement(desc, "dc:title").text = cho.title
    
    return ET.tostring(root, encoding="unicode")

def export_memory_rdf(memory):
    """Export memory with both intrinsic and CHO-linked metadata"""
    if not memory:
        return ""
    
    root = ET.Element("rdf:RDF")
    root.set("xmlns:rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    root.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")
    root.set("xmlns:dcterms", "http://purl.org/dc/terms/")
    root.set("xmlns:web", "http://example.org/web/")
    root.set("xmlns:oaf", "http://www.openarchives.org/OAI/2.0/oai_dc/")
    root.set("xmlns:rdaGr2", "http://RDVocab.info/GRupElmComps/")
    
    desc = ET.SubElement(root, "rdf:Description")
    desc.set("rdf:about", f"http://example.org/memory/{memory.custom_id}")
    
    # Add memory properties
    ET.SubElement(desc, "rdf:type").text = "Memory"
    ET.SubElement(desc, "dc:identifier").text = memory.custom_id
    ET.SubElement(desc, "dc:title").text = memory.title
    
    # Add metadata
    metadata = extract_metadata(memory.text)
    
    # Memory-intrinsic metadata
    for md in metadata:
        if md.get("type") == MetadataType.MEMORY.value:
            tag = md["field"].replace(":", "_")
            ET.SubElement(desc, tag).text = md["value"]
    
    # CHO-linked metadata (as references)
    cho_refs = set()
    for md in metadata:
        if md.get("type") == MetadataType.CHO.value:
            cho_refs.add(md.get("cho"))
    
    for cho_id in cho_refs:
        ref = ET.SubElement(desc, "dc:relation")
        ref.text = f"http://example.org/cho/{cho_id}"
    
    return ET.tostring(root, encoding="unicode")
