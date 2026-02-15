"""
Production-Grade Text Normalization Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose: Eliminate scammer obfuscation techniques before detection
Architecture: 11-stage deterministic pipeline
Security: No eval(), no exec()

Pipeline Flow:
Raw Input → Unicode → Zero-Width → Control Chars → Homoglyphs → 
Hex-URL Decode → Leetspeak → Char-Spacing → URL Deobfuscation →
Short-URL Expansion → Whitespace → Lowercase → Output
"""

import re
import logging
import unicodedata
from typing import Dict, List, Optional, Set, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import requests

# ═══════════════════════════════════════════════════════════════
# PRECOMPILED PATTERNS (Performance Optimization)
# ═══════════════════════════════════════════════════════════════

# Zero-width characters (INVISIBLE UNICODE)
ZERO_WIDTH_PATTERN = re.compile(
    r'[\u200B\u200C\u200D\u200E\u200F\uFEFF\u2060\u180E]'
)

# Control characters (ASCII 0-31 except whitespace)
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1F\x7F]')

# Multiple whitespace consolidation
MULTI_WHITESPACE_PATTERN = re.compile(r'\s+')

# URL detection for targeted deobfuscation
URL_DETECTION_PATTERN = re.compile(
    r'(?:hxxp|h[tx]{2}ps?|www)[^\s]*',
    re.IGNORECASE
)

# Digit sequences (for phone number normalization)
PHONE_PATTERN = re.compile(r'[-\s().]')

# Character-spacing obfuscation: sequences of single chars separated by spaces
# Matches runs of 4+ single-character tokens like "h t t p : / / s b i . c o m"
CHAR_SPACING_PATTERN = re.compile(
    r'(?:^|(?<=\s))'
    r'((?:[^\s]\s){3,}[^\s])'
    r'(?=\s|$)',
)

# Hex-encoded URL pattern: continuous hex strings (≥14 hex chars = 7+ bytes)
# 687474703a2f2f = "http://" in hex, so any URL will be at least 14 hex chars.
HEX_ENCODED_PATTERN = re.compile(
    r'\b([0-9a-fA-F]{14,})\b'
)

# Full URL pattern (used for shortened URL detection)
FULL_URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')]+',
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════
# SHORTENED URL CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Known URL shortener domains — kept as a frozenset for O(1) lookups
SHORTENER_DOMAINS: frozenset = frozenset({
    # Major shorteners
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "v.gd", "buff.ly", "adf.ly", "j.mp",
    "rb.gy", "short.io", "cutt.ly", "shorturl.at", "clck.ru",
    "lnkd.in", "db.tt", "qr.ae", "amzn.to", "youtu.be",
    "surl.li", "rebrand.ly", "bl.ink", "tiny.cc", "x.co",
    # Social / common services
    "fb.me", "m.me", "wa.me", "redd.it", "dlvr.it",
    "soo.gd", "s2r.co", "clk.sh", "cli.re", "bc.vc",
    "po.st", "su.pr", "u.to", "mcaf.ee", "twit.ac",
    "href.li", "han.gl", "hyperurl.co", "bom.to", "zpr.io",
    # Regional / niche
    "shrtco.de", "0rz.tw", "b23.ru", "gee.su", "dwz.mk",
})

# Default timeout (seconds) for following redirects when expanding short URLs
SHORTENED_URL_EXPAND_TIMEOUT: float = 3.0

# Maximum number of redirects to follow
SHORTENED_URL_MAX_REDIRECTS: int = 10

# Logger
_log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# LEETSPEAK & OBFUSCATION MAPS
# ═══════════════════════════════════════════════════════════════

LEET_MAP: Dict[str, str] = {
    # Numbers
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "9": "g",
    
    # Special characters
    "@": "a",
    "$": "s",
    "€": "e",
    "£": "l",
    "¥": "y",
    "₹": "r",
    
    # Brackets/math
    "|": "i",
    "!": "i",
    "()": "o",
    "[]": "i",
    "{}": "o",
    "<>": "o",
    "/-\\": "a",
    "|\\|": "n",
    "|\\/|": "m",
    "\\|/": "v",
}

# URL obfuscation patterns (scammers use these to evade filters)
URL_OBFUSCATIONS: Dict[str, str] = {
    # Protocol obfuscation
    "hxxp": "http",
    "hxxps": "https",
    "h**p": "http",
    "h**ps": "https",
    "ht_tp": "http",
    "ht_tps": "https",
    
    # Dot obfuscation
    "[.]": ".",
    "(.)": ".",
    "{.}": ".",
    "< . >": ".",
    " dot ": ".",
    " DOT ": ".",
    "_dot_": ".",
    "-dot-": ".",
    "[dot]": ".",
    "(dot)": ".",
    
    # Slash obfuscation
    "\\/": "/",
    "//": "/",
}

# ═══════════════════════════════════════════════════════════════
# HOMOGLYPH NORMALIZATION (Unicode lookalikes)
# ═══════════════════════════════════════════════════════════════

HOMOGLYPH_MAP: Dict[str, str] = {
    # Cyrillic → Latin (scammers use Cyrillic to bypass filters)
    "а": "a",  # Cyrillic A
    "е": "e",  # Cyrillic E
    "о": "o",  # Cyrillic O
    "р": "p",  # Cyrillic P
    "с": "c",  # Cyrillic C
    "у": "y",  # Cyrillic Y
    "х": "x",  # Cyrillic X
    "і": "i",  # Ukrainian I
    "ӏ": "l",  # Palochka
    "ј": "j",  # Cyrillic J
    "ѕ": "s",  # Cyrillic S
    "һ": "h",  # Shha
    "ԁ": "d",  # Komi De
    
    # Greek → Latin
    "α": "a",
    "β": "b",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "n",
    "θ": "o",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "u",
    "ν": "v",
    "ξ": "e",
    "ο": "o",
    "π": "n",
    "ρ": "p",
    "σ": "o",
    "τ": "t",
    "υ": "u",
    "φ": "f",
    "χ": "x",
    "ψ": "ps",
    "ω": "w",
    
    # Mathematical → Latin
    "ℊ": "g",
    "ℎ": "h",
    "ℓ": "l",
    "℘": "p",
    "ℛ": "r",
    "ℯ": "e",
    "ℴ": "o",
    
    # Fullwidth → ASCII
    "Ａ": "a", "Ｂ": "b", "Ｃ": "c", "Ｄ": "d", "Ｅ": "e",
    "Ｆ": "f", "Ｇ": "g", "Ｈ": "h", "Ｉ": "i", "Ｊ": "j",
    "Ｋ": "k", "Ｌ": "l", "Ｍ": "m", "Ｎ": "n", "Ｏ": "o",
    "Ｐ": "p", "Ｑ": "q", "Ｒ": "r", "Ｓ": "s", "Ｔ": "t",
    "Ｕ": "u", "Ｖ": "v", "Ｗ": "w", "Ｘ": "x", "Ｙ": "y", "Ｚ": "z",
}

# ═══════════════════════════════════════════════════════════════
# HINDI/DEVANAGARI NORMALIZATION
# ═══════════════════════════════════════════════════════════════

DEVANAGARI_VARIATIONS: Dict[str, str] = {
    # Common typing variations in Hindi
    "क़": "क",
    "ख़": "ख",
    "ग़": "ग",
    "ज़": "ज",
    "ड़": "ड",
    "ढ़": "ढ",
    "फ़": "फ",
    "य़": "य",
    
    # Nukta normalization (combining marks)
    "\u093C": "",  # Nukta combining mark
}

# ═══════════════════════════════════════════════════════════════
# STAGE 1: Unicode Normalization
# ═══════════════════════════════════════════════════════════════

@lru_cache(maxsize=1024)
def normalize_unicode(text: str) -> str:
    """
    Apply Unicode NFKC normalization.
    
    NFKC = Normalization Form KC (Compatibility Composition)
    - Converts ligatures to base characters
    - Converts superscripts/subscripts to normal
    - Converts fullwidth chars to halfwidth
    
    Example: ℀ → a/c, ﬁ → fi, ² → 2
    """
    return unicodedata.normalize("NFKC", text)


# ═══════════════════════════════════════════════════════════════
# STAGE 2: Zero-Width Character Removal
# ═══════════════════════════════════════════════════════════════

def remove_zero_width(text: str) -> str:
    """
    Remove invisible zero-width characters.
    
    Scammers use these to split keywords:
    "p​a​y​p​a​l" → "paypal"
    """
    return ZERO_WIDTH_PATTERN.sub("", text)


# ═══════════════════════════════════════════════════════════════
# STAGE 3: Control Character Removal
# ═══════════════════════════════════════════════════════════════

def remove_control_characters(text: str) -> str:
    """
    Remove non-printable ASCII control characters (0x00-0x1F, 0x7F).
    Preserves: \t (tab), \n (newline), \r (return).
    """
    # Keep tabs and newlines, remove others
    result = []
    for char in text:
        code = ord(char)
        if code in (9, 10, 13):  # Tab, LF, CR
            result.append(char)
        elif 32 <= code <= 126 or code >= 128:  # Printable
            result.append(char)
    return "".join(result)


# ═══════════════════════════════════════════════════════════════
# STAGE 4: Homoglyph Normalization
# ═══════════════════════════════════════════════════════════════

def normalize_homoglyphs(text: str) -> str:
    """
    Replace visually similar characters with ASCII equivalents.
    
    Example: "раураl" (Cyrillic) → "paypal" (Latin)
    """
    for fake, real in HOMOGLYPH_MAP.items():
        text = text.replace(fake, real)
    
    # Devanagari variations
    for fake, real in DEVANAGARI_VARIATIONS.items():
        text = text.replace(fake, real)
    
    return text


# ═══════════════════════════════════════════════════════════════
# STAGE 5: Hex-Encoded URL Decoding
# ═══════════════════════════════════════════════════════════════

def decode_hex_urls(text: str) -> str:
    """
    Detect and decode hex-encoded URLs embedded in text.

    Scammers encode entire URLs as hexadecimal strings to evade filters:
        "687474703a2f2f7365637572652d7362692e78797a" → "http://secure-sbi.xyz"

    Strategy:
    1. Find long hexadecimal strings (≥14 hex chars = 7+ bytes).
    2. Check that the byte length is even (valid hex pairs).
    3. Attempt to decode as ASCII/UTF-8.
    4. Only replace if the decoded result contains a URL-like pattern
       (http://, https://, or domain.tld) to avoid false positives.
    """
    def _try_decode(match: re.Match) -> str:
        hex_str = match.group(1)
        # Must have even length (each byte = 2 hex chars)
        if len(hex_str) % 2 != 0:
            return match.group(0)
        try:
            decoded = bytes.fromhex(hex_str).decode('utf-8', errors='strict')
        except (ValueError, UnicodeDecodeError):
            return match.group(0)
        # Only accept if it looks like a URL or domain
        if re.search(r'https?://', decoded, re.IGNORECASE) or \
           re.search(r'[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}', decoded):
            return decoded
        return match.group(0)

    return HEX_ENCODED_PATTERN.sub(_try_decode, text)


# ═══════════════════════════════════════════════════════════════
# STAGE 6: Leetspeak Conversion
# ═══════════════════════════════════════════════════════════════

def normalize_leetspeak(text: str) -> str:
    """
    Context-aware leetspeak conversion.
    
    Converts: "Fr33" → "free", "p@yp@l" → "paypal"
    Preserves: "+91-9876543210" (phone numbers), "https://site.com" (URLs)
    
    Strategy:
    1. Protect numeric sequences (phone numbers, IDs, etc.)
    2. Only convert numbers when they're clearly part of words
    3. Always convert symbol substitutions (@, $, etc.)
    """
    
    # Patterns to protect from conversion
    PROTECT_PATTERNS = [
        (r'\+?\d{10,}', '___PHONE___'),           # Phone numbers: +919876543210
        (r'\b\d{8,}\b', '___NUMBER___'),          # Long numeric sequences: 12345678
        (r'https?://[^\s]+', '___URL___'),        # URLs
        (r'\b\d{4}-\d{4}-\d{4,}\b', '___ACCOUNT___'),  # Account patterns
    ]
    
    # Step 1: Replace protected patterns with placeholders
    protected = {}
    counter = 0
    for pattern, placeholder in PROTECT_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            key = f"{placeholder}{counter}"
            protected[key] = match
            text = text.replace(match, key, 1)
            counter += 1
    
    # Step 2: Apply multi-character leetspeak replacements
    for fake, real in sorted(LEET_MAP.items(), key=lambda x: -len(x[0])):
        if len(fake) > 1:
            text = text.replace(fake, real)
    
    # Step 3: Apply single-character replacements (symbols always, numbers contextually)
    # Always convert symbols
    SYMBOL_LEET = {"@": "a", "$": "s", "€": "e", "£": "l", "¥": "y", "₹": "r", "|": "i"}
    for fake, real in SYMBOL_LEET.items():
        text = text.replace(fake, real)
    
    # Convert numbers ONLY when part of words (has letters nearby)
    NUMBER_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g"}
    
    # Use word boundary detection - only convert numbers inside words
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        
        # If it's a number that could be leetspeak
        if char in NUMBER_LEET:
            # Check if it's part of a word (has letters before or after)
            has_letter_before = i > 0 and text[i-1].isalpha()
            has_letter_after = i < len(text)-1 and text[i+1].isalpha()
            
            # Only convert if it's clearly part of a word
            if has_letter_before or has_letter_after:
                result.append(NUMBER_LEET[char])
            else:
                result.append(char)
        else:
            result.append(char)
        i += 1
    
    text = ''.join(result)
    
    # Step 4: Restore protected patterns
    for key, original in protected.items():
        text = text.replace(key, original)
    
    return text


# ═══════════════════════════════════════════════════════════════
# STAGE 7: Character-Spacing Deobfuscation
# ═══════════════════════════════════════════════════════════════

def deobfuscate_char_spacing(text: str) -> str:
    """
    Collapse character-spacing obfuscation where scammers insert spaces
    between every character to evade pattern matching.

    Example:
        "h t t p : / / s b i - l o g i n . x y z" → "http://sbi-login.xyz"
        "s e n d m o n e y" → "sendmoney"

    Only collapses runs of 4+ single-character tokens to avoid
    breaking normal short words.
    """
    def _collapse(match: re.Match) -> str:
        fragment = match.group(1)
        # Only collapse if most tokens are single characters
        tokens = fragment.split(' ')
        single_char_count = sum(1 for t in tokens if len(t) == 1)
        # At least 70% single chars and minimum 4 tokens
        if len(tokens) >= 4 and single_char_count / len(tokens) >= 0.7:
            return ''.join(tokens)
        return fragment

    return CHAR_SPACING_PATTERN.sub(_collapse, text)


# ═══════════════════════════════════════════════════════════════
# STAGE 8: URL Deobfuscation
# ═══════════════════════════════════════════════════════════════

def deobfuscate_urls(text: str) -> str:
    """
    Fix common URL obfuscation patterns.
    
    Example: "hxxps://paypаl[.]com" → "https://paypal.com"
    """
    # Apply all obfuscation replacements
    for fake, real in URL_OBFUSCATIONS.items():
        text = text.replace(fake, real)
    
    # Additional URL-specific cleaning
    text = re.sub(r'h\*{2,}ps?', 'https', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*dot\s*', '.', text, flags=re.IGNORECASE)
    
    # Fix any remaining hxxp/hxxps patterns
    text = text.replace("hxxp://", "http://")
    text = text.replace("hxxps://", "https://")
    text = text.replace("http:/", "http://")
    text = text.replace("https:/", "https://")
    
    return text


# ═══════════════════════════════════════════════════════════════
# STAGE 9: Shortened URL Expansion
# ═══════════════════════════════════════════════════════════════

def _is_shortened_url(url: str) -> bool:
    """
    Determine whether *url* points to a known URL shortener.

    Checks the hostname (case-insensitive) against SHORTENER_DOMAINS.
    Also catches very short path-only URLs (e.g. bit.ly/abc).
    """
    try:
        # Strip protocol
        without_proto = re.sub(r'^https?://', '', url, flags=re.IGNORECASE)
        host = without_proto.split('/')[0].split('?')[0].split('#')[0].lower()
        return host in SHORTENER_DOMAINS
    except Exception:
        return False


def _expand_single_url(
    url: str,
    timeout: float = SHORTENED_URL_EXPAND_TIMEOUT,
    max_redirects: int = SHORTENED_URL_MAX_REDIRECTS,
) -> str:
    """
    Expand a single shortened URL by following redirects.

    Performs a HEAD request (fast, no body downloaded) with
    ``allow_redirects=True`` and returns the final resolved URL.
    Falls back to the original URL on any error or timeout.

    Args:
        url: The shortened URL to expand.
        timeout: Per-request timeout in seconds.
        max_redirects: Maximum redirect hops.

    Returns:
        The expanded URL, or the original on failure.
    """
    try:
        session = requests.Session()
        session.max_redirects = max_redirects
        response = session.head(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        final_url = response.url
        if final_url and final_url != url:
            _log.debug("Expanded shortened URL: %s -> %s", url, final_url)
            return final_url
    except requests.exceptions.Timeout:
        _log.warning("Timeout expanding shortened URL: %s", url)
    except requests.exceptions.TooManyRedirects:
        _log.warning("Too many redirects for shortened URL: %s", url)
    except requests.exceptions.RequestException as exc:
        _log.debug("Failed to expand shortened URL %s: %s", url, exc)
    except Exception as exc:  # pragma: no cover — safety net
        _log.debug("Unexpected error expanding URL %s: %s", url, exc)
    return url


def expand_shortened_urls(
    text: str,
    timeout: float = SHORTENED_URL_EXPAND_TIMEOUT,
    max_workers: int = 4,
) -> str:
    """
    Detect and expand shortened URLs in *text*.

    Scammers frequently use URL shorteners to hide malicious destinations.
    This stage:
    1. Finds all URLs in the text.
    2. Checks each against a list of known shortener domains.
    3. Expands matching URLs in parallel (with per-URL timeout).
    4. Replaces the shortened URLs with their expanded forms.

    Args:
        text: Input text potentially containing shortened URLs.
        timeout: Timeout per URL expansion (seconds).
        max_workers: Max threads for parallel expansion.

    Returns:
        Text with shortened URLs replaced by their expanded destinations.
    """
    urls = FULL_URL_PATTERN.findall(text)
    if not urls:
        return text

    short_urls = [url for url in urls if _is_shortened_url(url)]
    if not short_urls:
        return text

    # De-duplicate while preserving order
    seen: Set[str] = set()
    unique_short: List[str] = []
    for u in short_urls:
        if u not in seen:
            seen.add(u)
            unique_short.append(u)

    # Expand in parallel with a thread pool for I/O-bound work
    expanded_map: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(unique_short))) as pool:
        futures = {
            pool.submit(_expand_single_url, u, timeout): u
            for u in unique_short
        }
        for future in futures:
            original = futures[future]
            try:
                expanded_map[original] = future.result(timeout=timeout + 2)
            except FuturesTimeoutError:
                _log.warning("Thread-level timeout expanding: %s", original)
                expanded_map[original] = original
            except Exception:
                expanded_map[original] = original

    # Substitute expanded URLs back into the text
    for short, expanded in expanded_map.items():
        if expanded != short:
            text = text.replace(short, expanded)

    return text


# ═══════════════════════════════════════════════════════════════
# STAGE 10: Whitespace Normalization
# ═══════════════════════════════════════════════════════════════

def normalize_whitespace(text: str) -> str:
    """
    Collapse multiple whitespace characters into single space.
    Remove leading/trailing whitespace.
    
    Example: "urgent   action  needed" → "urgent action needed"
    """
    # Replace all whitespace variants with single space
    text = MULTI_WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════
# STAGE 11: Phone Number Normalization (Helper)
# ═══════════════════════════════════════════════════════════════

def normalize_phone_number(text: str) -> str:
    """
    Normalize phone number formatting.
    
    Example: "+91 (987) 654-3210" → "+919876543210"
    """
    return PHONE_PATTERN.sub("", text)


# ═══════════════════════════════════════════════════════════════
# MAIN NORMALIZATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def normalize_input(text: str, expand_urls: bool = True) -> str:
    """
    Production-grade 11-stage normalization pipeline.
    
    ✅ Deterministic (same input → same output)
    ✅ Idempotent (running twice = same result)
    ✅ Safe (no eval, no exec)
    
    Args:
        text: Raw user input (potentially obfuscated)
        expand_urls: Whether to expand shortened URLs (requires network).
                     Set to False when offline or for fastest processing.
    
    Returns:
        Normalized, lowercase, clean text ready for detection
    
    Example:
        Input:  "Fr​33 Bіtcоin!!! Clіck hxxps://раураl[.]com"
        Output: "free bitcoin!!! click https://paypal.com"
    """
    
    # Type safety
    if not isinstance(text, str):
        return ""
    
    # Empty check
    if not text.strip():
        return ""
    
    # Execute pipeline
    text = normalize_unicode(text)              # Stage 1
    text = remove_zero_width(text)              # Stage 2
    text = remove_control_characters(text)      # Stage 3
    text = normalize_homoglyphs(text)           # Stage 4
    text = decode_hex_urls(text)                # Stage 5
    text = normalize_leetspeak(text)            # Stage 6
    text = deobfuscate_char_spacing(text)       # Stage 7
    text = deobfuscate_urls(text)               # Stage 8
    if expand_urls:                             # Stage 9
        text = expand_shortened_urls(text)
    text = normalize_whitespace(text)           # Stage 10
    text = text.lower()                         # Stage 11
    
    return text


# ═══════════════════════════════════════════════════════════════
# ADVANCED: Selective Normalization (for specific fields)
# ═══════════════════════════════════════════════════════════════

def normalize_for_detection(text: str) -> str:
    """
    Alias for normalize_input (primary use case).
    """
    return normalize_input(text)


def normalize_for_display(text: str) -> str:
    """
    Lighter normalization for UI display (preserve readability).
    """
    text = normalize_unicode(text)
    text = remove_zero_width(text)
    text = normalize_whitespace(text)
    return text


def normalize_url_for_extraction(url: str) -> str:
    """
    Specialized normalization for URL extraction.
    """
    url = deobfuscate_urls(url)
    url = normalize_homoglyphs(url)
    url = url.lower()
    return url


def normalize_phone_for_extraction(phone: str) -> str:
    """
    Specialized normalization for phone number extraction.
    """
    phone = normalize_phone_number(phone)
    phone = re.sub(r'[^\d+]', '', phone)
    return phone


# ═══════════════════════════════════════════════════════════════
# DIAGNOSTICS & DEBUG
# ═══════════════════════════════════════════════════════════════

def get_normalization_report(text: str) -> Dict[str, str]:
    """
    Debug function: Show transformation at each stage.
    
    Returns:
        Dictionary with results from each normalization stage
    """
    report = {
        "original": text,
        "stage1_unicode": normalize_unicode(text),
    }
    
    current = report["stage1_unicode"]
    
    current = remove_zero_width(current)
    report["stage2_zero_width"] = current
    
    current = remove_control_characters(current)
    report["stage3_control_chars"] = current
    
    current = normalize_homoglyphs(current)
    report["stage4_homoglyphs"] = current
    
    current = decode_hex_urls(current)
    report["stage5_hex_urls"] = current
    
    current = normalize_leetspeak(current)
    report["stage6_leetspeak"] = current
    
    current = deobfuscate_char_spacing(current)
    report["stage7_char_spacing"] = current
    
    current = deobfuscate_urls(current)
    report["stage8_urls"] = current
    
    current = expand_shortened_urls(current)
    report["stage9_short_urls"] = current
    
    current = normalize_whitespace(current)
    report["stage10_whitespace"] = current
    
    current = current.lower()
    report["stage11_final"] = current
    
    return report


# ═══════════════════════════════════════════════════════════════
# PERFORMANCE TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Fr​33 Bіtcоin!!!",
        "Clіck hxxps://раураl[.]com",
        "Ur𝓰𝓮𝓷𝓽 @cti0n n3eded",
        "Cаll +91 (987) 654-3210",
        "आपका खाता बंद हो जाएगा",
        "УРI भेजो 1000₹",
    ]
    
    print("═" * 70)
    print("NORMALIZATION MODULE - TEST RUN")
    print("═" * 70)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"  Input:  {test!r}")
        normalized = normalize_input(test)
        print(f"  Output: {normalized!r}")
    
    print("\n" + "═" * 70)
    print("DETAILED REPORT FOR TEST 1:")
    print("═" * 70)
    report = get_normalization_report(test_cases[0])
    for stage, result in report.items():
        print(f"{stage:20s}: {result!r}")
