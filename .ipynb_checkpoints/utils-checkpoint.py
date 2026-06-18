
import re

def extract_metadata(text):
    pattern = r"<(.*?)>(.*?)</\1>"
    matches = re.findall(pattern, text)

    metadata = {}

    for field, value in matches:
        metadata.setdefault(field, []).append(value)

    return metadata
