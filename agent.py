"""
Agent module for generating honeypot responses using dialogue strategy.
"""

import time
from intelligence import extract_intel, maybe_finish, store_intel
from callback import send_final_result
from dialogue_strategy import execute_strategy, ConversationState, infer_asked_field
from defense import defend_against_bot_accusation
from memory import save_session, append_chat_log
from llm_engine import analyze_message


SYSTEM_PROMPT = """
You are a normal person who received a suspicious call/message.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.

Your goal is to make the caller reveal specific details by asking direct questions.
Every response MUST ask for at least one of these that has NOT been collected yet:
- Their full name or supervisor's name
- A callback phone number or helpline number
- A UPI ID
- A bank account number
- An official email address
- A website URL or link
- A case ID, reference number, or FIR number
- A policy number or insurance number
- An order number or tracking number

IMPORTANT: Once a piece of information has been extracted, move on to the next
missing item. Do NOT keep asking for information that has already been provided.

Frame questions naturally as a confused person would:
"What is your name sir?", "Can you give me a number to call back?",
"What is the case reference number?", "What is the UPI ID I should use?"
"""

def agent_reply(session_id, session, scammer_text, known_scam_type: str = None):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)
    
    # 1b. Detect scam type — use caller-provided type if available;
    # only fire a separate LLM call when genuinely unknown (saves one API round-trip).
    if known_scam_type and known_scam_type != "unknown":
        session["scam_type"] = known_scam_type
    elif session.get("scam_type", "unknown") == "unknown":
        try:
            history = session.get("history", [])
            analysis = analyze_message(scammer_text, history)
            detected = analysis.get("scam_narrative", {}).get("category", "unknown")
            if detected and detected != "unknown":
                session["scam_type"] = detected
        except Exception:
            pass  # Keep existing scam_type on failure
    
    # 2. Increment message counter
    session["messages"] = session.get("messages", 0) + 1

    # 3. Initialize dialogue state if not present
    if "dialogue_state" not in session:
        session["dialogue_state"] = ConversationState.INIT
        session["state_turn_count"] = 0

    # 4. Get reply — either from bot defense OR dialogue strategy
    turn_count = session.get("state_turn_count", 0)
    defense_result = defend_against_bot_accusation(scammer_text, turn_count)
    
    if defense_result:
        reply, _ = defense_result
    else:
        # Normal dialogue strategy path
        session["state_turn_count"] = session.get("state_turn_count", 0) + 1

        reply, next_state, metadata = execute_strategy(session, scammer_text)

        # Store micro-behavior metadata for /debug/strategy visibility
        if "response_metadata" not in session:
            session["response_metadata"] = []
        session["response_metadata"].append(metadata)

        if next_state != session["dialogue_state"]:
            session["dialogue_state"] = next_state
            session["state_turn_count"] = 0

        if "scam_score" not in session:
            session["scam_score"] = 0.5

    # Track which extraction field this reply targeted to prevent repeat questions
    asked_field = infer_asked_field(reply)
    if asked_field:
        if "asked_fields" not in session:
            session["asked_fields"] = {}
        session["asked_fields"][asked_field] = session["asked_fields"].get(asked_field, 0) + 1

    # ── Everything below runs for EVERY message (defense or not) ──

    # 5. Append to history
    if "history" not in session:
        session["history"] = []
    now = time.time()
    session["history"].append({"sender": "scammer", "text": scammer_text, "timestamp": now})
    session["history"].append({"sender": "user", "text": reply, "timestamp": now})

    # 6. Persist chat exchange to Redis list (audit trail)
    append_chat_log(session_id, scammer_text, reply, session.get("messages", 0))

    # 7. Persist extracted intel snapshot to Redis list
    store_intel(session_id, session.get("intel", {}))

    # 8. Decide if conversation should finish
    should_finish = maybe_finish(session)
    print("MESSAGES:", session.get("messages"))
    print("INTEL:", session.get("intel"))
    print("FINISH?", should_finish)
    if should_finish:
        session["completed"] = True
        send_final_result(session_id, session)

    # 10. Save session back to Redis after all updates
    save_session(session_id, session)

    return reply
