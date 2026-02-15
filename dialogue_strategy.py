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
# PERSISTENCE / REPETITION DETECTION FROM MEMORY
# ═══════════════════════════════════════════════════════════════

# Semantic categories a scammer may repeat persistently
_PERSISTENCE_CATEGORIES = {
    "payment_demand": [
        r'\b(send|pay|transfer|deposit|upi|amount|rs|rupees?|₹)\b',
    ],
    "link_push": [
        r'\b(click|link|open|visit|url|website|verify.*(link|site))\b',
        r'https?://',
    ],
    "urgency_threat": [
        r'\b(urgent|immediately|now|quick|asap|hurry|expire|deadline|today|right\s*now|last\s+chance)\b',
    ],
    "authority_pressure": [
        r'\b(officer|inspector|manager|police|arrest|legal|fir|case|court|government|rbi|suspend|block)\b',
    ],
    "credential_request": [
        r'\b(otp|pin|password|cvv|card\s*number|aadhar|pan|login)\b',
    ],
}


def detect_repetition_from_memory(session: Dict) -> Dict:
    """
    Analyse the conversation memory to detect scammer *persistence*.

    Checks two axes:
    1. **Exact repetition** – via `message_hashes` (same message sent > 1×).
    2. **Semantic repetition** – the same *category* of demand appearing
       in 2+ of the last 4 scammer messages.

    Returns a dict with:
        is_persistent (bool)  – True if any persistence detected
        exact_repeats (int)   – number of exactly-repeated messages
        persistent_categories (list[str]) – categories being repeated
        pressure_level (float) – 0.0-1.0 severity
        summary (str)         – human-readable summary for prompt injection
    """
    result = {
        "is_persistent": False,
        "exact_repeats": 0,
        "persistent_categories": [],
        "pressure_level": 0.0,
        "summary": "",
    }

    # ── Exact repetition ───────────────────────────────────────
    hashes = session.get("message_hashes", {})
    exact_repeats = sum(1 for cnt in hashes.values() if cnt > 1)
    result["exact_repeats"] = exact_repeats

    # ── Semantic repetition (last 4 scammer messages) ─────────
    history = session.get("history", [])
    scammer_msgs = [
        msg.get("text", "")
        for msg in history
        if isinstance(msg, dict) and msg.get("sender") == "scammer"
    ][-4:]

    if len(scammer_msgs) < 2:
        return result

    category_hits: Dict[str, int] = {cat: 0 for cat in _PERSISTENCE_CATEGORIES}

    for text in scammer_msgs:
        text_lower = text.lower()
        for cat, patterns in _PERSISTENCE_CATEGORIES.items():
            if any(re.search(p, text_lower) for p in patterns):
                category_hits[cat] += 1

    repeated_cats = [
        cat for cat, count in category_hits.items()
        if count >= 2
    ]

    result["persistent_categories"] = repeated_cats

    # ── Compute pressure level ─────────────────────────────────
    pressure = 0.0
    if exact_repeats > 0:
        pressure += min(exact_repeats * 0.15, 0.4)
    pressure += len(repeated_cats) * 0.15
    # Bonus if urgency + payment together
    if "urgency_threat" in repeated_cats and "payment_demand" in repeated_cats:
        pressure += 0.2
    if "credential_request" in repeated_cats:
        pressure += 0.15
    result["pressure_level"] = min(pressure, 1.0)

    result["is_persistent"] = (
        exact_repeats > 0
        or len(repeated_cats) > 0
    )

    # ── Build human-readable summary for the LLM prompt ───────
    if result["is_persistent"]:
        parts = []
        if exact_repeats:
            parts.append(f"the scammer has sent {exact_repeats} exact-repeat message(s)")
        if repeated_cats:
            labels = {
                "payment_demand": "demanding payment",
                "link_push": "pushing a link",
                "urgency_threat": "making urgent threats",
                "authority_pressure": "claiming authority/legal action",
                "credential_request": "requesting credentials/OTP",
            }
            descs = [labels.get(c, c) for c in repeated_cats]
            parts.append(f"they keep {', '.join(descs)}")
        result["summary"] = "The scammer is being persistent: " + "; ".join(parts) + "."

    return result


# Responses designed specifically for when persistence is detected.
# Keyed by the persistence category that is strongest.
_PERSISTENCE_RESPONSES: Dict[str, List[str]] = {
    "payment_demand": [
        "You already told me to pay. I need to think about it, this is a lot of money.",
        "I heard you the first time about the payment. Let me arrange funds.",
        "I understand you want me to pay, but I'm still checking with my {person}.",
        "You keep saying to pay. Can you explain one more time why exactly?",
        "Please stop rushing me about the money. I need the exact details again.",
    ],
    "link_push": [
        "You already sent me the link. I'm trying to open it but it's slow.",
        "I saw the link, but my phone is giving a warning. Is there another way?",
        "I'm having trouble with the link you keep sending. Can you spell the website?",
        "I clicked the link before but nothing happened. What should I do?",
    ],
    "urgency_threat": [
        "You keep saying it's urgent. But I need to be careful with my money.",
        "I understand it's urgent, but please don't rush me. I'm confused.",
        "Every message you send says urgent. That's making me more worried, not faster.",
        "If it's so urgent, why can't I just visit the branch?",
    ],
    "authority_pressure": [
        "You said you were from {entity} before too. Can you prove it this time?",
        "You keep mentioning your authority. I just want to verify before I act.",
        "If you really are an officer, then you'll understand I need time.",
        "I heard the first time that this is official. But how do I confirm?",
    ],
    "credential_request": [
        "You asked for this information already. I'm scared to share it.",
        "I'm not comfortable sharing my OTP/PIN again. Is there another way?",
        "My {person} said never to share OTP with anyone. Why do you need it?",
        "I already told you I'm not sure about sharing passwords.",
    ],
    "_generic": [
        "You keep repeating the same thing. I need a moment to think.",
        "I heard you before. Please don't pressure me.",
        "I understand what you're saying, you told me already. Let me process this.",
        "You've said this multiple times now. I'm trying my best.",
    ],
}


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
        "goal": "Establish victim persona, appear confused and concerned",
        "extraction_targets": ["narrative_type", "urgency_level", "impersonation_entity"],
        "responses": [
            "Hello? Who is this?",
            "I'm sorry, I don't understand. What is this about?",
            "Is this really from {entity}? How do I know this is legitimate?",
            "This is very sudden. Can you explain what's happening?",
            "I'm a bit worried. Is there a problem with my account?",
            "Wait, I need to understand this properly. Start from the beginning.",
        ],
        "max_turns": 2,
    },
    
    ConversationState.PROBE_REASON: {
        "goal": "Extract scam narrative, authority claims, and urgency tactics",
        "extraction_targets": ["authority_title", "reference_numbers", "alleged_issue", "deadline"],
        "responses": [
            "Why is my account blocked? I haven't done anything wrong.",
            "What exactly is the issue? I need to understand the reason.",
            "Can you give me a reference number or case ID for this?",
            "Who specifically are you? What's your employee ID or badge number?",
            "Which department are you calling from? What's the official number?",
            "How did this happen? I use my account normally.",
            "Is this issue with all my accounts or just one?",
            "What triggered this? I haven't received any email about this.",
        ],
        "max_turns": 4,
    },
    
    ConversationState.PROBE_PAYMENT: {
        "goal": "Extract payment redirection details (UPI, account numbers, amounts)",
        "extraction_targets": ["upi_ids", "account_numbers", "payment_amounts", "payment_reason"],
        "responses": [
            "Why do I need to send money? I thought you were helping me?",
            "How much exactly do I need to pay? And to which account?",
            "Can you send me the UPI ID? I need to copy it carefully.",
            "What is this payment for? Is it a fee or penalty?",
            "Will I get this money back? How long will it take?",
            "I've never paid like this before. Is there a receipt?",
            "Can I pay some other way? I'm not comfortable with UPI.",
            "My son handles my payments. Can I call him first?",
            "What's the exact amount in numbers? I want to be sure.",
            "Which bank account should I use to send the money?",
        ],
        "max_turns": 5,
    },
    
    ConversationState.PROBE_LINK: {
        "goal": "Extract phishing URLs, domains, and social engineering around clicking",
        "extraction_targets": ["phishing_urls", "domain_names", "link_purpose", "credentials_requested"],
        "responses": [
            "I'm not sure about clicking links in messages. Is this safe?",
            "What exactly will happen when I click this link?",
            "Can you tell me the full website address? I want to verify it.",
            "Is this link from the official {entity} website?",
            "My antivirus is warning me about this link. Why?",
            "What information will the website ask for?",
            "Do I need to enter my password or PIN on this website?",
            "Can I access this from the official app instead?",
            "The link looks strange. Can you explain the URL?",
            "Will clicking this link solve the problem immediately?",
        ],
        "max_turns": 4,
    },
    
    ConversationState.STALL: {
        "goal": "Buy time while extracting additional details, appear hesitant",
        "extraction_targets": ["alternative_contacts", "supervisor_info", "callback_numbers", "additional_threats"],
        "responses": [
            "I need to think about this. This is moving very fast.",
            "Can I call you back in 10 minutes? I need to check something.",
            "Let me talk to my son first. He knows about these things.",
            "I'm at work right now. Can we do this later today?",
            "This is making me very nervous. How do I know this is real?",
            "Can I visit the branch instead? I prefer doing this in person.",
            "What happens if I don't do this right now?",
            "Is there a supervisor I can speak to? I want to confirm everything.",
            "Let me verify this with customer care first.",
            "I need to get my reading glasses. Give me a minute.",
            "Can you send me an official email or SMS about this?",
        ],
        "max_turns": 3,
    },
    
    ConversationState.CONFIRM_DETAILS: {
        "goal": "Make scammer repeat details, verify extracted intelligence",
        "extraction_targets": ["confirmation_of_previous_intel", "contradictions", "new_details"],
        "responses": [
            "Let me repeat back what you said to make sure I understood correctly.",
            "So the UPI ID is {detail}? Can you confirm that again?",
            "You mentioned {detail} earlier. Is that still correct?",
            "Just to be clear, I need to pay {amount} to {recipient}?",
            "The account number you gave was {detail}. Can you verify?",
            "You said your name was {name}. What was your employee ID again?",
            "I wrote down {detail}. Is that exactly right?",
            "Can you spell out the website address letter by letter?",
            "What was the reference number you mentioned? I want to note it.",
            "Before I proceed, let me confirm: {detail}. Correct?",
        ],
        "max_turns": 3,
    },
    
    ConversationState.ESCALATE_EXTRACTION: {
        "goal": "Push for phone numbers, alternative contacts, supervisor details",
        "extraction_targets": ["phone_numbers", "backup_contacts", "organization_structure", "escalation_threats"],
        "responses": [
            "I'm still not convinced. Can I speak to your supervisor?",
            "What's the main helpline number? I want to verify this independently.",
            "Do you have a landline number I can call back?",
            "Can you give me the official customer care number?",
            "What's your manager's name and direct number?",
            "Is there a verification code or OTP I need to share with you?",
            "You're asking for sensitive information. How can I trust you?",
            "What if I report this to the police? What will happen?",
            "I'm recording this conversation. Is that okay?",
            "Give me your full name and employee details for my records.",
        ],
        "max_turns": 4,
    },
    
    ConversationState.CLOSE: {
        "goal": "Wind down conversation, appear compliant but delay final action",
        "extraction_targets": ["final_instructions", "follow_up_timeline", "threats_for_non_compliance"],
        "responses": [
            "Okay, I think I understand now. Let me do this carefully.",
            "Alright, I'll try to do what you said. Give me some time.",
            "Thank you for explaining. I'll handle this today.",
            "I need to arrange the money first. I'll get back to you.",
            "Let me talk to my bank and sort this out.",
            "Okay, I'll click the link and see what happens.",
            "I'm going to try this UPI payment now. Wish me luck.",
            "Thanks for your help. I hope this resolves the issue.",
            "I'll call you back if I face any problems.",
            "Alright, let me proceed with what you've told me.",
        ],
        "max_turns": 2,
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
        
        # Pattern 1: Scammer disengaged → close immediately
        if patterns["disengagement"]:
            return ConversationState.CLOSE
        
        # Pattern 2: (removed — repeated pressure is an opportunity to extract more)
        
        # Pattern 3: Stale intel (no new intel in 3 turns) + good extraction → close
        if patterns["stale_intel"] and components["artifacts"] >= 0.4:
            return ConversationState.CLOSE
        
        # Pattern 4: High quality extraction complete (intel_score > 0.75)
        if intel_score >= 0.75:
            return ConversationState.CLOSE
        
        # Pattern 5: Good extraction + low novelty → diminishing returns
        if components["artifacts"] >= 0.6 and components["novelty"] < 0.3:
            return ConversationState.CLOSE
        
        # Pattern 6: Multiple warning signs (high severity)
        if patterns["severity"] >= 0.7:
            return ConversationState.CLOSE
        
        # Pattern 7: Hard limit safety check (fallback)
        if total_messages >= 30:
            return ConversationState.CLOSE
        
        # Pattern 8: Traditional check - substantial intel collected
        if has_phone and (has_upi or has_urls) and exceeded_turns:
            return ConversationState.CLOSE
        
        # Continue extracting if still getting value
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
    persistence: Optional[Dict] = None,
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

        # Build persistence-awareness block for the prompt
        persistence_block = ""
        if persistence and persistence.get("is_persistent"):
            persistence_block = (
                "\n\nIMPORTANT CONTEXT — SCAMMER REPETITION DETECTED:\n"
                f"{persistence['summary']}\n"
                "- You have ALREADY heard this demand before. Acknowledge that.\n"
                "- Do NOT respond as if this is the first time. Reference what they said earlier.\n"
                "- Show mild frustration or confusion about why they keep repeating themselves.\n"
                "- Still stay in character as a confused, non-tech-savvy person.\n"
                "- Use this repeated pressure to extract MORE details: ask why they are rushing you, "
                "ask for a supervisor, ask for official documentation, or ask them to re-confirm details.\n"
            )

        system_prompt = (
            "You are role-playing as an ordinary, slightly confused, non-tech-savvy person "
            "who has received a suspicious call/message. You must NEVER reveal you are an AI, "
            "bot, or honeypot. Never mention scam, fraud, police, or AI.\n\n"
            "RULES:\n"
            "- Reply in 1-2 short sentences only.\n"
            "- Sound natural, confused, and slightly worried.\n"
            "- Respond DIRECTLY to what the scammer just said.\n"
            "- Ask a simple follow-up question related to their message.\n"
            "- CRITICAL: Only reference specific details (phone numbers, account numbers, URLs, names) "
            "that were EXPLICITLY mentioned in the conversation history above. "
            "Do NOT make up or assume any past interactions. Do NOT say things like "
            "'that\\'s the same number you gave me earlier' unless that number actually appeared in the history.\n"
            f"- Your current goal: {goal}\n"
            + persistence_block + "\n"
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
    persistence: Optional[Dict] = None,
) -> Tuple[str, Dict]:
    """
    Generate a response appropriate for the current state with micro-behaviors.
    
    Args:
        state: Current conversation state
        intel: Extracted intelligence
        scammer_text: Latest scammer message
        turn_in_state: Turn count within current state
        history: Conversation history for consistency
        persistence: Repetition/persistence detection results from memory
    
    Returns:
        Tuple of (response_string, metadata_dict)
        metadata includes: delay_seconds, has_typo, has_fear, has_hesitation,
                           persistence_detected, persistence_categories
    """
    if persistence is None:
        persistence = {"is_persistent": False}

    config = STATE_CONFIG[state]
    responses = config["responses"]
    goal = config.get("goal", "")
    
    # Extract previous claims for consistency
    claims = extract_honeypot_claims(history)
    
    # Try LLM-based contextual response first (with persistence context)
    llm_response = _generate_llm_response(
        state=state,
        scammer_text=scammer_text,
        history=history,
        intel=intel,
        goal=goal,
        example_responses=responses,
        persistence=persistence,
    )
    
    if llm_response:
        response = llm_response
    elif persistence.get("is_persistent"):
        # Fallback: use persistence-aware templates when repetition is detected
        cats = persistence.get("persistent_categories", [])
        # Pick the best matching category's templates
        chosen_templates = None
        for cat in cats:
            if cat in _PERSISTENCE_RESPONSES:
                chosen_templates = _PERSISTENCE_RESPONSES[cat]
                break
        if not chosen_templates:
            chosen_templates = _PERSISTENCE_RESPONSES["_generic"]

        template = random.choice(chosen_templates)
        response = _interpolate_response(template, intel, scammer_text, claims)
    else:
        # Normal fallback: pick from state template list
        if turn_in_state < len(responses):
            template = responses[turn_in_state]
        else:
            template = random.choice(responses)
        response = _interpolate_response(template, intel, scammer_text, claims)
    
    # Initialize metadata
    metadata = {
        "delay_seconds": 0,
        "has_typo": False,
        "has_fear": False,
        "has_hesitation": False,
        "has_correction": False,
        "persistence_detected": persistence.get("is_persistent", False),
        "persistence_categories": persistence.get("persistent_categories", []),
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
    
    # ── Detect scammer persistence from memory ────────────────
    persistence = detect_repetition_from_memory(session)
    
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
    # Pass persistence info so response generation is memory-aware
    response, metadata = generate_state_response(
        state=next_state,
        intel=intel,
        scammer_text=scammer_text,
        turn_in_state=turn_in_state,
        history=history,
        persistence=persistence,
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
