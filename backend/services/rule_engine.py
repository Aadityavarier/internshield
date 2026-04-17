"""
InternShield — Rule-Based Analysis Engine

8 deterministic rules that catch structural red flags in offer letters.
Each rule returns a score (0.0 = safe, 1.0 = highly suspicious) and a reason.
"""

import re
import json
import os
from typing import Tuple
from datetime import datetime
from dateutil import parser as date_parser
from rapidfuzz import fuzz

import textstat


# Load reference data
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


SUSPICIOUS_DOMAINS = _load_json("suspicious_domains.json")
KNOWN_FAKE_COMPANIES = _load_json("known_fake_companies.json")
URGENCY_PHRASES = [
    "respond within 24 hours",
    "limited slots",
    "offer expires",
    "act immediately",
    "don't miss this opportunity",
    "limited time offer",
    "respond urgently",
    "seats filling fast",
    "last date to respond",
    "immediate joining required",
    "confirm within",
    "hurry up",
    "first come first serve",
]


def run_all_rules(text: str) -> Tuple[float, list[dict]]:
    """
    Run all 8 rules against extracted text.
    Returns (aggregate_score, list_of_flags).
    aggregate_score: 0.0 = all rules pass, 1.0 = all rules flag maximally.
    """
    rules = [
        check_email_domain,
        check_stipend_plausibility,
        check_known_fake_company,
        check_missing_fields,
        check_date_logic,
        check_grammar_quality,
        check_urgency_language,
        check_generic_greeting,
    ]

    flags = []
    total_score = 0.0

    for rule_fn in rules:
        score, flag = rule_fn(text)
        total_score += score
        if flag:
            flags.append(flag)

    # Normalize to 0-1 range
    aggregate = total_score / len(rules)

    # Invert: high rule score = suspicious, so confidence = 1 - aggregate
    # But we return the "suspicion" score to the caller
    return aggregate, flags


def check_email_domain(text: str) -> Tuple[float, dict | None]:
    """Rule 1: Flag personal email domains used in a corporate context."""
    personal_domains = [
        "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
        "rediffmail.com", "protonmail.com", "aol.com", "ymail.com",
        "mail.com", "inbox.com", "zoho.com",
    ]

    email_pattern = r"[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    found_emails = re.findall(email_pattern, text)

    if not found_emails:
        return 0.3, {
            "rule": "email_domain",
            "severity": "medium",
            "message": "No email address found in the letter. Legitimate offer letters typically include a corporate email.",
            "score": 0.3,
        }

    for domain in found_emails:
        domain_lower = domain.lower()
        if domain_lower in personal_domains:
            return 0.8, {
                "rule": "email_domain",
                "severity": "high",
                "message": f"Email domain is {domain_lower} — a personal email service. Legitimate companies use corporate email domains.",
                "score": 0.8,
            }

    return 0.0, None


def check_stipend_plausibility(text: str) -> Tuple[float, dict | None]:
    """Rule 2: Flag implausible stipend amounts."""
    # Match patterns like ₹500, Rs. 500, Rs 500, INR 500, ₹ 5,00,000
    patterns = [
        r"[₹]\s*([\d,]+(?:\.\d+)?)",
        r"(?:Rs\.?|INR|rupees)\s*([\d,]+(?:\.\d+)?)",
    ]

    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match.replace(",", ""))
                amounts.append(amount)
            except ValueError:
                continue

    if not amounts:
        return 0.1, None  # No amount mentioned isn't necessarily a red flag

    for amount in amounts:
        if amount < 1000:
            return 0.9, {
                "rule": "stipend_amount",
                "severity": "high",
                "message": f"Stipend of ₹{amount:,.0f}/month is significantly below market rate. Most legitimate internships offer at least ₹5,000/month.",
                "score": 0.9,
            }
        elif amount > 200000:
            return 0.6, {
                "rule": "stipend_amount",
                "severity": "medium",
                "message": f"Stipend of ₹{amount:,.0f}/month is unusually high for an internship. Verify this carefully.",
                "score": 0.6,
            }

    return 0.0, None


def check_known_fake_company(text: str) -> Tuple[float, dict | None]:
    """Rule 3: Fuzzy match company names against known fake entities."""
    text_lower = text.lower()

    for company in KNOWN_FAKE_COMPANIES:
        company_lower = company.lower()
        # Check direct mention
        if company_lower in text_lower:
            return 1.0, {
                "rule": "known_fake_company",
                "severity": "critical",
                "message": f"Company '{company}' matches a known fraudulent entity in our database.",
                "score": 1.0,
            }

        # Fuzzy match — catch slight variations
        words = text_lower.split()
        for i in range(len(words)):
            chunk = " ".join(words[i:i+4])
            if fuzz.partial_ratio(company_lower, chunk) > 85:
                return 0.8, {
                    "rule": "known_fake_company",
                    "severity": "high",
                    "message": f"Text closely matches known fraudulent entity '{company}'. Possible name variation detected.",
                    "score": 0.8,
                }

    return 0.0, None


def check_missing_fields(text: str) -> Tuple[float, dict | None]:
    """Rule 4: Check for absence of essential fields in an offer letter."""
    missing = []
    text_lower = text.lower()

    # Check for company address
    address_indicators = ["address", "office", "floor", "building", "tower", "plot", "sector", "block"]
    if not any(ind in text_lower for ind in address_indicators):
        missing.append("company address")

    # Check for HR / signatory name
    hr_indicators = ["hr", "human resources", "sincerely", "regards", "signed by", "authorized signatory"]
    if not any(ind in text_lower for ind in hr_indicators):
        missing.append("HR signatory")

    # Check for CIN / registration number
    cin_pattern = r"[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}"
    if not re.search(cin_pattern, text):
        if "cin" not in text_lower and "registration" not in text_lower:
            missing.append("company CIN/registration number")

    # Check for joining date
    date_indicators = ["joining date", "start date", "date of joining", "commencement", "reporting date"]
    if not any(ind in text_lower for ind in date_indicators):
        missing.append("joining/start date")

    if len(missing) >= 3:
        return 0.7, {
            "rule": "missing_fields",
            "severity": "high",
            "message": f"Letter is missing critical fields: {', '.join(missing)}. Legitimate offer letters typically include all of these.",
            "score": 0.7,
        }
    elif len(missing) >= 1:
        return 0.3, {
            "rule": "missing_fields",
            "severity": "medium",
            "message": f"Letter is missing: {', '.join(missing)}. Consider verifying these details independently.",
            "score": 0.3,
        }

    return 0.0, None


def check_date_logic(text: str) -> Tuple[float, dict | None]:
    """Rule 5: Check for impossible date combinations."""
    date_pattern = r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
    found_dates = re.findall(date_pattern, text)

    parsed_dates = []
    for d in found_dates:
        try:
            parsed = date_parser.parse(d, dayfirst=True)
            parsed_dates.append(parsed)
        except (ValueError, OverflowError):
            continue

    if len(parsed_dates) >= 2:
        parsed_dates.sort()
        earliest = parsed_dates[0]
        latest = parsed_dates[-1]

        # Check for dates far in the past
        if earliest.year < 2020:
            return 0.5, {
                "rule": "date_logic",
                "severity": "medium",
                "message": f"Letter contains a date from {earliest.year}, which seems unusually old for a current offer.",
                "score": 0.5,
            }

        # Check for dates far in the future
        if latest.year > datetime.now().year + 1:
            return 0.6, {
                "rule": "date_logic",
                "severity": "medium",
                "message": f"Letter contains a date in {latest.year}, which seems unusually far in the future.",
                "score": 0.6,
            }

    return 0.0, None


def check_grammar_quality(text: str) -> Tuple[float, dict | None]:
    """Rule 6: Check text readability and quality."""
    if len(text) < 100:
        return 0.4, {
            "rule": "grammar_quality",
            "severity": "medium",
            "message": "Letter is unusually short. Legitimate offer letters typically contain detailed terms and conditions.",
            "score": 0.4,
        }

    # Flesch reading ease: higher = easier to read
    try:
        reading_ease = textstat.flesch_reading_ease(text)
    except Exception:
        return 0.0, None

    # Very low readability might indicate generated/garbled text
    if reading_ease < 10:
        return 0.5, {
            "rule": "grammar_quality",
            "severity": "medium",
            "message": "Text readability is very low, suggesting potentially garbled or machine-generated content.",
            "score": 0.5,
        }

    # Very high readability (overly simple) might indicate a basic scam
    if reading_ease > 90:
        return 0.4, {
            "rule": "grammar_quality",
            "severity": "low",
            "message": "Text uses unusually simple language for a formal corporate letter.",
            "score": 0.4,
        }

    return 0.0, None


def check_urgency_language(text: str) -> Tuple[float, dict | None]:
    """Rule 7: Flag high-pressure urgency tactics."""
    text_lower = text.lower()
    found_phrases = []

    for phrase in URGENCY_PHRASES:
        if phrase in text_lower:
            found_phrases.append(phrase)

    if len(found_phrases) >= 2:
        return 0.8, {
            "rule": "urgency_language",
            "severity": "high",
            "message": f"Letter uses multiple high-pressure language tactics: \"{'\", \"'.join(found_phrases)}\". Legitimate companies don't pressure candidates to respond immediately.",
            "score": 0.8,
        }
    elif len(found_phrases) == 1:
        return 0.4, {
            "rule": "urgency_language",
            "severity": "medium",
            "message": f"Letter contains urgency language: \"{found_phrases[0]}\". This is sometimes used in fraudulent offers.",
            "score": 0.4,
        }

    return 0.0, None


def check_generic_greeting(text: str) -> Tuple[float, dict | None]:
    """Rule 8: Flag generic greetings instead of personalized ones."""
    generic_patterns = [
        r"dear\s+candidate",
        r"dear\s+applicant",
        r"dear\s+student",
        r"dear\s+sir\s*/?\s*ma'?a?m",
        r"to\s+whom\s+it\s+may\s+concern",
        r"dear\s+sir\s+or\s+madam",
    ]

    text_lower = text.lower()
    for pattern in generic_patterns:
        if re.search(pattern, text_lower):
            return 0.5, {
                "rule": "generic_greeting",
                "severity": "medium",
                "message": "Letter uses a generic greeting instead of addressing you by name. Legitimate offer letters are personalized.",
                "score": 0.5,
            }

    return 0.0, None
