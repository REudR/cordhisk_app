from services.types import MetadataType

METADATA_FIELDS = {
    "CHO": {
        "type": MetadataType.CHO,
        "fields": {
            "dc:contributor": {"label": "Contributor"},
            "dc:coverage": {"label": "Coverage"},
            "dc:creator": {"label": "Creator"},
            "dc:date": {"label": "Date"},
            "dc:description": {"label": "Description"},
            "dc:format": {"label": "Format"},
            "dc:language": {"label": "Language"},
            "dc:publisher": {"label": "Publisher"},
            "dc:source": {"label": "Source"},
            "dc:subject": {"label": "Subject"},
            "dc:title": {"label": "Title"},
            "dc:type": {"label": "Type"},
            "dcterms:created": {"label": "Created"},
            "dcterms:extent": {"label": "Extent"},
            "dcterms:issued": {"label": "Issued"},
            "dcterms:medium": {"label": "Medium"},
            "dcterms:provenance": {"label": "Provenance"},
            "dcterms:spatial": {"label": "Spatial"},
            "dcterms:tableOfContents": {"label": "Table Of Contents"},
            "dcterms:temporal": {"label": "Temporal"}
        }
    },

    "Agent": {
        "type": MetadataType.CHO,
        "fields": {
            "oaf:name": {"label": "Name"},
            "rdaGr2:biographicalInformation": {"label": "Biography"},
            "rdaGr2:dateOfBirth": {"label": "Date Of Birth"},
            "rdaGr2:dateOfDeath": {"label": "Date Of Death"},
            "rdaGr2:dateOfEstablishment": {"label": "Establishment Date"},
            "rdaGr2:dateOfTermination": {"label": "Termination Date"},
            "rdaGr2:gender": {"label": "Gender"},
            "rdaGr2:placeOfBirth": {"label": "Place Of Birth"},
            "rdaGr2:placeOfDeath": {"label": "Place Of Death"},
            "rdaGr2:professionOrOccupation": {"label": "Profession"}
        }
    },

    "WebResource": {
        "type": MetadataType.MEMORY,
        "fields": {
            "web:dc:creator": {"label": "Creator"},
            "web:dc:description": {"label": "Description"},
            "web:dc:source": {"label": "Source"},
            "web:dcterms:created": {"label": "Created"}
        }
    }
}