"""
Hybrid Scam Detection System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Multi-Signal Weighted Scoring Model:
  scam_score = 0.25 * keyword_score
             + 0.20 * urgency_score
             + 0.20 * authority_score
             + 0.15 * payment_request_score
             + 0.20 * LLM_intent_score

Thresholds:
  scam_score >= 0.40  →  Scam detected
  scam_score >= 0.25  →  Suspicious (engage if conversation ongoing)

Additional Detectors:
  • Authority impersonation detection
  • Emotional manipulation patterns (fear / greed / sympathy / guilt)
  • Payment redirection patterns
  • Optional LLM-backed intent classification (OpenAI / Groq)
  • Falls back to heuristic intent scoring when no LLM configured
"""

import re
from typing import Dict, Tuple, List, Optional
from normalizer import normalize_input, normalize_for_detection
from llm_engine import analyze_message, get_llm_intent


# ═══════════════════════════════════════════════════════════════
# WEIGHT CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SIGNAL_WEIGHTS = {
    "keyword":         0.25,
    "urgency":         0.20,
    "authority":       0.20,
    "payment_request": 0.15,
    "llm_intent":      0.20,
}

# Detection thresholds
SCAM_THRESHOLD = 0.40         # Above this → definite scam
SUSPICIOUS_THRESHOLD = 0.25   # Above this → engage if conversation ongoing


# ═══════════════════════════════════════════════════════════════
# SIGNAL 1 — KEYWORD SCORING  (weight 0.25)
# Tiered keywords with severity weights
# ═══════════════════════════════════════════════════════════════

KEYWORD_TIERS = {
    "critical": {
        "words": [
            "otp", "cvv", "pin", "password", "mpin",
            "phishing", "malware", "hack",
        ],
        "weight": 1.0,
    },
    "high": {
        "words": [
            "blocked", "suspended", "frozen", "locked", "deactivated",
            "verify", "confirm", "update", "kyc", "validation",
            "prize", "winner", "congratulations", "reward", "lottery",
            "refund", "cashback", "compensation",
        ],
        "weight": 0.7,
    },
    "medium": {
        "words": [
            "account", "bank", "transaction", "payment", "transfer",
            "wallet", "credit", "debit", "upi", "paytm", "phonepe",
            "gpay", "expire", "security", "customer care", "support",
            "helpline", "link", "click",
        ],
        "weight": 0.4,
    },
    "low": {
        "words": [
            "free", "offer", "deal", "limited", "exclusive",
            "pending", "failed", "issue", "problem",
        ],
        "weight": 0.2,
    },
}


def compute_keyword_score(text: str) -> float:
    """
    Weighted keyword scoring with tier-based severity.
    Returns 0.0 – 1.0.
    """
    total_weight = 0.0
    matches = 0

    for tier_data in KEYWORD_TIERS.values():
        for word in tier_data["words"]:
            if word in text:
                total_weight += tier_data["weight"]
                matches += 1

    if matches == 0:
        return 0.0

    # Normalize: 3+ critical or 5+ high keywords → max score (diminishing returns)
    return round(min(1.0, total_weight / 3.0), 4)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 2 — URGENCY SCORING  (weight 0.20)
# Time-pressure, threats, countdowns
# ═══════════════════════════════════════════════════════════════

URGENCY_PATTERNS = {
    "time_pressure": {
        "patterns": [
            r"\b(urgent|immediately|right now|asap|hurry|quickly)\b",
            r"\b(within \d+ (hour|minute|day)s?)\b",
            r"\b(last chance|final warning|deadline)\b",
            r"\b(today only|now or never|act fast)\b",
            r"\b(running out|time is running|don't delay)\b",
        ],
        "weight": 0.35,
    },
    "threat_language": {
        "patterns": [
            r"\b(will be (blocked|suspended|frozen|closed|terminated|deactivated))\b",
            r"\b(legal action|police|arrest|jail|court|case filed)\b",
            r"\b(permanent(ly)? (block|suspend|close|delete))\b",
            r"\b(cannot be (recovered|restored|reversed))\b",
            r"\b(your .{0,30} (at risk|in danger|compromised))\b",
        ],
        "weight": 0.40,
    },
    "countdown": {
        "patterns": [
            r"\b\d+\s*(hours?|minutes?|mins?|hrs?)\s*(left|remaining)\b",
            r"\b(expires? (in|within|by))\b",
            r"\b(before .{0,20} (expires?|closes?|blocks?))\b",
        ],
        "weight": 0.25,
    },
}


def compute_urgency_score(text: str) -> float:
    """
    Multi-pattern urgency detection.
    Returns 0.0 – 1.0.
    """
    score = 0.0

    for data in URGENCY_PATTERNS.values():
        for pattern in data["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += data["weight"]
                break  # one hit per category is enough

    return round(min(1.0, score), 4)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 3 — AUTHORITY IMPERSONATION SCORING  (weight 0.20)
# Institution names, titles, official language
# ═══════════════════════════════════════════════════════════════

AUTHORITY_PATTERNS = {
    "institution_impersonation": {
        "patterns": [
            # Banks & financial institutions
            r"\b(reserve bank|rbi|state bank|sbi|hdfc|icici|axis bank|pnb)\b",
            r"\b(national bank|central bank|federal bank)\b",
            # Government
            r"\b(government|ministry|department of|income tax|it department)\b",
            r"\b(aadhaar|aadhar|pan card|passport office)\b",
            r"\b(customs|immigration|cyber cell|cyber crime)\b",
            # Tech companies
            r"\b(microsoft|apple|google|amazon|meta|facebook|whatsapp)\b",
            r"\b(paypal|razorpay|stripe)\b",
            # Telecom
            r"\b(airtel|jio|vodafone|bsnl|idea)\b",
        ],
        "weight": 0.35,
    },
    "title_impersonation": {
        "patterns": [
            r"\b(officer|inspector|manager|director|executive|supervisor)\b",
            r"\b(senior .{0,15} (officer|manager|executive))\b",
            r"\b(chief .{0,15} (officer|manager))\b",
            r"\b(head of .{0,20}(department|division|security))\b",
            r"\b(i am (from|calling from|with) .{0,30}(bank|department|office|company))\b",
        ],
        "weight": 0.30,
    },
    "official_language": {
        "patterns": [
            r"\b(as per (rbi|government|regulation|policy|guideline))\b",
            r"\b(in accordance with|pursuant to|under section)\b",
            r"\b(official (notice|notification|communication|letter))\b",
            r"\b(reference (number|id|no\.?|code))\b",
            r"\b(case (number|id|no\.?|file))\b",
            r"\b(complaint (number|id|no\.?|registered))\b",
            r"\b(mandatory|compulsory|required by law)\b",
        ],
        "weight": 0.35,
    },
}


def compute_authority_score(text: str) -> float:
    """
    Detect authority impersonation attempts.
    Returns 0.0 – 1.0.
    """
    score = 0.0

    for data in AUTHORITY_PATTERNS.values():
        for pattern in data["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += data["weight"]
                break

    return round(min(1.0, score), 4)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 4 — PAYMENT REQUEST SCORING  (weight 0.15)
# Payment identifiers, request language, redirection
# ═══════════════════════════════════════════════════════════════

PAYMENT_PATTERNS = {
    "payment_identifiers": {
        "patterns": [
            # UPI IDs
            r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}",
            # Bank account patterns (9-18 consecutive digits)
            r"\b\d{9,18}\b",
            # IFSC codes
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        ],
        "weight": 0.40,
    },
    "payment_request_language": {
        "patterns": [
            r"\b(send|transfer|pay|deposit)\b.{0,30}\b(money|amount|rs|rupees?|inr|₹|\$)\b",
            r"\b(rs\.?|rupees?|₹)\s*\d+",
            r"\b\d+\s*(rs\.?|rupees?|₹|dollars?|\$)\b",
            r"\b(processing fee|service charge|verification fee|refundable deposit)\b",
            r"\b(registration fee|activation charge|insurance fee|convenience fee)\b",
            r"\b(pay .{0,20} (to|via|through|using) .{0,20}(upi|paytm|phonepe|gpay|account))\b",
        ],
        "weight": 0.35,
    },
    "payment_redirection": {
        "patterns": [
            r"\b(send (to|money to|payment to))\b",
            r"\b(transfer (to|funds to|amount to))\b",
            r"\b(pay (to|at|into|via))\b",
            r"\b(deposit (into|to|in))\b",
            r"\b(use (this|the following) (upi|account|number))\b",
            r"\b(scan (this|the) (qr|code|barcode))\b",
            r"\b(click .{0,15}(pay|send|transfer|confirm))\b",
        ],
        "weight": 0.25,
    },
}


def compute_payment_score(text: str) -> float:
    """
    Detect payment requests and redirection patterns.
    Returns 0.0 – 1.0.
    """
    score = 0.0

    for data in PAYMENT_PATTERNS.values():
        for pattern in data["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += data["weight"]
                break

    return round(min(1.0, score), 4)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 5 — LLM INTENT SCORING  (weight 0.20)
# Delegated to llm_engine.py (cached, structured, with fallback)
# ═══════════════════════════════════════════════════════════════

def compute_llm_intent_score(text: str, history: list) -> Tuple[float, str]:
    """Retrieve intent score from llm_engine (LLM → cache → heuristic)."""
    return get_llm_intent(text, history)


# ═══════════════════════════════════════════════════════════════
# SUPPLEMENTARY — EMOTIONAL MANIPULATION DETECTOR
# (boosts composite score when detected)
# ═══════════════════════════════════════════════════════════════

EMOTIONAL_MANIPULATION = {
    "fear": [
        r"\b(you will lose|lose (all|everything)|risk losing)\b",
        r"\b(arrested|jail|criminal|prosecution)\b",
        r"\b(compromised|breached|unauthorized access)\b",
        r"\b(someone (is|has been) (using|accessing))\b",
    ],
    "greed": [
        r"\b(won|winning|prize|reward|cashback|bonus)\b",
        r"\b(guaranteed|100%|easy money|double)\b",
        r"\b(free|complimentary|no cost|zero charge)\b",
        r"\b(lakh|crore|million|thousand)\b",
    ],
    "sympathy": [
        r"\b(please help|need help|emergency)\b",
        r"\b(hospital|accident|dying|illness)\b",
        r"\b(stranded|stuck|helpless)\b",
    ],
    "guilt": [
        r"\b(don't you trust|why won't you|are you refusing)\b",
        r"\b(everyone (else|is)|all (customers|users))\b",
        r"\b(if you (don't|refuse|fail to))\b",
    ],
}


def detect_emotional_manipulation(text: str) -> Dict[str, bool]:
    """
    Detect emotional manipulation tactics.
    Returns dict of { tactic → detected }.
    """
    results = {}
    for tactic, patterns in EMOTIONAL_MANIPULATION.items():
        results[tactic] = any(
            re.search(p, text, re.IGNORECASE) for p in patterns
        )
    return results


# ═══════════════════════════════════════════════════════════════
# COMPOSITE SCORING ENGINE
# ═══════════════════════════════════════════════════════════════

def compute_scam_score(text: str, history: list) -> Dict:
    """
    Multi-Signal Weighted Scoring Model.

      scam_score = 0.25 * keyword_score
                 + 0.20 * urgency_score
                 + 0.20 * authority_score
                 + 0.15 * payment_request_score
                 + 0.20 * LLM_intent_score

    Returns detailed breakdown dict.
    """
    # ── Normalize ──────────────────────────────────────────────
    text_normalized = normalize_for_detection(text)

    if text != text_normalized:
        print(f"\n{'━' * 70}")
        print(f"🔍 NORMALIZATION APPLIED:")
        print(f"{'━' * 70}")
        print(f"📥 ORIGINAL:   {text!r}")
        print(f"📤 NORMALIZED: {text_normalized!r}")
        print(f"{'━' * 70}\n")

    # ── Individual signals ─────────────────────────────────────
    keyword_score    = compute_keyword_score(text_normalized)
    urgency_score    = compute_urgency_score(text_normalized)
    authority_score  = compute_authority_score(text_normalized)
    # Payment score checks BOTH normalized AND original text
    # (normalizer converts @ → a, which breaks UPI detection)
    payment_score    = max(
        compute_payment_score(text_normalized),
        compute_payment_score(text.lower()),
    )
    llm_analysis = analyze_message(text, history)
    llm_intent_score = llm_analysis["intent"]["confidence"]
    detected_intent  = llm_analysis["intent"]["label"]

    # ── Weighted composite ─────────────────────────────────────
    scam_score = (
        SIGNAL_WEIGHTS["keyword"]         * keyword_score
      + SIGNAL_WEIGHTS["urgency"]         * urgency_score
      + SIGNAL_WEIGHTS["authority"]       * authority_score
      + SIGNAL_WEIGHTS["payment_request"] * payment_score
      + SIGNAL_WEIGHTS["llm_intent"]      * llm_intent_score
    )

    # ── Emotional manipulation boost (up to +0.10) ─────────────
    emotional = detect_emotional_manipulation(text_normalized)
    emotional_count = sum(1 for v in emotional.values() if v)
    emotional_boost = min(0.10, emotional_count * 0.03)
    scam_score = min(1.0, scam_score + emotional_boost)

    # ── History boost (ongoing conversation lowers bar) ────────
    history_boost = 0.0
    if len(history) > 0:
        history_boost = min(0.10, len(history) * 0.02)
        scam_score = min(1.0, scam_score + history_boost)

    # ── Hard-trigger overrides ─────────────────────────────────
    hard_trigger = False
    hard_trigger_reason = None

    # Direct credential requests → always trigger
    if re.search(
        r"\b(share|send|provide|give|enter).{0,15}(otp|cvv|pin|password|mpin)\b",
        text_normalized, re.IGNORECASE,
    ):
        hard_trigger = True
        hard_trigger_reason = "credential_harvest_attempt"
        scam_score = max(scam_score, 0.90)

    # UPI ID + payment language → always trigger  (check ORIGINAL text for @)
    if (
        re.search(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
        and payment_score > 0.3
    ):
        hard_trigger = True
        hard_trigger_reason = "payment_redirection_with_upi"
        scam_score = max(scam_score, 0.80)

    scam_score = round(scam_score, 4)

    return {
        "scam_score": scam_score,
        "is_scam": scam_score >= SCAM_THRESHOLD,
        "is_suspicious": scam_score >= SUSPICIOUS_THRESHOLD,
        "threshold_used": SCAM_THRESHOLD,
        "signals": {
            "keyword": {
                "score": keyword_score,
                "weight": SIGNAL_WEIGHTS["keyword"],
                "weighted": round(keyword_score * SIGNAL_WEIGHTS["keyword"], 4),
            },
            "urgency": {
                "score": urgency_score,
                "weight": SIGNAL_WEIGHTS["urgency"],
                "weighted": round(urgency_score * SIGNAL_WEIGHTS["urgency"], 4),
            },
            "authority": {
                "score": authority_score,
                "weight": SIGNAL_WEIGHTS["authority"],
                "weighted": round(authority_score * SIGNAL_WEIGHTS["authority"], 4),
            },
            "payment_request": {
                "score": payment_score,
                "weight": SIGNAL_WEIGHTS["payment_request"],
                "weighted": round(payment_score * SIGNAL_WEIGHTS["payment_request"], 4),
            },
            "llm_intent": {
                "score": llm_intent_score,
                "weight": SIGNAL_WEIGHTS["llm_intent"],
                "weighted": round(llm_intent_score * SIGNAL_WEIGHTS["llm_intent"], 4),
                "detected_intent": detected_intent,
            },
        },
        "llm_analysis": {
            "intent": llm_analysis["intent"],
            "social_engineering": llm_analysis["social_engineering"],
            "scam_narrative": llm_analysis["scam_narrative"],
            "composite_score": llm_analysis["composite_score"],
            "source": llm_analysis.get("source", "unknown"),
        },
        "boosters": {
            "emotional_manipulation": emotional,
            "emotional_boost": round(emotional_boost, 4),
            "history_boost": round(history_boost, 4),
        },
        "hard_trigger": hard_trigger,
        "hard_trigger_reason": hard_trigger_reason,
    }


# ═══════════════════════════════════════════════════════════════
# PUBLIC API  (backward-compatible with old detect_scam)
# ═══════════════════════════════════════════════════════════════

def detect_scam(text: str, history: list) -> bool:
    """
    Drop-in replacement for original detect_scam.
    Returns True if the message is classified as a scam.
    """
    if not text or len(text.strip()) < 3:
        return False

    result = compute_scam_score(text, history)

    # Log scoring details
    _log_detection(text, result)

    # Primary: above scam threshold
    if result["is_scam"]:
        return True

    # Secondary: suspicious + conversation already ongoing
    if result["is_suspicious"] and len(history) > 0:
        return True
    
    # NEW: suspicious + authority impersonation → engage immediately (even on first message)
    # Messages claiming to be from banks, police, cyber cell should always engage
    if result["is_suspicious"] and result["signals"]["authority"]["score"] >= 0.3:
        return True

    # Tertiary: hard signals (URL / phone / UPI) maintain backward compat
    # Check ORIGINAL text for UPI (@ survives) and normalized for URLs/phones
    text_normalized = normalize_for_detection(text)
    has_url   = bool(re.search(r"https?://", text)) or bool(re.search(r"https?://", text_normalized))
    has_phone = bool(re.search(r"\+?\d{10,}", text))
    has_upi   = bool(re.search(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text))

    if has_url or has_upi or has_phone:
        return True

    return False


def detect_scam_detailed(text: str, history: list) -> Dict:
    """
    Full scoring breakdown (for /debug/score endpoint or frontend display).
    """
    if not text or len(text.strip()) < 3:
        return {
            "scam_score": 0.0,
            "is_scam": False,
            "is_suspicious": False,
            "signals": {},
            "boosters": {},
            "hard_trigger": False,
            "hard_trigger_reason": None,
        }

    return compute_scam_score(text, history)


# ═══════════════════════════════════════════════════════════════
# RED FLAG DETECTOR  (human-readable list for frontend/output)
# ═══════════════════════════════════════════════════════════════

def detect_red_flags(text: str, history: list, precomputed: Dict = None) -> List[str]:
    """
    Return a list of plain-English red flag strings detected in the message.
    Draws on all scoring signals, hard triggers, emotional patterns, and
    LLM analysis so the frontend can display them to an analyst.
    Accepts an optional pre-computed result from detect_scam_detailed to
    avoid redundant LLM calls.
    """
    if not text or len(text.strip()) < 3:
        return []

    result = precomputed if precomputed is not None else compute_scam_score(text, history)
    signals = result["signals"]
    boosters = result["boosters"]
    llm = result.get("llm_analysis", {})

    flags: List[str] = []

    # ── Hard triggers (highest confidence) ──
    if result["hard_trigger"]:
        reason = result["hard_trigger_reason"]
        if reason == "credential_harvest_attempt":
            flags.append("Credential harvesting — asks for OTP, PIN, CVV, or password")
        elif reason == "payment_redirection_with_upi":
            flags.append("Payment redirection — provides UPI ID alongside payment pressure")

    # ── Signal-based flags ──
    if signals.get("urgency", {}).get("score", 0) >= 0.5:
        flags.append("Artificial urgency — uses time pressure or threat of immediate consequences")
    elif signals.get("urgency", {}).get("score", 0) >= 0.25:
        flags.append("Mild urgency language detected")

    if signals.get("authority", {}).get("score", 0) >= 0.5:
        flags.append("Authority impersonation — claims to be bank, government, or law enforcement")
    elif signals.get("authority", {}).get("score", 0) >= 0.25:
        flags.append("Possible authority impersonation")

    if signals.get("payment_request", {}).get("score", 0) >= 0.5:
        flags.append("Unsolicited payment request — pressuring victim to transfer money")
    elif signals.get("payment_request", {}).get("score", 0) >= 0.25:
        flags.append("Payment-related language detected")

    if signals.get("keyword", {}).get("score", 0) >= 0.6:
        flags.append("High concentration of known scam keywords")

    # ── Emotional manipulation flags ──
    emotional = boosters.get("emotional_manipulation", {})
    if emotional.get("fear"):
        flags.append("Fear manipulation — threatens arrest, loss, or harm")
    if emotional.get("greed"):
        flags.append("Greed manipulation — promises prize, reward, or easy money")
    if emotional.get("sympathy"):
        flags.append("Sympathy manipulation — invokes emergency or helplessness")
    if emotional.get("guilt"):
        flags.append("Guilt manipulation — pressures victim to comply by questioning trust")

    # ── LLM-derived flags ──
    narrative_cat = llm.get("scam_narrative", {}).get("category", "unknown")
    if narrative_cat and narrative_cat not in ("unknown", ""):
        label = narrative_cat.replace("_", " ").title()
        flags.append(f"Scam type identified: {label}")

    se = llm.get("social_engineering", {})
    se_tactics = [k for k, v in se.items() if v is True]
    if se_tactics:
        readable = ", ".join(t.replace("_", " ").title() for t in se_tactics)
        flags.append(f"Social engineering tactics: {readable}")

    intent_label = llm.get("intent", {}).get("label", "")
    intent_conf = llm.get("intent", {}).get("confidence", 0)
    if intent_label and intent_label not in ("benign", "unknown", "") and intent_conf >= 0.5:
        flags.append(f"LLM intent classification: {intent_label.replace('_', ' ').title()} (confidence {intent_conf:.0%})")

    return flags


# ═══════════════════════════════════════════════════════════════
# LOGGING HELPER
# ═══════════════════════════════════════════════════════════════

def _log_detection(text: str, result: Dict):
    """Pretty-print detection result for server logs."""
    score = result["scam_score"]
    if result["is_scam"]:
        verdict = "🚨 SCAM"
    elif result["is_suspicious"]:
        verdict = "⚠️  SUSPICIOUS"
    else:
        verdict = "✅ CLEAN"

    signals = result["signals"]
    trigger = (
        f" [HARD TRIGGER: {result['hard_trigger_reason']}]"
        if result["hard_trigger"]
        else ""
    )

    print(f"\n{'━' * 70}")
    print(f"🔍 HYBRID DETECTION: {verdict} (score={score:.4f}){trigger}")
    print(f"{'━' * 70}")
    print(f"  📝 Text: {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"  ┌─ Keyword:         {signals['keyword']['score']:.4f} × {signals['keyword']['weight']} = {signals['keyword']['weighted']:.4f}")
    print(f"  ├─ Urgency:         {signals['urgency']['score']:.4f} × {signals['urgency']['weight']} = {signals['urgency']['weighted']:.4f}")
    print(f"  ├─ Authority:       {signals['authority']['score']:.4f} × {signals['authority']['weight']} = {signals['authority']['weighted']:.4f}")
    print(f"  ├─ Payment Request: {signals['payment_request']['score']:.4f} × {signals['payment_request']['weight']} = {signals['payment_request']['weighted']:.4f}")
    print(f"  ├─ LLM Intent:      {signals['llm_intent']['score']:.4f} × {signals['llm_intent']['weight']} = {signals['llm_intent']['weighted']:.4f}  [{signals['llm_intent']['detected_intent']}]")
    print(f"  ├─ Emotional Boost: +{result['boosters']['emotional_boost']:.4f}")
    print(f"  └─ History Boost:   +{result['boosters']['history_boost']:.4f}")
    print(f"{'━' * 70}")
