import re

# ═══════════════════════════════════════════════════════════════
# 🔥 IMPORT NORMALIZATION MODULE
# ═══════════════════════════════════════════════════════════════
from normalizer import normalize_input, normalize_for_detection

SCAM_KEYWORDS = [
    "account", "blocked", "verify", "urgent", "immediately",
    "upi", "bank", "suspended", "link", "click", "update",
    "confirm", "security", "expire", "freeze", "locked",
    "payment", "transfer", "wallet", "paytm", "phonepe",
    "gpay", "refund", "reward", "prize", "congratulations",
    "customer care", "support", "helpline", "kyc", "otp",
    "debit", "credit", "transaction", "failed", "pending"
]

def detect_scam(text, history):
    """
    🔥 ENHANCED: Now with normalization preprocessing
    
    Scam detection with multiple signals - defeats obfuscation attacks.
    Returns True if message appears suspicious.
    """
    if not text or len(text.strip()) < 3:
        return False
    
    # ═══════════════════════════════════════════════════════════
    # 🔥 CRITICAL: Normalize input BEFORE detection
    # This defeats: zero-width chars, homoglyphs, leetspeak, URL obfuscation
    # ═══════════════════════════════════════════════════════════
    text_normalized = normalize_for_detection(text)
    text_lower = text_normalized  # Already lowercase from normalization
    
    # 📍 DEBUG: Print normalization results
    if text != text_normalized:
        print(f"\n{'━'*70}")
        print(f"🔍 NORMALIZATION APPLIED:")
        print(f"{'━'*70}")
        print(f"📥 ORIGINAL:   {text!r}")
        print(f"📤 NORMALIZED: {text_normalized!r}")
        print(f"{'━'*70}\n")
    
    # Check 1: Keyword matching (more lenient)
    keyword_score = sum(1 for k in SCAM_KEYWORDS if k in text_lower)
    
    # Check 2: Contains URLs
    has_url = bool(re.search(r'https?://', text))
    
    # Check 3: Contains phone numbers
    has_phone = bool(re.search(r'\+?\d{10,}', text))
    
    # Check 4: Contains UPI IDs
    has_upi = bool(re.search(r'[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}', text))
    
    # Check 5: Contains account/card numbers (8+ consecutive digits)
    has_financial_number = bool(re.search(r'\d{8,}', text))
    
    # Check 6: Urgency indicators
    urgency_words = ['urgent', 'immediately', 'now', 'asap', 'quickly', 'hurry']
    has_urgency = any(word in text_lower for word in urgency_words)
    
    # Decision logic: be more permissive
    # Engage if ANY of these conditions are met:
    if has_url or has_upi or has_phone:
        return True
    
    if keyword_score >= 2:  # At least 2 scam keywords
        return True
    
    if keyword_score >= 1 and (has_urgency or has_financial_number):
        return True
    
    # If this is not the first message in conversation, be more lenient
    if len(history) > 0 and keyword_score >= 1:
        return True
    
    return False