import re

# ═══════════════════════════════════════════════════════════════
# 🔥 IMPORT NORMALIZATION HELPERS
# ═══════════════════════════════════════════════════════════════
from normalizer import (
    normalize_url_for_extraction,
    normalize_unicode,
    remove_zero_width,
    normalize_whitespace
)
from telemetry import track_intelligence

def extract_intel(session, text):
    """
    🔥 ENHANCED: Smart normalization for extraction
    
    Intelligence extraction with comprehensive pattern matching.
    Uses LIGHT normalization to preserve phone numbers and UPIs.
    """
    # ═══════════════════════════════════════════════════════════
    # 🔥 CRITICAL: Use LIGHT normalization for extraction
    # We want to remove invisible chars but preserve numbers!
    # ═══════════════════════════════════════════════════════════
    
    # Light normalization: only remove invisible chars and normalize whitespace
    text_clean = normalize_unicode(text)
    text_clean = remove_zero_width(text_clean)
    text_clean = normalize_whitespace(text_clean)
    
    # For keyword matching, use lowercase
    text_lower = text_clean.lower()
    
    # Extract UPI IDs - use lightly normalized text
    upis = re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text_clean)
    new_upis = 0
    for upi in upis:
        if upi not in session["intel"]["upiIds"]:
            session["intel"]["upiIds"].append(upi)
            new_upis += 1
    if new_upis > 0:
        track_intelligence("upi", new_upis)
    
    # Extract phone numbers (multiple formats) - PRESERVE ORIGINAL NUMBERS
    # +91xxxxxxxxxx, 91xxxxxxxxxx, or 10-digit numbers in context
    phones = re.findall(r"\+?91\d{10}|\+\d{10,}|(?<![\d])\d{10}(?![\d])", text_clean)
    new_phones = 0
    for phone in phones:
        cleaned_phone = phone.strip()
        if cleaned_phone and cleaned_phone not in session["intel"]["phoneNumbers"]:
            session["intel"]["phoneNumbers"].append(cleaned_phone)
            new_phones += 1
    if new_phones > 0:
        track_intelligence("phone", new_phones)
    
    # Extract URLs/links - use lightly normalized text
    links = re.findall(r"https?://\S+", text_clean)
    new_urls = 0
    for link in links:
        # Clean up trailing punctuation
        link = link.rstrip('.,;:!?)')
        # Apply URL-specific normalization for deobfuscation
        link_normalized = normalize_url_for_extraction(link)
        if link_normalized not in session["intel"]["phishingLinks"]:
            session["intel"]["phishingLinks"].append(link_normalized)
            new_urls += 1
    if new_urls > 0:
        track_intelligence("url", new_urls)
    
    # Extract potential bank account numbers (8-16 digits) - use lightly normalized text
    accounts = re.findall(r"\b\d{8,16}\b", text_clean)
    new_accounts = 0
    for account in accounts:
        # Avoid phone numbers that might be caught here
        if len(account) != 10 and account not in session["intel"]["bankAccounts"]:
            session["intel"]["bankAccounts"].append(account)
            new_accounts += 1
    if new_accounts > 0:
        track_intelligence("account", new_accounts)
    
    # Track suspicious keywords (deduplicated)
    keywords = [
        'upi', 'verify', 'urgent', 'blocked', 'suspended', 'kyc',
        'otp', 'cvv', 'pin', 'password', 'expire', 'immediately',
        'customer care', 'refund', 'wallet', 'paytm', 'phonepe', 'gpay'
    ]
    
    for keyword in keywords:
        if keyword in text_lower and keyword not in session["intel"]["suspiciousKeywords"]:
            session["intel"]["suspiciousKeywords"].append(keyword)

def maybe_finish(session):
    """
    Determine if conversation should end based on multiple criteria.
    """
    # End if we've had 15+ messages
    if session["messages"] >= 15:
        return True
    
    # End if we've collected substantial intel (at least 3 different types)
    intel_collected = 0
    if session["intel"]["upiIds"]:
        intel_collected += 1
    if session["intel"]["phoneNumbers"]:
        intel_collected += 1
    if session["intel"]["phishingLinks"]:
        intel_collected += 1
    if session["intel"]["bankAccounts"]:
        intel_collected += 1
    
    # If we have rich intel and conversation is long enough (10+ messages)
    if intel_collected >= 3 and session["messages"] >= 10:
        return True
    
    # End if conversation reaches 20 messages regardless
    if session["messages"] >= 20:
        return True
    
    return False
