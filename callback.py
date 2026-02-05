import requests

def send_final_result(session_id, session):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": session["messages"],
        "extractedIntelligence": session["intel"],
        "agentNotes": "Scammer used urgency tactics (account blocked), "
    "requested UPI payment, and later shared a suspicious link "
    "and phone number to escalate trust."
    }

    requests.post(
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
        json=payload,
        timeout=5
    )