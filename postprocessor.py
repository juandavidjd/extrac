import re

class PostProcessor:

    def __init__(self):
        pass

    def extract_codigos(self, text):
        codes = re.findall(r"\b\d{3,6}\b", text)
        return list(set(codes))

    def extract_precio(self, text):
        text = text.replace(".", "").replace(",", "")
        matches = re.findall(r"\$?\s?(\d{3,7})", text)
        return matches[0] if matches else None

    def extract_empaque(self, text):
        match = re.search(r"(X\s?\d+)", text.upper())
        return match.group(1) if match else None

    def clean_description(self, text):
        return text.strip().title()
