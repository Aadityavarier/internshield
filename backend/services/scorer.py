"""
InternShield — Weighted Ensemble Scorer

Combines outputs from all three analysis models into a final verdict.
Enhanced with non-linear scaling, flag-count penalties, and minimum-evidence checks.
"""

import math
from models.schemas import Verdict, DimensionScores


WEIGHTS = {
    "nlp": 0.45,
    "rules": 0.35,
    "ner": 0.20,
}


def compute_final_score(
    nlp_confidence: float,
    rule_suspicion: float,
    ner_verification: float,
    flag_count: int = 0,
) -> tuple[float, Verdict, DimensionScores]:
    """
    Compute the weighted ensemble score and verdict.

    Args:
        nlp_confidence: 0.0 (fake) to 1.0 (genuine) from NLP classifier
        rule_suspicion: 0.0 (clean) to 1.0 (highly suspicious) from rule engine
        ner_verification: 0.0 (unverified) to 1.0 (verified) from NER
        flag_count: total number of flags triggered across all engines

    Returns:
        (final_score_percentage, verdict, dimension_scores)
    """
    # Convert rule suspicion to a confidence-like score (invert it)
    rule_confidence = 1.0 - rule_suspicion

    # --- Weighted combination ---
    raw_score = (
        WEIGHTS["nlp"] * nlp_confidence
        + WEIGHTS["rules"] * rule_confidence
        + WEIGHTS["ner"] * ner_verification
    )

    # --- Non-linear scaling to spread the distribution ---
    # Apply a power curve that stretches scores away from the middle
    # This prevents clustering around 50-60% and 80-90%
    if raw_score >= 0.5:
        # Upper half: use sqrt to expand high scores
        normalized = (raw_score - 0.5) * 2  # Map 0.5-1.0 to 0-1
        scaled = math.pow(normalized, 0.8)   # Power < 1 stretches toward 1
        raw_score = 0.5 + scaled * 0.5       # Map back to 0.5-1.0
    else:
        # Lower half: use power to push low scores lower
        normalized = (0.5 - raw_score) * 2   # Map 0-0.5 to 0-1 (inverted)
        scaled = math.pow(normalized, 0.8)   # Power < 1 stretches toward 0
        raw_score = 0.5 - scaled * 0.5       # Map back to 0-0.5

    # --- Flag-count penalty ---
    # Many flags = additional penalty regardless of component scores
    if flag_count >= 6:
        flag_penalty = 0.12
    elif flag_count >= 4:
        flag_penalty = 0.08
    elif flag_count >= 2:
        flag_penalty = 0.04
    else:
        flag_penalty = 0.0

    raw_score -= flag_penalty

    # --- Disagreement detection ---
    # If NLP and rules strongly disagree, apply skepticism
    disagreement = abs(nlp_confidence - rule_confidence)
    if disagreement > 0.5:
        # When engines disagree strongly, trust the more suspicious one
        raw_score -= 0.05

    # --- Minimum evidence check ---
    # If NER found almost nothing (score < 0.2), the letter is sparse
    # Apply a ceiling — can't be "genuine" without entities
    if ner_verification < 0.2:
        raw_score = min(raw_score, 0.55)

    # Scale to percentage
    final_score = round(raw_score * 100, 1)
    final_score = max(0, min(100, final_score))

    # Determine verdict with finer thresholds
    if final_score >= 72:
        verdict = Verdict.GENUINE
    elif final_score >= 40:
        verdict = Verdict.SUSPICIOUS
    else:
        verdict = Verdict.FAKE

    dimensions = DimensionScores(
        rules=round(rule_confidence, 3),
        nlp=round(nlp_confidence, 3),
        ner=round(ner_verification, 3),
    )

    return final_score, verdict, dimensions


def get_next_steps(verdict: Verdict, company_name: str | None = None) -> list[str]:
    """Generate context-aware next steps based on the verdict."""
    if verdict == Verdict.FAKE:
        steps = [
            "🚨 Do NOT share any personal documents (Aadhaar, PAN, bank details) with this organization.",
            "Report this offer letter to your college placement cell immediately.",
            "If you found this on Internshala or LinkedIn, report the listing on the platform.",
            "File a complaint on the National Cyber Crime Portal (cybercrime.gov.in) if you've already shared any information.",
            "Do NOT pay any 'registration fee', 'security deposit', or 'training charges'. Legitimate companies never ask candidates for money.",
        ]
        if company_name:
            steps.append(f"Search for '{company_name}' on MCA21 (mca.gov.in) to check if it's a registered company.")
        return steps

    elif verdict == Verdict.SUSPICIOUS:
        steps = [
            "⚠️ Verify this offer independently before sharing any personal information.",
            "Search for the company on LinkedIn and check if it has a legitimate presence (employee count, posts, verified page).",
            "Call the company's official number (found independently, NOT from this letter) and ask to speak with HR.",
            "Check the company's reviews on Glassdoor and AmbitionBox.",
        ]
        if company_name:
            steps.append(f"Verify '{company_name}' CIN on MCA21 portal (mca.gov.in/mcafoportal).")
        steps.extend([
            "If you received this unsolicited (you didn't apply), treat it with high suspicion.",
            "Ask your college placement cell if they have a relationship with this company.",
        ])
        return steps

    else:  # GENUINE
        steps = [
            "✅ This letter appears to be from a legitimate organization.",
            "Standard next steps: review the compensation and terms carefully before accepting.",
            "Respond within the deadline mentioned in the letter.",
            "Keep a copy of this offer letter for your records.",
            "Prepare your joining documents (ID proof, education certificates, bank details) for the onboarding process.",
            "Connect with your future manager or team on LinkedIn.",
        ]
        return steps
