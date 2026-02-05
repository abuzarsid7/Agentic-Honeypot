import re

def extract_intel(session, text):
    """
    Enhanced intelligence extraction with comprehensive pattern matching.
    Automatically deduplicates entries.
    """
    text_l = text.lower()
    
    # Extract UPI IDs (handle various formats)
    upis = re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
    for upi in upis:
        if upi not in session["intel"]["upiIds"]:
            session["intel"]["upiIds"].append(upi)
    
    # Extract phone numbers (multiple formats)
    # +91xxxxxxxxxx, 91xxxxxxxxxx, or 10-digit numbers in context
    phones = re.findall(r"\+?91\d{10}|\+\d{10,}|(?<![\d])\d{10}(?![\d])", text)
    for phone in phones:
        cleaned_phone = phone.strip()
        if cleaned_phone and cleaned_phone not in session["intel"]["phoneNumbers"]:
            session["intel"]["phoneNumbers"].append(cleaned_phone)
    
    # Extract URLs/links
    links = re.findall(r"https?://\S+", text)
    for link in links:
        # Clean up trailing punctuation
        link = link.rstrip('.,;:!?)')
        if link not in session["intel"]["phishingLinks"]:
            session["intel"]["phishingLinks"].append(link)
    
    # Extract potential bank account numbers (8-16 digits)
    accounts = re.findall(r"\b\d{8,16}\b", text)
    for account in accounts:
        # Avoid phone numbers that might be caught here
        if len(account) != 10 and account not in session["intel"]["bankAccounts"]:
            session["intel"]["bankAccounts"].append(account)
    
    # Track suspicious keywords (deduplicated)
    keywords = [
        'upi', 'verify', 'urgent', 'blocked', 'suspended', 'kyc',
        'otp', 'cvv', 'pin', 'password', 'expire', 'immediately',
        'customer care', 'refund', 'wallet', 'paytm', 'phonepe', 'gpay'
    ]
    
    for keyword in keywords:
        if keyword in text_l and keyword not in session["intel"]["suspiciousKeywords"]:
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
