""" 
Hybrid Intelligence Extraction Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Combines multiple extraction techniques:
1. Regex-based extraction (fast, reliable)
2. Advanced pattern extraction (obfuscated URLs, split numbers, number words)
3. LLM-based extraction (context-aware, handles edge cases)
4. Merge & deduplication (normalized, consolidated results)
"""

import json
import re
import os
from typing import Dict, List, Set, Tuple
from redis_client import redis_client

def store_intel(session_id, intel_data):
    redis_client.rpush(
        f"intel:{session_id}",
        json.dumps(intel_data)
    )

# ═══════════════════════════════════════════════════════════════
# IMPORT DEPENDENCIES
# ═══════════════════════════════════════════════════════════════
from normalizer import (
    normalize_url_for_extraction,
    normalize_unicode,
    remove_zero_width,
    remove_control_characters,
    normalize_homoglyphs,
    deobfuscate_char_spacing,
    deobfuscate_urls,
    expand_shortened_urls,
    normalize_whitespace,
    normalize_phone_for_extraction,
)
from telemetry import track_intelligence


# ═══════════════════════════════════════════════════════════════
# ADVANCED PATTERN EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_obfuscated_urls(text: str) -> List[str]:
    """
    Extract URLs with obfuscation techniques:
    - Character-spaced: "h t t p : / / s b i . c o m"
    - hxxp/hxxps instead of http/https
    - [.] or (.) or [dot] instead of .
    - Spelled out: "google dot com slash phish"
    - Spaces: "example . com"
    """
    urls = []

    # Pre-process: collapse character-spacing obfuscation first
    text_collapsed = deobfuscate_char_spacing(text)
    text_lower = text_collapsed.lower()
    
    # Pattern 1: hxxp/hxxps URLs
    hxxp_urls = re.findall(r'hxxps?://[\w\-\.\[\]\(\)]+', text_lower)
    for url in hxxp_urls:
        # De-obfuscate
        deobf = url.replace('hxxp://', 'http://').replace('hxxps://', 'https://')
        deobf = deobf.replace('[.]', '.').replace('(.)', '.').replace('[dot]', '.')
        urls.append(deobf)
    
    # Pattern 2: URLs with [.] or (.) or [dot]
    bracket_urls = re.findall(r'https?://[\w\-]+(?:\[\.\]|\(\.\)|\[dot\])[\w\-\.\[\]\(\)]+', text_lower)
    for url in bracket_urls:
        deobf = url.replace('[.]', '.').replace('(.)', '.').replace('[dot]', '.')
        urls.append(deobf)
    
    # Pattern 3: Spelled out URLs (google dot com slash something)
    spelled_pattern = r'([\w\-]+)\s+(?:dot|DOT)\s+([\w]+)(?:\s+(?:slash|/)\s+([\w\-]+))?'
    spelled_urls = re.findall(spelled_pattern, text, re.IGNORECASE)
    for match in spelled_urls:
        domain, tld, path = match
        url = f"{domain}.{tld}"
        if path:
            url += f"/{path}"
        urls.append(url)
    
    # Pattern 4: Spaced URLs (example . com)
    spaced_pattern = r'([\w\-]+)\s*\.\s*([\w]+)(?:\s*/\s*([\w\-]+))?'
    spaced_urls = re.findall(spaced_pattern, text_lower)
    for match in spaced_urls:
        domain, tld, path = match
        # Avoid false positives (like "5. com" or common phrases)
        if len(domain) > 2 and tld in ['com', 'net', 'org', 'in', 'co', 'io', 'app']:
            url = f"{domain}.{tld}"
            if path:
                url += f"/{path}"
            urls.append(url)
    
    return urls


def extract_split_numbers(text: str) -> List[str]:
    """
    Extract phone numbers with various splitting patterns:
    - Spaced: "98765 43210" or "9 8 7 6 5 4 3 2 1 0"
    - Dashed: "98765-43210"
    - Comma-separated: "98765,43210"
    - Mixed: "call me at 9 8 7-6 5 4 3 2 1 0"
    """
    numbers = set()  # Use set to avoid duplicates
    
    # Pattern 1: Single-space separated digits (9 8 7 6 5...)
    single_spaced = re.findall(r'(?:\d\s){9,}\d', text)
    for num in single_spaced:
        cleaned = num.replace(' ', '')
        if len(cleaned) == 10:
            numbers.add(cleaned)
    
    # Pattern 2: Multi-space separated (98765 43210)
    multi_spaced = re.findall(r'\d{3,5}\s+\d{3,5}(?:\s+\d{2,5})*', text)
    for num in multi_spaced:
        cleaned = re.sub(r'\s+', '', num)
        if 10 <= len(cleaned) <= 12:
            numbers.add(cleaned)
    
    # Pattern 3: Dashed numbers (98765-43210)
    dashed = re.findall(r'\d{3,5}-\d{3,5}(?:-\d{2,5})*', text)
    for num in dashed:
        cleaned = num.replace('-', '')
        if 10 <= len(cleaned) <= 12:
            numbers.add(cleaned)
    
    # Pattern 4: Comma-separated (98765,43210)
    comma_sep = re.findall(r'\d{3,5},\d{3,5}(?:,\d{2,5})*', text)
    for num in comma_sep:
        cleaned = num.replace(',', '')
        if 10 <= len(cleaned) <= 12:
            numbers.add(cleaned)
    
    return list(numbers)


def extract_number_words(text: str) -> List[str]:
    """
    Extract numbers spelled out in words:
    - "nine eight seven six five four three two one zero"
    - "call me at nine-eight-seven-six-five..."
    """
    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
    }
    
    numbers = []
    text_lower = text.lower()
    
    # Pattern: Sequence of number words (space or dash separated)
    number_words = '|'.join(word_to_digit.keys())
    pattern = rf'(?:{number_words})(?:[\s\-]+(?:{number_words})){{5,}}'
    
    matches = re.findall(pattern, text_lower)
    for match in matches:
        # Convert words to digits
        words = re.findall(number_words, match)
        digits = ''.join(word_to_digit[w] for w in words)
        if 10 <= len(digits) <= 12:
            numbers.append(digits)
    
    return numbers


# ═══════════════════════════════════════════════════════════════
# LLM-BASED EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_intel_with_llm(text: str, history: List) -> Dict[str, List[str]]:
    """
    Use LLM to extract intelligence that regex might miss.
    Returns structured extraction results.
    """
    # Check if LLM is available (API keys set)
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
        # LLM not available, return empty results
        return {
            "upiIds": [],
            "phoneNumbers": [],
            "phishingLinks": [],
            "bankAccounts": [],
            "suspiciousKeywords": [],
            "source": "llm_unavailable"
        }
    
    try:
        from llm_engine import _get_llm_client
        
        provider_info = _get_llm_client()
        if not provider_info:
            return {"upiIds": [], "phoneNumbers": [], "phishingLinks": [], 
                    "bankAccounts": [], "suspiciousKeywords": [], "source": "llm_unavailable"}
        
        client, model, label = provider_info
        
        # Build extraction prompt — strict, no hallucination
        system_prompt = """You are a strict intelligence extraction assistant. Your job is to extract ONLY items that are EXPLICITLY present in the given text.

RULES:
- ONLY return items that appear verbatim (or with minor formatting differences) in the text.
- If a category has NO matching items in the text, return an EMPTY array [].
- DO NOT infer, guess, or fabricate any values.
- DO NOT extract email addresses as UPI IDs. UPI IDs end with Indian payment handles like @paytm, @ybl, @okaxis, @upi, @sbi, @hdfcbank etc.
- Phone numbers must be 10-digit Indian numbers (with optional +91/91 prefix). Do NOT extract random digit sequences.
- Bank account numbers are 9-18 digit numbers that are NOT phone numbers.
- URLs must actually appear in the text (even if obfuscated with [.] or spaces).
- Suspicious keywords: only extract if the word/phrase literally appears in the text.

Return ONLY valid JSON with these exact keys: upiIds, phoneNumbers, phishingLinks, bankAccounts, suspiciousKeywords.
Each must be an array of strings. Prefer empty arrays over wrong extractions.

Example input: "Send money to raj@paytm and call 9876543210"
Example output: {"upiIds": ["raj@paytm"], "phoneNumbers": ["9876543210"], "phishingLinks": [], "bankAccounts": [], "suspiciousKeywords": []}

Example input: "Hello, how are you today?"
Example output: {"upiIds": [], "phoneNumbers": [], "phishingLinks": [], "bankAccounts": [], "suspiciousKeywords": []}"""
        
        user_prompt = f"Extract intelligence ONLY from items explicitly present in this message. If nothing is found, return empty arrays.\n\nMessage: \"{text}\"\n\nReturn JSON only."
        
        # Call LLM directly with correct client and model
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.1,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Strip markdown fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        result = json.loads(content)
        
        if result and isinstance(result, dict):
            # Post-LLM validation: cross-check extracted values against the source text
            result = _validate_llm_extraction(result, text)
            result["source"] = "llm"
            return result
        else:
            return {"upiIds": [], "phoneNumbers": [], "phishingLinks": [], 
                    "bankAccounts": [], "suspiciousKeywords": [], "source": "llm_error"}
    
    except Exception as e:
        return {"upiIds": [], "phoneNumbers": [], "phishingLinks": [], 
                "bankAccounts": [], "suspiciousKeywords": [], "source": "llm_error"}


# ═══════════════════════════════════════════════════════════════
# POST-LLM VALIDATION (reject hallucinated values)
# ═══════════════════════════════════════════════════════════════

def _validate_llm_extraction(result: Dict, source_text: str) -> Dict:
    """
    Cross-check every LLM-extracted value against the source text.
    Discard any value whose core content is NOT found in the original message.
    This prevents hallucinated UPI IDs, phone numbers, etc.
    """
    text_lower = source_text.lower()
    # Digits-only version for numeric lookups
    text_digits = re.sub(r'\D', '', source_text)

    # --- UPI IDs: the local-part@handle must appear in text ---
    validated_upis = []
    for upi in result.get("upiIds", []):
        if upi.lower() in text_lower:
            validated_upis.append(upi)
    result["upiIds"] = validated_upis

    # --- Phone numbers: the digits must appear in the text ---
    validated_phones = []
    for phone in result.get("phoneNumbers", []):
        digits = re.sub(r'\D', '', phone)
        # Strip leading 91 for matching
        core = digits[-10:] if len(digits) >= 10 else digits
        if core and core in text_digits:
            validated_phones.append(phone)
    result["phoneNumbers"] = validated_phones

    # --- URLs: domain must appear somewhere in the text ---
    validated_urls = []
    for url in result.get("phishingLinks", []):
        # Extract domain from url
        domain_match = re.search(r'(?:https?://)?([\w\-\.]+)', url)
        if domain_match:
            domain = domain_match.group(1).lower().replace('[.]', '.').replace('(.)', '.')
            # Check if domain (or obfuscated form) appears in text
            if domain in text_lower or domain.replace('.', ' . ') in text_lower or domain.replace('.', '[.]') in text_lower:
                validated_urls.append(url)
    result["phishingLinks"] = validated_urls

    # --- Bank accounts: digits must appear in text ---
    validated_accounts = []
    for acc in result.get("bankAccounts", []):
        digits = re.sub(r'\D', '', acc)
        if digits and digits in text_digits:
            validated_accounts.append(acc)
    result["bankAccounts"] = validated_accounts

    # --- Keywords: word must appear in text ---
    validated_keywords = []
    for kw in result.get("suspiciousKeywords", []):
        if kw.lower() in text_lower:
            validated_keywords.append(kw)
    result["suspiciousKeywords"] = validated_keywords

    return result


# ═══════════════════════════════════════════════════════════════
# MERGE & DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

def normalize_phone_number(phone: str) -> str:
    """Normalize phone number for deduplication."""
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    # Remove leading +91 or 91
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    return digits


def normalize_upi_id(upi: str) -> str:
    """Normalize UPI ID for deduplication."""
    return upi.lower().strip()


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication.
    
    Handles:
    - Double protocols: http://https://x.com → https://x.com
    - Protocol-agnostic dedup: http://x.com and https://x.com → same key
    - Trailing slashes, whitespace, trailing punctuation
    """
    url = url.lower().strip()
    # Strip trailing punctuation that may have been captured
    url = url.rstrip('.,;:!?)')
    # Remove trailing slashes
    url = url.rstrip('/')

    # Fix double-protocol URLs (e.g. http://https://site.com)
    double_proto = re.match(r'^https?://(?:https?://)', url)
    if double_proto:
        # Keep the inner (real) protocol
        url = re.sub(r'^https?://(https?://)', r'\1', url)

    # Ensure http/https prefix
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    return url


def _url_dedup_key(url: str) -> str:
    """Return a protocol-agnostic key so http:// and https:// variants
    of the same URL are treated as duplicates."""
    return re.sub(r'^https?://', '', url)


def normalize_account(account: str) -> str:
    """Normalize account number for deduplication."""
    return re.sub(r'\D', '', account)


def merge_and_deduplicate(
    regex_results: Dict[str, List[str]],
    advanced_results: Dict[str, List[str]],
    llm_results: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """
    Merge results from all extraction methods and deduplicate.
    
    Returns:
        Merged dictionary with deduplicated, normalized results
    """
    merged = {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "suspiciousKeywords": []
    }
    
    # Merge UPI IDs (case-insensitive dedup)
    seen_upis: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for upi in source.get("upiIds", []):
            normalized = normalize_upi_id(upi)
            if normalized not in seen_upis and '@' in normalized:
                seen_upis.add(normalized)
                merged["upiIds"].append(upi)  # Keep original case
    
    # Merge phone numbers (normalize to 10 digits)
    seen_phones: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for phone in source.get("phoneNumbers", []):
            normalized = normalize_phone_number(phone)
            if len(normalized) == 10 and normalized not in seen_phones:
                seen_phones.add(normalized)
                merged["phoneNumbers"].append(normalized)
    
    # Merge URLs (normalize and dedup, protocol-agnostic)
    seen_urls: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for url in source.get("phishingLinks", []):
            normalized = normalize_url(url)
            key = _url_dedup_key(normalized)
            if key not in seen_urls:
                seen_urls.add(key)
                merged["phishingLinks"].append(normalized)
    
    # Merge bank accounts (numeric only, avoid phone conflicts)
    # Collect all phone digits to cross-check
    all_phone_digits = set()
    for phone in merged["phoneNumbers"]:
        d = re.sub(r'\D', '', phone)
        all_phone_digits.add(d)
        if d.startswith('91') and len(d) == 12:
            all_phone_digits.add(d[2:])
        if len(d) == 10:
            all_phone_digits.add('91' + d)
    
    seen_accounts: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for account in source.get("bankAccounts", []):
            normalized = normalize_account(account)
            # Reject if it overlaps with any known phone number
            if normalized in all_phone_digits:
                continue
            # Reject 10-12 digit numbers (almost always phone numbers)
            if 10 <= len(normalized) <= 12:
                continue
            # Valid bank accounts are typically 9-18 digits
            if 9 <= len(normalized) <= 18:
                if normalized not in seen_accounts:
                    seen_accounts.add(normalized)
                    merged["bankAccounts"].append(normalized)
    
    # Merge keywords (case-insensitive dedup)
    seen_keywords: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for keyword in source.get("suspiciousKeywords", []):
            normalized = keyword.lower().strip()
            if normalized and normalized not in seen_keywords:
                seen_keywords.add(normalized)
                merged["suspiciousKeywords"].append(normalized)
    
    return merged


# ═══════════════════════════════════════════════════════════════
# MAIN EXTRACTION FUNCTION (HYBRID)
# ═══════════════════════════════════════════════════════════════

def extract_intel(session, text):
    """
    🔥 HYBRID INTELLIGENCE EXTRACTION
    
    Combines three extraction methods:
    1. Regex-based (fast, reliable patterns)
    2. Advanced patterns (obfuscated URLs, split numbers, number words)
    3. LLM-based (context-aware, edge cases)
    
    Results are merged and deduplicated for maximum accuracy.
    """
    # ═══════════════════════════════════════════════════════════
    # STEP 1: REGEX-BASED EXTRACTION (Traditional)
    # ═══════════════════════════════════════════════════════════
    
    # Extraction-safe normalization: stages 1-4 + 6-9
    # Skips leetspeak (stage 5) because it converts @ → a (destroys UPI IDs)
    # and converts digits → letters (destroys phone numbers)
    text_clean = normalize_unicode(text)            # Stage 1: NFKC
    text_clean = remove_zero_width(text_clean)      # Stage 2: invisible chars
    text_clean = remove_control_characters(text_clean)  # Stage 3: control chars
    text_clean = normalize_homoglyphs(text_clean)   # Stage 4: Cyrillic/Greek → Latin
    text_clean = deobfuscate_char_spacing(text_clean)  # Stage 6: h t t p → http
    text_clean = deobfuscate_urls(text_clean)        # Stage 7: hxxps → https, [.] → .
    text_clean = expand_shortened_urls(text_clean)   # Stage 8: bit.ly → real URL
    text_clean = normalize_whitespace(text_clean)    # Stage 9: collapse whitespace
    text_lower = text_clean.lower()
    
    regex_results = {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "suspiciousKeywords": []
    }
    
    # Extract UPI IDs — only match known Indian UPI handles (not plain emails)
    _UPI_HANDLES = (
        'paytm', 'ybl', 'okaxis', 'okhdfcbank', 'oksbi', 'okicici',
        'upi', 'apl', 'ibl', 'sbi', 'hdfcbank', 'icici', 'axisbank',
        'axl', 'boi', 'citi', 'citigold', 'dlb', 'fbl', 'federal',
        'idbi', 'idfcbank', 'indus', 'kbl', 'kotak', 'lvb', 'pnb',
        'rbl', 'sib', 'uco', 'union', 'vijb', 'abfspay', 'freecharge',
        'jio', 'airtel', 'postbank', 'waheed', 'slice', 'jupiter',
        'fi', 'gpay', 'phonepe', 'amazonpay', 'mobikwik', 'niyopay',
    )
    _upi_handle_pattern = '|'.join(re.escape(h) for h in _UPI_HANDLES)
    upi_regex = rf"[a-zA-Z0-9.\-_]{{2,}}@(?:{_upi_handle_pattern})\b"
    regex_results["upiIds"] = re.findall(upi_regex, text_clean, re.IGNORECASE)
    
    # Extract phone numbers (+91xxxxxxxxxx, 91xxxxxxxxxx, or 10-digit)
    regex_results["phoneNumbers"] = re.findall(r"\+?91\d{10}|\+\d{10,}|(?<![\d])\d{10}(?![\d])", text_clean)
    
    # Collect all extracted phone digits (10-digit normalized) to exclude from bank accounts
    _phone_digits = set()
    for p in regex_results["phoneNumbers"]:
        digits = re.sub(r'\D', '', p)
        if digits.startswith('91') and len(digits) == 12:
            _phone_digits.add(digits)       # full 12-digit form
            _phone_digits.add(digits[2:])   # 10-digit form
        else:
            _phone_digits.add(digits)
    
    # Extract URLs
    links = re.findall(r"https?://\S+", text_clean)
    regex_results["phishingLinks"] = [link.rstrip('.,;:!?)') for link in links]
    
    # Extract bank account numbers (typically 9-18 digits, NOT phone numbers)
    # Real Indian bank accounts are 9-18 digits; exclude anything that matches a phone number
    accounts = re.findall(r"\b\d{9,18}\b", text_clean)
    regex_results["bankAccounts"] = [
        acc for acc in accounts
        if acc not in _phone_digits
        and re.sub(r'\D', '', acc) not in _phone_digits
        and not (10 <= len(acc) <= 12)   # 10-12 digit numbers are almost certainly phone numbers
    ]
    
    # Extract keywords
    keywords = [
        'upi', 'verify', 'urgent', 'blocked', 'suspended', 'kyc',
        'otp', 'cvv', 'pin', 'password', 'expire', 'immediately',
        'customer care', 'refund', 'wallet', 'paytm', 'phonepe', 'gpay'
    ]
    regex_results["suspiciousKeywords"] = [kw for kw in keywords if kw in text_lower]
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: ADVANCED PATTERN EXTRACTION
    # ═══════════════════════════════════════════════════════════
    
    advanced_results = {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "suspiciousKeywords": []
    }
    
    # Extract obfuscated URLs
    advanced_results["phishingLinks"] = extract_obfuscated_urls(text)
    
    # Extract split/spaced numbers
    advanced_results["phoneNumbers"] = extract_split_numbers(text)
    
    # Extract number words (nine eight seven...)
    advanced_results["phoneNumbers"].extend(extract_number_words(text))
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: LLM-BASED EXTRACTION
    # ═══════════════════════════════════════════════════════════
    
    history = session.get("history", [])
    llm_results = extract_intel_with_llm(text, history)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 4: MERGE & DEDUPLICATE
    # ═══════════════════════════════════════════════════════════
    
    merged = merge_and_deduplicate(regex_results, advanced_results, llm_results)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: UPDATE SESSION WITH NEW INTELLIGENCE
    # ═══════════════════════════════════════════════════════════
    
    # Track extraction sources for debugging
    extraction_metadata = {
        "regex_count": {
            "upis": len(regex_results["upiIds"]),
            "phones": len(regex_results["phoneNumbers"]),
            "urls": len(regex_results["phishingLinks"]),
        },
        "advanced_count": {
            "phones": len(advanced_results["phoneNumbers"]),
            "urls": len(advanced_results["phishingLinks"]),
        },
        "llm_count": {
            "upis": len(llm_results.get("upiIds", [])),
            "phones": len(llm_results.get("phoneNumbers", [])),
            "urls": len(llm_results.get("phishingLinks", [])),
        },
        "llm_source": llm_results.get("source", "unavailable")
    }
    
    # Store metadata in session (for /debug/intelligence endpoint)
    if "extraction_metadata" not in session:
        session["extraction_metadata"] = []
    session["extraction_metadata"].append(extraction_metadata)
    
    # Update session intel with merged results
    new_counts = {"upi": 0, "phone": 0, "url": 0, "account": 0}
    
    # Add UPI IDs (normalized: lowercase)
    for upi in merged["upiIds"]:
        upi_norm = upi.lower().strip()
        if upi_norm not in session["intel"]["upiIds"]:
            session["intel"]["upiIds"].append(upi_norm)
            new_counts["upi"] += 1
    
    # Add phone numbers (normalized: 10 digits only)
    for phone in merged["phoneNumbers"]:
        phone_norm = re.sub(r'\D', '', phone)
        if phone_norm.startswith('91') and len(phone_norm) == 12:
            phone_norm = phone_norm[2:]
        if len(phone_norm) == 10 and phone_norm not in session["intel"]["phoneNumbers"]:
            session["intel"]["phoneNumbers"].append(phone_norm)
            new_counts["phone"] += 1
    
    # Add URLs (normalized: lowercase, deobfuscated, no trailing slash)
    # Build a set of protocol-agnostic keys for existing session URLs
    _existing_url_keys = set()
    for existing in session["intel"]["phishingLinks"]:
        _existing_url_keys.add(re.sub(r'^https?://', '', existing.lower().rstrip('/')))

    for url in merged["phishingLinks"]:
        url_norm = normalize_url_for_extraction(url).rstrip('/')
        # Fix double-protocol (e.g. http://https://site.com)
        url_norm = re.sub(r'^https?://(https?://)', r'\1', url_norm)
        if not url_norm.startswith(('http://', 'https://')):
            url_norm = 'http://' + url_norm
        # Protocol-agnostic dedup against session
        url_key = re.sub(r'^https?://', '', url_norm)
        if url_key not in _existing_url_keys:
            _existing_url_keys.add(url_key)
            session["intel"]["phishingLinks"].append(url_norm)
            new_counts["url"] += 1
    
    # Add bank accounts (normalized: digits only)
    for account in merged["bankAccounts"]:
        acc_norm = re.sub(r'\D', '', account)
        if acc_norm and acc_norm not in session["intel"]["bankAccounts"]:
            session["intel"]["bankAccounts"].append(acc_norm)
            new_counts["account"] += 1
    
    # Add keywords (normalized: lowercase)
    for keyword in merged["suspiciousKeywords"]:
        kw_norm = keyword.lower().strip()
        if kw_norm and kw_norm not in session["intel"]["suspiciousKeywords"]:
            session["intel"]["suspiciousKeywords"].append(kw_norm)
    
    # Track telemetry
    if new_counts["upi"] > 0:
        track_intelligence("upi", new_counts["upi"])
    if new_counts["phone"] > 0:
        track_intelligence("phone", new_counts["phone"])
    if new_counts["url"] > 0:
        track_intelligence("url", new_counts["url"])
    if new_counts["account"] > 0:
        track_intelligence("account", new_counts["account"])
    
    # Track extraction history for novelty rate calculation
    total_new_intel = sum(new_counts.values())
    if "intel_extraction_history" not in session:
        session["intel_extraction_history"] = []
    
    session["intel_extraction_history"].append({
        "turn": session.get("messages", 0),
        "new_intel_count": total_new_intel,
        "breakdown": new_counts.copy(),
        "extraction_methods_used": {
            "regex": extraction_metadata["regex_count"],
            "advanced": extraction_metadata["advanced_count"],
            "llm": extraction_metadata["llm_source"],
        }
    })

# ═══════════════════════════════════════════════════════════════
# INTELLIGENT CLOSING LOGIC
# ═══════════════════════════════════════════════════════════════

def calculate_intel_score(session: dict) -> dict:
    """
    Calculate weighted intelligence score to determine conversation value.
    
    Components:
    - unique_artifacts (0-1): Quality/diversity of extracted intel
    - scam_confidence (0-1): How confident we are it's a scam
    - engagement_depth (0-1): How engaged the scammer is
    - novelty_rate (0-1): Rate of new intel extraction
    
    Weights:
    - 0.35 × unique_artifacts (most important - actual extraction)
    - 0.25 × scam_confidence (confirms it's worth continuing)
    - 0.20 × engagement_depth (scammer still engaged)
    - 0.20 × novelty_rate (still extracting new info)
    
    Returns:
        dict with score (0-1) and components
    """
    intel = session.get("intel", {})
    history = session.get("history", [])
    messages = session.get("messages", 0)
    
    # ── 1. Unique Artifacts Score (0-1) ────────────────────────
    # Count unique intelligence items across all types
    unique_count = (
        len(intel.get("upiIds", [])) +
        len(intel.get("phoneNumbers", [])) +
        len(intel.get("phishingLinks", [])) +
        len(intel.get("bankAccounts", [])) +
        min(len(intel.get("suspiciousKeywords", [])), 5)  # Cap keywords at 5
    )
    
    # Diversity bonus: having multiple types is better than many of one type
    types_collected = sum([
        1 if intel.get("upiIds", []) else 0,
        1 if intel.get("phoneNumbers", []) else 0,
        1 if intel.get("phishingLinks", []) else 0,
        1 if intel.get("bankAccounts", []) else 0,
    ])
    diversity_multiplier = 1.0 + (types_collected * 0.15)  # +15% per type
    
    # Normalize: 10+ items = 1.0, apply diversity bonus
    artifacts_score = min(1.0, (unique_count / 10.0) * diversity_multiplier)
    
    # ── 2. Scam Confidence Score (0-1) ─────────────────────────
    # Use existing scam score from last detection
    scam_confidence = session.get("scam_score", 0.5)
    
    # ── 3. Engagement Depth Score (0-1) ────────────────────────
    # Measure scammer's engagement quality
    engagement_score = 0.5  # Default neutral
    
    if messages >= 2:
        # Get last 3 scammer messages (skip user messages)
        scammer_messages = [msg for msg in history if msg.get("sender") == "scammer"][-3:]
        
        if scammer_messages:
            avg_length = sum(len(msg.get("text", "")) for msg in scammer_messages) / len(scammer_messages)
            
            # Long messages (150+ chars) = engaged (0.8-1.0)
            # Medium (50-150) = moderate (0.5-0.8)
            # Short (<50) = disengaging (0.2-0.5)
            if avg_length >= 150:
                engagement_score = 0.9
            elif avg_length >= 80:
                engagement_score = 0.7
            elif avg_length >= 40:
                engagement_score = 0.5
            else:
                engagement_score = 0.3
    
    # ── 4. Novelty Rate Score (0-1) ────────────────────────────
    # Track if we're still extracting new intel
    extraction_history = session.get("intel_extraction_history", [])
    
    if len(extraction_history) < 3:
        novelty_score = 1.0  # Early stage, assume high novelty
    else:
        # Check last 3 turns for new intel
        recent_extractions = extraction_history[-3:]
        new_intel_count = sum(turn.get("new_intel_count", 0) for turn in recent_extractions)
        
        # 3+ new items in last 3 turns = high novelty (0.8-1.0)
        # 1-2 items = moderate (0.4-0.6)
        # 0 items = stagnant (0.0-0.2)
        if new_intel_count >= 3:
            novelty_score = 0.9
        elif new_intel_count == 2:
            novelty_score = 0.6
        elif new_intel_count == 1:
            novelty_score = 0.4
        else:
            novelty_score = 0.1  # Stagnant
    
    # ── 5. Calculate Weighted Score ────────────────────────────
    weighted_score = (
        0.35 * artifacts_score +
        0.25 * scam_confidence +
        0.20 * engagement_score +
        0.20 * novelty_score
    )
    
    return {
        "score": weighted_score,
        "components": {
            "artifacts": artifacts_score,
            "scam_confidence": scam_confidence,
            "engagement": engagement_score,
            "novelty": novelty_score,
        },
        "weights": {
            "artifacts": 0.35,
            "scam_confidence": 0.25,
            "engagement": 0.20,
            "novelty": 0.20,
        },
        "details": {
            "unique_items": unique_count,
            "types_collected": types_collected,
            "avg_scammer_length": engagement_score * 100,  # Approximate
        }
    }


def detect_scammer_patterns(session: dict) -> dict:
    """
    Detect scammer behavioral patterns that indicate closing conditions.
    
    Returns:
        dict with detected patterns and severity
    """
    history = session.get("history", [])
    scammer_messages = [msg for msg in history if msg.get("sender") == "scammer"][-5:]
    
    patterns = {
        "repeated_pressure": False,
        "disengagement": False,
        "stale_intel": False,
        "severity": 0.0,  # 0-1 scale
    }
    
    # ── 1. Repeated Pressure Detection ────────────────────────
    # Scammer repeating same urgency keywords = getting frustrated
    urgency_keywords = ['urgent', 'immediately', 'now', 'quick', 'asap', 'hurry']
    pressure_count = 0
    
    for msg in scammer_messages[-3:]:  # Last 3 messages
        text = msg.get("text", "").lower()
        if any(keyword in text for keyword in urgency_keywords):
            pressure_count += 1
    
    if pressure_count >= 2:  # 2+ pressure messages in last 3
        patterns["repeated_pressure"] = True
        patterns["severity"] += 0.3
    
    # ── 2. Disengagement Detection ─────────────────────────────
    # Short messages, dismissive tone
    if len(scammer_messages) >= 2:
        recent_lengths = [len(msg.get("text", "")) for msg in scammer_messages[-2:]]
        avg_length = sum(recent_lengths) / len(recent_lengths)
        
        # Very short responses (<30 chars) suggest giving up
        if avg_length < 30:
            patterns["disengagement"] = True
            patterns["severity"] += 0.4
    
    # ── 3. Stale Intel Detection ──────────────────────────────
    # No new intel in last 3 turns
    extraction_history = session.get("intel_extraction_history", [])
    
    if len(extraction_history) >= 3:
        recent_new_intel = sum(
            turn.get("new_intel_count", 0) 
            for turn in extraction_history[-3:]
        )
        
        if recent_new_intel == 0:
            patterns["stale_intel"] = True
            patterns["severity"] += 0.5
    
    return patterns


def should_close_conversation(session: dict) -> tuple[bool, str]:
    """
    Intelligent decision on whether to close conversation.
    
    Prevents:
    - Infinite loops (stale intel detection)
    - Premature close (minimum quality threshold)
    - Under-extraction (novelty rate check)
    
    Returns:
        (should_close, reason)
    """
    messages = session.get("messages", 0)
    intel_score_data = calculate_intel_score(session)
    intel_score = intel_score_data["score"]
    components = intel_score_data["components"]
    patterns = detect_scammer_patterns(session)
    
    # ── Safety: Hard limits ────────────────────────────────────
    # Absolute max: 30 messages regardless (prevent infinite loop)
    if messages >= 30:
        return True, "hard_limit_reached"
    
    # Absolute min: At least 6 messages (prevent premature close)
    if messages < 6:
        return False, "too_early"
    
    # ── Condition 1: No new intel in last 3 turns ──────────────
    if patterns["stale_intel"] and messages >= 10:
        # If extraction stagnated AND we have decent intel, close
        if components["artifacts"] >= 0.4:  # At least 40% intel collected
            return True, "intel_stagnation"
    
    # ── Condition 2: Repeated pressure tactics ─────────────────
    if patterns["repeated_pressure"] and messages >= 8:
        # Scammer getting frustrated, close strategically
        if components["artifacts"] >= 0.3:  # At least 30% intel
            return True, "scammer_pressure"
    
    # ── Condition 3: Scammer disengagement ─────────────────────
    if patterns["disengagement"]:
        # Scammer giving up, finalize now
        return True, "scammer_disengaged"
    
    # ── Condition 4: High quality extraction complete ──────────
    # Intel score > 0.75 AND decent conversation length
    if intel_score >= 0.75 and messages >= 12:
        return True, "high_quality_complete"
    
    # ── Condition 5: Good extraction + low novelty ─────────────
    # We have good intel but not getting more
    if components["artifacts"] >= 0.6 and components["novelty"] < 0.3 and messages >= 10:
        return True, "diminishing_returns"
    
    # ── Condition 6: Pattern severity threshold ────────────────
    # Multiple negative patterns detected
    if patterns["severity"] >= 0.7 and messages >= 8:
        return True, "multiple_warning_signs"
    
    # ── Continue: Still extracting value ───────────────────────
    # High novelty OR low intel collected OR scammer still engaged
    if components["novelty"] >= 0.5 or components["artifacts"] < 0.5:
        return False, "continue_extraction"
    
    # Default: continue if no clear closing signal
    return False, "normal_flow"


def maybe_finish(session):
    """
    Determine if conversation should end using intelligent scoring.
    
    Replaced simple message counting with:
    - Weighted intel scoring
    - Novelty rate tracking
    - Scammer pattern detection
    - Strategic closing conditions
    """
    should_close, reason = should_close_conversation(session)
    
    # Store closing metadata for telemetry
    if should_close and "close_reason" not in session:
        session["close_reason"] = reason
        session["final_intel_score"] = calculate_intel_score(session)
    
    return should_close
