"""
Agent module for generating honeypot responses using dialogue strategy.
"""

from intelligence import extract_intel, maybe_finish
from callback import send_final_result
from dialogue_strategy import execute_strategy, ConversationState

SYSTEM_PROMPT = """
You are a normal person.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.
Ask simple questions.
"""

def agent_reply(session_id, session, scammer_text):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)

    # 2. Initialize dialogue state if not present
    if "dialogue_state" not in session:
        session["dialogue_state"] = ConversationState.INIT
        session["state_turn_count"] = 0
        session["state_history"] = []

    # 3. Execute dialogue strategy to get response + next state + metadata
    reply, next_state, metadata = execute_strategy(session, scammer_text)

    # 4. Track state transitions
    if next_state != session["dialogue_state"]:
        session["state_history"].append({
            "from": session["dialogue_state"],
            "to": next_state,
            "turn": session.get("messages", 0) // 2,
        })
        session["dialogue_state"] = next_state
        session["state_turn_count"] = 1
    else:
        session["state_turn_count"] = session.get("state_turn_count", 0) + 1

    # 5. Store metadata for debugging/telemetry
    if "response_metadata" not in session:
        session["response_metadata"] = []
    session["response_metadata"].append({
        "turn": session.get("messages", 0) // 2,
        "state": next_state,
        "delay_seconds": metadata.get("delay_seconds", 0),
        "has_typo": metadata.get("has_typo", False),
        "has_fear": metadata.get("has_fear", False),
        "has_hesitation": metadata.get("has_hesitation", False),
        "has_correction": metadata.get("has_correction", False),
    })
    
    # 5.5. Update scam score in session for intel_score calculation
    # (detector should have set this, but ensure it exists)
    if "scam_score" not in session:
        session["scam_score"] = 0.5  # Default neutral

    # 6. Decide if conversation should finish
    if maybe_finish(session) and not session["completed"]:
        session["completed"] = True

        # 🚨 MANDATORY GUVI CALLBACK
        send_final_result(session_id, session)

    return reply
