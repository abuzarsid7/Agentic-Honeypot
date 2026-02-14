"""
Agent module for generating honeypot responses using dialogue strategy.
"""

from intelligence import extract_intel, maybe_finish
from callback import send_final_result
from dialogue_strategy import execute_strategy, ConversationState
from defense import defend_against_bot_accusation
from memory import save_session


SYSTEM_PROMPT = """
You are a normal person.
You are confused, cautious, slightly worried.
Never mention scam, fraud, police, or AI.
Ask simple questions.
"""

def agent_reply(session_id, session, scammer_text):
    # 1. Extract intelligence
    extract_intel(session, scammer_text)
    
    # Increment session[message] for history
    session["messages"] = session.get("messages", 0) + 1

    # 2. Initialize dialogue state if not present
    if "dialogue_state" not in session:
        session["dialogue_state"] = ConversationState.INIT
        session["state_turn_count"] = 0

    # 2.5. Check for bot accusation and defend if needed
    turn_count = session.get("state_turn_count", 0)
    defense_result = defend_against_bot_accusation(scammer_text, turn_count)
    
    if defense_result:
        # Bot accusation detected - use defensive response
        reply, defense_metadata = defense_result
        
        # Save session (intelligence was already extracted)
        save_session(session_id, session)
        
        # Defense activated - no need to track extra metadata in simplified schema
        # Just return the defensive response
        return reply
    current_state = session.get("dialogue_state")
    session["state_turn_count"] = session.get("state_turn_count", 0) + 1

    # 3. Execute dialogue strategy to get response + next state + metadata
    reply, next_state, metadata = execute_strategy(session, scammer_text)

    # 4. Track state transitions and reset turn count on state change
    if next_state != session["dialogue_state"]:
        session["dialogue_state"] = next_state
        session["state_turn_count"] = 0  # Reset turn count on state change
    
    # 5. Update scam score in session for intel_score calculation
    # (detector should have set this, but ensure it exists)
    if "scam_score" not in session:
        session["scam_score"] = 0.5  # Default neutral

    # 6. Decide if conversation should finish
    should_finish = maybe_finish(session)
    if should_finish:
        # 🚨 MANDATORY GUVI CALLBACK
        send_final_result(session_id, session)

    if "history" not in session:
        session["history"] = []
    session["history"].append({
    "sender": "scammer",
    "text": scammer_text
    })
    session["history"].append({
    "sender": "user",
    "text": reply
})
    
    # 7. Save session back to Redis after all updates
    save_session(session_id, session)

    return reply
