import time
import requests

def send_final_result(session_id, session):
    """
    Send final results to GUVI API with comprehensive intelligence summary.
    Generates dynamic agent notes based on collected intel.
    Output matches the corrected structure:
      sessionId, status, scamDetected, extractedIntelligence,
      totalMessagesExchanged, engagementDurationSeconds, agentNotes
    """
    # Generate dynamic agent notes based on what was collected
    notes = generate_agent_notes(session)

    # Calculate engagement duration from first and last message timestamps
    history = session.get("history", [])
    timestamps = [msg.get("timestamp") for msg in history if msg.get("timestamp")]
    if len(timestamps) >= 2:
        engagement_duration = int(timestamps[-1] - timestamps[0])
    elif timestamps:
        engagement_duration = 0
    else:
        # Fallback to start_time if no timestamps on messages
        start_time = session.get("start_time", time.time())
        engagement_duration = int(time.time() - start_time)

    # Build extractedIntelligence with only the required fields
    intel = session.get("intel", {})
    extracted_intelligence = {
        "phoneNumbers": intel.get("phoneNumbers", []),
        "bankAccounts": intel.get("bankAccounts", []),
        "upiIds": intel.get("upiIds", []),
        "phishingLinks": intel.get("phishingLinks", []),
        "emailAddresses": intel.get("emails", []),
        "names": intel.get("names", []),
        "caseIds": intel.get("caseIds", []),
        "policyNumbers": intel.get("policyNumbers", []),
        "orderNumbers": intel.get("orderNumbers", []),
    }

    payload = {
        "sessionId": session_id,
        "status": "success",
        "scamDetected": True,
        "extractedIntelligence": extracted_intelligence,
        "totalMessagesExchanged": session.get("messages", len(session.get("history", [])) // 2),
        "engagementDurationSeconds": engagement_duration,
        "agentNotes": notes,
    }

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
    
    # Analyze intelligence collected
    if intel.get("phishingLinks"):
        notes.append(f"Shared {len(intel['phishingLinks'])} phishing link(s)")
    
    if intel.get("upiIds"):
        notes.append(f"Requested payment to {len(intel['upiIds'])} UPI ID(s)")
    
    if intel.get("phoneNumbers"):
        notes.append(f"Provided {len(intel['phoneNumbers'])} phone number(s) for callback")
    
    if intel.get("bankAccounts"):
        notes.append(f"Mentioned {len(intel['bankAccounts'])} account number(s)")
    
    if intel.get("names"):
        notes.append(f"Identified name(s): {', '.join(intel['names'])}")
    
    if intel.get("emails"):
        notes.append(f"Shared {len(intel['emails'])} email address(es)")
    
    if intel.get("caseIds"):
        notes.append(f"Referenced {len(intel['caseIds'])} case/reference ID(s)")
    
    if intel.get("policyNumbers"):
        notes.append(f"Mentioned {len(intel['policyNumbers'])} policy number(s)")
    
    if intel.get("orderNumbers"):
        notes.append(f"Referenced {len(intel['orderNumbers'])} order number(s)")
    
    # Analyze conversation pattern
    if len(session.get("history", [])) < 10:
        notes.append("Scammer attempted quick conversion")
    else:
        notes.append("Extended conversation to build trust")
    
    if not notes:
        notes.append("Suspicious messaging patterns detected with potential scam indicators")
    
    return ". ".join(notes) + "."