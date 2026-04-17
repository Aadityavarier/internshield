"""
InternShield — NLP Classifier (Zero-Shot)

Uses a lightweight zero-shot classification approach to classify offer letters
as genuine or fake without requiring fine-tuned training data.
"""

import re
from typing import Tuple


# We use a keyword/semantic analysis approach as a lightweight alternative
# to transformer-based zero-shot classification.
# This avoids the ~1.6GB model download and works within RAM constraints.
# When deploying on a server with more resources, swap this for:
#   from transformers import pipeline
#   classifier = pipeline("zero-shot-classification", model="typeform/distilbart-mnli-12-1")


# Indicators of legitimacy
GENUINE_INDICATORS = [
    # Formal structure
    (r"(terms?\s+and\s+conditions?|terms\s+of\s+employment)", 0.08, "Contains terms and conditions"),
    (r"(probation\s+period|probationary)", 0.07, "Mentions probation period"),
    (r"(non[\-\s]?disclosure|nda|confidentiality\s+agreement)", 0.08, "Includes NDA/confidentiality clause"),
    (r"(intellectual\s+property|ip\s+rights)", 0.06, "References IP rights"),
    (r"(code\s+of\s+conduct|company\s+polic)", 0.06, "References company policies"),

    # Financial details
    (r"(ctc|cost\s+to\s+company|compensation\s+breakup)", 0.07, "Has compensation breakdown"),
    (r"(pf|provident\s+fund|esi|gratuity)", 0.08, "Mentions statutory benefits (PF/ESI)"),
    (r"(tax\s+deduction|tds|income\s+tax)", 0.06, "References tax deductions"),

    # Legal elements
    (r"(cin|corporate\s+identity\s+number)", 0.09, "Contains CIN reference"),
    (r"(registered\s+office|corporate\s+office)", 0.07, "Mentions registered office"),
    (r"(authorized\s+signatory)", 0.07, "Has authorized signatory"),
    (r"(offer\s+is\s+subject\s+to|contingent\s+upon)", 0.06, "Conditional offer language"),
    (r"(background\s+verification|background\s+check)", 0.07, "Mentions background verification"),

    # Professional language
    (r"(we\s+are\s+pleased\s+to\s+(offer|inform|extend))", 0.06, "Professional offer language"),
    (r"(designation|role|position)\s*:\s*\w+", 0.05, "Specifies designation/role"),
    (r"(reporting\s+(to|manager)|supervisor)", 0.05, "Mentions reporting structure"),
]

# Indicators of fraud
FRAUD_INDICATORS = [
    # Payment demands
    (r"(pay|deposit|transfer|send)\s*(rs\.?|₹|inr|money|amount|fee)", 0.15, "Requests money/payment from candidate"),
    (r"(registration\s+fee|processing\s+fee|security\s+deposit)", 0.15, "Demands registration/processing fee"),
    (r"(training\s+fee|kit\s+charge|laptop\s+deposit)", 0.12, "Charges for training/equipment"),

    # Unrealistic promises
    (r"(guaranteed?\s+(placement|job|salary))", 0.10, "Guarantees placement/job"),
    (r"(100\s*%\s*(placement|guaranteed))", 0.12, "Claims 100% guarantee"),
    (r"(earn\s+(up\s+to|upto)\s*₹?\s*\d+\s*lakh)", 0.10, "Unrealistic earning claims"),
    (r"(no\s+(experience|skills?)\s+(required|needed))", 0.08, "No experience required for skilled role"),
    (r"(work\s+from\s+home.*earn|earn.*work\s+from\s+home)", 0.08, "WFH earning scheme language"),

    # Suspicious communication
    (r"(whatsapp|telegram|signal)\s*(for|to|at)\s*(details|more|joining)", 0.10, "Uses WhatsApp/Telegram for official comms"),
    (r"(call\s+this\s+number|contact\s+on\s+(mobile|cell|phone))", 0.06, "Directs to personal phone number"),
    (r"(click\s+(here|this\s+link|below).*register)", 0.08, "Pushes registration via link"),

    # Vague or missing specifics
    (r"(multinational|mnc|top\s+company)\s+(?!.*name)", 0.06, "References vague 'MNC' without name"),
    (r"(selected|shortlisted)\s+(based\s+on\s+(your\s+)?(resume|profile|cv))", 0.07, "Unsolicited selection claim"),
]


def classify_text(text: str) -> Tuple[float, list[dict]]:
    """
    Classify text using keyword/semantic analysis.
    Returns (confidence_score, list_of_flags).

    confidence_score: 0.0 = likely fake, 1.0 = likely genuine.
    """
    text_lower = text.lower()
    flags = []

    genuine_score = 0.0
    fraud_score = 0.0

    # Check genuine indicators
    for pattern, weight, description in GENUINE_INDICATORS:
        if re.search(pattern, text_lower):
            genuine_score += weight

    # Check fraud indicators
    for pattern, weight, description in FRAUD_INDICATORS:
        if re.search(pattern, text_lower):
            fraud_score += weight
            flags.append({
                "rule": "nlp_classifier",
                "severity": "high" if weight >= 0.10 else "medium",
                "message": description,
                "score": weight,
            })

    # Normalize scores to 0-1 range
    genuine_score = min(genuine_score, 1.0)
    fraud_score = min(fraud_score, 1.0)

    # Calculate confidence: high genuine + low fraud = high confidence
    if genuine_score + fraud_score == 0:
        confidence = 0.5  # Neutral if nothing detected
    else:
        confidence = genuine_score / (genuine_score + fraud_score + 0.001)

    # Boost confidence if many genuine indicators and no fraud indicators
    if genuine_score > 0.3 and fraud_score == 0:
        confidence = min(confidence + 0.15, 1.0)

    # Penalize if many fraud indicators
    if fraud_score > 0.3 and genuine_score < 0.2:
        confidence = max(confidence - 0.15, 0.0)

    return confidence, flags
