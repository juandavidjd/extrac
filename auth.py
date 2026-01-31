VALID_API_KEYS = {
    "ADSI-LOCAL-KEY-001",
    "SRM-QK-APP-KEY",
    "CATRMU-NODE-KEY"
}

def validate_api_key(key: str):
    if key not in VALID_API_KEYS:
        raise Exception("API Key inválida o no autorizada")
