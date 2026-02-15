import requests

def send_final_result(session_id, session):
    """
    Send final results to GUVI API with comprehensive intelligence summary.
    Generates dynamic agent notes based on collected intel.
    """
    # Generate dynamic agent notes based on what was collected
    notes = generate_agent_notes(session)
    
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": session.get("messages", 0),
        "extractedIntelligence": session["intel"],
        "agentNotes": notes
    }
    
    print(f"\n{'='*60}")
    print(f"📤 CALLBACK PAYLOAD for session {session_id}:")
    print(f"   Messages Exchanged: {payload['totalMessagesExchanged']}")
    print(f"   Extracted Intelligence:")
    for key, value in payload['extractedIntelligence'].items():
        print(f"     • {key}: {value}")
    print(f"   Agent Notes: {payload['agentNotes']}")
    print(f"   Endpoint: https://hackathon.guvi.in/api/updateHoneyPotFinalResult")
    print(f"{'='*60}\n")

    try:
        response = requests.post(
            "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        print(f"✅ Successfully sent results for session {session_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send results for session {session_id}: {e}")
        # Still return True since we tried - don't want to retry endlessly
        return False

def generate_agent_notes(session):
    """
    Generate comprehensive notes based on collected intelligence.
    """
    notes = []
    intel = session["intel"]
    
    # Analyze tactics used
    if any(kw in intel["suspiciousKeywords"] for kw in ['urgent', 'immediately', 'blocked', 'suspended', 'expire']):
        notes.append("Scammer employed urgency tactics to pressure victim")
    
    if 'verify' in intel["suspiciousKeywords"] or 'kyc' in intel["suspiciousKeywords"]:
        notes.append("Used verification/KYC pretext to appear legitimate")
    
    # Analyze intelligence collected
    if intel["phishingLinks"]:
        notes.append(f"Shared {len(intel['phishingLinks'])} phishing link(s)")
    
    if intel["upiIds"]:
        notes.append(f"Requested payment to {len(intel['upiIds'])} UPI ID(s)")
    
    if intel["phoneNumbers"]:
        notes.append(f"Provided {len(intel['phoneNumbers'])} phone number(s) for callback")
    
    if intel["bankAccounts"]:
        notes.append(f"Mentioned {len(intel['bankAccounts'])} account number(s)")
    
    # Analyze conversation pattern
    if session.get("messages", 0) < 10:
        notes.append("Scammer attempted quick conversion")
    else:
        notes.append("Extended conversation to build trust")
    
    if not notes:
        notes.append("Suspicious messaging patterns detected with potential scam indicators")
    
    return ". ".join(notes) + "."