import re

LOCATION_MAPPING = {
    # English -> Indonesian Mapping
    "west java": "jawa barat",
    "east java": "jawa timur",
    "central java": "jawa tengah",
    "north sumatra": "sumatera utara",
    "south sumatra": "sumatera selatan",
    "west sumatra": "sumatera barat",
    "south sulawesi": "sulawesi selatan",
    "north sulawesi": "sulawesi utara",
    "central sulawesi": "sulawesi tengah",
    "southeast sulawesi": "sulawesi tenggara",
    "west sulawesi": "sulawesi barat",
    "west kalimantan": "kalimantan barat",
    "east kalimantan": "kalimantan timur",
    "central kalimantan": "kalimantan tengah",
    "south kalimantan": "kalimantan selatan",
    "north kalimantan": "kalimantan utara",
    "dki jakarta": "jakarta",
    "jakarta raya": "jakarta",
    "java": "jawa",
    "sumatra": "sumatera",
    "sulawesi": "sulawesi",
    "kalimantan": "kalimantan",
    "bali": "bali",
    "papua": "papua",
    # Add more equivalents as needed
}

def normalize_location_name(name: str) -> str:
    """
    Normalizes a location name by:
    1. Lowercasing
    2. Stripping whitespace
    3. Translating known English terms to canonical Indonesian
    """
    if not name:
        return ""
    
    # Lowercase and strip spaces
    normalized = name.lower().strip()
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Exact mapping check
    if normalized in LOCATION_MAPPING:
        return LOCATION_MAPPING[normalized]
        
    return normalized
