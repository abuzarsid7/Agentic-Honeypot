"""
Agent module for generating honeypot responses using dialogue strategy.
"""

import hashlib
from intelligence import extract_intel, maybe_finish, store_intel
from callback import send_final_result
from dialogue_strategy import execute_strategy, ConversationState
from defense import defend_against_bot_accusation
from memory import save_session, append_chat_log


SYSTEM_PROMPT = """
You are a normal person.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.
Ask simple questions.
"""

def agent_reply(session_id, session, scammer_text):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)
    
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

        if next_state != session["dialogue_state"]:
            session["dialogue_state"] = next_state
            session["state_turn_count"] = 0

        if "scam_score" not in session:
            session["scam_score"] = 0.5

    # ── Everything below runs for EVERY message (defense or not) ──

    # 5. Append to history
    if "history" not in session:
        session["history"] = []
    session["history"].append({"sender": "scammer", "text": scammer_text})
    session["history"].append({"sender": "user", "text": reply})

    # 6. Track message hash for deduplication / repeat detection
    if "message_hashes" not in session:
        session["message_hashes"] = {}
    msg_hash = hashlib.sha256(scammer_text.encode()).hexdigest()[:12]
    session["message_hashes"][msg_hash] = session["message_hashes"].get(msg_hash, 0) + 1

    # 7. Persist chat exchange to Redis list (audit trail)
    append_chat_log(session_id, scammer_text, reply, session.get("messages", 0))

    # 8. Persist extracted intel snapshot to Redis list
    store_intel(session_id, session.get("intel", {}))

    # 9. Decide if conversation should finish
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
