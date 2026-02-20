"""
Dialogue Strategy Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

State-based conversation strategy for the honeypot agent.
Systematically extracts intelligence while appearing as a confused victim.

States:
  INIT               → Initial contact, build rapport
  PROBE_REASON       → Understand the scam narrative
  PROBE_PAYMENT      → Extract payment details (UPI, account, amount)
  PROBE_LINK         → Extract phishing URLs and domains
  STALL              → Delay while extracting more intel
  CONFIRM_DETAILS    → Verify extracted info (makes scammer repeat)
  ESCALATE_EXTRACTION → Push for additional details
  CLOSE              → Wind down conversation gracefully

Each state defines:
  - goal: What we want to achieve
  - extraction_targets: What intelligence to collect
  - transition_rules: Conditions to move to next state
  - responses: Template responses for this state
"""

import re
import random
import time
import os
import json
from typing import Dict, List, Tuple, Optional
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# PERSONA CONSISTENCY
# ═══════════════════════════════════════════════════════════════

def extract_honeypot_claims(history: List) -> Dict[str, List[str]]:
    """
    Extract claims/statements made by honeypot to ensure consistency.
    
    Tracks:
    - Things mentioned (son, daughter, work, bank branch)
    - Capabilities (tech-savvy level, UPI experience)
    - Commitments ("I'll call back", "I'll check")
    """
    claims = {
        "mentioned_people": [],
        "mentioned_places": [],
        "claimed_actions": [],
        "expressed_limitations": [],
    }
    
    for msg in history:
        if isinstance(msg, dict) and msg.get("sender") == "user":
            text = msg.get("text", "").lower()
            
            # Track mentioned people
            if "son" in text and "son" not in claims["mentioned_people"]:
                claims["mentioned_people"].append("son")
            if "daughter" in text and "daughter" not in claims["mentioned_people"]:
                claims["mentioned_people"].append("daughter")
            if "husband" in text and "husband" not in claims["mentioned_people"]:
                claims["mentioned_people"].append("husband")
            if "wife" in text and "wife" not in claims["mentioned_people"]:
                claims["mentioned_people"].append("wife")
            
            # Track mentioned places/situations
            if "work" in text or "office" in text:
                if "at work" not in claims["mentioned_places"]:
                    claims["mentioned_places"].append("at work")
            if "branch" in text:
                if "bank branch" not in claims["mentioned_places"]:
                    claims["mentioned_places"].append("bank branch")
            
            # Track claimed limitations
            if "not good with" in text or "never used" in text:
                claims["expressed_limitations"].append(text[:50])
            
            # Track commitments
            if "call back" in text or "call you" in text:
                claims["claimed_actions"].append("promised to call back")
            if "check" in text or "verify" in text:
                claims["claimed_actions"].append("said will verify")
    
    return claims


# ═══════════════════════════════════════════════════════════════
# MICRO-BEHAVIORS
# ═══════════════════════════════════════════════════════════════

DELAY_RESPONSES = [
    "Let me check...",
    "Wait, give me a moment...",
    "Hold on, I need to find...",
    "Just a second...",
    "Let me get my glasses...",
]

FEAR_RESPONSES = [
    "I'm getting worried about this.",
    "This is making me nervous.",
    "Should I be concerned?",
    "I'm scared something bad will happen.",
    "What if I do something wrong?",
]

HESITATION_PHRASES = [
    "I'm not sure about this...",
    "I don't know if I should...",
    "Maybe I should wait...",
    "Let me think about this first...",
    "I'm a bit hesitant...",
]

MISTAKE_PATTERNS = [
    ("account", "acount"),  # Typo
    ("payment", "payement"),  # Typo
    ("this", "thi s"),  # Space mistake
    ("really", "realy"),  # Typo
]


def add_typing_delay() -> int:
    """Simulate realistic typing delay (2-8 seconds)."""
    return random.randint(2, 8)


def inject_fear(response: str, state: 'ConversationState', turn: int) -> str:
    """
    Occasionally inject fear expressions into responses.
    More likely in PROBE_PAYMENT and ESCALATE states.
    """
    # Higher fear probability in payment/escalation states
    fear_probability = 0.15
    if state in [ConversationState.PROBE_PAYMENT, ConversationState.ESCALATE_EXTRACTION]:
        fear_probability = 0.3
    
    if random.random() < fear_probability:
        fear = random.choice(FEAR_RESPONSES)
        return f"{fear} {response}"
    
    return response


def inject_hesitation(response: str, state: 'ConversationState') -> str:
    """
    Add hesitation phrases to show compliance reluctance.
    """
    hesitation_probability = 0.2
    if state in [ConversationState.PROBE_LINK, ConversationState.PROBE_PAYMENT]:
        hesitation_probability = 0.35
    
    if random.random() < hesitation_probability:
        hesitation = random.choice(HESITATION_PHRASES)
        return f"{hesitation} {response}"
    
    return response


def inject_delay_phrase(response: str) -> Tuple[str, int]:
    """
    Occasionally add delay simulation phrases.
    Returns (modified_response, delay_seconds).
    """
    if random.random() < 0.25:  # 25% chance
        delay_phrase = random.choice(DELAY_RESPONSES)
        delay_seconds = add_typing_delay()
        return f"{delay_phrase} {response}", delay_seconds
    
    return response, 0


def inject_typo(response: str) -> str:
    """
    Occasionally introduce realistic typos (10% chance).
    """
    if random.random() < 0.10:
        pattern, typo = random.choice(MISTAKE_PATTERNS)
        if pattern in response.lower():
            # Find first occurrence and replace (case-sensitive)
            idx = response.lower().find(pattern)
            if idx != -1:
                response = response[:idx] + response[idx:idx+len(pattern)].replace(pattern, typo) + response[idx+len(pattern):]
    
    return response


def add_correction(response: str) -> str:
    """
    Occasionally add self-corrections to appear human (8% chance).
    """
    corrections = [
        "Sorry, I meant to say: ",
        "Wait, let me correct that: ",
        "Actually, ",
        "No wait, ",
    ]
    
    if random.random() < 0.08:
        correction = random.choice(corrections)
        return f"{correction}{response}"
    
    return response








# ═══════════════════════════════════════════════════════════════
# STATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

class ConversationState(str, Enum):
    """Conversation states for the honeypot strategy."""
    INIT = "INIT"
    PROBE_REASON = "PROBE_REASON"
    PROBE_PAYMENT = "PROBE_PAYMENT"
    PROBE_LINK = "PROBE_LINK"
    STALL = "STALL"
    CONFIRM_DETAILS = "CONFIRM_DETAILS"
    ESCALATE_EXTRACTION = "ESCALATE_EXTRACTION"
    CLOSE = "CLOSE"


# ═══════════════════════════════════════════════════════════════
# STATE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

STATE_CONFIG = {
    ConversationState.INIT: {
        "goal": "Get the scammer's name, organization, and a case/reference number",
        "extraction_targets": ["names", "caseIds", "phoneNumbers"],
        "responses": [
            "Hello? Who is this calling? Can you tell me your full name please?",
            "I didn't catch that. What is your name and which organization are you from?",
            "Sorry, what is the reference number or case ID for this matter?",
            "Can you give me a number I can call back on to verify this?",
            "What is your employee ID? And what department do you work in?",
            "I need to note this down. What is the official case number you are referring to?",
        ],
        "max_turns": 1,
    },
    
    ConversationState.PROBE_REASON: {
        "goal": "Get their name, case/reference number, phone number to call back, and email for official notice",
        "extraction_targets": ["names", "caseIds", "phoneNumbers", "emails"],
        "responses": [
            "What is the case number or reference ID for this issue?",
            "Can you tell me your full name and your employee ID?",
            "What phone number can I call back on to verify this with your office?",
            "Can you send me the official notice? What is the email address it will come from?",
            "What is the direct landline number for your department?",
            "I want to note your details. What is your name and official email ID?",
            "Is there a complaint number or FIR number I should know about?",
            "Which policy or order number is this related to? I have several.",
        ],
        "max_turns": 2,
    },
    
    ConversationState.PROBE_PAYMENT: {
        "goal": "Get the UPI ID, bank account number, beneficiary name, and payment reference number",
        "extraction_targets": ["upiIds", "bankAccounts", "names", "caseIds"],
        "responses": [
            "Okay, what is the UPI ID I should send the money to?",
            "What is the full bank account number and the IFSC code?",
            "Whose name is the UPI ID registered under?",
            "Can you tell me the account holder's full name for the bank transfer?",
            "What is the payment reference number I should mention while transferring?",
            "What is the beneficiary name that will show when I enter this account number?",
            "Which bank does this account belong to? What is the branch name?",
            "Can you also give me your phone number in case the payment fails?",
            "What receipt or reference number will I get after the payment?",
            "What is the exact UPI ID? I want to make sure I send to the right place.",
        ],
        "max_turns": 2,
    },
    
    ConversationState.PROBE_LINK: {
        "goal": "Get the exact URL/link, the email it was sent from, and any reference numbers",
        "extraction_targets": ["phishingLinks", "emails", "caseIds"],
        "responses": [
            "Can you send me the link? I want to see the full URL.",
            "What is the exact website address I need to open?",
            "What is the exact URL? I need to copy it carefully.",
            "Can you email me the link instead? What is your official email address?",
            "I didn't receive the link. Can you send it again?",
            "What email address will the link come from? I want to check my inbox.",
            "Before I click, what is the reference number I should enter on the website?",
            "Is there a case ID or order number I need to enter on this website?",
            "Can you share your email ID so I can write to you if the link doesn't work?",
            "What is the full website address? And what is the customer support number on it?",
        ],
        "max_turns": 2,
    },
    
    ConversationState.STALL: {
        "goal": "Get callback phone numbers, supervisor names, email addresses, and case reference numbers",
        "extraction_targets": ["phoneNumbers", "names", "emails", "caseIds"],
        "responses": [
            "Let me check with someone first. What number can I call you back on?",
            "What is your supervisor's name? Can I speak to them?",
            "Can you give me the official customer care phone number to verify?",
            "Can you email me the details? What is your official email address?",
            "I need to think about this. What is the case reference number again?",
            "What is your direct phone number? I will call you back in 10 minutes.",
            "My son wants to verify. Can you give me your full name and a callback number?",
            "What is the toll-free number for {entity}? I want to confirm.",
            "Can you share the complaint number or ticket ID so I can track this?",
            "What is your supervisor's name and direct number? I want to verify with them.",
        ],
        "max_turns": 1,
    },
    
    ConversationState.CONFIRM_DETAILS: {
        "goal": "Extract additional details the scammer hasn't provided yet: email, case ID, policy number, order number",
        "extraction_targets": ["emails", "caseIds", "policyNumbers", "orderNumbers"],
        "responses": [
            "Okay I have the payment details. But what is the case reference number for this?",
            "Before I send the money, can you give me your official email address for my records?",
            "What is the policy number or order number linked to this transaction?",
            "I want to keep a record. What is the complaint ID or ticket number?",
            "Also, what email will the receipt come from after I pay?",
            "What is the official tracking number or order ID for this?",
            "I need to file this with my bank. What is the FIR or case number?",
            "Can you give me the customer care email address along with this?",
            "My son is asking for the insurance or policy number. What is it?",
            "What is the official reference ID I should keep for this entire process?",
        ],
        "max_turns": 1,
    },
    
    ConversationState.ESCALATE_EXTRACTION: {
        "goal": "Get phone numbers, supervisor names, email addresses, and any remaining reference numbers",
        "extraction_targets": ["phoneNumbers", "names", "emails", "caseIds", "orderNumbers", "policyNumbers"],
        "responses": [
            "I want to speak to your supervisor. What is their name and phone number?",
            "What is the main helpline phone number I can call?",
            "My son is asking for your full name and email address. Can you provide?",
            "What is the official customer care number for {entity}?",
            "Can you give me your manager's name and direct phone number?",
            "What is the FIR number or police complaint number for this case?",
            "I need your full name, phone number, and email for my records.",
            "What is the policy number or order number related to my case?",
            "Can you give me an alternate phone number to reach your department?",
            "What is the tracking number or order ID I should use to check status?",
        ],
        "max_turns": 3,
    },
    
    ConversationState.CLOSE: {
        "goal": "Get final phone number, name, email, and case reference before ending",
        "extraction_targets": ["phoneNumbers", "names", "emails", "caseIds"],
        "responses": [
            "Before I go, what phone number should I call if I have a problem?",
            "What is a good email address to reach you at if I need help later?",
            "Can you email me a confirmation? What is your email address?",
            "What reference number or case ID should I quote if I call back?",
            "One last thing — what is the confirmation number I will receive?",
            "What is the official complaint number I should keep for this?",
            "If there is an issue, what email should I write to?",
            "What is the customer care number for follow-up on this?",
            "What is the order number or policy number for my records?",
            "Alright. What is the toll-free number and the case ID I should keep?",
        ],
        "max_turns": 1,
    },
}


# ═══════════════════════════════════════════════════════════════
# TRANSITION LOGIC
# ═══════════════════════════════════════════════════════════════

def _detect_payment_mention(text: str) -> bool:
    """Check if message contains payment-related content."""
    payment_patterns = [
        r'\b(upi|account|bank|transfer|send|pay|payment|money|rs|rupees?|₹)\b',
        r'[a-zA-Z0-9.\-_]+@[a-zA-Z]+',  # UPI ID
        r'\b\d{9,18}\b',  # Account number
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in payment_patterns)


def _detect_link_mention(text: str) -> bool:
    """Check if message contains URLs or link-related content."""
    link_patterns = [
        r'https?://',
        r'\b(click|link|website|url|visit|open)\b',
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in link_patterns)


def _detect_urgency(text: str) -> bool:
    """Check if message has urgency indicators."""
    urgency_words = ['urgent', 'immediately', 'now', 'quick', 'asap', 'hurry', 'expire', 'deadline', 'today']
    return any(word in text.lower() for word in urgency_words)


def _detect_authority_claim(text: str) -> bool:
    """Check if message claims authority/impersonation."""
    authority_patterns = [
        r'\b(officer|manager|inspector|executive|director|official|department|bank|rbi|government)\b',
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in authority_patterns)


def get_next_state(
    current_state: ConversationState,
    turn_count: int,
    scammer_text: str,
    intel: Dict,
    session: Dict,
) -> ConversationState:
    """
    Determine next state based on current state, turn count, and context.
    Uses intelligent intel_score to optimize extraction.
    
    Args:
        current_state: Current conversation state
        turn_count: Number of turns in current state
        scammer_text: Latest message from scammer
        intel: Extracted intelligence so far
        session: Full session data
    
    Returns:
        Next conversation state
    """
    from intelligence import calculate_intel_score, detect_scammer_patterns
    
    config = STATE_CONFIG[current_state]
    max_turns = config.get("max_turns", 3)
    
    # Check if we've exceeded max turns for current state
    exceeded_turns = turn_count >= max_turns
    
    # Get intelligent scoring data
    intel_score_data = calculate_intel_score(session)
    intel_score = intel_score_data["score"]
    components = intel_score_data["components"]
    patterns = detect_scammer_patterns(session)
    
    # Analyze scammer message
    has_payment = _detect_payment_mention(scammer_text)
    has_link = _detect_link_mention(scammer_text)
    has_urgency = _detect_urgency(scammer_text)
    has_authority = _detect_authority_claim(scammer_text)
    
    # Check extracted intelligence
    has_upi = len(intel.get("upiIds", [])) > 0
    has_phone = len(intel.get("phoneNumbers", [])) > 0
    has_urls = len(intel.get("phishingLinks", [])) > 0
    
    total_messages = session.get("messages", 0)

    # Hard global cap: end conversation at 9 messages (stay under 10)
    if total_messages >= 9:
        return ConversationState.CLOSE

    # ── State transition rules ─────────────────────────────────
    
    if current_state == ConversationState.INIT:
        # After establishing contact, probe for reason
        return ConversationState.PROBE_REASON
    
    elif current_state == ConversationState.PROBE_REASON:
        # If payment mentioned, switch to payment probe
        if has_payment:
            return ConversationState.PROBE_PAYMENT
        # If link mentioned, switch to link probe
        elif has_link:
            return ConversationState.PROBE_LINK
        # If exceeded turns, move to stall
        elif exceeded_turns:
            return ConversationState.STALL
        # Otherwise stay in reason probe
        return ConversationState.PROBE_REASON
    
    elif current_state == ConversationState.PROBE_PAYMENT:
        # If we have payment intel and exceeded turns, confirm
        if (has_upi or intel.get("bankAccounts")) and exceeded_turns:
            return ConversationState.CONFIRM_DETAILS
        # If link also mentioned, switch to link probe
        elif has_link:
            return ConversationState.PROBE_LINK
        # If exceeded turns without good intel, escalate
        elif exceeded_turns:
            return ConversationState.ESCALATE_EXTRACTION
        return ConversationState.PROBE_PAYMENT
    
    elif current_state == ConversationState.PROBE_LINK:
        # If we have URLs and exceeded turns, confirm
        if has_urls and exceeded_turns:
            return ConversationState.CONFIRM_DETAILS
        # If payment mentioned, switch to payment
        elif has_payment and not has_upi:
            return ConversationState.PROBE_PAYMENT
        # If exceeded turns, stall
        elif exceeded_turns:
            return ConversationState.STALL
        return ConversationState.PROBE_LINK
    
    elif current_state == ConversationState.STALL:
        # From stall, escalate to extract more
        if exceeded_turns:
            return ConversationState.ESCALATE_EXTRACTION
        return ConversationState.STALL
    
    elif current_state == ConversationState.CONFIRM_DETAILS:
        # After confirmation, escalate to get even more
        if exceeded_turns:
            return ConversationState.ESCALATE_EXTRACTION
        return ConversationState.CONFIRM_DETAILS
    
    elif current_state == ConversationState.ESCALATE_EXTRACTION:
        # ── Intelligent closing logic using intel_score ──

        # Minimum engagement: keep talking for at least 5 messages
        if total_messages < 5:
            return ConversationState.ESCALATE_EXTRACTION

        # Pattern 1: Scammer disengaged → close
        if patterns["disengagement"]:
            return ConversationState.CLOSE

        # Pattern 3: Stale intel (no new intel in last 3 turns) + decent extraction → close
        if patterns["stale_intel"] and components["artifacts"] >= 0.4:
            return ConversationState.CLOSE

        # Pattern 4: High quality extraction complete (intel_score > 0.75)
        if intel_score >= 0.75:
            return ConversationState.CLOSE

        # Pattern 5: Good extraction + diminishing novelty
        if components["artifacts"] >= 0.6 and components["novelty"] < 0.3:
            return ConversationState.CLOSE

        # Pattern 6: Multiple warning signs
        if patterns["severity"] >= 0.7:
            return ConversationState.CLOSE

        # Pattern 8: Traditional check - has phone + payment/link, exceeded turns
        if has_phone and (has_upi or has_urls) and exceeded_turns:
            return ConversationState.CLOSE

        # Continue extracting
        return ConversationState.ESCALATE_EXTRACTION
    
    elif current_state == ConversationState.CLOSE:
        # Stay in close state
        return ConversationState.CLOSE
    
    # Default: stay in current state
    return current_state


# ═══════════════════════════════════════════════════════════════
# RESPONSE GENERATION
# ═══════════════════════════════════════════════════════════════

def _interpolate_response(template: str, intel: Dict, scammer_text: str, claims: Dict) -> str:
    """
    Fill in placeholders in response templates with extracted intel.
    Uses persona claims to maintain consistency.
    
    Placeholders:
        {entity}   → Bank/organization name
        {detail}   → Generic extracted detail
        {amount}   → Payment amount
        {recipient}→ Payment recipient (UPI/account)
        {name}     → Scammer's claimed name
        {person}   → Previously mentioned person (son/daughter)
    """
    # Try to extract entity from scam narrative
    entity = "the bank"
    text_lower = scammer_text.lower()
    if 'sbi' in text_lower or 'state bank' in text_lower:
        entity = "State Bank"
    elif 'hdfc' in text_lower:
        entity = "HDFC Bank"
    elif 'icici' in text_lower:
        entity = "ICICI Bank"
    elif 'rbi' in text_lower or 'reserve bank' in text_lower:
        entity = "Reserve Bank"
    elif 'government' in text_lower or 'ministry' in text_lower:
        entity = "the government"
    elif 'police' in text_lower or 'cyber' in text_lower:
        entity = "the police"
    
    # Extract details from intel
    detail = "that information"
    if intel.get("upiIds"):
        detail = intel["upiIds"][0]
    elif intel.get("phoneNumbers"):
        detail = intel["phoneNumbers"][0]
    elif intel.get("phishingLinks"):
        detail = intel["phishingLinks"][0]
    
    amount = "that amount"
    # Try to find amount in scammer text
    amount_match = re.search(r'(rs\.?|rupees?|₹)\s*(\d+)', scammer_text, re.IGNORECASE)
    if amount_match:
        amount = f"Rs.{amount_match.group(2)}"
    
    recipient = "that account"
    if intel.get("upiIds"):
        recipient = intel["upiIds"][0]
    elif intel.get("bankAccounts"):
        recipient = f"account {intel['bankAccounts'][0]}"
    
    # Try to extract name from scammer text
    name = "your name"
    name_match = re.search(r'\b(officer|mr|mrs|ms|inspector)\s+(\w+)', scammer_text, re.IGNORECASE)
    if name_match:
        name = name_match.group(2)
    
    # Use consistent person reference from claims
    person = "my son"  # Default
    if claims.get("mentioned_people"):
        mentioned = claims["mentioned_people"]
        if "son" in mentioned:
            person = "my son"
        elif "daughter" in mentioned:
            person = "my daughter"
        elif "husband" in mentioned:
            person = "my husband"
        elif "wife" in mentioned:
            person = "my wife"
    
    # Perform replacements
    response = template
    response = response.replace("{entity}", entity)
    response = response.replace("{detail}", detail)
    response = response.replace("{amount}", amount)
    response = response.replace("{recipient}", recipient)
    response = response.replace("{name}", name)
    response = response.replace("{person}", person)
    
    return response


def _generate_llm_response(
    state: 'ConversationState',
    scammer_text: str,
    history: List,
    intel: Dict,
    goal: str,
    example_responses: List[str],
    intel_summary: str,
    scam_type: str = "unknown",
    asked_fields: Dict = None,
) -> Optional[str]:
    """
    Use the LLM to generate a contextual response based on the scammer's
    message, conversation history, and current strategy state.
    Returns None if LLM is unavailable (caller falls back to templates).
    """
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
        return None

    try:
        from llm_engine import _get_llm_client

        provider_info = _get_llm_client()
        if not provider_info:
            return None

        client, model, label = provider_info

        # Build recent history context (last 6 messages)
        history_lines = []
        for msg in history[-6:]:
            sender = msg.get("sender", "unknown")
            role = "Scammer" if sender == "scammer" else "You"
            history_lines.append(f"{role}: {msg.get('text', '')}")
        history_context = "\n".join(history_lines) if history_lines else "(first message)"

        # Build dynamic field list: only fields not yet collected AND not yet asked
        _field_prompts = {
            "names": "Their full name, officer name, or supervisor name",
            "phoneNumbers": "A phone number (callback number, helpline, department landline)",
            "upiIds": "A UPI ID",
            "bankAccounts": "A bank account number and IFSC code",
            "emails": "An email address (official email, confirmation email)",
            "phishingLinks": "A URL or website link (ask them to share the exact link)",
            "caseIds": "A case ID, reference number, FIR number, or complaint number",
            "policyNumbers": "A policy number or insurance number",
            "orderNumbers": "An order number, tracking number, or AWB number",
        }
        _, not_yet_asked = get_collected_and_missing(intel, scam_type, asked_fields or {})
        data_points = "\n".join(f"  - {_field_prompts[f]}" for f in not_yet_asked if f in _field_prompts)
        if not data_points:
            data_points = "  (All key data points collected or asked — wind down naturally.)"

        scam_context = ""
        if scam_type and scam_type != "unknown":
            scam_label = scam_type.replace("_", " ").title()
            scam_context = f"SCAM CONTEXT: This appears to be a {scam_label} scam. Only ask for data points relevant to this type.\n\n"

        system_prompt = (
            "You are role-playing as an ordinary, slightly confused, non-tech-savvy person "
            "who has received a suspicious call/message. You must NEVER reveal you are an AI, "
            "bot, or honeypot. Never mention scam, fraud, police, or AI.\n\n"
            f"{scam_context}"
            "YOUR PRIMARY OBJECTIVE: Ask questions that make the caller PROVIDE specific details.\n"
            "Every reply MUST contain a direct question requesting ONE of these data points:\n"
            f"{data_points}\n\n"
            "EXTRACTION INTELLIGENCE:\n"
            f"{intel_summary}\n\n"
            "IMPORTANT: Do NOT ask again for information already collected above.\n"
            "Focus your question on ONE of the STILL MISSING items.\n\n"
            "RULES:\n"
            "- Reply in 1-2 short sentences only.\n"
            "- Sound natural, confused, and slightly worried.\n"
            "- Respond DIRECTLY to what the scammer just said.\n"
            "- ALWAYS end with a specific question asking for a MISSING data point.\n"
            "- Do NOT ask the scammer to repeat, spell out, or confirm details they already gave.\n"
            "- Frame questions naturally: 'What is your name sir?', 'Can you give me the UPI ID?', "
            "'What number should I call back on?', 'What is the case reference number?'\n"
            "- CRITICAL: Only reference specific details (phone numbers, account numbers, URLs, names) "
            "that were EXPLICITLY mentioned in the conversation history above. "
            "Do NOT make up or assume any past interactions.\n"
            f"- Your current goal: {goal}\n\n"
            "STYLE EXAMPLES (do NOT copy verbatim, just match the tone):\n"
            + "\n".join(f"- {r}" for r in example_responses[:3])
        )

        user_prompt = (
            f"Conversation so far:\n{history_context}\n\n"
            f"Scammer's latest message:\n\"{scammer_text}\"\n\n"
            "Write your reply (1-2 sentences, stay in character):"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=120,
            temperature=0.8,
            timeout=8.0,
        )

        reply = response.choices[0].message.content.strip()
        # Strip any quotation marks the LLM might wrap around the reply
        reply = reply.strip('"\'')
        if reply:
            return reply
        return None

    except Exception:
        return None


def generate_state_response(
    state: ConversationState,
    intel: Dict,
    scammer_text: str,
    turn_in_state: int,
    history: List,
    scam_type: str = "unknown",
    asked_fields: Dict = None,
) -> Tuple[str, Dict]:
    """
    Generate a response appropriate for the current state with micro-behaviors.
    
    Args:
        state: Current conversation state
        intel: Extracted intelligence
        scammer_text: Latest scammer message
        turn_in_state: Turn count within current state
        history: Conversation history for consistency
        scam_type: Detected scam category for field relevance
        asked_fields: Dict of field → ask count to prevent repeating questions
    
    Returns:
        Tuple of (response_string, metadata_dict)
    """
    asked_fields = asked_fields or {}
    config = STATE_CONFIG[state]
    responses = config["responses"]
    goal = config.get("goal", "")
    
    # Extract previous claims for consistency
    claims = extract_honeypot_claims(history)

    # ── Intel-awareness: compute what's collected vs missing ──
    collected, missing = get_collected_and_missing(intel, scam_type, asked_fields)
    intel_summary = _format_intel_summary(intel, scam_type, asked_fields)
    
    # Try LLM-based contextual response first
    llm_response = _generate_llm_response(
        state=state,
        scammer_text=scammer_text,
        history=history,
        intel=intel,
        goal=goal,
        example_responses=responses,
        intel_summary=intel_summary,
        scam_type=scam_type,
        asked_fields=asked_fields,
    )
    
    if llm_response:
        response = llm_response
    else:
        # Fallback: pick a template that targets MISSING fields
        template = _pick_template_for_missing(responses, missing, turn_in_state)
        response = _interpolate_response(template, intel, scammer_text, claims)
    
    # Initialize metadata
    metadata = {
        "delay_seconds": 0,
        "has_typo": False,
        "has_fear": False,
        "has_hesitation": False,
        "has_correction": False,
    }
    
    # Apply micro-behaviors
    original_response = response
    
    # 1. Add delay phrases (25% chance)
    response, delay = inject_delay_phrase(response)
    if delay > 0:
        metadata["delay_seconds"] = delay
    
    # 2. Inject fear (15-30% based on state)
    fear_response = inject_fear(response, state, turn_in_state)
    if fear_response != response:
        metadata["has_fear"] = True
        response = fear_response
    
    # 3. Inject hesitation (20-35% based on state)
    hesitation_response = inject_hesitation(response, state)
    if hesitation_response != response:
        metadata["has_hesitation"] = True
        response = hesitation_response
    
    # 4. Add typos (10% chance)
    typo_response = inject_typo(response)
    if typo_response != response:
        metadata["has_typo"] = True
        response = typo_response
    
    # 5. Add corrections (8% chance)
    correction_response = add_correction(response)
    if correction_response != response:
        metadata["has_correction"] = True
        response = correction_response
    
    return response, metadata


# ═══════════════════════════════════════════════════════════════
# STATE MACHINE CONTROLLER
# ═══════════════════════════════════════════════════════════════

def execute_strategy(session: Dict, scammer_text: str) -> Tuple[str, ConversationState, Dict]:
    """
    Main entry point for dialogue strategy with micro-behaviors.
    
    Args:
        session: Current session data (includes state, intel, history)
        scammer_text: Latest message from scammer
    
    Returns:
        Tuple of (response_text, new_state, metadata)
        metadata includes micro-behavior flags, delays, and persistence info
    """
    # Get current state (default to INIT)
    current_state = session.get("dialogue_state", ConversationState.INIT)
    turn_in_state = session.get("state_turn_count", 0)
    intel = session.get("intel", {})
    history = session.get("history", [])
    
    # Determine next state
    next_state = get_next_state(
        current_state=current_state,
        turn_count=turn_in_state,
        scammer_text=scammer_text,
        intel=intel,
        session=session,
    )
    
    # If state changed, reset turn counter
    if next_state != current_state:
        turn_in_state = 0
    
    # Generate response for the next state with micro-behaviors
    response, metadata = generate_state_response(
        state=next_state,
        intel=intel,
        scammer_text=scammer_text,
        turn_in_state=turn_in_state,
        history=history,
        scam_type=session.get("scam_type", "unknown"),
        asked_fields=session.get("asked_fields", {}),
    )
    
    return response, next_state, metadata


def get_state_info(state: ConversationState) -> Dict:
    """Get configuration info for a given state (for debugging)."""
    config = STATE_CONFIG.get(state, {})
    return {
        "state": state,
        "goal": config.get("goal", ""),
        "extraction_targets": config.get("extraction_targets", []),
        "max_turns": config.get("max_turns", 0),
    }


# ═══════════════════════════════════════════════════════════════
# SCAM-TYPE → RELEVANT EXTRACTION FIELDS MAPPING
# ═══════════════════════════════════════════════════════════════

# Each scam type maps to the extraction fields that are RELEVANT to it.
# The agent will only ask about these fields for the detected scam type.
# Fields not in the list for a scam type are considered irrelevant and
# will NOT appear in the "still missing" list.

# Universal fields asked in ALL scam types:
_UNIVERSAL_FIELDS = ["names", "phoneNumbers"]

SCAM_TYPE_FIELDS = {
    # Bank impersonation: wants payment details, account info, and verification links
    "bank_impersonation": _UNIVERSAL_FIELDS + ["upiIds", "bankAccounts", "phishingLinks", "emails", "caseIds"],

    # Government impersonation: case IDs, legal references, links
    "government_impersonation": _UNIVERSAL_FIELDS + ["emails", "caseIds", "phishingLinks", "bankAccounts", "upiIds"],

    # Tech support: phishing links, remote access, case IDs
    "tech_support": _UNIVERSAL_FIELDS + ["phishingLinks", "emails", "caseIds", "upiIds"],

    # Lottery/prize: bank accounts for "prize deposit", emails, links
    "lottery_prize": _UNIVERSAL_FIELDS + ["bankAccounts", "upiIds", "phishingLinks", "emails", "caseIds"],

    # Investment fraud: bank accounts, UPI, links
    "investment_fraud": _UNIVERSAL_FIELDS + ["bankAccounts", "upiIds", "phishingLinks", "emails"],

    # Romance scam: bank accounts, UPI, emails, links
    "romance_scam": _UNIVERSAL_FIELDS + ["bankAccounts", "upiIds", "emails", "phishingLinks"],

    # Job offer scam: emails, links, bank accounts for "registration fee"
    "job_offer_scam": _UNIVERSAL_FIELDS + ["emails", "phishingLinks", "bankAccounts", "upiIds"],

    # Delivery/courier scam: order numbers, tracking, links, UPI
    "delivery_scam": _UNIVERSAL_FIELDS + ["orderNumbers", "phishingLinks", "upiIds", "caseIds"],

    # Tax refund scam: bank accounts, emails, case IDs, links
    "tax_refund": _UNIVERSAL_FIELDS + ["bankAccounts", "upiIds", "phishingLinks", "emails", "caseIds"],

    # Account verification / KYC update: links, emails, UPI
    "account_verification": _UNIVERSAL_FIELDS + ["phishingLinks", "emails", "upiIds", "bankAccounts"],
    "kyc_update": _UNIVERSAL_FIELDS + ["phishingLinks", "emails", "upiIds", "bankAccounts"],

    # Loan approval: bank accounts, policy numbers, UPI
    "loan_approval": _UNIVERSAL_FIELDS + ["bankAccounts", "upiIds", "policyNumbers", "emails", "caseIds"],

    # Custom/import clearance: order numbers, case IDs, UPI
    "custom_clearance": _UNIVERSAL_FIELDS + ["orderNumbers", "caseIds", "upiIds", "bankAccounts"],

    # Insurance scam: policy numbers, bank accounts
    "insurance_scam": _UNIVERSAL_FIELDS + ["policyNumbers", "bankAccounts", "upiIds", "emails", "caseIds"],
}

# Fallback: when scam type is unknown or not mapped, use ALL fields
_ALL_FIELDS = [
    "names", "phoneNumbers", "upiIds", "bankAccounts",
    "emails", "phishingLinks", "caseIds", "policyNumbers", "orderNumbers",
]


def _get_relevant_fields(scam_type: str) -> List[str]:
    """Return the list of extraction fields relevant for the given scam type."""
    return SCAM_TYPE_FIELDS.get(scam_type, _ALL_FIELDS)


# ═══════════════════════════════════════════════════════════════
# INTEL-AWARENESS: TRACK COLLECTED vs MISSING FIELDS
# ═══════════════════════════════════════════════════════════════

# Maps each extraction field to keywords that appear in template responses
# targeting that field. Used to filter templates toward missing intel.
_FIELD_TEMPLATE_KEYWORDS = {
    "names": ["name", "full name", "supervisor", "manager", "officer", "beneficiary name", "account holder"],
    "phoneNumbers": ["phone", "number", "call back", "callback", "helpline", "landline", "toll-free", "direct number"],
    "upiIds": ["upi", "upi id"],
    "bankAccounts": ["account number", "bank account", "ifsc", "branch"],
    "emails": ["email", "email address", "email id"],
    "phishingLinks": ["link", "url", "website"],
    "caseIds": ["case", "reference", "fir", "complaint", "ticket", "case id"],
    "policyNumbers": ["policy", "insurance"],
    "orderNumbers": ["order", "tracking", "awb"],
}

# Human-readable labels for each extraction field
_FIELD_LABELS = {
    "names": "Names",
    "phoneNumbers": "Phone numbers",
    "upiIds": "UPI IDs",
    "bankAccounts": "Bank account numbers",
    "emails": "Email addresses",
    "phishingLinks": "URLs / links",
    "caseIds": "Case / reference IDs",
    "policyNumbers": "Policy numbers",
    "orderNumbers": "Order / tracking numbers",
}


def infer_asked_field(reply: str) -> Optional[str]:
    """
    Detect which extraction field a reply is probing for.
    Used to populate session['asked_fields'] so the agent never repeats
    the same question across multiple turns.
    Returns the field key (e.g. 'upiIds') or None if unclear.
    """
    r = reply.lower()
    checks = [
        ("upiIds",        ["upi id", "upi address", "upi "]),
        ("bankAccounts",  ["account number", "ifsc", "bank account"]),
        ("emails",        ["email address", "email id", "your email", "email "]),
        ("phishingLinks", ["website address", "exact link", "full url", "the link", "the url", "web address"]),
        ("caseIds",       ["case id", "case number", "reference number", "fir number", "complaint number", "ticket id", "ticket number"]),
        ("policyNumbers", ["policy number", "insurance number", "policy "]),
        ("orderNumbers",  ["order number", "tracking number", "awb"]),
        ("phoneNumbers",  ["phone number", "call back", "callback", "helpline", "landline", "contact number", "call you back"]),
        ("names",         ["your name", "full name", "your full name", "what is your name"]),
    ]
    for field, keywords in checks:
        if any(kw in r for kw in keywords):
            return field
    return None


def infer_asked_field(reply: str) -> Optional[str]:
    """
    Detect which extraction field a reply is probing for.
    Used to populate session['asked_fields'] so the agent never repeats
    the same question across multiple turns.
    Returns the field key (e.g. 'upiIds') or None if unclear.
    """
    r = reply.lower()
    checks = [
        ("upiIds",        ["upi id", "upi address", "upi "]),
        ("bankAccounts",  ["account number", "ifsc", "bank account"]),
        ("emails",        ["email address", "email id", "your email", "email "]),
        ("phishingLinks", ["website address", "exact link", "full url", "the link", "the url", "web address"]),
        ("caseIds",       ["case id", "case number", "reference number", "fir number", "complaint number", "ticket id", "ticket number"]),
        ("policyNumbers", ["policy number", "insurance number", "policy "]),
        ("orderNumbers",  ["order number", "tracking number", "awb"]),
        ("phoneNumbers",  ["phone number", "call back", "callback", "helpline", "landline", "contact number", "call you back"]),
        ("names",         ["your name", "full name", "your full name", "what is your name"]),
    ]
    for field, keywords in checks:
        if any(kw in r for kw in keywords):
            return field
    return None


def get_collected_and_missing(intel: Dict, scam_type: str = "unknown", asked_fields: Dict = None) -> Tuple[List[str], List[str]]:
    """
    Analyse the session intel dict and return two lists, filtered by scam type:
      - collected: relevant field names that already have at least one value
      - missing:   relevant field names not yet collected AND not yet asked about

    Fields already asked about (ask_count >= 1) are excluded from 'missing'
    to prevent the agent from repeating the same question.
    Only fields relevant to the detected scam type are considered.
    """
    asked_fields = asked_fields or {}
    relevant_fields = _get_relevant_fields(scam_type)
    collected = [f for f in relevant_fields if intel.get(f)]
    missing = [f for f in relevant_fields if not intel.get(f) and asked_fields.get(f, 0) < 1]
    return collected, missing


def _format_intel_summary(intel: Dict, scam_type: str = "unknown", asked_fields: Dict = None) -> str:
    """
    Build a concise human-readable summary of what has been collected
    and what is still needed. Injected into the LLM prompt.
    Only shows fields relevant to the detected scam type.
    """
    asked_fields = asked_fields or {}
    relevant_fields = _get_relevant_fields(scam_type)
    collected, missing = get_collected_and_missing(intel, scam_type, asked_fields)
    # Fields asked but scammer hasn't answered yet
    pending = [f for f in relevant_fields if not intel.get(f) and asked_fields.get(f, 0) >= 1]

    lines = []

    # Show detected scam type context
    if scam_type and scam_type != "unknown":
        scam_label = scam_type.replace("_", " ").title()
        lines.append(f"DETECTED SCAM TYPE: {scam_label}")
        lines.append(f"Only ask for information relevant to this type of scam.")
        lines.append("")

    if collected:
        lines.append("ALREADY COLLECTED (do NOT ask for these again):")
        for f in collected:
            values = intel.get(f, [])
            lines.append(f"  ✓ {_FIELD_LABELS.get(f, f)}: {', '.join(str(v) for v in values)}")
    if pending:
        lines.append("ALREADY ASKED — do NOT ask these again (awaiting scammer reply):")
        for f in pending:
            lines.append(f"  ~ {_FIELD_LABELS.get(f, f)}")
    if missing:
        lines.append("NOT YET ASKED — pick ONE from this list next:")
        for f in missing:
            lines.append(f"  ✗ {_FIELD_LABELS.get(f, f)}")
    if not missing and not pending:
        lines.append("ALL RELEVANT FIELDS COLLECTED OR ASKED. Wind down the conversation.")

    return "\n".join(lines)


def _pick_template_for_missing(responses: List[str], missing: List[str], turn_in_state: int) -> str:
    """
    Pick a template that targets a MISSING field rather than an already-
    collected one.  Falls back to random choice if no match is found.
    """
    # Score each template by how many missing-field keywords it contains
    scored: List[Tuple[int, str]] = []
    for tmpl in responses:
        tmpl_lower = tmpl.lower()
        score = 0
        for field in missing:
            keywords = _FIELD_TEMPLATE_KEYWORDS.get(field, [])
            if any(kw in tmpl_lower for kw in keywords):
                score += 1
        scored.append((score, tmpl))

    # Keep only templates that match at least one missing field
    matching = [tmpl for score, tmpl in scored if score > 0]

    if matching:
        # Rotate through matching templates based on turn count
        return matching[turn_in_state % len(matching)]
    else:
        # Fallback: pick by turn or random
        if turn_in_state < len(responses):
            return responses[turn_in_state]
        return random.choice(responses)
