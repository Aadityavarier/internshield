"""
InternShield — Weighted Ensemble Scorer

Combines outputs from all three analysis models into a final verdict.
"""

from models.schemas import Verdict, DimensionScores


WEIGHTS = {
    "nlp": 0.50,
    "rules": 0.30,
    "ner": 0.20,
}


def compute_final_score(
    nlp_confidence: float,
    rule_suspicion: float,
    ner_verification: float,
) -> tuple[float, Verdict, DimensionScores]:
    """
    Compute the weighted ensemble score and verdict.

    Args:
        nlp_confidence: 0.0 (fake) to 1.0 (genuine) from NLP classifier
        rule_suspicion: 0.0 (clean) to 1.0 (highly suspicious) from rule engine
        ner_verification: 0.0 (unverified) to 1.0 (verified) from NER

    Returns:
        (final_score_percentage, verdict, dimension_scores)
    """
    # Convert rule suspicion to a confidence-like score (invert it)
    rule_confidence = 1.0 - rule_suspicion

    # Weighted combination
    raw_score = (
        WEIGHTS["nlp"] * nlp_confidence
        + WEIGHTS["rules"] * rule_confidence
        + WEIGHTS["ner"] * ner_verification
    )

    # Scale to percentage
    final_score = round(raw_score * 100, 1)
    final_score = max(0, min(100, final_score))

    # Determine verdict
    if final_score >= 75:
        verdict = Verdict.GENUINE
    elif final_score >= 45:
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
