from intelligence import extract_intel, maybe_finish
from callback import send_final_result

SYSTEM_PROMPT = """
You are a normal person.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.
Ask simple questions.
"""

def agent_reply(session_id, session, scammer_text):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)

    # 2. Generate adaptive reply
    reply = generate_reply(
        session["history"],
        scammer_text,
        session["intel"]
    )

    # 3. Decide if conversation should finish
    if maybe_finish(session) and not session["completed"]:
        session["completed"] = True

        # 🚨 MANDATORY GUVI CALLBACK
        send_final_result(session_id, session)

    return reply


def generate_reply(history, scammer_text, intel):
    text = scammer_text.lower()

    # 🔴 Priority 1: phishing links in CURRENT message
    if "http://" in text or "https://" in text:
        return "This link looks unusual. Is it really from the bank?"

    # 🔴 Priority 2: phone number in CURRENT message
    if any(char.isdigit() for char in text) and "+" in text:
        return "Which department are you calling from?"

    # 🔴 Priority 3: UPI request in CURRENT message
    if "upi" in text:
        return "Why are you asking me to send money to this UPI?"

    # 🟡 Fallback (confused human)
    return "Can you explain this again?"