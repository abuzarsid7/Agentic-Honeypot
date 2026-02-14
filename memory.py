"""
Session memory management for the honeypot agent.
Tracks conversation state, extracted intelligence, and dialogue strategy state.
"""

from dialogue_strategy import ConversationState

import json
from redis_client import redis_client

SESSION_TTL = 3600  # 1 hour

# Local cache for backwards compatibility (optional)
sessions = {}


def get_session(session_id: str):
    """
    Retrieve session from Redis. Creates new session if not found.
    Never accepts external history to prevent overwriting stored state.
    
    Args:
        session_id: Unique session identifier
        
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

    # If session doesn't exist, create new one with empty state
    session = {
        "history": [],
        "messages": 0,
        "scam_score": 0.5,
        "intel": {
            "phoneNumbers": [],
            "upiIds": [],
            "cryptoWallets": [],
            "phishingLinks": [],
            "bankAccounts": [],
            "suspiciousKeywords": [],
        },
        "dialogue_state": ConversationState.INIT,
        "state_turn_count": 0,
        "message_hashes": {},  # {hash: count} for deduplication
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
    import hashlib
    
    # Get latest session from Redis
    session = get_session(session_id)
    
    # Append message exchange to history
    session["history"].append(message)
    session["history"].append({
        "sender": "user",
        "text": reply
    })
    
    # Track message hashes for deduplication
    if "message_hashes" not in session:
        session["message_hashes"] = {}
    
    # Hash the scammer message
    msg_hash = hashlib.sha256(message.get("text", "").encode()).hexdigest()[:8]
    session["message_hashes"][msg_hash] = session["message_hashes"].get(msg_hash, 0) + 1
    
    # Save back to Redis
    save_session(session_id, session)


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