"""
Session memory management for the honeypot agent.
Tracks conversation state, extracted intelligence, and dialogue strategy state.
"""

from dialogue_strategy import ConversationState

sessions = {}

def get_session(session_id, history):
    if session_id not in sessions:
        sessions[session_id] = {
            "history": history[:],
            "intel": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": []
            },
            "messages": 0,
            "completed": False,
            "asked_about": set(),  # Track what we've already asked about
            "response_count": {},   # Count how many times each response type used
            # Dialogue strategy state
            "dialogue_state": ConversationState.INIT,
            "state_turn_count": 0,
            "state_history": [],  # Track state transitions
            "response_metadata": [],  # Track micro-behaviors
        }
    return sessions[session_id]

def update_session(session_id, message, reply):
    sessions[session_id]["history"].append(message)
    sessions[session_id]["history"].append({
        "sender": "user",
        "text": reply
    })
    sessions[session_id]["messages"] += 2