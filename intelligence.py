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
    normalize_whitespace
)
from telemetry import track_intelligence


# ═══════════════════════════════════════════════════════════════
# ADVANCED PATTERN EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_obfuscated_urls(text: str) -> List[str]:
    """
    Extract URLs with obfuscation techniques:
    - hxxp/hxxps instead of http/https
    - [.] or (.) or [dot] instead of .
    - Spelled out: "google dot com slash phish"
    - Spaces: "example . com"
    """
    urls = []
    text_lower = text.lower()
    
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
    
    # Mask email/UPI @domain parts before Patterns 3 & 4 to avoid false positives.
    # e.g. user@gmail.com → the "gmail.com" part would otherwise be captured as a URL.
    text_safe = re.sub(r'@[\w.\-]+', '@MASKED', text)
    text_safe_lower = re.sub(r'@[\w.\-]+', '@MASKED', text_lower)

    # Pattern 3: Spelled out URLs (google dot com slash something)
    spelled_pattern = r'([\w\-]+)\s+(?:dot|DOT)\s+([\w]+)(?:\s+(?:slash|/)\s+([\w\-]+))?'
    spelled_urls = re.findall(spelled_pattern, text_safe, re.IGNORECASE)
    for match in spelled_urls:
        domain, tld, path = match
        url = f"http://{domain}.{tld}"
        if path:
            url += f"/{path}"
        urls.append(url)
    
    # Pattern 4: Spaced URLs (example . com)
    spaced_pattern = r'([\w\-]+)\s*\.\s*([\w]+)(?:\s*/\s*([\w\-]+))?'
    spaced_urls = re.findall(spaced_pattern, text_safe_lower)
    for match in spaced_urls:
        domain, tld, path = match
        # Avoid false positives (like "5. com" or common phrases)
        if len(domain) > 2 and tld in ['com', 'net', 'org', 'in', 'co', 'io', 'app']:
            url = f"http://{domain}.{tld}"
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
    _empty = {
        "upiIds": [], "phoneNumbers": [], "phishingLinks": [],
        "bankAccounts": [],
        "names": [], "emails": [],
        "caseIds": [], "policyNumbers": [], "orderNumbers": [],
    }
    # Check if LLM is available (API keys set)
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
        return {**_empty, "source": "llm_unavailable"}
    
    try:
        # Import LLM engine (only if available)
        from llm_engine import _get_llm_client
        
        provider_info = _get_llm_client()
        if not provider_info:
            return {**_empty, "source": "llm_unavailable"}
        
        client, model, label = provider_info
        
        # Build extraction prompt
        system_prompt = """You are an intelligence extraction assistant. Extract the following from the given text:
1. UPI IDs (format: xyz@bank)
2. Phone numbers (10-12 digits, any format)
3. URLs/Links — ONLY actual web URLs (http, https, www, hxxp, or domain[.]tld format). Do NOT include UPI IDs (user@bank) or email addresses here.
4. Bank account numbers (8-16 digits)
5. Names — ONLY actual human person names (first name, last name, or full name). Examples: "Rajesh Kumar", "Priya", "Sharma".
   Do NOT include: titles alone ("Officer", "Inspector"), organization names ("Amazon", "SBI"), roles ("customer support"), or generic words.
   If a title accompanies a person name, include only the person name part (e.g. "Officer Vikram Singh" → extract "Vikram Singh").
6. Emails — standard email addresses
7. Case IDs / Reference numbers (e.g. CASE-12345, REF-20230001, FIR/123/2024)
8. Policy numbers (e.g. POL-123456, LIC12345678)
9. Order numbers (e.g. ORD-12345, AWB1234567890)

Return ONLY valid JSON with these exact keys: upiIds, phoneNumbers, phishingLinks, bankAccounts, names, emails, caseIds, policyNumbers, orderNumbers.
Each should be an array of strings. Extract ALL instances, even if obfuscated or split.
IMPORTANT for names: Only extract strings that are clearly human person names. If no person name is mentioned, return an empty array for names. Do NOT guess or infer names from context.

Example:
{"upiIds": ["scam@paytm"], "phoneNumbers": ["9876543210"], "phishingLinks": ["http://fake-bank.com"], "bankAccounts": [], "names": ["Rajesh Kumar"], "emails": [], "caseIds": ["REF-20230001"], "policyNumbers": [], "orderNumbers": []}"""
        
        user_prompt = f"Extract intelligence from this scammer message:\n\n{text}\n\nReturn JSON only."
        
        # Call LLM directly with the extraction prompt
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
        
        # Strip markdown fences if LLM wraps output
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        result = json.loads(content)
        
        if result and isinstance(result, dict):
            # Add source indicator
            result["source"] = "llm"
            # Ensure all expected keys exist and values are lists
            for k in _empty:
                if k not in result or not isinstance(result[k], list):
                    result[k] = []
            return result
        else:
            return {**_empty, "source": "llm_error"}
    
    except json.JSONDecodeError as e:
        print(f"⚠️  LLM extraction returned invalid JSON: {e}")
        return {**_empty, "source": "llm_error"}
    except Exception as e:
        print(f"⚠️  LLM extraction failed ({type(e).__name__}): {e}")
        return {**_empty, "source": "llm_error"}


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
    """Normalize URL for deduplication."""
    url = url.lower().strip()
    # Remove trailing slashes
    url = url.rstrip('/')
    # Ensure http/https prefix
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url


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
        "names": [],
        "emails": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
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
    
    # Merge URLs (normalize and dedup)
    seen_urls: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for url in source.get("phishingLinks", []):
            normalized = normalize_url(url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                merged["phishingLinks"].append(normalized)
    
    # Merge bank accounts (numeric only, avoid phone conflicts)
    seen_accounts: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for account in source.get("bankAccounts", []):
            normalized = normalize_account(account)
            # Avoid phone numbers (10 digits) being treated as accounts
            if 8 <= len(normalized) <= 16 and len(normalized) != 10:
                if normalized not in seen_accounts:
                    seen_accounts.add(normalized)
                    merged["bankAccounts"].append(normalized)
    
    # Merge names (case-insensitive dedup, title case)
    seen_names: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for name in source.get("names", []):
            key = name.strip().lower()
            if key and key not in seen_names and len(key) > 1:
                seen_names.add(key)
                merged["names"].append(name.strip().title())
    
    # Merge emails (case-insensitive dedup)
    seen_emails: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for email in source.get("emails", []):
            normalized = email.lower().strip()
            if normalized and normalized not in seen_emails and '@' in normalized and '.' in normalized:
                seen_emails.add(normalized)
                merged["emails"].append(normalized)
    
    # Merge case IDs (case-insensitive dedup)
    seen_case_ids: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for cid in source.get("caseIds", []):
            normalized = cid.strip().upper()
            if normalized and normalized not in seen_case_ids:
                seen_case_ids.add(normalized)
                merged["caseIds"].append(cid.strip())

    # Merge policy numbers (case-insensitive dedup)
    seen_policy: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for pol in source.get("policyNumbers", []):
            normalized = pol.strip().upper()
            if normalized and normalized not in seen_policy:
                seen_policy.add(normalized)
                merged["policyNumbers"].append(pol.strip())

    # Merge order numbers (case-insensitive dedup)
    seen_orders: Set[str] = set()
    for source in [regex_results, advanced_results, llm_results]:
        for order in source.get("orderNumbers", []):
            normalized = order.strip().upper()
            if normalized and normalized not in seen_orders:
                seen_orders.add(normalized)
                merged["orderNumbers"].append(order.strip())

    # Cross-field dedup: remove any phishing link that is just the domain of a known
    # UPI ID or email address (e.g. http://gmail.com appearing because user@gmail.com
    # was captured by the spaced-URL pattern).
    at_domains: Set[str] = set()
    for upi in merged["upiIds"]:
        if '@' in upi:
            at_domains.add(upi.split('@', 1)[1].lower().strip())
    for email in merged["emails"]:
        if '@' in email:
            at_domains.add(email.split('@', 1)[1].lower().strip())

    def _link_is_bare_domain(url: str) -> bool:
        stripped = re.sub(r'^https?://', '', url).rstrip('/')
        return stripped.lower() in at_domains

    merged["phishingLinks"] = [u for u in merged["phishingLinks"] if not _link_is_bare_domain(u)]

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
    
    # Light normalization: only remove invisible chars and normalize whitespace
    text_clean = normalize_unicode(text)
    text_clean = remove_zero_width(text_clean)
    text_clean = normalize_whitespace(text_clean)
    text_lower = text_clean.lower()
    
    regex_results = {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "names": [],
        "emails": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
    }
    
    # ── Known UPI handle suffixes ──
    _UPI_SUFFIXES = {
        'paytm', 'ybl', 'okhdfcbank', 'okaxis', 'oksbi', 'okicici',
        'upi', 'sbi', 'hdfcbank', 'icici', 'axisbank', 'kotak',
        'pnb', 'gpay', 'phonepe', 'apl', 'ratn', 'barodampay',
        'ibl', 'axl', 'pingpay', 'freecharge', 'waaxis', 'wasbi',
        'wahdfcbank', 'waicici', 'abfspay', 'ikwik', 'jupiteraxis',
        'yesbankltd', 'yesbank', 'federal', 'rbl', 'dbs', 'indus',
        'citi', 'hsbc', 'sc', 'idbi', 'unionbank', 'boi', 'cnrb',
        'idfcbank', 'aubank', 'dlb', 'cub', 'kvb', 'tmb', 'jio',
        'slice', 'niyoicici', 'postbank', 'finobank', 'kkbk',
        'imobile', 'mahb', 'indianbank', 'psb', 'uboi', 'cbin',
    }

    # Step A: Extract ALL @-tokens from text
    all_at_tokens = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+', text_clean)

    # Step B: Classify each token as UPI or email
    upi_ids = []
    emails = []
    for token in all_at_tokens:
        local, domain = token.rsplit('@', 1)
        domain_lower = domain.lower()
        # It's a UPI ID if:
        #   1) The domain is a known UPI suffix, OR
        #   2) The domain has NO dot (e.g. xyz@something — not an email pattern)
        if domain_lower in _UPI_SUFFIXES:
            upi_ids.append(token)
        elif '.' not in domain:
            # No dot in domain → likely UPI (e.g. custom@bank), not email
            upi_ids.append(token)
        else:
            # Has a dot → standard email (e.g. user@gmail.com)
            # Validate it looks like an email (domain.tld)
            if re.match(r'^[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', domain):
                emails.append(token)

    # Deduplicate: remove any email that was also matched as UPI
    upi_set = set(u.lower() for u in upi_ids)
    emails = [e for e in emails if e.lower() not in upi_set]

    regex_results["upiIds"] = upi_ids
    regex_results["emails"] = emails

    # Extract phone numbers (+91xxxxxxxxxx, 91xxxxxxxxxx, or 10-digit)
    regex_results["phoneNumbers"] = re.findall(r"\+?91\d{10}|\+\d{10,}|(?<!\d)\d{10}(?!\d)", text_clean)

    # Extract URLs
    links = re.findall(r"https?://\S+", text_clean)
    regex_results["phishingLinks"] = [link.rstrip('.,;:!?)') for link in links]

    # Extract account numbers (8-16 digits, but not 10-digit phone numbers)
    accounts = re.findall(r"\b\d{8,16}\b", text_clean)
    regex_results["bankAccounts"] = [acc for acc in accounts if len(acc) != 10]

    # NOTE: Name extraction is handled exclusively by the LLM (Step 3)
    # because regex-based name extraction produces too many false positives—
    # common English words after "I am", "this is" etc. get misidentified as names.
    # The LLM has semantic understanding to distinguish "I am Rajesh" (name)
    # from "I am calling" (not a name).

    # Extract case IDs / reference numbers (e.g. CASE-12345, REF-20230001, FIR/123/2024, CRN12345678)
    case_patterns = re.findall(
        r'\b(?:CASE|REF|FIR|CRN|COMP|CR|TKT|INC|SR|TICKET)[\s\-/#]?\d{3,15}(?:/\d{2,4})?\b',
        text_clean, re.IGNORECASE
    )
    regex_results["caseIds"] = [c.strip() for c in case_patterns]

    # Extract policy numbers (e.g. POL-123456, POLICY/2024/1234, LIC12345678)
    policy_patterns = re.findall(
        r'\b(?:POL|POLICY|LIC|INS|PLAN)[\s\-/#]?\d{4,15}(?:/\d{2,4})?\b',
        text_clean, re.IGNORECASE
    )
    regex_results["policyNumbers"] = [p.strip() for p in policy_patterns]

    # Extract order numbers (e.g. ORD-12345, ORDER#9876543, AWB1234567890)
    order_patterns = re.findall(
        r'\b(?:ORD|ORDER|AWB|TRACK|TRK|SHIP|PKG)[\s\-/#]?\d{4,15}\b',
        text_clean, re.IGNORECASE
    )
    regex_results["orderNumbers"] = [o.strip() for o in order_patterns]

    # ═══════════════════════════════════════════════════════════
    # STEP 2: ADVANCED PATTERN EXTRACTION
    # ═══════════════════════════════════════════════════════════
    
    advanced_results = {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "names": [],
        "emails": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
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
    
    # Add UPI IDs
    for upi in merged["upiIds"]:
        if upi not in session["intel"]["upiIds"]:
            session["intel"]["upiIds"].append(upi)
            new_counts["upi"] += 1
    
    # Add phone numbers
    for phone in merged["phoneNumbers"]:
        if phone not in session["intel"]["phoneNumbers"]:
            session["intel"]["phoneNumbers"].append(phone)
            new_counts["phone"] += 1
    
    # Add URLs
    for url in merged["phishingLinks"]:
        if url not in session["intel"]["phishingLinks"]:
            session["intel"]["phishingLinks"].append(url)
            new_counts["url"] += 1
    
    # Add bank accounts
    for account in merged["bankAccounts"]:
        if account not in session["intel"]["bankAccounts"]:
            session["intel"]["bankAccounts"].append(account)
            new_counts["account"] += 1
    
    # Add names
    for name in merged.get("names", []):
        if name not in session["intel"].get("names", []):
            session["intel"].setdefault("names", []).append(name)
    
    # Add emails
    for email in merged.get("emails", []):
        if email not in session["intel"].get("emails", []):
            session["intel"].setdefault("emails", []).append(email)
    
    # Add case IDs
    for cid in merged.get("caseIds", []):
        if cid not in session["intel"].get("caseIds", []):
            session["intel"].setdefault("caseIds", []).append(cid)

    # Add policy numbers
    for pol in merged.get("policyNumbers", []):
        if pol not in session["intel"].get("policyNumbers", []):
            session["intel"].setdefault("policyNumbers", []).append(pol)

    # Add order numbers
    for order in merged.get("orderNumbers", []):
        if order not in session["intel"].get("orderNumbers", []):
            session["intel"].setdefault("orderNumbers", []).append(order)

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
        "turn": len(session.get("history", [])) // 2,
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
    messages = len(history)
    
    # ── 1. Unique Artifacts Score (0-1) ────────────────────────
    # Count unique intelligence items across all types
    unique_count = (
        len(intel.get("upiIds", [])) +
        len(intel.get("phoneNumbers", [])) +
        len(intel.get("phishingLinks", [])) +
        len(intel.get("bankAccounts", [])) +
        len(intel.get("names", [])) +
        len(intel.get("emails", [])) +
        len(intel.get("caseIds", [])) +
        len(intel.get("policyNumbers", [])) +
        len(intel.get("orderNumbers", []))
    )
    
    # Diversity bonus: having multiple types is better than many of one type
    types_collected = sum([
        1 if intel.get("upiIds", []) else 0,
        1 if intel.get("phoneNumbers", []) else 0,
        1 if intel.get("phishingLinks", []) else 0,
        1 if intel.get("bankAccounts", []) else 0,
        1 if intel.get("names", []) else 0,
        1 if intel.get("emails", []) else 0,
        1 if intel.get("caseIds", []) else 0,
        1 if intel.get("policyNumbers", []) else 0,
        1 if intel.get("orderNumbers", []) else 0,
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
        scammer_messages = [msg for msg in history if msg.get("sender") == "assistant"][-3:]
        
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
    scammer_messages = [msg for msg in history if msg.get("sender") == "assistant"][-5:]
    
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
        # Note: repeated pressure is NOT a closing signal —
        # it’s an opportunity to extract more intel while the scammer is engaged.
    
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
    messages = len(session.get("history", []))
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
    # Scammer pressure = opportunity to extract more intel.
    # The persistence detection in dialogue_strategy handles this
    # with strategic responses, so we keep the conversation open.
    
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
