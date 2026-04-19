"""
InternShield — NLP Classifier (Enhanced Keyword/Semantic Analysis)

Uses a keyword/semantic analysis approach to classify offer letters
as genuine or fake. Scoring is designed to produce a wide range of
outputs rather than clustering at two fixed values.

Scoring Philosophy:
  - Start at 0.5 (neutral / no opinion)
  - Genuine indicators push UP, fraud indicators push DOWN
  - Absence of expected genuine markers also pushes DOWN
  - Structural signals (length, formatting) provide minor adjustments
  - Final score is clamped to [0.05, 0.98] — never absolute certainty
"""

import re
import math
from typing import Tuple


# ──────────────────────────────────────────────────────────
#  GENUINE INDICATORS — things a real offer letter should have
# ──────────────────────────────────────────────────────────

# Each entry: (regex_pattern, score_boost, description, is_critical)
# is_critical: if True, absence of this pattern is also penalizing
GENUINE_INDICATORS = [
    # --- Formal structure ---
    (r"(terms?\s+and\s+conditions?|terms\s+of\s+employment)", 0.04, "Contains terms and conditions", True),
    (r"(probation\s+period|probationary\s+period)", 0.04, "Mentions probation period", False),
    (r"(non[\-\s]?disclosure|nda|confidentiality\s+agreement)", 0.05, "Includes NDA/confidentiality clause", False),
    (r"(intellectual\s+property|ip\s+rights)", 0.03, "References IP rights", False),
    (r"(code\s+of\s+conduct|company\s+polic)", 0.03, "References company policies", False),
    (r"(notice\s+period)", 0.03, "Mentions notice period", False),
    (r"(termination|dismissal)\s+(clause|policy)", 0.03, "Includes termination clause", False),

    # --- Financial details (strong signal) ---
    (r"(ctc|cost\s+to\s+company|compensation\s+breakup)", 0.05, "Has compensation breakdown", True),
    (r"(basic\s+salary|gross\s+salary|net\s+salary)", 0.04, "Mentions specific salary component", True),
    (r"(pf|provident\s+fund|esi|gratuity)", 0.05, "Mentions statutory benefits (PF/ESI)", True),
    (r"(tax\s+deduction|tds|income\s+tax)", 0.04, "References tax deductions", False),
    (r"(hra|house\s+rent\s+allowance|dearness\s+allowance)", 0.04, "Mentions HRA/DA", False),
    (r"(medical\s+insurance|health\s+insurance|group\s+insurance)", 0.04, "Mentions insurance benefits", False),

    # --- Legal elements (strong signal) ---
    (r"(cin|corporate\s+identity\s+number)", 0.06, "Contains CIN reference", True),
    (r"(registered\s+office|corporate\s+office)", 0.04, "Mentions registered office", True),
    (r"(authorized\s+signatory)", 0.04, "Has authorized signatory", True),
    (r"(offer\s+is\s+subject\s+to|contingent\s+upon)", 0.04, "Conditional offer language", False),
    (r"(background\s+verification|background\s+check)", 0.04, "Mentions background verification", False),
    (r"(employee\s+id|employee\s+code|employee\s+number)", 0.03, "References employee ID", False),

    # --- Professional language ---
    (r"(we\s+are\s+pleased\s+to\s+(offer|inform|extend))", 0.02, "Professional offer language", False),
    (r"(designation|role|position)\s*:\s*\w+", 0.03, "Specifies designation/role", False),
    (r"(reporting\s+(to|manager)|supervisor)", 0.03, "Mentions reporting structure", False),
    (r"(letter\s+of\s+(appointment|offer|intent))", 0.03, "Uses formal letter type", False),
    (r"(human\s+resources?\s+department|hr\s+department)", 0.03, "References HR department", False),
]

# ──────────────────────────────────────────────────────────
#  FRAUD INDICATORS — red flags that indicate scam
# ──────────────────────────────────────────────────────────

# Each entry: (regex_pattern, score_penalty, description)
FRAUD_INDICATORS = [
    # --- Payment demands (strongest red flags) ---
    (r"(pay|deposit|transfer|send)\s*(rs\.?|₹|inr|money|amount|fee)", 0.18, "Requests money/payment from candidate"),
    (r"(registration\s+fee|processing\s+fee|security\s+deposit)", 0.20, "Demands registration/processing fee"),
    (r"(training\s+fee|kit\s+charge|laptop\s+deposit)", 0.15, "Charges for training/equipment"),
    (r"(refundable\s+(deposit|amount|fee))", 0.15, "Mentions 'refundable deposit' — common scam tactic"),
    (r"(pay\s+before\s+joining|advance\s+payment)", 0.18, "Demands payment before joining"),

    # --- Unrealistic promises ---
    (r"(guaranteed?\s+(placement|job|salary|income))", 0.12, "Guarantees placement/job"),
    (r"(100\s*%\s*(placement|guaranteed|success))", 0.14, "Claims 100% guarantee"),
    (r"(earn\s+(up\s+to|upto)\s*₹?\s*\d+\s*lakh)", 0.12, "Unrealistic earning claims"),
    (r"(no\s+(experience|skills?)\s+(required|needed))", 0.10, "No experience required for skilled role"),
    (r"(work\s+from\s+home.*earn|earn.*work\s+from\s+home)", 0.10, "WFH earning scheme language"),
    (r"(unlimited\s+(earning|income|potential))", 0.10, "Unlimited earning claims"),
    (r"(life\s*changing\s+opportunity|dream\s+job)", 0.06, "Hype language"),

    # --- Suspicious communication channels ---
    (r"(whatsapp|telegram|signal)\s*(for|to|at|:)?\s*(details|more|joining|info|contact)", 0.12, "Uses WhatsApp/Telegram for official comms"),
    (r"(join\s+(our|the)\s+(whatsapp|telegram)\s+group)", 0.14, "Directs to WhatsApp/Telegram group"),
    (r"(call\s+this\s+number|contact\s+on\s+(mobile|cell|phone))", 0.08, "Directs to personal phone number"),
    (r"(click\s+(here|this\s+link|below).*register)", 0.10, "Pushes registration via link"),
    (r"(google\s*form|typeform|jotform)", 0.12, "Uses Google Forms/Typeform for hiring"),
    (r"(bit\.ly|tinyurl|short\.link|goo\.gl)", 0.10, "Uses URL shortener — obfuscation"),

    # --- Vague or missing specifics ---
    (r"(multinational|mnc|top\s+company)\s+(?!.*named)", 0.08, "References vague 'MNC' without name"),
    (r"(selected|shortlisted)\s+(based\s+on\s+(your\s+)?(resume|profile|cv))", 0.09, "Unsolicited selection claim"),
    (r"(you\s+have\s+been\s+(selected|chosen|picked))\s+(without|from\s+our\s+database)", 0.10, "Unsolicited selection without application"),
    (r"(congratulations!?\s+you\s+(have\s+been|are)\s+selected)", 0.08, "Over-enthusiastic congratulations"),

    # --- Urgency / Pressure (echoes rule engine but contributes to NLP too) ---
    (r"(respond\s+within\s+24\s+hours?|immediately|urgent|asap)", 0.06, "Uses urgency/pressure language"),
    (r"(limited\s+slots?|seats?\s+filling\s+fast|only\s+\d+\s+seats?)", 0.08, "Creates artificial scarcity"),
    (r"(offer\s+(will\s+)?expire|last\s+chance|final\s+call)", 0.07, "Pressures with expiry threats"),

    # --- Structural scam patterns ---
    (r"(no\s+interview|direct\s+selection|skip\s+interview)", 0.12, "Claims no interview needed"),
    (r"(refer\s+and\s+earn|referral\s+bonus\s+for\s+candidates)", 0.10, "Referral scheme — pyramid smell"),
    (r"(multi[\-\s]?level|mlm|network\s+marketing)", 0.14, "MLM/network marketing pattern"),
    (r"(data\s+entry|typing\s+job|copy\s+paste)", 0.08, "Common scam job type keywords"),
    (r"(watch\s+videos?\s+and\s+earn|like\s+and\s+earn)", 0.14, "Click-and-earn scam pattern"),
]


# ──────────────────────────────────────────────────────────
#  STRUCTURAL SIGNALS — document-level signals
# ──────────────────────────────────────────────────────────

def _compute_structural_score(text: str) -> float:
    """
    Analyze text structure for legitimacy signals.
    Returns a score from -0.15 (very suspicious structure) to +0.10 (strong structure).
    """
    adjustment = 0.0
    text_lower = text.lower()
    word_count = len(text.split())

    # Very short text — suspicious (real offers are detailed)
    if word_count < 80:
        adjustment -= 0.10
    elif word_count < 150:
        adjustment -= 0.05
    elif word_count > 500:
        adjustment += 0.03  # Longer, detailed letters are slightly more credible

    # Excessive exclamation marks — unprofessional
    exclamation_count = text.count("!")
    if exclamation_count > 5:
        adjustment -= 0.06
    elif exclamation_count > 10:
        adjustment -= 0.10

    # ALL CAPS words (more than 10% of words) — unprofessional
    words = text.split()
    caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
    if len(words) > 0 and caps_words / len(words) > 0.10:
        adjustment -= 0.06

    # Check for paragraph structure (legitimate letters have multiple paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 4:
        adjustment += 0.03
    elif len(paragraphs) <= 1:
        adjustment -= 0.04

    # Check for numbered/bulleted lists (common in real offers)
    if re.search(r"(\d+[\.\)]\s+\w+|\•|\-\s+\w+)", text):
        adjustment += 0.02

    # Check for salary/stipend figures (real offers specify amounts)
    if re.search(r"(₹|rs\.?|inr)\s*[\d,]+", text_lower):
        adjustment += 0.03

    # Check for specific date formats (real offers have specific dates)
    date_count = len(re.findall(r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}", text))
    if date_count >= 2:
        adjustment += 0.02
    elif date_count == 0:
        adjustment -= 0.03

    return max(-0.15, min(0.10, adjustment))


def classify_text(text: str) -> Tuple[float, list[dict]]:
    """
    Classify text using enhanced keyword/semantic analysis.
    Returns (confidence_score, list_of_flags).

    confidence_score: 0.0 = likely fake, 1.0 = likely genuine.

    Scoring approach:
      1. Start at 0.5 (neutral)
      2. Add genuine indicator boosts
      3. Subtract fraud indicator penalties
      4. Apply absence-of-legitimacy penalty
      5. Add structural score
      6. Clamp to [0.05, 0.98]
    """
    text_lower = text.lower()
    flags = []

    genuine_boost = 0.0
    fraud_penalty = 0.0
    genuine_matches = 0
    critical_genuine_matches = 0
    critical_genuine_total = 0

    # ── Count genuine indicators ──
    for pattern, boost, description, is_critical in GENUINE_INDICATORS:
        if is_critical:
            critical_genuine_total += 1
        if re.search(pattern, text_lower):
            genuine_boost += boost
            genuine_matches += 1
            if is_critical:
                critical_genuine_matches += 1

    # ── Count fraud indicators ──
    fraud_matches = 0
    for pattern, penalty, description in FRAUD_INDICATORS:
        if re.search(pattern, text_lower):
            fraud_penalty += penalty
            fraud_matches += 1
            flags.append({
                "rule": "nlp_classifier",
                "severity": "high" if penalty >= 0.10 else "medium",
                "message": description,
                "score": penalty,
            })

    # ── Absence-of-legitimacy penalty ──
    # If most critical genuine indicators are missing, that's suspicious
    if critical_genuine_total > 0:
        critical_ratio = critical_genuine_matches / critical_genuine_total
        if critical_ratio < 0.2:
            # Missing almost all critical genuine markers
            absence_penalty = 0.12
        elif critical_ratio < 0.4:
            absence_penalty = 0.07
        elif critical_ratio < 0.6:
            absence_penalty = 0.03
        else:
            absence_penalty = 0.0
    else:
        absence_penalty = 0.05

    # If no genuine indicators matched at all — very suspicious
    if genuine_matches == 0:
        absence_penalty += 0.10

    # ── Structural score ──
    structural_adjustment = _compute_structural_score(text)

    # ── Compute final confidence ──
    # Start at 0.5 (neutral)
    confidence = 0.5

    # Cap the genuine boost to avoid over-inflating
    genuine_boost = min(genuine_boost, 0.40)

    # Cap the fraud penalty (they can stack, but cap to avoid going too negative)
    fraud_penalty = min(fraud_penalty, 0.50)

    # Apply adjustments
    confidence += genuine_boost
    confidence -= fraud_penalty
    confidence -= absence_penalty
    confidence += structural_adjustment

    # Apply a mild sigmoid to spread the distribution
    # This transforms the linear sum into a more spread-out curve
    # centered at 0.5
    centered = confidence - 0.5
    confidence = 0.5 + 0.5 * (centered / (abs(centered) + 0.15)) if abs(centered) > 0.001 else 0.5

    # Clamp — never give absolute certainty
    confidence = max(0.05, min(0.98, confidence))

    # ── Add summary flag if heavily suspicious ──
    if fraud_matches >= 3:
        flags.append({
            "rule": "nlp_classifier",
            "severity": "critical",
            "message": f"Multiple fraud patterns detected ({fraud_matches} red flags). This strongly resembles a scam.",
            "score": 0.0,
        })
    elif fraud_matches == 0 and genuine_matches <= 2:
        flags.append({
            "rule": "nlp_classifier",
            "severity": "medium",
            "message": "Letter lacks typical professional indicators found in legitimate offer letters.",
            "score": 0.3,
        })

    return confidence, flags
