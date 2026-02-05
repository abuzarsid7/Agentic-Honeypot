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
            "completed": False
        }
    return sessions[session_id]

def update_session(session_id, message, reply):
    sessions[session_id]["history"].append(message)
    sessions[session_id]["history"].append({
        "sender": "user",
        "text": reply
    })
    sessions[session_id]["messages"] += 2