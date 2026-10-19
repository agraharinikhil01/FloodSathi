"""
src/triage/fallback.py
----------------------
Offline, deterministic keyword and regex-based emergency triage parser.
Operates with zero network calls and zero API key requirements.
Accurately classifies Hindi, English, and Hinglish messages into structured TriageResult.
"""

from __future__ import annotations

import re

from backend.app.triage.models import TriageResult

# ── Keywords Lists ──────────────────────────────────────────────────────────
CRITICAL_KEYWORDS = {
    # Hindi Devanagari
    "गले तक",
    "छत पर",
    "छत तक",
    "डूब रहा",
    "डूब रहे",
    "मर रहे",
    "मर जाएंगे",
    "जान का खतरा",
    "सांप",
    "हार्ट अटैक",
    "ऑक्सीजन",
    "सांस लेने",
    # Hinglish & English
    "mar jayenge",
    "mar rahe",
    "dub raha",
    "doob raha",
    "chhat par",
    "chhat tak",
    "roof",
    "rooftop",
    "gale tak paani",
    "gale tak pani",
    "sinking",
    "drowning",
    "critical",
    "life threatening",
    "bleeding",
    "heart attack",
    "oxygen",
    "snake",
    "labor pain",
    "convulsions",
    "104 fever",
    "cut off by flood",
    "dialysis",
}

HIGH_KEYWORDS = {
    # Hindi Devanagari
    "फंसे",
    "फंसा",
    "बचाओ",
    "नाव",
    "बोट",
    "पानी बढ़ रहा",
    "घिरे",
    "घिरे हुए",
    "घायल",
    "रास्ता कट",
    "तुरंत",
    "तत्काल",
    # Hinglish & English
    "trapped",
    "fase",
    "fasa",
    "phasa",
    "phas gaye",
    "bachao",
    "rescue",
    "boat",
    "urgent",
    "emergency",
    "pani badh raha",
    "paani badh raha",
    "stranded",
    "surrounded",
    "evacuate",
    "evacuation",
    "injured",
    "injury",
    "bandage",
    "stretcher",
    "inundated",
}

FOOD_KEYWORDS = {
    # Hindi Devanagari
    "खाना",
    "राशन",
    "भूखे",
    "पीने का पानी",
    "भोजन",
    "बिस्कुट",
    # Hinglish & English
    "khana",
    "food",
    "ration",
    "bhookhe",
    "bhukhe",
    "drinking water",
    "peene ka pani",
    "peene ka paani",
    "water bottles",
    "milk powder",
    "biscuit",
    "biscuits",
    "rice packets",
}

MEDICAL_KEYWORDS = {
    # Hindi Devanagari
    "डॉक्टर",
    "दवाई",
    "अस्पताल",
    "एंबुलेंस",
    "ओआरएस",
    "बीमार",
    "बुखार",
    "डायरिया",
    "उल्टी",
    "सांप",
    "गर्भवती",
    "सांस",
    "इंजेक्शन",
    "टिटनेस",
    # Hinglish & English
    "doctor",
    "dawai",
    "medicine",
    "medicines",
    "hospital",
    "ambulance",
    "sick",
    "bimar",
    "fever",
    "pregnant",
    "garbhvati",
    "delivery",
    "injured",
    "injury",
    "wound",
    "heart attack",
    "bleeding",
    "snake",
    "oxygen",
    "convulsions",
    "labor pain",
    "dialysis",
    "insulin",
    "diabetic",
    "first aid",
    "diarrhea",
    "vomit",
    "tetanus",
}

SHELTER_KEYWORDS = {
    # Hindi Devanagari
    "शेल्टर",
    "आश्रय",
    "तंबू",
    "तिरपाल",
    "कच्चा घर",
    "घर ढह",
    "खुले आसमान",
    "टेंट",
    # Hinglish & English
    "shelter",
    "ashray",
    "ghar doob gaya",
    "ghar tut gaya",
    "kacha ghar",
    "tent",
    "tarpaulin",
    "blanket",
    "blankets",
    "homeless",
    "stay",
    "accommodation",
    "submerged",
}

LOW_KEYWORDS = {
    # Hindi Devanagari
    "क्या आज",
    "अनुमान",
    "जानकारी",
    "किस समय",
    "वितरण",
    # Hinglish & English
    "confirm whether",
    "open tomorrow",
    "power department",
    "electricity pole",
    "helpline number",
    "want to know",
    "inquiry",
}

KNOWN_LOCATIONS: dict[str, str] = {
    # Devanagari -> English
    "भूरगांव": "Bhuragaon",
    "मयोंग": "Mayong",
    "लहरिघाट": "Laharighat",
    "मोरीगांव": "Morigaon",
    "जगीरोड": "Jagiroad",
    "धरमतुल": "Dharamtul",
    "धमधा": "Dhamdha",
    "दानापुर": "Danapur",
    "बोरबोरी": "Borbori",
    "कटिहार": "Katihar",
    "पटना": "Patna",
    "सिलचर": "Silchar",
    "धेमाजी": "Dhemaji",
    "मुजफ्फरपुर": "Muzaffarpur",
    "दरभंगा": "Darbhanga",
    "सीतामढ़ी": "Sitamarhi",
    "गुवाहाटी": "Guwahati",
    "धुबरी": "Dhubri",
    "बारपेटा": "Barpeta",
    "लखीमपुर": "Lakhimpur",
    "गोलपारा": "Goalpara",
    "अलपुझा": "Alappuzha",
    "एर्नाकुलम": "Ernakulam",
    # English names
    "bhuragaon": "Bhuragaon",
    "mayong": "Mayong",
    "laharighat": "Laharighat",
    "morigaon": "Morigaon",
    "jagiroad": "Jagiroad",
    "dharamtul": "Dharamtul",
    "dhamdha": "Dhamdha",
    "danapur": "Danapur",
    "borbori": "Borbori",
    "koliabor": "Koliabor",
    "katihar": "Katihar",
    "patna": "Patna",
    "silchar": "Silchar",
    "dhemaji": "Dhemaji",
    "muzaffarpur": "Muzaffarpur",
    "ghogamukh": "Ghogamukh",
    "chhatarpur": "Chhatarpur",
    "alappuzha": "Alappuzha",
    "ernakulam": "Ernakulam",
    "nagaon": "Nagaon",
    "cachar": "Cachar",
    "guwahati": "Guwahati",
    "dhubri": "Dhubri",
    "barpeta": "Barpeta",
    "lakhimpur": "Lakhimpur",
    "goalpara": "Goalpara",
    "darbhanga": "Darbhanga",
    "sitamarhi": "Sitamarhi",
    "highway": "Highway",
}


def detect_language(text: str) -> str:
    """Identify if text is Devanagari Hindi, Romanized Hinglish, or English."""
    devanagari_chars = sum(1 for c in text if "\u0900" <= c <= "\u097f")
    if devanagari_chars >= 3:
        return "hi"

    hinglish_markers = {
        "hai",
        "hain",
        "ke",
        "ki",
        "ka",
        "ko",
        "me",
        "mein",
        "paani",
        "pani",
        "bachao",
        "bhaiya",
        "madad",
        "chahiye",
        "ghar",
        "log",
        "kripya",
        "rahe",
        "fase",
        "phas",
        "doob",
        "par",
        "chhat",
        "khana",
    }
    words = {w.lower().strip(".,!?") for w in text.split()}
    if words.intersection(hinglish_markers):
        return "hinglish"

    return "en"


def extract_people_count(text: str) -> int:
    """Extract number of individuals affected from textual patterns."""
    text_lower = text.lower()

    # Pattern: Digit followed by people indicator or stand-alone count
    m = re.search(
        r"(\d+)\s*(?:log|people|members|persons|jan|aadmi|bachche|bache|villagers|patients|families|परिवार|लोग|बच्चे|मरीज|घायल|मजदूर)?",
        text_lower,
    )
    if m and m.group(1):
        val = int(m.group(1))
        if "family" in text_lower or "परिवार" in text_lower or "families" in text_lower:
            val = max(val * 4, val)
        return min(max(val, 1), 500)

    word_map = {
        "one": 1,
        "ek": 1,
        "एक": 1,
        "two": 2,
        "do": 2,
        "दो": 2,
        "three": 3,
        "teen": 3,
        "तीन": 3,
        "four": 4,
        "chaar": 4,
        "चार": 4,
        "five": 5,
        "paanch": 5,
        "पांच": 5,
        "six": 6,
        "che": 6,
        "छह": 6,
        "family": 4,
        "parivar": 4,
        "परिवार": 4,
    }
    for word, count in word_map.items():
        if word in text_lower:
            return count

    return 1


def extract_vulnerable_groups(text: str) -> list[str]:
    """Identify vulnerable demographics mentioned in the plea."""
    text_lower = text.lower()
    groups: list[str] = []

    if any(
        w in text_lower
        for w in (
            "elderly",
            "old",
            "budhe",
            "bujurg",
            "daadi",
            "daada",
            "senior",
            "बुजुर्ग",
            "बूढ़े",
            "वृद्ध",
            "दादा",
            "दादी",
        )
    ):
        groups.append("elderly")
    if any(
        w in text_lower
        for w in (
            "child",
            "children",
            "baby",
            "infant",
            "bache",
            "bacche",
            "kid",
            "kids",
            "बच्चे",
            "बच्चा",
            "शिशु",
        )
    ):
        groups.append("children")
    if any(
        w in text_lower
        for w in ("pregnant", "garbhvati", "expecting", "maternity", "delivery", "गर्भवती")
    ):
        groups.append("pregnant")
    if any(
        w in text_lower
        for w in (
            "disabled",
            "handicapped",
            "wheelchair",
            "divyang",
            "paralyzed",
            "दिव्यांग",
            "विकलांग",
        )
    ):
        groups.append("disabled")

    return sorted(list(set(groups)))


def extract_location(text: str, fallback_district: str = "Morigaon") -> str:
    """Extract geographical location, village, or district from message."""
    text_lower = text.lower()

    # Direct dictionary check for known locations in English or Devanagari
    for key, standard_name in KNOWN_LOCATIONS.items():
        if key in text_lower or key in text:
            return standard_name

    # Regex search for prepositional patterns (in / near / mein)
    m = re.search(r"(?:in|at|near|mein|me|paas|ke paas)\s+([A-Z][a-zA-Z\s]{2,20})", text)
    if m:
        cand = m.group(1).strip()
        if len(cand) >= 3 and cand.lower() not in ("water", "flood", "danger", "trouble", "home"):
            return cand

    return fallback_district


def extract_urgency(text: str) -> tuple[str, int]:
    """Classify emergency urgency and map to 1-5 score."""
    text_lower = text.lower()

    # Check for low-urgency inquiries first if no high/critical distress words
    is_low_inquiry = any(k in text_lower for k in LOW_KEYWORDS)
    has_critical = any(k in text_lower for k in CRITICAL_KEYWORDS)
    has_high = any(k in text_lower for k in HIGH_KEYWORDS)

    if is_low_inquiry and not (has_critical or has_high):
        return "low", 2

    if has_critical:
        return "critical", 5
    if has_high:
        return "high", 4

    # Medical emergencies with pregnant or disabled individuals or high medical keywords
    has_medical = any(k in text_lower for k in MEDICAL_KEYWORDS)
    vulnerable_groups = extract_vulnerable_groups(text)
    if has_medical and ("pregnant" in vulnerable_groups or "disabled" in vulnerable_groups):
        return "high", 4
    if has_medical:
        return "high", 4

    if any(k in text_lower for k in FOOD_KEYWORDS) or any(
        k in text_lower for k in SHELTER_KEYWORDS
    ):
        return "medium", 3

    return "medium", 3


def extract_need(text: str) -> str:
    """Determine primary emergency category."""
    text_lower = text.lower()

    if any(k in text_lower for k in LOW_KEYWORDS) and not any(
        k in text_lower for k in (CRITICAL_KEYWORDS | HIGH_KEYWORDS)
    ):
        return "other"

    if any(k in text_lower for k in MEDICAL_KEYWORDS):
        return "medical"
    if any(k in text_lower for k in HIGH_KEYWORDS) or any(
        k in text_lower for k in CRITICAL_KEYWORDS
    ):
        return "rescue"
    if any(k in text_lower for k in FOOD_KEYWORDS):
        return "food"
    if any(k in text_lower for k in SHELTER_KEYWORDS):
        return "shelter"

    return "rescue"


def fallback_triage(raw_text: str, fallback_district: str = "Morigaon") -> TriageResult:
    """Deterministic extractor parsing text when LLM is unavailable."""
    lang = detect_language(raw_text)
    urgency, urgency_score = extract_urgency(raw_text)
    need = extract_need(raw_text)
    people_count = extract_people_count(raw_text)
    vulnerable = extract_vulnerable_groups(raw_text)
    location_text = extract_location(raw_text, fallback_district=fallback_district)

    summary_en = f"{people_count} person(s) in {location_text} need urgent {need} assistance."
    if vulnerable:
        summary_en += f" Includes: {', '.join(vulnerable)}."

    summary_hi = f"{location_text} में {people_count} लोगों को {need} की तत्काल आवश्यकता है।"
    if vulnerable:
        summary_hi += f" प्रभावित: {', '.join(vulnerable)}।"

    return TriageResult(
        location_text=location_text,
        urgency=urgency,
        urgency_score=urgency_score,
        need=need,
        people_count=people_count,
        vulnerable=vulnerable,
        summary=summary_en,
        summary_hi=summary_hi,
        language=lang,
    )
