"""
Test script for InternShield scoring pipeline.
Runs sample genuine and fake offer letters through the full pipeline
and verifies that scores are varied (not clustering at two values).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.nlp_classifier import classify_text
from services.rule_engine import run_all_rules
from services.ner_extractor import extract_and_verify
from services.scorer import compute_final_score


# ────────────────────────────────────────────────
# TEST CASES
# ────────────────────────────────────────────────

GENUINE_OFFER = """
Dear Priya Sharma,

Subject: Offer of Employment – Software Engineer Intern

We are pleased to extend this offer of employment to you for the position of Software Engineer Intern
at TechVista Solutions Pvt. Ltd. (CIN: U72200KA2015PTC123456).

Your appointment is subject to the following terms and conditions:

1. Designation: Software Engineer Intern
2. Reporting To: Mr. Rajesh Kumar, Engineering Manager
3. Date of Joining: 1st July 2025
4. Location: TechVista Solutions Pvt. Ltd., 4th Floor, Tower B, Prestige Tech Park, Outer Ring Road, Bangalore - 560103
5. Duration: 6 months (1st July 2025 to 31st December 2025)

Compensation:
- Stipend: ₹25,000 per month (Twenty-Five Thousand Rupees Only)
- This amount is subject to TDS deductions as per Income Tax regulations

Benefits:
- Provident Fund (PF) contribution as per statutory requirements
- Group Medical Insurance coverage
- Access to company learning portal and training resources

Terms and Conditions:
- This offer is contingent upon successful background verification
- You are required to serve a notice period of 15 days
- All intellectual property created during your tenure will belong to TechVista Solutions Pvt. Ltd.
- You are expected to adhere to the company's Code of Conduct and NDA policies
- Probation period: First 2 months from date of joining

Please confirm your acceptance by signing and returning this letter by 25th June 2025.

For any queries, please contact:
HR Department: hr@techvista.com
Phone: +91-80-4567-8901

Warm Regards,
Anita Desai
Head of Human Resources
TechVista Solutions Pvt. Ltd.
Authorized Signatory
"""

FAKE_OFFER_OBVIOUS = """
CONGRATULATIONS! YOU HAVE BEEN SELECTED!!!

Dear Candidate,

You have been selected based on your resume for an exciting work from home opportunity!!

Company: Top MNC (name confidential)
Salary: Earn upto ₹5 lakh per month! No experience required!

To confirm your selection, please pay a registration fee of Rs. 5,000 as security deposit.
This amount is refundable deposit after 6 months.

Send payment via UPI to: hiring.manager@gmail.com
WhatsApp: +91-98765-43210 for joining details
Join our WhatsApp group: https://chat.whatsapp.com/abc123

LIMITED SLOTS! HURRY UP! Respond within 24 hours or offer expires!
Seats filling fast! Don't miss this opportunity!

Click here to register: https://bit.ly/fake-offer-123

No interview needed! Direct selection!
"""

FAKE_OFFER_SUBTLE = """
Dear Candidate,

We are pleased to inform you that you have been shortlisted based on your profile
for the position of Business Development Associate at Global Enterprises.

Role: Business Development Associate
Location: Work from Home
Joining Date: Immediate

Selected candidates will receive a monthly stipend of ₹15,000.

To complete your onboarding, please fill this form: https://docs.google.com/forms/d/fakeform123

For more details, contact us on WhatsApp: +91-87654-32109

Regards,
HR Team
"""

SUSPICIOUS_OFFER = """
Dear Student,

Greetings from Innovatech Corp!

We are glad to offer you the position of Marketing Intern at our organization.

Duration: 3 months
Stipend: ₹8,000/month

Please confirm within 24 hours as we have limited slots available.

Contact: hr.innovatech@gmail.com

Regards,
Team HR
"""

VERY_SHORT_TEXT = """
You are selected for internship. Pay Rs 2000 registration fee to confirm.
Contact on WhatsApp: 9876543210. Respond immediately.
"""


def test_pipeline(name: str, text: str):
    """Run a single test through the full pipeline."""
    # NLP
    nlp_conf, nlp_flags = classify_text(text)

    # Rules
    rule_susp, rule_flags = run_all_rules(text)

    # NER
    ner_score, ner_flags, entities = extract_and_verify(text)

    # All flags
    all_flags = nlp_flags + rule_flags + ner_flags

    # Final score
    final_score, verdict, dims = compute_final_score(
        nlp_confidence=nlp_conf,
        rule_suspicion=rule_susp,
        ner_verification=ner_score,
        flag_count=len(all_flags),
    )

    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"  NLP confidence:   {nlp_conf:.3f}")
    print(f"  Rule suspicion:   {rule_susp:.3f}")
    print(f"  NER verification: {ner_score:.3f}")
    print(f"  Flag count:       {len(all_flags)}")
    print(f"  ─────────────────────────────")
    print(f"  FINAL SCORE:      {final_score}%")
    print(f"  VERDICT:          {verdict.value}")
    print(f"  Dimensions:       NLP={dims.nlp:.3f}  Rules={1-rule_susp:.3f}  NER={dims.ner:.3f}")
    if entities.get("company_name"):
        print(f"  Company:          {entities['company_name']}")

    return final_score, verdict.value


if __name__ == "__main__":
    results = []

    tests = [
        ("Genuine Offer (TechVista)", GENUINE_OFFER),
        ("Obvious Fake (Payment + Scam)", FAKE_OFFER_OBVIOUS),
        ("Subtle Fake (Google Forms)", FAKE_OFFER_SUBTLE),
        ("Suspicious (Gmail + Urgency)", SUSPICIOUS_OFFER),
        ("Very Short Scam Text", VERY_SHORT_TEXT),
    ]

    for name, text in tests:
        score, verdict = test_pipeline(name, text)
        results.append((name, score, verdict))

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    scores = []
    for name, score, verdict in results:
        print(f"  {score:5.1f}%  {verdict:<15s}  {name}")
        scores.append(score)

    unique_scores = len(set(scores))
    score_range = max(scores) - min(scores)
    print(f"\n  Unique scores: {unique_scores}/{len(scores)}")
    print(f"  Score range:   {min(scores):.1f}% - {max(scores):.1f}% (spread: {score_range:.1f}%)")

    if unique_scores <= 2:
        print("\n  ❌ FAIL: Still clustering at only 2 values!")
    elif score_range < 30:
        print("\n  ⚠️  WARNING: Score range is narrow. May need further tuning.")
    else:
        print("\n  ✅ PASS: Scores are well-distributed!")
