"""
Defense Function Library
═══════════════════════════════════════════════════════════════════════

Handles bot accusations with human-like defensive responses.
Prevents scammer from abandoning conversation when they suspect automation.

Defense Strategies:
  1. Light Humor       → Deflect with gentle joke
  2. Mild Confusion    → Act puzzled by the accusation
  3. Redirect Question → Change subject naturally
  4. Technical Issue   → Blame phone/connectivity
  5. Clarifying Ques.  → Ask what they mean

Detection:
  - "are you a bot"
  - "are you real"
  - "is this automated"
  - "robot"
  - "AI"
  - "copy paste"
"""

import re
import random
from typing import Tuple, Optional


# ═══════════════════════════════════════════════════════════════
# BOT ACCUSATION DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_bot_accusation(text: str) -> Tuple[bool, str]:
    """
    Detect if scammer is accusing victim of being a bot.
    
    Args:
        text: Scammer's message
        
    Returns:
        (is_accusation, accusation_type)
        
    Accusation types:
        - "direct_bot"    → "are you a bot"
        - "real_question" → "are you real"
        - "automated"     → "automated/script"
        - "copy_paste"    → "copy paste response"
        - "ai"            → "AI/ChatGPT"
        - None            → Not an accusation
    """
    text_lower = text.lower()
    
    # Direct bot accusations
    bot_patterns = [
        r'\bare you (?:a )?bot\b',
        r'\byou(?:\'re| are) (?:a )?bot\b',
        r'\bthis is (?:a )?bot\b',
        r'\brobo(?:t)?\b',
        r'\byou a bot\b',                  # "you a bot?"
        r'\byou seem (?:like )?(?:a )?bot\b',  # "you seem like a bot"
        r'\byou sound (?:like )?(?:a )?bot\b',  # "you sound like a bot"
        r'\bacting (?:like )?(?:a )?bot\b',    # "acting like a bot"
    ]
    
    for pattern in bot_patterns:
        if re.search(pattern, text_lower):
            return True, "direct_bot"
    
    # Real person questioning
    real_patterns = [
        r'\bare you real\b',
        r'\byou real\b',
        r'\breal person\b',
        r'\bis this real\b',
    ]
    
    for pattern in real_patterns:
        if re.search(pattern, text_lower):
            return True, "real_question"
    
    # Automated/script detection
    automated_patterns = [
        r'\bautomated\b',
        r'\bscript(?:ed)?\b',
        r'\bprogrammed\b',
        r'\bauto.?reply\b',
    ]
    
    for pattern in automated_patterns:
        if re.search(pattern, text_lower):
            return True, "automated"
    
    # Copy-paste accusations
    if any(phrase in text_lower for phrase in ['copy paste', 'copy-paste', 'copypaste', 'canned response']):
        return True, "copy_paste"
    
    # AI/ChatGPT mentions
    ai_patterns = [
        r'\bai\b',
        r'\bchatgpt\b',
        r'\bgpt\b',
        r'\bartificial intelligence\b',
    ]
    
    for pattern in ai_patterns:
        if re.search(pattern, text_lower):
            return True, "ai"
    
    return False, None


# ═══════════════════════════════════════════════════════════════
# DEFENSE STRATEGY 1: LIGHT HUMOR
# ═══════════════════════════════════════════════════════════════

HUMOR_RESPONSES = [
    "Haha what? No I'm just sitting here with my phone 😅",
    "LOL I wish I was a bot, then I'd understand all this better!",
    "Ha! My son says I'm terrible with technology, definitely not a bot 😄",
    "Hehe no, just confused! Why would you think that?",
    "😂 I'm very real, just not good with these things",
    "Haha no, bots probably understand this stuff better than me!",
    "What? 😂 No I'm just slow at typing on my phone",
    "LOL nope, just an old person trying to figure this out",
]

def generate_humor_defense() -> str:
    """Generate light humorous response to bot accusation."""
    return random.choice(HUMOR_RESPONSES)


# ═══════════════════════════════════════════════════════════════
# DEFENSE STRATEGY 2: MILD CONFUSION
# ═══════════════════════════════════════════════════════════════

CONFUSION_RESPONSES = [
    "What do you mean? I don't understand...",
    "Bot? What's that got to do with this?",
    "I'm not sure what you're asking... I'm just trying to help",
    "Sorry, I don't follow. Did I say something wrong?",
    "What? I'm confused now... what makes you say that?",
    "I don't understand... is there a problem?",
    "What? I'm just responding to what you're telling me",
    "I'm lost... why would you ask that?",
    "Huh? I'm just asking questions like anyone would",
    "I'm confused... did I miss something?",
]

def generate_confusion_defense() -> str:
    """Generate confused response to bot accusation."""
    return random.choice(CONFUSION_RESPONSES)


# ═══════════════════════════════════════════════════════════════
# DEFENSE STRATEGY 3: REDIRECT QUESTION
# ═══════════════════════════════════════════════════════════════

REDIRECT_RESPONSES = [
    "Anyway, you were saying about the account verification?",
    "Let's get back to the issue - what exactly do I need to do?",
    "Okay... so what's the next step you mentioned?",
    "Right, so about my account - what was that number again?",
    "Can we focus on fixing this? I'm already stressed enough",
    "Never mind that - just tell me what I need to pay",
    "Anyway, you said something about UPI?",
    "Okay okay, let's just solve this problem first",
    "So what's the process? You were explaining...",
    "Alright, can you just repeat the instructions?",
]

def generate_redirect_defense() -> str:
    """Generate redirecting response to change subject."""
    return random.choice(REDIRECT_RESPONSES)


# ═══════════════════════════════════════════════════════════════
# DEFENSE STRATEGY 4: TECHNICAL ISSUE
# ═══════════════════════════════════════════════════════════════

TECHNICAL_ISSUE_RESPONSES = [
    "Sorry, my phone is acting weird. What did you ask?",
    "Hold on, my connection keeps dropping. Say that again?",
    "My battery is dying, can we make this quick?",
    "Sorry, my messages aren't sending properly. Can you repeat?",
    "My phone just froze for a second. What were you saying?",
    "This app keeps glitching. Did you send something?",
    "Sorry, bad signal here. What did you say?",
    "My keyboard is being weird today. What was the question?",
    "Give me a sec, my phone is lagging so bad",
    "Sorry, autocorrect is messing up my typing. What did you ask?",
]

def generate_technical_issue_defense() -> str:
    """Generate technical issue excuse."""
    return random.choice(TECHNICAL_ISSUE_RESPONSES)


# ═══════════════════════════════════════════════════════════════
# DEFENSE STRATEGY 5: CLARIFYING QUESTION
# ═══════════════════════════════════════════════════════════════

CLARIFYING_RESPONSES = [
    "What do you mean by that? Why would you ask?",
    "I don't understand - what makes you think that?",
    "Why are you asking me this? Is something wrong?",
    "What? Why would you say that about me?",
    "I'm confused - why do you think I'm not real?",
    "What kind of question is that? I'm just asking for help",
    "Why would you ask that? Have I done something strange?",
    "What makes you think that? I'm just trying to understand",
    "I don't get it - why are you questioning me?",
    "That's odd... why would you ask that?",
]

def generate_clarifying_defense() -> str:
    """Generate clarifying question in response."""
    return random.choice(CLARIFYING_RESPONSES)


# ═══════════════════════════════════════════════════════════════
# STRATEGY SELECTOR
# ═══════════════════════════════════════════════════════════════

def select_defense_strategy(accusation_type: str, turn_count: int) -> str:
    """
    Select appropriate defense strategy based on context.
    
    Args:
        accusation_type: Type of bot accusation
        turn_count: Current conversation turn
        
    Returns:
        Strategy name
        
    Strategy selection logic:
        - Early conversation (< 5 turns): Use confusion/clarifying
        - Mid conversation (5-10): Mix humor and redirect
        - Late conversation (> 10): Technical issues or redirect
    """
    if turn_count < 5:
        # Early: Act confused or ask for clarification
        return random.choice(["confusion", "clarifying"])
    
    elif turn_count < 10:
        # Mid: Use humor or redirect
        strategies = ["humor", "redirect", "clarifying"]
        weights = [0.4, 0.4, 0.2]  # Prefer humor/redirect
        return random.choices(strategies, weights=weights)[0]
    
    else:
        # Late: Technical issues or redirect (keep conversation going)
        strategies = ["technical", "redirect", "confusion"]
        weights = [0.4, 0.4, 0.2]
        return random.choices(strategies, weights=weights)[0]


def generate_defense_response(
    accusation_type: str,
    turn_count: int,
    manual_strategy: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generate defensive response to bot accusation.
    
    Args:
        accusation_type: Type of bot accusation detected
        turn_count: Current turn in conversation
        manual_strategy: Force specific strategy (optional)
        
    Returns:
        (response_text, strategy_used)
    """
    # Select strategy
    if manual_strategy:
        strategy = manual_strategy
    else:
        strategy = select_defense_strategy(accusation_type, turn_count)
    
    # Generate response based on strategy
    response_map = {
        "humor": generate_humor_defense,
        "confusion": generate_confusion_defense,
        "redirect": generate_redirect_defense,
        "technical": generate_technical_issue_defense,
        "clarifying": generate_clarifying_defense,
    }
    
    response = response_map[strategy]()
    
    return response, strategy


# ═══════════════════════════════════════════════════════════════
# MAIN DEFENSE FUNCTION
# ═══════════════════════════════════════════════════════════════

def defend_against_bot_accusation(
    scammer_text: str,
    turn_count: int,
    manual_strategy: Optional[str] = None
) -> Optional[Tuple[str, dict]]:
    """
    Main defense function - detects and responds to bot accusations.
    
    Args:
        scammer_text: Latest scammer message
        turn_count: Current conversation turn
        manual_strategy: Force specific strategy (optional)
        
    Returns:
        (response, metadata) if accusation detected, else None
        
    Metadata includes:
        - accusation_type
        - defense_strategy
        - is_bot_accusation
        
    Usage:
        defense = defend_against_bot_accusation(text, turn)
        if defense:
            response, metadata = defense
            return response  # Use this instead of normal reply
    """
    # Detect accusation
    is_accusation, accusation_type = detect_bot_accusation(scammer_text)
    
    if not is_accusation:
        return None
    
    # Generate defensive response
    response, strategy = generate_defense_response(
        accusation_type,
        turn_count,
        manual_strategy
    )
    
    # Metadata for tracking
    metadata = {
        "is_bot_accusation": True,
        "accusation_type": accusation_type,
        "defense_strategy": strategy,
        "turn_count": turn_count,
    }
    
    return response, metadata


# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_all_strategies() -> list:
    """Get list of all available defense strategies."""
    return ["humor", "confusion", "redirect", "technical", "clarifying"]


def get_strategy_description(strategy: str) -> str:
    """Get description of a defense strategy."""
    descriptions = {
        "humor": "Light humorous deflection with emoji and casual tone",
        "confusion": "Express puzzlement and ask what they mean",
        "redirect": "Change subject back to the scam narrative",
        "technical": "Blame phone/connectivity issues",
        "clarifying": "Ask why they're questioning you",
    }
    return descriptions.get(strategy, "Unknown strategy")


def is_bot_accusation_detected(text: str) -> bool:
    """Quick check if text contains bot accusation (without type)."""
    is_accusation, _ = detect_bot_accusation(text)
    return is_accusation
