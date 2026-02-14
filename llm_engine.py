"""
LLM Analysis Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Centralized LLM integration for the Agnetic HoneyPot.
Provides three analysis capabilities via a single batched call:
  1. Intent Classification       — what the scammer is trying to do
  2. Social Engineering Detection — manipulation tactics in use
  3. Scam Narrative Classification — which scam playbook is being run

Features:
  • Structured JSON output (validated with fallback)
  • In-memory TTL cache keyed on normalised text hash
  • Automatic heuristic fallback when LLM is unavailable or fails
  • Supports OpenAI, Groq (and any OpenAI-compatible endpoint)

Usage:
    from llm_engine import analyze_message, get_llm_analysis, get_cache_stats

    # Full structured analysis (cached, with fallback)
    result = analyze_message(text, history)

    # Just the LLM intent score for the weighted model
    score, intent = get_llm_intent(text, history)
"""

import os
import re
import json
import time
import hashlib
from typing import Dict, Tuple, Optional, Any
from collections import OrderedDict
from normalizer import normalize_for_detection
from openai import OpenAI
from groq import Groq
import redis_client

def get_llm_cache(prompt: str):
    key = hashlib.sha256(prompt.encode()).hexdigest()
    return redis_client.get(f"llm_cache:{key}")

def set_llm_cache(prompt: str, response: str):
    key = hashlib.sha256(prompt.encode()).hexdigest()
    redis_client.setex(
        f"llm_cache:{key}",
        86400,  # 24 hours
        response
    )
# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Cache settings
CACHE_MAX_SIZE = 512          # max entries
CACHE_TTL_SECONDS = 600       # 10 minutes

# LLM provider auto-detection order
_LLM_PROVIDERS = [
    {
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "label": "Groq",
    },
    {
        "env_key": "OPENAI_API_KEY",
        "base_url": None,   # default
        "model": "gpt-5.2-mini",
        "label": "OpenAI",
    },
]


# ═══════════════════════════════════════════════════════════════
# STRUCTURED OUTPUT SCHEMA
# ═══════════════════════════════════════════════════════════════

ANALYSIS_SCHEMA = {
    "intent": {
        "label": "",           # e.g. "credential_harvesting"
        "confidence": 0.0,     # 0.0 – 1.0
        "reasoning": "",
    },
    "social_engineering": {
        "tactics": [],         # e.g. ["fear", "authority", "urgency"]
        "severity": "",        # "none" | "low" | "medium" | "high" | "critical"
        "details": "",
    },
    "scam_narrative": {
        "category": "",        # e.g. "bank_impersonation"
        "stage": "",           # "opening" | "building_trust" | "exploitation" | "closing"
        "description": "",
    },
    "composite_score": 0.0,    # overall scam likelihood 0.0 – 1.0
    "source": "",              # "llm" | "heuristic"
}

# Intent categories (shared with heuristic fallback)
INTENT_CATEGORIES = [
    "credential_harvesting",
    "phishing_link",
    "financial_fraud",
    "impersonation_scam",
    "tech_support_scam",
    "payment_redirection",
    "emotional_manipulation",
    "advance_fee_fraud",
    "romance_scam",
    "benign",
]

# Social engineering tactics
SE_TACTICS = [
    "fear", "urgency", "authority", "scarcity",
    "social_proof", "reciprocity", "greed",
    "sympathy", "guilt", "intimidation",
]

# Scam narrative categories
NARRATIVE_CATEGORIES = [
    "bank_impersonation",
    "government_impersonation",
    "tech_support",
    "lottery_prize",
    "investment_fraud",
    "romance_scam",
    "job_offer_scam",
    "delivery_scam",
    "tax_refund",
    "account_verification",
    "kyc_update",
    "loan_approval",
    "custom_clearance",
    "unknown",
]


# ═══════════════════════════════════════════════════════════════
# LLM PROMPT
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are a cybersecurity analyst specializing in scam and fraud detection.
Analyze the given message (and optional conversation history) and return
a single JSON object with EXACTLY these three sections:

{
  "intent": {
    "label": "<one of: credential_harvesting, phishing_link, financial_fraud, impersonation_scam, tech_support_scam, payment_redirection, emotional_manipulation, advance_fee_fraud, romance_scam, benign>",
    "confidence": <float 0.0-1.0>,
    "reasoning": "<one sentence>"
  },
  "social_engineering": {
    "tactics": [<list of: fear, urgency, authority, scarcity, social_proof, reciprocity, greed, sympathy, guilt, intimidation>],
    "severity": "<none|low|medium|high|critical>",
    "details": "<one sentence>"
  },
  "scam_narrative": {
    "category": "<one of: bank_impersonation, government_impersonation, tech_support, lottery_prize, investment_fraud, romance_scam, job_offer_scam, delivery_scam, tax_refund, account_verification, kyc_update, loan_approval, custom_clearance, unknown>",
    "stage": "<opening|building_trust|exploitation|closing>",
    "description": "<one sentence>"
  },
  "composite_score": <float 0.0-1.0>
}

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no extra keys.
- Be conservative: only flag as scam if there are clear indicators.
- composite_score should reflect overall scam likelihood.
"""


def _build_user_prompt(text: str, history: list) -> str:
    """Build the user-role prompt with conversation context."""
    parts = []

    if history:
        parts.append("Conversation history (most recent):")
        recent = history[-8:]
        for msg in recent:
            sender = msg.get("sender", "unknown")
            role = "Scammer" if sender == "scammer" else "Victim"
            parts.append(f"  {role}: {msg.get('text', '')}")
        parts.append("")

    parts.append(f'Analyze this latest message:\n"{text}"')
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# RESPONSE CACHE (LRU + TTL)
# ═══════════════════════════════════════════════════════════════

class _LRUTTLCache:
    """Simple LRU cache with per-entry TTL expiration."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self._store: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, history: list) -> str:
        history_tail = ""
        if history:
            history_tail = "|".join(
                m.get("text", "")[:60] for m in history[-4:]
            )
        raw = f"{text}||{history_tail}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, text: str, history: list) -> Optional[Dict]:
        key = self._make_key(text, history)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            self._misses += 1
            return None
        # Move to end (most-recently used)
        self._store.move_to_end(key)
        self._hits += 1
        return value

    def put(self, text: str, history: list, value: Dict):
        key = self._make_key(text, history)
        self._store[key] = (time.time(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 2) if total > 0 else 0.0,
        }

    def clear(self):
        self._store.clear()
        self._hits = 0
        self._misses = 0


_cache = _LRUTTLCache()


def get_cache_stats() -> Dict:
    """Return cache performance stats."""
    return _cache.stats()


def clear_cache():
    """Flush the LLM analysis cache."""
    _cache.clear()


# ═══════════════════════════════════════════════════════════════
# HEURISTIC FALLBACK ENGINE
# ═══════════════════════════════════════════════════════════════

# --- Intent heuristics ---
_INTENT_RULES = {
    "credential_harvesting": {
        "patterns": [
            r"\b(share|provide|send|enter|type|give).{0,25}(otp|cvv|pin|password|mpin|card.?number)\b",
            r"\b(otp|cvv|pin|password|mpin).{0,20}(share|send|provide|enter|give|tell)\b",
            r"\b(what is your|tell me your|enter your|share your).{0,20}(otp|pin|password|cvv)\b",
        ],
        "confidence": 0.92,
    },
    "phishing_link": {
        "patterns": [
            r"\b(click|open|visit|go to|tap)\b.{0,30}(link|url|website|page|site)",
            r"https?://\S+",
            r"\b(verify|update|confirm).{0,15}(by clicking|via link|on this link)\b",
        ],
        "confidence": 0.75,
    },
    "financial_fraud": {
        "patterns": [
            r"\b(won|winning|winner|lottery|prize|jackpot|lucky draw)\b",
            r"\b(invest|investment|guaranteed returns|double your money)\b",
            r"\b(inheritance|unclaimed funds|beneficiary)\b",
        ],
        "confidence": 0.82,
    },
    "impersonation_scam": {
        "patterns": [
            r"\b(this is .{0,20}(officer|bank|department|police|customs))\b",
            r"\b(calling from .{0,20}(bank|rbi|police|cyber|government))\b",
            r"\b(we have detected|we found|your account has)\b",
        ],
        "confidence": 0.78,
    },
    "tech_support_scam": {
        "patterns": [
            r"\b(virus|malware|trojan|hacked|breached|compromised)\b",
            r"\b(remote access|anydesk|teamviewer|download .{0,15}(app|software))\b",
            r"\b(your (computer|phone|device) .{0,20}(infected|at risk|compromised))\b",
        ],
        "confidence": 0.83,
    },
    "payment_redirection": {
        "patterns": [
            r"\b(send|transfer|pay|deposit).{0,25}(money|amount|rs|rupees?|inr|₹|\$)\b",
            r"\b(processing fee|service charge|verification fee|refundable deposit)\b",
            r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}",
        ],
        "confidence": 0.80,
    },
    "advance_fee_fraud": {
        "patterns": [
            r"\b(advance|upfront|small).{0,15}(fee|charge|payment|deposit)\b",
            r"\b(release|unlock|claim).{0,20}(funds?|prize|reward|amount)\b",
        ],
        "confidence": 0.80,
    },
    "emotional_manipulation": {
        "patterns": [
            r"\b(you will lose|lose all|risk losing|permanently lose)\b",
            r"\b(arrested|jail|criminal|prosecution|sued)\b",
            r"\b(please help|i (need|beg)|dying|hospital|emergency)\b",
            r"\b(everyone is doing|don't you trust|are you scared)\b",
        ],
        "confidence": 0.68,
    },
}

# --- Social-engineering tactic heuristics ---
_SE_RULES = {
    "fear": [
        r"\b(you will lose|lose (all|everything)|risk losing)\b",
        r"\b(arrested|jail|criminal|prosecution)\b",
        r"\b(compromised|breached|unauthorized)\b",
    ],
    "urgency": [
        r"\b(urgent|immediately|right now|asap|hurry|quickly)\b",
        r"\b(within \d+ (hour|minute|day)s?)\b",
        r"\b(last chance|final warning|deadline|today only)\b",
    ],
    "authority": [
        r"\b(officer|inspector|manager|director|executive)\b",
        r"\b(reserve bank|rbi|government|ministry|department)\b",
        r"\b(as per (rbi|government|regulation|policy))\b",
    ],
    "scarcity": [
        r"\b(limited (time|offer|slots?)|only \d+ left|exclusive)\b",
        r"\b(first come|while (stocks?|supplies?) last)\b",
    ],
    "social_proof": [
        r"\b(everyone|all (customers|users)|many people|thousands)\b",
        r"\b(already (received|claimed|verified))\b",
    ],
    "reciprocity": [
        r"\b(free|complimentary|bonus|gift|as a token)\b",
        r"\b(we are giving|you have been selected)\b",
    ],
    "greed": [
        r"\b(won|winning|prize|reward|cashback|bonus|jackpot)\b",
        r"\b(guaranteed|100%|easy money|double|crore|lakh|million)\b",
    ],
    "sympathy": [
        r"\b(please help|need help|emergency|hospital|accident)\b",
        r"\b(stranded|stuck|helpless|dying|illness)\b",
    ],
    "guilt": [
        r"\b(don't you trust|why won't you|are you refusing)\b",
        r"\b(if you (don't|refuse|fail to))\b",
    ],
    "intimidation": [
        r"\b(legal action|police|arrest|court|case filed)\b",
        r"\b(permanent(ly)? (block|suspend|ban|close|delete))\b",
    ],
}

# --- Narrative heuristics ---
_NARRATIVE_RULES = {
    "bank_impersonation": [
        r"\b(bank|sbi|hdfc|icici|axis|pnb|rbi).{0,30}(blocked|suspended|frozen|verify|officer|manager|alert)\b",
        r"\b(account|debit card|credit card).{0,20}(blocked|suspended|compromised|frozen)\b",
        r"\b(sbi|hdfc|icici|axis|pnb|rbi)\b.*\b(otp|verify|blocked|officer|account)\b",
    ],
    "government_impersonation": [
        r"\b(government|ministry|aadhaar|pan card|income tax|it department)\b",
        r"\b(customs|immigration|cyber cell|cyber crime)\b",
    ],
    "tech_support": [
        r"\b(virus|malware|hacked|remote access|anydesk|teamviewer)\b",
        r"\b(microsoft|apple|google).{0,15}(support|helpline|alert)\b",
    ],
    "lottery_prize": [
        r"\b(won|winner|lottery|lucky draw|prize|jackpot|congratulations)\b",
    ],
    "investment_fraud": [
        r"\b(invest|investment|guaranteed returns|high returns|trading)\b",
        r"\b(double your|triple your|10x|100x)\b",
    ],
    "kyc_update": [
        r"\b(kyc|know your customer).{0,20}(update|verify|expired|mandatory)\b",
    ],
    "account_verification": [
        r"\b(verify|validate|confirm).{0,20}(account|identity|details)\b",
    ],
    "loan_approval": [
        r"\b(loan|credit).{0,15}(approved|sanctioned|pre-?approved|eligible)\b",
    ],
    "delivery_scam": [
        r"\b(package|parcel|delivery|shipment).{0,20}(stuck|held|customs|fee)\b",
    ],
    "tax_refund": [
        r"\b(tax|refund|it returns?).{0,20}(claim|pending|eligible|process)\b",
    ],
}


def _heuristic_intent(text: str) -> Dict:
    """Heuristic intent classification."""
    best_score = 0.0
    best_intent = "benign"
    best_reason = "No scam indicators detected."

    for intent, data in _INTENT_RULES.items():
        for pattern in data["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                if data["confidence"] > best_score:
                    best_score = data["confidence"]
                    best_intent = intent
                    best_reason = f"Pattern match: {intent.replace('_', ' ')} indicators found."
                break

    return {
        "label": best_intent,
        "confidence": round(best_score, 4),
        "reasoning": best_reason,
    }


def _heuristic_social_engineering(text: str) -> Dict:
    """Heuristic social-engineering detection."""
    detected = []
    for tactic, patterns in _SE_RULES.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                detected.append(tactic)
                break

    count = len(detected)
    if count == 0:
        severity = "none"
    elif count <= 1:
        severity = "low"
    elif count <= 2:
        severity = "medium"
    elif count <= 3:
        severity = "high"
    else:
        severity = "critical"

    details = (
        f"Detected {count} social-engineering tactic(s): {', '.join(detected)}."
        if detected
        else "No social-engineering tactics detected."
    )

    return {
        "tactics": detected,
        "severity": severity,
        "details": details,
    }


def _heuristic_narrative(text: str) -> Dict:
    """Heuristic scam-narrative classification."""
    for category, patterns in _NARRATIVE_RULES.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return {
                    "category": category,
                    "stage": "exploitation",   # heuristic can't tell stage well
                    "description": f"Message matches {category.replace('_', ' ')} scam pattern.",
                }

    return {
        "category": "unknown",
        "stage": "opening",
        "description": "No recognised scam narrative detected.",
    }


def _heuristic_analysis(text: str, history: list) -> Dict:
    """Full heuristic fallback — mirrors the LLM output schema."""
    text_lower = text.lower()

    intent   = _heuristic_intent(text_lower)
    se       = _heuristic_social_engineering(text_lower)
    narrative = _heuristic_narrative(text_lower)

    # Composite: blend intent confidence with SE severity
    severity_map = {"none": 0.0, "low": 0.2, "medium": 0.4, "high": 0.7, "critical": 0.9}
    composite = round(
        0.6 * intent["confidence"]
      + 0.4 * severity_map.get(se["severity"], 0.0),
        4,
    )

    return {
        "intent": intent,
        "social_engineering": se,
        "scam_narrative": narrative,
        "composite_score": composite,
        "source": "heuristic",
    }


# ═══════════════════════════════════════════════════════════════
# LLM CLIENT
# ═══════════════════════════════════════════════════════════════

def _get_llm_client():
    """
    Auto-detect and return (client, model, label) or None.
    Tries Groq first (free / fast), then OpenAI.
    """
    try:
        import openai  # noqa: F811
    except ImportError:
        return None

    for provider in _LLM_PROVIDERS:
        api_key = os.getenv(provider["env_key"])
        if api_key:
            kwargs = {"api_key": api_key}
            if provider["base_url"]:
                kwargs["base_url"] = provider["base_url"]
            client = openai.OpenAI(**kwargs)
            return client, provider["model"], provider["label"]

    return None


def _validate_llm_response(raw: Dict) -> Dict:
    """
    Validate and sanitize LLM JSON output.
    Fills in defaults for any missing or malformed fields.
    """
    result = {}

    # --- Intent ---
    intent_raw = raw.get("intent", {})
    label = intent_raw.get("label", "benign")
    if label not in INTENT_CATEGORIES:
        label = "benign"
    result["intent"] = {
        "label": label,
        "confidence": max(0.0, min(1.0, float(intent_raw.get("confidence", 0.0)))),
        "reasoning": str(intent_raw.get("reasoning", ""))[:200],
    }

    # --- Social engineering ---
    se_raw = raw.get("social_engineering", {})
    tactics = [t for t in se_raw.get("tactics", []) if t in SE_TACTICS]
    severity = se_raw.get("severity", "none")
    if severity not in ("none", "low", "medium", "high", "critical"):
        severity = "none"
    result["social_engineering"] = {
        "tactics": tactics,
        "severity": severity,
        "details": str(se_raw.get("details", ""))[:200],
    }

    # --- Scam narrative ---
    narr_raw = raw.get("scam_narrative", {})
    category = narr_raw.get("category", "unknown")
    if category not in NARRATIVE_CATEGORIES:
        category = "unknown"
    stage = narr_raw.get("stage", "opening")
    if stage not in ("opening", "building_trust", "exploitation", "closing"):
        stage = "opening"
    result["scam_narrative"] = {
        "category": category,
        "stage": stage,
        "description": str(narr_raw.get("description", ""))[:200],
    }

    # --- Composite ---
    result["composite_score"] = round(
        max(0.0, min(1.0, float(raw.get("composite_score", 0.0)))), 4
    )
    result["source"] = "llm"

    return result


def _call_llm(text: str, history: list) -> Optional[Dict]:
    """
    Make a single LLM call and return validated structured JSON.
    Returns None on any failure (caller will fall back to heuristic).
    """
    provider_info = _get_llm_client()
    if provider_info is None:
        return None

    client, model, label = provider_info

    try:
        user_prompt = _build_user_prompt(text, history)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=400,
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()

        # Strip markdown fences if LLM wraps output
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        raw = json.loads(content)
        result = _validate_llm_response(raw)
        result["_llm_provider"] = label
        result["_llm_model"] = model
        return result

    except json.JSONDecodeError as e:
        print(f"⚠️  LLM returned invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"⚠️  LLM call failed ({type(e).__name__}): {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def analyze_message(text: str, history: list | None = None) -> Dict:
    """
    Full LLM-powered analysis with cache and heuristic fallback.

    Returns structured JSON:
    {
        "intent":              { "label", "confidence", "reasoning" },
        "social_engineering":  { "tactics", "severity", "details" },
        "scam_narrative":      { "category", "stage", "description" },
        "composite_score":     float,
        "source":              "llm" | "heuristic",
    }
    """
    if history is None:
        history = []

    # Normalise for consistent cache keys
    text_norm = normalize_for_detection(text)

    # 1️⃣  Cache check
    cached = _cache.get(text_norm, history)
    if cached is not None:
        cached["_cache"] = "hit"
        return cached

    # 2️⃣  Try LLM
    result = _call_llm(text, history)

    # 3️⃣  Fallback to heuristic
    if result is None:
        result = _heuristic_analysis(text_norm, history)

    # 4️⃣  Cache result
    _cache.put(text_norm, history, result)
    result["_cache"] = "miss"

    return result


def get_llm_intent(text: str, history: list | None = None) -> Tuple[float, str]:
    """
    Convenience wrapper for the weighted scoring model in detector.py.
    Returns (confidence_score, intent_label).
    """
    result = analyze_message(text, history)
    return result["intent"]["confidence"], result["intent"]["label"]


def is_llm_available() -> bool:
    """Check whether an LLM provider is configured."""
    return _get_llm_client() is not None


def get_provider_info() -> Dict:
    """Return info about the active LLM provider (or None)."""
    info = _get_llm_client()
    if info is None:
        return {"available": False, "provider": None, "model": None}
    _, model, label = info
    return {"available": True, "provider": label, "model": model}
