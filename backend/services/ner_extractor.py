"""
InternShield — Named Entity Recognition (NER) Extractor

Uses spaCy to extract key entities from offer letters and verify them.
Enhanced with wider score ranges and cross-entity validation.
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


# Weighted entity checks — critical entities weight more
ENTITY_WEIGHTS = {
    "company_name": 0.25,
    "person_names": 0.20,
    "contact_info": 0.25,
    "locations": 0.15,
    "dates": 0.15,
}


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

    # Extract with spaCy if available
    if SPACY_AVAILABLE and nlp:
        entities = _extract_with_spacy(text, entities)
    else:
        entities = _extract_with_regex(text, entities)

    # --- Verification checks (weighted) ---
    check_scores = {}

    # 1. Company name presence (critical)
    if entities["company_name"]:
        # Further validate: is the company name reasonable?
        company = entities["company_name"]
        if len(company.split()) >= 2 or any(
            s in company.lower()
            for s in ["ltd", "limited", "pvt", "private", "inc", "corp", "llp",
                       "solutions", "technologies", "tech", "services", "consulting"]
        ):
            check_scores["company_name"] = 1.0
        else:
            check_scores["company_name"] = 0.6  # Found but unverified format
    else:
        check_scores["company_name"] = 0.0
        flags.append({
            "rule": "ner_company",
            "severity": "high",
            "message": "Could not identify a clear company name in the letter. Legitimate offer letters prominently display the company name.",
            "score": 0.0,
        })

    # 2. HR / signatory person name presence (important)
    if len(entities["person_names"]) >= 2:
        check_scores["person_names"] = 1.0
    elif len(entities["person_names"]) == 1:
        check_scores["person_names"] = 0.7
    else:
        check_scores["person_names"] = 0.0
        flags.append({
            "rule": "ner_person",
            "severity": "high",
            "message": "No HR contact person name identified. Legitimate letters include HR signatory details.",
            "score": 0.0,
        })

    # 3. Contact information (critical — emails and/or phones)
    has_email = len(entities["emails"]) > 0
    has_phone = len(entities["phones"]) > 0
    has_corporate_email = any(
        not _is_personal_email(e) for e in entities["emails"]
    )

    if has_corporate_email and has_phone:
        check_scores["contact_info"] = 1.0
    elif has_corporate_email:
        check_scores["contact_info"] = 0.8
    elif has_email and has_phone:
        check_scores["contact_info"] = 0.5  # Email is personal
    elif has_email:
        check_scores["contact_info"] = 0.3
    elif has_phone:
        check_scores["contact_info"] = 0.3
    else:
        check_scores["contact_info"] = 0.0
        flags.append({
            "rule": "ner_contact",
            "severity": "high",
            "message": "No contact information (email or phone) found in the letter.",
            "score": 0.0,
        })

    # 4. Location/address presence
    if len(entities["locations"]) >= 2:
        check_scores["locations"] = 1.0
    elif len(entities["locations"]) == 1:
        check_scores["locations"] = 0.7
    else:
        check_scores["locations"] = 0.0
        flags.append({
            "rule": "ner_location",
            "severity": "medium",
            "message": "No company location/address identified in the letter.",
            "score": 0.0,
        })

    # 5. Date mentions
    if len(entities["dates"]) >= 3:
        check_scores["dates"] = 1.0
    elif len(entities["dates"]) >= 1:
        check_scores["dates"] = 0.7
    else:
        check_scores["dates"] = 0.1

    # --- Cross-entity validation ---
    cross_validation_adjustment = 0.0

    # Check if email domain matches company name
    if entities["company_name"] and entities["emails"]:
        company_words = set(entities["company_name"].lower().split())
        # Remove common suffixes
        company_words -= {"pvt", "ltd", "limited", "private", "inc", "corp", "llp", ".", ","}
        for email in entities["emails"]:
            domain = email.split("@")[-1].lower().split(".")[0]
            if any(word in domain for word in company_words if len(word) > 3):
                cross_validation_adjustment += 0.08  # Domain matches company — good sign
                break
        else:
            # No email matched the company name
            if not any(_is_personal_email(e) for e in entities["emails"]):
                cross_validation_adjustment -= 0.03  # Corporate email but doesn't match company name

    # Check for personal email as sole contact
    if entities["emails"] and all(_is_personal_email(e) for e in entities["emails"]):
        cross_validation_adjustment -= 0.08
        flags.append({
            "rule": "ner_email_personal",
            "severity": "high",
            "message": "All email addresses in the letter use personal email domains (Gmail, Yahoo, etc.). Legitimate companies use corporate domains.",
            "score": 0.0,
        })

    # --- Calculate weighted verification score ---
    verification_score = 0.0
    for check_name, weight in ENTITY_WEIGHTS.items():
        score = check_scores.get(check_name, 0.0)
        verification_score += weight * score

    # Apply cross-validation
    verification_score += cross_validation_adjustment

    # Completeness bonus/penalty
    entities_found = sum(1 for s in check_scores.values() if s > 0.5)
    total_checks = len(check_scores)
    if entities_found == total_checks:
        verification_score += 0.05  # All entities found — strong signal
    elif entities_found <= 1:
        verification_score -= 0.05  # Almost nothing found — weak letter

    # Clamp
    verification_score = max(0.0, min(1.0, verification_score))

    return verification_score, flags, entities


def _is_personal_email(email: str) -> bool:
    """Check if an email address uses a personal/free email domain."""
    personal_domains = {
        "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
        "rediffmail.com", "protonmail.com", "aol.com", "ymail.com",
        "mail.com", "inbox.com", "zoho.com", "icloud.com", "live.com",
        "yandex.com",
    }
    domain = email.split("@")[-1].lower()
    return domain in personal_domains


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

    # Try to find person names (after "Regards" or "Signed by" or "HR Manager")
    name_patterns = [
        r"(?:regards|sincerely|signed\s+by|authorized\s+signatory)[,\s:]*\n?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:hr\s+manager|hr\s+head|hr\s+director)[,\s:]*\n?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
    ]
    for pattern in name_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["person_names"].extend(matches)

    # Extract location clues
    location_patterns = [
        r"(?:located\s+(?:at|in)|address|office)[:\s]+([A-Z][A-Za-z\s,]+(?:India|Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Noida|Gurgaon|Gurugram))",
    ]
    for pattern in location_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["locations"].extend(matches)

    return entities
