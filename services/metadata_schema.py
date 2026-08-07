from services.types import MetadataType

METADATA_FIELDS = {
    "CHO": {
        "type": MetadataType.CHO,
        "fields": {
            "dc:contributor": {"label": "Contributor", "description": "Person or group that helped create the resource."},
            "dc:coverage": {"label": "Coverage", "description": "Topic, place, or time period covered by the resource."},
            "dc:creator": {"label": "Creator", "description": "Main creator or author of the resource."},
            "dc:date": {"label": "Date", "description": "Date associated with the resource."},
            "dc:description": {"label": "Description", "description": "Short summary or note describing the resource."},
            "dc:format": {"label": "Format", "description": "File or presentation format of the resource."},
            "dc:language": {"label": "Language", "description": "Language used in the resource."},
            "dc:publisher": {"label": "Publisher", "description": "Entity that published or issued the resource."},
            "dc:source": {"label": "Source", "description": "Origin or reference source for the resource."},
            "dc:subject": {"label": "Subject", "description": "Main topic or theme represented by the resource."},
            "dc:title": {"label": "Title", "description": "Primary name or title of the resource."},
            "dc:type": {"label": "Type", "description": "General category or nature of the resource."},
            "dcterms:created": {"label": "Created", "description": "Creation date of the resource or artifact."},
            "dcterms:extent": {"label": "Extent", "description": "Size, length, or scope of the resource."},
            "dcterms:issued": {"label": "Issued", "description": "Date the resource was issued or made available."},
            "dcterms:medium": {"label": "Medium", "description": "Material or carrier used for the resource."},
            "dcterms:provenance": {"label": "Provenance", "description": "History of ownership or custody."},
            "dcterms:spatial": {"label": "Spatial", "description": "Place or geographic context linked to the resource."},
            "dcterms:tableOfContents": {"label": "Table Of Contents", "description": "Structured contents or section list for the resource."},
            "dcterms:temporal": {"label": "Temporal", "description": "Time period or date range relevant to the resource."}
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