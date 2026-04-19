"""
InternShield — Rule-Based Analysis Engine

10 deterministic rules that catch structural red flags in offer letters.
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
    "last few seats",
    "offer valid till",
    "respond today",
    "do not delay",
]


def run_all_rules(text: str) -> Tuple[float, list[dict]]:
    """
    Run all 10 rules against extracted text.
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
        check_suspicious_links,
        check_payment_demands,
    ]

    flags = []
    total_score = 0.0
    triggered_count = 0

    for rule_fn in rules:
        score, flag = rule_fn(text)
        total_score += score
        if score > 0.3:
            triggered_count += 1
        if flag:
            if isinstance(flag, list):
                flags.extend(flag)
            else:
                flags.append(flag)

    # Normalize to 0-1 range
    aggregate = total_score / len(rules)

    # Apply a boosted aggregate if multiple rules triggered
    if triggered_count >= 5:
        aggregate = min(aggregate * 1.3, 1.0)
    elif triggered_count >= 3:
        aggregate = min(aggregate * 1.15, 1.0)

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
        return 0.4, {
            "rule": "email_domain",
            "severity": "medium",
            "message": "No email address found in the letter. Legitimate offer letters typically include a corporate email.",
            "score": 0.4,
        }

    personal_found = []
    corporate_found = []
    for domain in found_emails:
        domain_lower = domain.lower()
        if domain_lower in personal_domains:
            personal_found.append(domain_lower)
        else:
            corporate_found.append(domain_lower)

    if personal_found and not corporate_found:
        return 0.8, {
            "rule": "email_domain",
            "severity": "high",
            "message": f"Email domain is {personal_found[0]} — a personal email service. Legitimate companies use corporate email domains.",
            "score": 0.8,
        }
    elif personal_found and corporate_found:
        return 0.3, {
            "rule": "email_domain",
            "severity": "medium",
            "message": f"Mix of personal ({personal_found[0]}) and corporate email domains found. Verify the corporate email independently.",
            "score": 0.3,
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

    # Check for compensation details
    comp_indicators = ["salary", "stipend", "compensation", "ctc", "remuneration", "pay"]
    if not any(ind in text_lower for ind in comp_indicators):
        missing.append("compensation/salary details")

    # Check for role/designation
    role_indicators = ["designation", "position", "role", "job title"]
    if not any(ind in text_lower for ind in role_indicators):
        missing.append("role/designation")

    # Scoring: more missing = higher suspicion (lowered threshold from 3 to 2)
    if len(missing) >= 4:
        return 0.8, {
            "rule": "missing_fields",
            "severity": "high",
            "message": f"Letter is missing critical fields: {', '.join(missing)}. Legitimate offer letters typically include all of these.",
            "score": 0.8,
        }
    elif len(missing) >= 2:
        return 0.5, {
            "rule": "missing_fields",
            "severity": "medium",
            "message": f"Letter is missing: {', '.join(missing)}. Consider verifying these details independently.",
            "score": 0.5,
        }
    elif len(missing) == 1:
        return 0.2, {
            "rule": "missing_fields",
            "severity": "low",
            "message": f"Letter is missing: {', '.join(missing)}.",
            "score": 0.2,
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
        return 0.6, {
            "rule": "grammar_quality",
            "severity": "high",
            "message": "Letter is unusually short. Legitimate offer letters typically contain detailed terms and conditions.",
            "score": 0.6,
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

    if len(found_phrases) >= 3:
        return 0.9, {
            "rule": "urgency_language",
            "severity": "critical",
            "message": f"Letter uses multiple high-pressure language tactics: \"{'\", \"'.join(found_phrases[:3])}\". This is a strong scam indicator.",
            "score": 0.9,
        }
    elif len(found_phrases) == 2:
        return 0.7, {
            "rule": "urgency_language",
            "severity": "high",
            "message": f"Letter uses high-pressure language: \"{'\", \"'.join(found_phrases)}\". Legitimate companies don't pressure candidates to respond immediately.",
            "score": 0.7,
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
        r"hi\s+there",
        r"hello\s+candidate",
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


def check_suspicious_links(text: str) -> Tuple[float, dict | None]:
    """Rule 9: Flag suspicious links — Google Forms, URL shorteners, etc."""
    text_lower = text.lower()
    flags = []
    max_score = 0.0

    # Google Forms / Typeform / survey links
    if re.search(r"(docs\.google\.com/forms|forms\.gle|typeform\.com|jotform\.com|surveymonkey)", text_lower):
        max_score = max(max_score, 0.8)
        flags.append({
            "rule": "suspicious_links",
            "severity": "high",
            "message": "Letter contains a link to Google Forms / survey tool. Legitimate companies do not use Google Forms for hiring.",
            "score": 0.8,
        })

    # URL shorteners
    if re.search(r"(bit\.ly|tinyurl|short\.link|goo\.gl|t\.co|is\.gd|buff\.ly)", text_lower):
        max_score = max(max_score, 0.6)
        flags.append({
            "rule": "suspicious_links",
            "severity": "medium",
            "message": "Letter contains shortened URLs which obscure the actual destination. This is a common tactic in scam letters.",
            "score": 0.6,
        })

    # WhatsApp/Telegram group links
    if re.search(r"(chat\.whatsapp\.com|t\.me/|wa\.me/)", text_lower):
        max_score = max(max_score, 0.7)
        flags.append({
            "rule": "suspicious_links",
            "severity": "high",
            "message": "Letter contains WhatsApp/Telegram group invite links. Legitimate companies use official channels for onboarding.",
            "score": 0.7,
        })

    if flags:
        return max_score, flags

    return 0.0, None


def check_payment_demands(text: str) -> Tuple[float, dict | None]:
    """Rule 10: Explicitly check for monetary demands from candidate."""
    text_lower = text.lower()
    flags = []
    max_score = 0.0

    payment_patterns = [
        (r"(pay|deposit|transfer)\s+(rs\.?|₹|inr)\s*[\d,]+", 0.9,
         "Letter explicitly asks you to pay money. Legitimate employers NEVER charge candidates."),
        (r"(registration\s+fee|processing\s+fee|admin\s+fee|joining\s+fee)", 0.9,
         "Letter mentions a registration/processing/joining fee. This is a hallmark of scam offers."),
        (r"(security\s+deposit|caution\s+deposit|refundable\s+deposit)", 0.85,
         "Letter asks for a 'security deposit'. Legitimate companies do not require deposits from interns/employees."),
        (r"(training\s+charges?|course\s+fee|certification\s+fee|material\s+fee)", 0.8,
         "Letter charges for training/certification. Legitimate employers provide training at their cost."),
        (r"(bank\s+account|account\s+number|ifsc|upi|gpay|phonepe|paytm).{0,50}(send|transfer|pay|deposit)", 0.9,
         "Letter provides payment details and asks you to transfer money. This is a scam."),
        (r"(neft|rtgs|imps).{0,50}(transfer|send|deposit)", 0.85,
         "Letter references bank transfer methods for candidate payments. Major red flag."),
    ]

    for pattern, score, message in payment_patterns:
        if re.search(pattern, text_lower):
            max_score = max(max_score, score)
            flags.append({
                "rule": "payment_demand",
                "severity": "critical",
                "message": message,
                "score": score,
            })

    if flags:
        return max_score, flags

    return 0.0, None
