"""
Session memory management for the honeypot agent.
Tracks conversation state, extracted intelligence, and dialogue strategy state.
"""

from dialogue_strategy import ConversationState

import json
import time
from redis_client import redis_client

SESSION_TTL = 3600  # 1 hour

# Local cache for backwards compatibility (optional)
sessions = {}


def get_session(session_id: str, history: list = None):
    """
    Retrieve session from Redis. Creates new session if not found.
    
    Args:
        session_id: Unique session identifier
        history: Optional conversation history to initialize with
        
    Returns:
        Session dict with intelligence, state, and history
    """
    key = f"session:{session_id}"
    data = redis_client.get(key)

    if data:
        session = json.loads(data)
        # Cache locally
        sessions[session_id] = session
        return session

    # If session doesn't exist, create new one
    session = {
        "history": history or [],
        "scam_score": 0.5,
        "start_time": time.time(),
        "intel": {
            "phoneNumbers": [],
            "upiIds": [],
            "phishingLinks": [],
            "bankAccounts": [],
            "names": [],
            "emails": [],
            "caseIds": [],
            "policyNumbers": [],
            "orderNumbers": [],
        },
        "dialogue_state": ConversationState.INIT,
        "state_turn_count": 0,
        "scam_type": "unknown",
        "asked_fields": {},
    }

    save_session(session_id, session)
    sessions[session_id] = session
    return session


def save_session(session_id: str, session: dict):
    """
    Save session to Redis with TTL.
    
    Args:
        session_id: Unique session identifier
        session: Session dict to persist
    """
    key = f"session:{session_id}"

    redis_client.setex(
        key,
        SESSION_TTL,
        json.dumps(session)
    )
    
    # Update local cache
    sessions[session_id] = session


def update_session(session_id: str, message: dict, reply: str):
    """
    Update session with new message exchange and save to Redis.
    
    Args:
        session_id: Unique session identifier
        message: Incoming scammer message dict
        reply: Honeypot's reply text
    """
    
    # Get latest session from Redis
    session = get_session(session_id)
    
    # Append message exchange to history
    now = time.time()
    msg_with_ts = {**message}
    if "timestamp" not in msg_with_ts:
        msg_with_ts["timestamp"] = now
    session["history"].append(msg_with_ts)
    session["history"].append({
        "sender": "user",
        "text": reply,
        "timestamp": now,
    })
    
    # Save back to Redis
    save_session(session_id, session)


def append_chat_log(session_id: str, scammer_text: str, reply: str, turn_number: int):
    """
    Append a chat exchange to a Redis list for audit trail.
    Each entry is a JSON object with scammer message, bot reply and turn number.
    """
    entry = json.dumps({
        "turn": turn_number,
        "scammer": scammer_text,
        "bot": reply,
    })
    key = f"chatlog:{session_id}"
    redis_client.rpush(key, entry)
    redis_client.expire(key, SESSION_TTL)


def refresh_session_from_redis(session_id: str) -> dict:
    """
    Force refresh session from Redis, bypassing local cache.
    Useful when session might have been updated externally.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Latest session from Redis or None if not found
    """
    key = f"session:{session_id}"
    data = redis_client.get(key)
    
    if data:
        session = json.loads(data)
        # Update local cache
        sessions[session_id] = session
        return session
    
    return None


def sync_session_to_redis(session_id: str, session: dict):
    """
    Sync an in-memory session dict back to Redis.
    Use this after making multiple updates to avoid repeated Redis writes.
    
    Args:
        session_id: Unique session identifier
        session: Updated session dict to sync
    """
    save_session(session_id, session)


def merge_session_updates(session_id: str, updates: dict) -> dict:
    """
    Merge partial updates into existing Redis session.
    Useful for updating specific fields without rewriting entire session.
    
    Args:
        session_id: Unique session identifier
        updates: Dict with fields to update
        
    Returns:
        Updated session
    """
    session = get_session(session_id)
    
    # Deep merge for nested dicts like 'intel'
    for key, value in updates.items():
        if key in session and isinstance(session[key], dict) and isinstance(value, dict):
            session[key].update(value)
        else:
            session[key] = value
    
    save_session(session_id, session)
    return session