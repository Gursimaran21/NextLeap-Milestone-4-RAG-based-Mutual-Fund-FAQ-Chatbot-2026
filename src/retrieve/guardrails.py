"""Guardrails: refuse advice, block PII, redirect performance questions."""

from __future__ import annotations

import re
from typing import Any, Literal

GuardKind = Literal["advice", "performance", "pii"]

# Educational placeholder used on soft refusals (facts-only framing)
EDUCATIONAL_LINK = "https://www.sebi.gov.in/legal/circulars/oct-2021/circular-on-risk-o-meter_53525.html"

_ADVICE_PATTERNS = [
    r"\bshould\s+i\b",
    r"\bshould\s+we\b",
    r"\bbuy\b",
    r"\bsell\b",
    r"\brecommend(?:ation|ed|s)?\b",
    r"\bbest\s+fund\b",
    r"\bbest\s+for\s+me\b",
    r"\bsuitable\s+for\s+me\b",
    r"\bwhich\s+(?:one|fund)\s+should\b",
    r"\binvest\s+in\b.*\?",
    r"\bworth\s+(?:buying|investing)\b",
    r"\badvice\b",
    r"\bportfolio\s+for\s+me\b",
]

_PERFORMANCE_PATTERNS = [
    r"\bhighest\s+return",
    r"\bbetter\s+return",
    r"\bhigher\s+return",
    r"\bbeat\s+the\s+market\b",
    r"\bwhich\s+will\s+perform\b",
    r"\bcompare\s+returns?\b",
    r"\breturn(?:s)?\s+compar",
    r"\bwhich\s+(?:fund|one)\s+(?:is\s+)?(?:better|best)\b",
    r"\bwill\s+(?:this|it)\s+(?:go\s+up|rise|grow|perform)\b",
    r"\bguaranteed\s+return",
    r"\bpredict(?:ion|ed)?\b.*\breturn",
    r"\breturn.*\bpredict",
]

# Indian PAN: 5 letters + 4 digits + 1 letter
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
# Aadhaar: 12 digits, often grouped
_AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
_OTP_RE = re.compile(r"\b(?:otp|one[-\s]?time\s+password)\b", re.IGNORECASE)
# Long digit sequences that look like account numbers (not years/amounts)
_ACCOUNT_RE = re.compile(r"\b(?:a/?c|account|folio)(?:\s*(?:no|number|#)?)?\s*[:\-]?\s*\d{9,18}\b", re.IGNORECASE)


def _matched(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _detect_pii(text: str) -> bool:
    if _EMAIL_RE.search(text):
        return True
    if _PHONE_RE.search(text):
        return True
    if _PAN_RE.search(text):
        return True
    if _AADHAAR_RE.search(text):
        return True
    if _OTP_RE.search(text):
        return True
    if _ACCOUNT_RE.search(text):
        return True
    return False


def _refusal(kind: GuardKind) -> str:
    if kind == "advice":
        return (
            "I can only share facts from public scheme pages — not buy/sell or suitability advice. "
            "Try asking a factual parameter such as expense ratio, exit load, minimum SIP, "
            f"lock-in, riskometer, or benchmark. Learn more about risk disclosure: {EDUCATIONAL_LINK}"
        )
    if kind == "performance":
        return (
            "I don't compute, compare, or predict returns. "
            "For official performance figures, please check the scheme's public factsheet/page. "
            "I can still answer facts like expense ratio, exit load, or minimum SIP if you ask."
        )
    return (
        "Please don't share personal or account details (PAN, Aadhaar, account numbers, OTP, "
        "email, or phone). I don't accept or store PII. "
        "Rephrase with only the scheme fact you need — for example exit load or expense ratio."
    )


def check_question(question: str) -> dict[str, Any]:
    """
    Check a user question before retrieval/generation.

    Returns:
      {
        ok: bool,
        reason: str | None,
        refusal_message: str | None,
        kind: "advice" | "performance" | "pii" | None,
      }
    """
    text = (question or "").strip()
    if not text:
        return {
            "ok": False,
            "reason": "empty_question",
            "refusal_message": "Please ask a factual question about one of the HDFC schemes in scope.",
            "kind": None,
        }

    # PII first — never proceed if secrets appear in the prompt
    if _detect_pii(text):
        return {
            "ok": False,
            "reason": "pii_detected",
            "refusal_message": _refusal("pii"),
            "kind": "pii",
        }

    if _matched(_ADVICE_PATTERNS, text):
        return {
            "ok": False,
            "reason": "investment_advice_request",
            "refusal_message": _refusal("advice"),
            "kind": "advice",
        }

    if _matched(_PERFORMANCE_PATTERNS, text):
        return {
            "ok": False,
            "reason": "performance_comparison_or_prediction",
            "refusal_message": _refusal("performance"),
            "kind": "performance",
        }

    return {
        "ok": True,
        "reason": None,
        "refusal_message": None,
        "kind": None,
    }


if __name__ == "__main__":
    demos = [
        "Should I buy HDFC Small Cap?",
        "What is the exit load of HDFC Small Cap?",
        "Email me details at user@example.com",
        "Which fund will give the highest returns?",
        "What is the ELSS lock-in for HDFC Tax Saver?",
        "My PAN is ABCDE1234F — what's the expense ratio?",
    ]
    for q in demos:
        result = check_question(q)
        status = "PASS" if result["ok"] else f"BLOCK:{result['kind']}"
        print(f"[{status}] {q}")
        if not result["ok"]:
            print(f"  -> {result['refusal_message'][:100]}...")
        print()
