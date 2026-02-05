from intelligence import extract_intel, maybe_finish
from callback import send_final_result
import re
import random

SYSTEM_PROMPT = """
You are a normal person.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.
Ask simple questions.
"""

def agent_reply(session_id, session, scammer_text):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)

    # 2. Generate adaptive reply with context awareness
    reply = generate_reply(
        session["history"],
        scammer_text,
        session["intel"],
        session["asked_about"],
        session["response_count"]
    )

    # 3. Decide if conversation should finish
    if maybe_finish(session) and not session["completed"]:
        session["completed"] = True

        # 🚨 MANDATORY GUVI CALLBACK
        send_final_result(session_id, session)

    return reply


def generate_reply(history, scammer_text, intel, asked_about, response_count):
    """
    Context-aware response generation that avoids repetition.
    Prioritizes extracting maximum intelligence.
    """
    text = scammer_text.lower()
    
    # Response variations for different scenarios
    LINK_RESPONSES = [
        "I'm not sure about clicking this link. Is it safe?",
        "This link looks strange. Can you tell me what website this is?",
        "I don't usually click links in messages. What will happen if I click it?",
        "My son told me to be careful with links. What is this for exactly?",
        "Is this link from the official bank website? The URL looks different."
    ]
    
    PHONE_RESPONSES = [
        "Which department is this number for?",
        "Should I call this number now? What will they ask me?",
        "Is this the official customer care number? Can I verify it somewhere?",
        "What information will I need when I call this number?",
        "I tried calling but no one picked up. Is this the right number?"
    ]
    
    UPI_RESPONSES = [
        "I've never sent money to a UPI ID before. Is this safe?",
        "Why do I need to send money? I thought my account was just blocked?",
        "How much do I need to send to this UPI?",
        "Can you explain why the bank needs me to send money via UPI?",
        "I'm confused. Will I get this money back after verification?",
        "My daughter handles my UPI. Can I pay some other way?"
    ]
    
    ACCOUNT_RESPONSES = [
        "Which account number are you talking about? I have multiple accounts.",
        "Can you confirm the last 4 digits of my account that's blocked?",
        "I need to check my account details. Can you wait a moment?",
        "How did you get my account information?"
    ]
    
    URGENCY_RESPONSES = [
        "I'm a bit worried. What happens if I don't do this immediately?",
        "How much time do I have? I'm not very good with technology.",
        "This is making me nervous. Can I go to the bank branch instead?",
        "Why is this so urgent? Is my money safe?"
    ]
    
    VERIFICATION_RESPONSES = [
        "What information do you need to verify my account?",
        "I have my account statement here. What should I check?",
        "Do I need to share my card details for verification?",
        "How will this verification process work?"
    ]
    
    GENERAL_CONFUSED = [
        "I don't understand. Can you explain this more simply?",
        "I'm not very tech-savvy. What exactly do I need to do?",
        "This is confusing me. Let me get my reading glasses.",
        "Can you repeat that? I didn't quite follow.",
        "I'm at work right now. Can you explain what's happening?",
        "Sorry, I'm a bit slow with these things. Walk me through it."
    ]
    
    def pick_response(category, responses):
        """Pick a response that hasn't been used yet, or random if all used."""
        key = category
        if key not in asked_about:
            # First time asking about this category
            asked_about.add(key)
            response_count[key] = 0
        
        # Track how many times this category has been used
        idx = response_count.get(key, 0)
        response_count[key] = idx + 1
        
        # Cycle through responses
        if idx < len(responses):
            return responses[idx]
        else:
            # All responses used, pick random
            return random.choice(responses)
    
    # Priority 1: Extract specific intelligence from current message
    
    # Check for URLs/links
    if re.search(r'https?://', text):
        return pick_response('link', LINK_RESPONSES)
    
    # Check for phone numbers
    if re.search(r'\+\d{10,}|\d{10,}', text) and 'phone' not in asked_about:
        asked_about.add('phone')
        return pick_response('phone', PHONE_RESPONSES)
    
    # Check for UPI mentions or UPI IDs
    if 'upi' in text or re.search(r'[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}', text):
        return pick_response('upi', UPI_RESPONSES)
    
    # Check for account/card number patterns
    if re.search(r'\d{8,}', text) and 'account' in text:
        return pick_response('account', ACCOUNT_RESPONSES)
    
    # Priority 2: Respond to scam tactics
    
    # Urgency tactics
    urgency_words = ['urgent', 'immediately', 'now', 'quick', 'asap', 'hurry', 'expire']
    if any(word in text for word in urgency_words):
        if 'urgency' not in asked_about or response_count.get('urgency', 0) < 2:
            return pick_response('urgency', URGENCY_RESPONSES)
    
    # Verification requests
    verify_words = ['verify', 'confirm', 'update', 'kyc', 'validation']
    if any(word in text for word in verify_words):
        if 'verify' not in asked_about or response_count.get('verify', 0) < 2:
            return pick_response('verify', VERIFICATION_RESPONSES)
    
    # Priority 3: Keep conversation going with confused/cautious responses
    return pick_response('general', GENERAL_CONFUSED)