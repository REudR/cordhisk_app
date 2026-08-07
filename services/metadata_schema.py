from services.types import MetadataType

METADATA_FIELDS = {
    "CHO": {
        "type": MetadataType.CHO,
        "fields": {
            "dc:contributor": {"label": "Contributor", "description": "An entity responsible for making contributions to the resource."},
            "dc:coverage": {"label": "Coverage", "description": "The spatial or temporal topic of the resource, the spatial applicability of the resource, or the jurisdiction under which the resource is relevant."},
            "dc:creator": {"label": "Creator", "description": "An entity primarily responsible for making the resource."},
            "dc:date": {"label": "Date", "description": "A point or period in time associated with an event in the lifecycle of the resource."},
            "dc:description": {"label": "Description", "description": "An account of the resource."},
            "dc:format": {"label": "Format", "description": "The file format, physical medium, or dimensions of the resource."},
            "dc:language": {"label": "Language", "description": "A language of the resource."},
            "dc:publisher": {"label": "Publisher", "description": "An entity responsible for making the resource available."},
            "dc:source": {"label": "Source", "description": "A related resource from which the described resource is derived."},
            "dc:subject": {"label": "Subject", "description": "The topic of the resource."},
            "dc:title": {"label": "Title", "description": "The name given to the resource."},
            "dc:type": {"label": "Type", "description": "The nature or genre of the resource."},
            "dcterms:created": {"label": "Created", "description": "Date of creation of the resource."},
            "dcterms:extent": {"label": "Extent", "description": "The size or duration of the resource."},
            "dcterms:issued": {"label": "Issued", "description": "Date of formal issuance of the resource."},
            "dcterms:medium": {"label": "Medium", "description": "The material or physical carrier of the resource."},
            "dcterms:provenance": {"label": "Provenance", "description": "A statement of any changes in ownership and custody of the resource since its creation."},
            "dcterms:spatial": {"label": "Spatial", "description": "Spatial characteristics of the resource."},
            "dcterms:tableOfContents": {"label": "Table Of Contents", "description": "A list of subresources or chapters that make up the resource."},
            "dcterms:temporal": {"label": "Temporal", "description": "Temporal characteristics of the resource."}
        }
    },

    "Agent": {
        "type": MetadataType.CHO,
        "fields": {
            "oaf:name": {"label": "Name", "description": "Preferred name of the person or organization."},
            "rdaGr2:biographicalInformation": {"label": "Biography", "description": "Short biographical note about the agent."},
            "rdaGr2:dateOfBirth": {"label": "Date Of Birth", "description": "Date when the person was born."},
            "rdaGr2:dateOfDeath": {"label": "Date Of Death", "description": "Date when the person died."},
            "rdaGr2:dateOfEstablishment": {"label": "Establishment Date", "description": "Date when the organization was established."},
            "rdaGr2:dateOfTermination": {"label": "Termination Date", "description": "Date when the organization ended or dissolved."},
            "rdaGr2:gender": {"label": "Gender", "description": "Gender or gender identity associated with the agent."},
            "rdaGr2:placeOfBirth": {"label": "Place Of Birth", "description": "Place where the person was born."},
            "rdaGr2:placeOfDeath": {"label": "Place Of Death", "description": "Place where the person died."},
            "rdaGr2:professionOrOccupation": {"label": "Profession", "description": "Main profession or occupation of the person."}
        }
    },

    "WebResource": {
        "type": MetadataType.MEMORY,
        "fields": {
            "dc:identifier": {"label": "Identifier", "description": "Stable identifier for the memory."},
            "dc:license": {"label": "License", "description": "Usage license selected for the memory."},
            "web:dc:creator": {"label": "Creator", "description": "Person or group that created the web resource."},
            "web:dc:description": {"label": "Description", "description": "Summary or notes about the web resource."},
            "web:dc:source": {"label": "Source", "description": "Source that the web resource came from."},
            "web:dcterms:created": {"label": "Created", "description": "Date the web resource was created."}
        }
    }
}