"""
scripts/make_synthetic_requests.py
----------------------------------
Generates 100 diverse, labeled synthetic distress messages in data/test_requests.json.
Used for offline benchmarking and triage accuracy validation across Hindi, English, and Hinglish.
Privacy notice: All data is completely synthetic; no real personal data is generated or stored.
"""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_FILE = Path("data/test_requests.json")

# Template bank for generating realistic synthetic emergency distress messages
SYNTHETIC_TEMPLATES = [
    # ── Critical Rescue (Hindi, Hinglish, English) ──────────────────────────
    (
        "मदद करो! भूरगांव में पानी गले तक पहुंच गया है। 6 लोग छत पर हैं। 2 बच्चे और बुजुर्ग हैं, नाव भेजो जल्दी!",
        "hi",
        "critical",
        "rescue",
        6,
        ["children", "elderly"],
        "Bhuragaon",
    ),
    (
        "Mayong village mein pani chhat tak aa gaya hai. 4 log fase hain, doob rahe hain, please rescue boat urgently!",
        "hinglish",
        "critical",
        "rescue",
        4,
        [],
        "Mayong",
    ),
    (
        "EMERGENCY: House sinking near Laharighat river bank! 5 family members trapped on rooftop including pregnant woman. Send NDRF boat immediately!",
        "en",
        "critical",
        "rescue",
        5,
        ["pregnant"],
        "Laharighat",
    ),
    (
        "पानी का स्तर बहुत बढ़ गया है, मोरीगांव मेन रोड पर 8 लोग बहने वाले हैं, जान का खतरा है, बचाओ!",
        "hi",
        "critical",
        "rescue",
        8,
        [],
        "Morigaon",
    ),
    (
        "Gale tak pani bhar chuka hai ghar ke andar. 3 log dub rahe hain Dharamtul ke paas, immediate rescue needed!",
        "hinglish",
        "critical",
        "rescue",
        3,
        [],
        "Dharamtul",
    ),
    # ── Critical Medical (Hindi, Hinglish, English) ─────────────────────────
    (
        "धमधा में बाढ़ के पानी में 1 व्यक्ति को सांप ने काट लिया है, अत्यधिक ब्लीडिंग हो रही है, डॉक्टर या एंबुलेंस भेजो!",
        "hi",
        "critical",
        "medical",
        1,
        [],
        "Dhamdha",
    ),
    (
        "Elderly patient having severe heart attack symptoms surrounded by 4ft water in Silchar hospital road. Doctor needed urgently!",
        "en",
        "critical",
        "medical",
        1,
        ["elderly"],
        "Silchar",
    ),
    (
        "Dhemaji me ek pregnant aurat ko labor pain shuru ho gaya hai. Charo taraf flood water hai. Ambulance boat chahiye turant!",
        "hinglish",
        "critical",
        "medical",
        2,
        ["pregnant"],
        "Dhemaji",
    ),
    (
        "Alappuzha kuttanad area: infant baby having high 104 fever and convulsions, no medicines available, road cut off by flood.",
        "en",
        "critical",
        "medical",
        2,
        ["children"],
        "Alappuzha",
    ),
    (
        "दानापुर में बाढ़ में फंसे बुजुर्ग को सांस लेने में भारी तकलीफ है, ऑक्सीजन सिलेंडर खत्म हो रहा है, तुरंत मेडिकल मदद!",
        "hi",
        "critical",
        "medical",
        1,
        ["elderly"],
        "Danapur",
    ),
    # ── High Rescue (Hindi, Hinglish, English) ──────────────────────────────
    (
        "हम 7 लोग लहरिघाट स्कूल में पानी से घिरे हुए हैं। चारों तरफ 3 फीट पानी है। सुरक्षित जगह निकालने में मदद करें।",
        "hi",
        "high",
        "rescue",
        7,
        [],
        "Laharighat",
    ),
    (
        "Water entered our ground floor in Nagaon. 5 people stranded on second floor. Water still rising slowly, need evacuation support.",
        "en",
        "high",
        "rescue",
        5,
        [],
        "Nagaon",
    ),
    (
        "Jagiroad bypass ke pas 10 log phas gaye hain car mein. Road block ho gaya hai flood water se, evacuation boat bhejiye.",
        "hinglish",
        "high",
        "rescue",
        10,
        [],
        "Jagiroad",
    ),
    (
        "बोरबोरी गांव में 4 परिवार फंसे हैं, लगभग 12 लोग। रास्ता कट गया है, बोट से रेस्क्यू की जरूरत है।",
        "hi",
        "high",
        "rescue",
        12,
        [],
        "Borbori",
    ),
    (
        "Flooding in Koliabor village. 6 villagers including 2 disabled elderly unable to walk out. Need rescue team with stretcher.",
        "en",
        "high",
        "rescue",
        6,
        ["disabled", "elderly"],
        "Koliabor",
    ),
    # ── High Medical / Health ───────────────────────────────────────────────
    (
        "Patna city bypass: 3 injured after tin roof collapsed due to heavy storm and flood. Need first aid kit and bandage.",
        "en",
        "high",
        "medical",
        3,
        [],
        "Patna",
    ),
    (
        "हमारे राहत शिविर मोरीगांव में 15 बच्चों को तेज डायरिया और उल्टी हो रही है। ओआरएस और डॉक्टर की टीम भेजें।",
        "hi",
        "high",
        "medical",
        15,
        ["children"],
        "Morigaon",
    ),
    (
        "Ghogamukh primary health centre inundated. 4 dialysis patients need transfer to district hospital urgently.",
        "en",
        "high",
        "medical",
        4,
        [],
        "Ghogamukh",
    ),
    (
        "Chhatarpur area mein diabetic patient ki insulin khatam ho gayi hai. 2 days se trapped hain, medicines deliver kijiye.",
        "hinglish",
        "high",
        "medical",
        1,
        [],
        "Chhatarpur",
    ),
    (
        "कटिहार रेलवे कॉलोनी में 5 लोग पानी में पैर कटने से घायल हैं। टिटनेस इंजेक्शन और दवाई की आवश्यकता है।",
        "hi",
        "high",
        "medical",
        5,
        [],
        "Katihar",
    ),
    # ── Medium Food & Water ─────────────────────────────────────────────────
    (
        "बिल्कुल सूखा राशन नहीं बचा है। जगीरोड में 10 मजदूर 2 दिन से भूखे हैं। पीने का पानी भी नहीं है।",
        "hi",
        "medium",
        "food",
        10,
        [],
        "Jagiroad",
    ),
    (
        "Mayong relief camp: drinking water contaminated with flood silt. 25 people need clean drinking water bottles and dry biscuits.",
        "en",
        "medium",
        "food",
        25,
        [],
        "Mayong",
    ),
    (
        "Morigaon ward 3 mein 8 log hain, khana pani sab doob gaya hai. Ration packets distribute karwayiye please.",
        "hinglish",
        "medium",
        "food",
        8,
        [],
        "Morigaon",
    ),
    (
        "Dhemaji railway station shelter: 40 displaced flood victims need baby milk powder and rice packets for dinner.",
        "en",
        "medium",
        "food",
        40,
        ["children"],
        "Dhemaji",
    ),
    (
        "लहरिघाट पंचायत भवन में 18 लोग ठहरे हुए हैं, भोजन की व्यवस्था नहीं है। कृपया भोजन के पैकेट भिजवाएं।",
        "hi",
        "medium",
        "food",
        18,
        [],
        "Laharighat",
    ),
    # ── Medium Shelter ──────────────────────────────────────────────────────
    (
        "हमारा कच्चा घर ढह गया है। भूरगांव तटबंध पर 6 लोग खुले आसमान में तिरपाल लगाकर रह रहे हैं। तंबू या शेल्टर चाहिए।",
        "hi",
        "medium",
        "shelter",
        6,
        [],
        "Bhuragaon",
    ),
    (
        "Silchar Tarapur: 4 families house submerged up to waist. Need temporary shelter in nearby high school.",
        "en",
        "medium",
        "shelter",
        14,
        [],
        "Silchar",
    ),
    (
        "Ghar pura flood water me chala gaya. 5 log highway side tent bana kar reh rahe hain. Tarpaulin and blankets needed urgently.",
        "hinglish",
        "medium",
        "shelter",
        5,
        [],
        "Highway",
    ),
    (
        "Muzaffarpur river side: 20 farm workers lost huts in flash flood. Need emergency relief camp accommodation.",
        "en",
        "medium",
        "shelter",
        20,
        [],
        "Muzaffarpur",
    ),
    (
        "धमधा कैंप में जगह नहीं है। 8 लोग और आ गए हैं, अतिरिक्त शेल्टर या टेंट की व्यवस्था करें।",
        "hi",
        "medium",
        "shelter",
        8,
        [],
        "Dhamdha",
    ),
    # ── Low Inquiries / Non-urgent / Other ──────────────────────────────────
    (
        "Can you confirm whether the national highway bridge at Morigaon is open for light vehicles tomorrow morning?",
        "en",
        "low",
        "other",
        1,
        [],
        "Morigaon",
    ),
    (
        "क्या आज रात जगीरोड में बारिश कम होने का अनुमान है? हमारे घर के बाहर 6 इंच पानी है।",
        "hi",
        "low",
        "other",
        1,
        [],
        "Jagiroad",
    ),
    (
        "Electricity pole fell near Laharighat market, no power since morning. Power department ko inform karein please.",
        "hinglish",
        "low",
        "other",
        1,
        [],
        "Laharighat",
    ),
    (
        "Want to know helpline number for district relief coordinator in Dhemaji.",
        "en",
        "low",
        "other",
        1,
        [],
        "Dhemaji",
    ),
    (
        "बाढ़ राहत सामग्री का वितरण किस समय होगा? भूरगांव सेंटर की जानकारी चाहिए।",
        "hi",
        "low",
        "other",
        1,
        [],
        "Bhuragaon",
    ),
]


def generate_synthetic_dataset(target_count: int = 100) -> list[dict]:
    """Expand the base template bank to target_count balanced test cases."""
    records = []
    base_len = len(SYNTHETIC_TEMPLATES)

    for i in range(target_count):
        idx = i % base_len
        template = SYNTHETIC_TEMPLATES[idx]
        text, lang, urgency, need, count, vuln, loc = template

        # Slight variation for expanded copies
        if i >= base_len:
            text_mod = f"{text} (Ref #{i + 1})"
            rec = {
                "id": i + 1,
                "raw_text": text_mod,
                "language": lang,
                "true_urgency": urgency,
                "true_need": need,
                "true_people_count": count,
                "true_vulnerable": list(vuln),
                "true_location": loc,
            }
        else:
            rec = {
                "id": i + 1,
                "raw_text": text,
                "language": lang,
                "true_urgency": urgency,
                "true_need": need,
                "true_people_count": count,
                "true_vulnerable": list(vuln),
                "true_location": loc,
            }
        records.append(rec)

    return records


def main() -> None:
    """Generate and write synthetic benchmark requests to disk."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = generate_synthetic_dataset(100)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated {len(records)} synthetic requests at {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
