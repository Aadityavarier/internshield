"""
InternShield — Named Entity Recognition (NER) Extractor

Uses spaCy to extract key entities from offer letters and verify them.
"""

import re
from typing import Tuple

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        SPACY_AVAILABLE = False
        nlp = None
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None


def extract_and_verify(text: str) -> Tuple[float, list[dict], dict]:
    """
    Extract named entities and perform verification checks.
    Returns (verification_score, flags, extracted_entities).

    verification_score: 0.0 = many red flags, 1.0 = entities verified.
    """
    entities = {
        "company_name": None,
        "person_names": [],
        "dates": [],
        "locations": [],
        "amounts": [],
        "emails": [],
        "phones": [],
    }

    flags = []
    score_components = []

    # Extract with spaCy if available
    if SPACY_AVAILABLE and nlp:
        entities = _extract_with_spacy(text, entities)
    else:
        entities = _extract_with_regex(text, entities)

    # --- Verification checks ---

    # 1. Company name presence
    if entities["company_name"]:
        score_components.append(0.8)
    else:
        score_components.append(0.3)
        flags.append({
            "rule": "ner_company",
            "severity": "medium",
            "message": "Could not identify a clear company name in the letter.",
            "score": 0.3,
        })

    # 2. HR person name presence
    if len(entities["person_names"]) >= 1:
        score_components.append(0.9)
    else:
        score_components.append(0.4)
        flags.append({
            "rule": "ner_person",
            "severity": "medium",
            "message": "No HR contact person name identified. Legitimate letters include HR signatory details.",
            "score": 0.4,
        })

    # 3. Location/address presence
    if len(entities["locations"]) >= 1:
        score_components.append(0.8)
    else:
        score_components.append(0.5)
        flags.append({
            "rule": "ner_location",
            "severity": "low",
            "message": "No company location/address identified in the letter.",
            "score": 0.5,
        })

    # 4. Contact information check
    if entities["emails"] or entities["phones"]:
        score_components.append(0.8)
    else:
        score_components.append(0.4)
        flags.append({
            "rule": "ner_contact",
            "severity": "medium",
            "message": "No contact information (email or phone) found in the letter.",
            "score": 0.4,
        })

    # 5. Date mentions
    if len(entities["dates"]) >= 1:
        score_components.append(0.8)
    else:
        score_components.append(0.5)

    # Calculate average verification score
    verification_score = sum(score_components) / len(score_components) if score_components else 0.5

    return verification_score, flags, entities


def _extract_with_spacy(text: str, entities: dict) -> dict:
    """Extract entities using spaCy NER."""
    doc = nlp(text)

    org_names = []
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org_names.append(ent.text.strip())
        elif ent.label_ == "PERSON":
            entities["person_names"].append(ent.text.strip())
        elif ent.label_ in ("DATE", "TIME"):
            entities["dates"].append(ent.text.strip())
        elif ent.label_ in ("GPE", "LOC", "FAC"):
            entities["locations"].append(ent.text.strip())
        elif ent.label_ == "MONEY":
            entities["amounts"].append(ent.text.strip())

    # Pick the most prominent ORG as company name
    if org_names:
        # The first or most frequently mentioned ORG
        from collections import Counter
        org_counts = Counter(org_names)
        entities["company_name"] = org_counts.most_common(1)[0][0]

    # Also extract emails and phones with regex
    entities["emails"] = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    entities["phones"] = re.findall(r"(?:\+91[\-\s]?)?(?:\d[\-\s]?){10}", text)

    # Deduplicate
    entities["person_names"] = list(set(entities["person_names"]))
    entities["locations"] = list(set(entities["locations"]))

    return entities


def _extract_with_regex(text: str, entities: dict) -> dict:
    """Fallback entity extraction using regex when spaCy is not available."""
    # Extract emails
    entities["emails"] = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)

    # Extract phone numbers
    entities["phones"] = re.findall(r"(?:\+91[\-\s]?)?(?:\d[\-\s]?){10}", text)

    # Try to find company name patterns
    company_patterns = [
        r"(?:at|from|by|of)\s+([A-Z][A-Za-z\s&]+(?:Ltd|Limited|Pvt|Private|Inc|Corp|LLP|Solutions|Technologies|Tech|Services|Consulting)\.?)",
        r"([A-Z][A-Za-z\s&]+(?:Ltd|Limited|Pvt|Private|Inc|Corp|LLP|Solutions|Technologies|Tech|Services|Consulting)\.?)",
    ]
    for pattern in company_patterns:
        match = re.search(pattern, text)
        if match:
            entities["company_name"] = match.group(1).strip()
            break

    # Extract dates
    date_patterns = [
        r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    ]
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text, re.IGNORECASE))

    return entities
