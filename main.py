from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from detector import detect_scam, detect_scam_detailed
from agent import agent_reply
from memory import get_session, update_session, sessions
from normalizer import get_normalization_report
from telemetry import track_request, track_detection, get_metrics
from llm_engine import analyze_message, get_cache_stats, clear_cache, get_provider_info
from dialogue_strategy import get_state_info
from defense import is_bot_accusation_detected
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

app = FastAPI()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    # Health check for Render + warm-up
    return {"status": "ok"}


@app.get("/metrics")
def metrics_endpoint(x_api_key: str = Header(None)):
    """
    📊 METRICS ENDPOINT: Real-time telemetry and performance stats
    
    Returns comprehensive metrics about:
    - API request statistics (latency, throughput, errors)
    - Scam detection performance
    - Intelligence extraction counts
    - Session analytics
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return get_metrics()


@app.get("/sessions")
def get_sessions(x_api_key: str = Header(None)):
    """
    📋 SESSIONS ENDPOINT: Get all active sessions
    
    Returns list of all sessions with basic info for dashboard display
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    from memory import sessions
    from datetime import datetime
    
    session_list = []
    for session_id, session in sessions.items():
        # Calculate basic metrics
        messages = len(session.get("history", [])) // 2  # Divide by 2 (user+agent pairs)
        intel = session.get("intel", {})
        intel_count = sum(len(v) if isinstance(v, list) else 0 for v in intel.values())
        
        # Get last activity timestamp
        last_activity = session.get("last_updated", datetime.now().timestamp())
        
        # Determine if there are hard triggers
        hard_trigger = session.get("hard_trigger", False)
        
        # Check for bot accusation defense
        bot_accusation = session.get("bot_accusation_triggered", False)
        
        session_list.append({
            "id": session_id,
            "score": session.get("scam_score", 0.0),
            "state": session.get("dialogue_state", "INIT"),
            "lastTactic": session.get("last_tactic", "Unknown"),
            "intelCount": intel_count,
            "messages": messages,
            "lastActivity": int(last_activity * 1000),  # Convert to milliseconds
            "hardTrigger": hard_trigger,
            "botAccusation": bot_accusation,
        })
    
    return {
        "status": "success",
        "sessions": session_list,
        "total": len(session_list)
    }


@app.get("/sessions/{session_id}")
def get_session_details(session_id: str, x_api_key: str = Header(None)):
    """
    🔍 SESSION DETAILS ENDPOINT: Get full session data
    
    Returns complete session information including conversation history,
    intelligence extracted, and dialogue state
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    from memory import sessions
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "status": "success",
        "session": session
    }


@app.post("/honeypot")
def honeypot(payload: dict, x_api_key: str = Header(None)):
    try:
        # � Track request with automatic timing
        with track_request():
            # 🔐 API key validation
            if x_api_key != API_KEY:
                raise HTTPException(status_code=401, detail="Invalid API key")

            session_id = payload["sessionId"]
            message = payload["message"]
            history = payload.get("conversationHistory", [])

            session = get_session(session_id, history)

            # 🛡️ PRIORITY CHECK: Bot accusation (always engage, even on first message)
            # This ensures defensive responses work even if scam detector misses it
            is_bot_accusation = is_bot_accusation_detected(message["text"])
            
            if is_bot_accusation:
                # Bot accusation detected - engage immediately to defend
                reply = agent_reply(session_id, session, message["text"])
                update_session(session_id, message, reply)
                track_detection(True)  # Count as engagement
                return {"status": "success", "reply": reply}

            scam_detected = detect_scam(message["text"], history)
            
            # 📊 Track detection result
            track_detection(scam_detected)

            if scam_detected:
                reply = agent_reply(session_id, session, message["text"])
                update_session(session_id, message, reply)
                return {"status": "success", "reply": reply}
            
            # Always engage with LLM-generated responses to catch subtle scams
            # This ensures we don't miss scammers who start with benign messages
            reply = agent_reply(session_id, session, message["text"])
            update_session(session_id, message, reply)
            return {"status": "success", "reply": reply}

    except HTTPException:
        # Let FastAPI handle auth errors properly
        raise

    except Exception as e:
        # 🚨 SAFETY NET: never return empty response
        return {
            "status": "error",
            "reply": "Temporary issue, please retry"
        }


@app.post("/debug/score")
def debug_scoring(payload: dict, x_api_key: str = Header(None)):
    """
    🔍 DEBUG ENDPOINT: Show hybrid scoring breakdown
    
    Returns the multi-signal weighted score and per-signal details.
    Useful for tuning thresholds and understanding detection decisions.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    text = payload.get("text", "")
    history = payload.get("conversationHistory", [])
    if not text:
        return {"status": "error", "message": "Text field required"}
    
    result = detect_scam_detailed(text, history)
    
    return {
        "status": "success",
        "input": text,
        **result,
    }


@app.post("/debug/llm")
def debug_llm_analysis(payload: dict, x_api_key: str = Header(None)):
    """
    🧠 DEBUG ENDPOINT: Full LLM analysis
    
    Returns structured JSON with:
    - Intent classification (label, confidence, reasoning)
    - Social engineering detection (tactics, severity, details)
    - Scam narrative classification (category, stage, description)
    - Composite score and source (llm / heuristic)
    - Cache hit/miss status
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    text = payload.get("text", "")
    history = payload.get("conversationHistory", [])
    if not text:
        return {"status": "error", "message": "Text field required"}
    
    result = analyze_message(text, history)
    
    return {
        "status": "success",
        "input": text,
        **result,
    }


@app.get("/debug/llm/cache")
def debug_llm_cache(x_api_key: str = Header(None)):
    """
    📊 LLM cache statistics: size, hit rate, TTL.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return {
        "status": "success",
        "provider": get_provider_info(),
        "cache": get_cache_stats(),
    }


@app.post("/debug/llm/cache/clear")
def debug_llm_cache_clear(x_api_key: str = Header(None)):
    """
    🗑️ Flush LLM analysis cache.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    clear_cache()
    return {"status": "success", "message": "LLM cache cleared"}


@app.post("/debug/normalize")
def debug_normalization(payload: dict, x_api_key: str = Header(None)):
    """
    🔍 DEBUG ENDPOINT: Show normalization pipeline stages
    
    Returns detailed report of how text transforms through 8 stages.
    Useful for demo and debugging obfuscation attacks.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    text = payload.get("text", "")
    if not text:
        return {"status": "error", "message": "Text field required"}
    
    report = get_normalization_report(text)
    
    return {
        "status": "success",
        "input": text,
        "stages": report,
        "final": report["stage8_final"],
        "transformations": {
            "unicode_changed": report["original"] != report["stage1_unicode"],
            "zero_width_removed": report["stage1_unicode"] != report["stage2_zero_width"],
            "control_chars_removed": report["stage2_zero_width"] != report["stage3_control_chars"],
            "homoglyphs_normalized": report["stage3_control_chars"] != report["stage4_homoglyphs"],
            "leetspeak_converted": report["stage4_homoglyphs"] != report["stage5_leetspeak"],
            "urls_deobfuscated": report["stage5_leetspeak"] != report["stage6_urls"],
            "whitespace_normalized": report["stage6_urls"] != report["stage7_whitespace"],
            "lowercased": report["stage7_whitespace"] != report["stage8_final"]
        }
    }


@app.post("/debug/strategy")
def debug_strategy(payload: dict, x_api_key: str = Header(None)):
    """
    🎯 DEBUG ENDPOINT: Show dialogue strategy state and progression
    
    Returns current state, goal, extraction targets, and state history.
    Useful for understanding conversation flow and state transitions.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    session_id = payload.get("sessionId", "")
    if not session_id:
        return {"status": "error", "message": "sessionId field required"}
    
    # Check if session exists
    if session_id not in sessions:
        return {
            "status": "error",
            "message": f"Session {session_id} not found"
        }
    
    session = sessions[session_id]
    current_state = session.get("dialogue_state", "INIT")
    state_info = get_state_info(current_state)
    
    # Calculate extraction progress
    intel = session.get("intel", {})
    extraction_progress = {
        "upi_ids": len(intel.get("upiIds", [])),
        "phone_numbers": len(intel.get("phoneNumbers", [])),
        "phishing_links": len(intel.get("phishingLinks", [])),
        "bank_accounts": len(intel.get("bankAccounts", [])),
        "names": len(intel.get("names", [])),
        "emails": len(intel.get("emails", [])),
        "case_ids": len(intel.get("caseIds", [])),
        "policy_numbers": len(intel.get("policyNumbers", [])),
        "order_numbers": len(intel.get("orderNumbers", [])),
    }
    
    # Get recent micro-behaviors (last 5 responses)
    metadata_history = session.get("response_metadata", [])
    recent_metadata = metadata_history[-5:] if len(metadata_history) > 5 else metadata_history
    
    # Calculate micro-behavior statistics
    total_responses = len(metadata_history)
    micro_behavior_stats = {
        "total_responses": total_responses,
        "delays_used": sum(1 for m in metadata_history if m.get("delay_seconds", 0) > 0),
        "fear_expressed": sum(1 for m in metadata_history if m.get("has_fear", False)),
        "hesitation_shown": sum(1 for m in metadata_history if m.get("has_hesitation", False)),
        "typos_made": sum(1 for m in metadata_history if m.get("has_typo", False)),
        "corrections_made": sum(1 for m in metadata_history if m.get("has_correction", False)),
    }
    
    return {
        "status": "success",
        "session_id": session_id,
        "current_state": current_state,
        "state_goal": state_info.get("goal", ""),
        "extraction_targets": state_info.get("extraction_targets", []),
        "state_turn_count": session.get("state_turn_count", 0),
        "max_turns_in_state": state_info.get("max_turns", 0),
        "state_history": session.get("state_history", []),
        "extraction_progress": extraction_progress,
        "total_messages": session.get("messages", 0),
        "conversation_completed": session.get("completed", False),
        "micro_behaviors": {
            "recent_responses": recent_metadata,
            "statistics": micro_behavior_stats,
        },
    }


@app.post("/debug/intelligence")
def debug_intelligence(payload: dict, x_api_key: str = Header(None)):
    """
    🔍 DEBUG ENDPOINT: Show hybrid intelligence extraction breakdown
    
    Returns extraction results from all three methods:
    - Regex-based extraction
    - Advanced pattern extraction (obfuscated URLs, split numbers)
    - LLM-based extraction
    Plus merge/deduplication statistics.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    text = payload.get("text", "")
    if not text:
        return {"status": "error", "message": "Text field required"}
    
    # Import extraction functions
    from intelligence import (
        extract_obfuscated_urls,
        extract_split_numbers,
        extract_number_words,
        extract_intel_with_llm,
        merge_and_deduplicate,
        normalize_unicode,
        remove_zero_width,
        normalize_whitespace
    )
    import re
    
    # Light normalization
    text_clean = normalize_unicode(text)
    text_clean = remove_zero_width(text_clean)
    text_clean = normalize_whitespace(text_clean)
    text_lower = text_clean.lower()
    
    # REGEX extraction — UPI vs email classification
    _UPI_SUFFIXES = {
        'paytm', 'ybl', 'okhdfcbank', 'okaxis', 'oksbi', 'okicici',
        'upi', 'sbi', 'hdfcbank', 'icici', 'axisbank', 'kotak',
        'pnb', 'gpay', 'phonepe', 'apl', 'ratn', 'barodampay',
        'ibl', 'axl', 'pingpay', 'freecharge', 'waaxis', 'wasbi',
        'wahdfcbank', 'waicici', 'abfspay', 'ikwik', 'jupiteraxis',
        'yesbankltd', 'yesbank', 'federal', 'rbl', 'dbs', 'indus',
        'citi', 'hsbc', 'sc', 'idbi', 'unionbank', 'boi', 'cnrb',
        'idfcbank', 'aubank', 'dlb', 'cub', 'kvb', 'tmb', 'jio',
        'slice', 'niyoicici', 'postbank', 'finobank', 'kkbk',
        'imobile', 'mahb', 'indianbank', 'psb', 'uboi', 'cbin',
    }
    all_at_tokens = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+', text_clean)
    upi_ids = []
    email_list = []
    for token in all_at_tokens:
        local, domain = token.rsplit('@', 1)
        domain_lower = domain.lower()
        if domain_lower in _UPI_SUFFIXES or '.' not in domain:
            upi_ids.append(token)
        elif re.match(r'^[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', domain):
            email_list.append(token)
    upi_set = set(u.lower() for u in upi_ids)
    email_list = [e for e in email_list if e.lower() not in upi_set]
    regex_results = {
        "upiIds": upi_ids,
        "phoneNumbers": re.findall(r"\+?91\d{10}|\+\d{10,}|(?<![\d])\d{10}(?![\d])", text_clean),
        "phishingLinks": [link.rstrip('.,;:!?)') for link in re.findall(r"https?://\S+", text_clean)],
        "bankAccounts": [acc for acc in re.findall(r"\b\d{8,16}\b", text_clean) if len(acc) != 10],
        "names": [],
        "emails": email_list,
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
    }
    
    # ADVANCED extraction
    advanced_results = {
        "upiIds": [],
        "phoneNumbers": extract_split_numbers(text) + extract_number_words(text),
        "phishingLinks": extract_obfuscated_urls(text),
        "bankAccounts": [],
        "names": [],
        "emails": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
    }
    
    # LLM extraction
    llm_results = extract_intel_with_llm(text, [])
    
    # MERGE
    merged = merge_and_deduplicate(regex_results, advanced_results, llm_results)
    
    return {
        "status": "success",
        "input": text,
        "extraction_methods": {
            "regex": {
                "upis": len(regex_results["upiIds"]),
                "phones": len(regex_results["phoneNumbers"]),
                "urls": len(regex_results["phishingLinks"]),
                "accounts": len(regex_results["bankAccounts"]),
                "results": regex_results
            },
            "advanced_patterns": {
                "phones": len(advanced_results["phoneNumbers"]),
                "urls": len(advanced_results["phishingLinks"]),
                "results": advanced_results
            },
            "llm": {
                "upis": len(llm_results.get("upiIds", [])),
                "phones": len(llm_results.get("phoneNumbers", [])),
                "urls": len(llm_results.get("phishingLinks", [])),
                "source": llm_results.get("source", "unavailable"),
                "results": llm_results
            }
        },
        "merged_results": {
            "upis": len(merged["upiIds"]),
            "phones": len(merged["phoneNumbers"]),
            "urls": len(merged["phishingLinks"]),
            "accounts": len(merged["bankAccounts"]),
            "names": len(merged.get("names", [])),
            "emails": len(merged.get("emails", [])),
            "case_ids": len(merged.get("caseIds", [])),
            "policy_numbers": len(merged.get("policyNumbers", [])),
            "order_numbers": len(merged.get("orderNumbers", [])),
            "results": merged
        },
        "deduplication_stats": {
            "total_before": {
                "phones": len(regex_results["phoneNumbers"]) + len(advanced_results["phoneNumbers"]) + len(llm_results.get("phoneNumbers", [])),
                "urls": len(regex_results["phishingLinks"]) + len(advanced_results["phishingLinks"]) + len(llm_results.get("phishingLinks", []))
            },
            "total_after": {
                "phones": len(merged["phoneNumbers"]),
                "urls": len(merged["phishingLinks"])
            }
        }
    }


@app.post("/debug/intel_score")
def debug_intel_score(payload: dict, x_api_key: str = Header(None)):
    """
    📊 DEBUG ENDPOINT: Show intelligent intel scoring data
    
    Returns:
    - Weighted intel score (0-1)
    - Component scores (artifacts, scam_confidence, engagement, novelty)
    - Scammer pattern detection
    - Closing decision with reasoning
    - Extraction history timeline
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Create mock session with provided data or use session_id
    session_id = payload.get("session_id")
    
    if session_id:
        # Get existing session
        session = sessions.get(session_id)
        if not session:
            return {"status": "error", "message": "Session not found"}
    else:
        # Create mock session from provided intel
        session = {
            "messages": payload.get("messages", 10),
            "scam_score": payload.get("scam_score", 0.65),
            "intel": payload.get("intel", {
                "upiIds": [],
                "phoneNumbers": [],
                "phishingLinks": [],
                "bankAccounts": [],
                "names": [],
                "emails": [],
                "caseIds": [],
                "policyNumbers": [],
                "orderNumbers": [],
            }),
            "history": payload.get("history", []),
            "intel_extraction_history": payload.get("intel_extraction_history", [])
        }
    
    from intelligence import (
        calculate_intel_score,
        detect_scammer_patterns,
        should_close_conversation
    )
    
    # Calculate scores
    intel_score_data = calculate_intel_score(session)
    patterns = detect_scammer_patterns(session)
    should_close, close_reason = should_close_conversation(session)
    
    return {
        "status": "success",
        "intel_score": {
            "overall_score": round(intel_score_data["score"], 3),
            "components": {
                k: round(v, 3) 
                for k, v in intel_score_data["components"].items()
            },
            "weights": intel_score_data["weights"],
            "details": intel_score_data["details"]
        },
        "scammer_patterns": {
            "repeated_pressure": patterns["repeated_pressure"],
            "disengagement": patterns["disengagement"],
            "stale_intel": patterns["stale_intel"],
            "severity": round(patterns["severity"], 2)
        },
        "closing_decision": {
            "should_close": should_close,
            "reason": close_reason,
            "interpretation": _interpret_close_reason(close_reason)
        },
        "extraction_timeline": session.get("intel_extraction_history", []),
        "session_stats": {
            "total_messages": session.get("messages", 0),
            "total_intel_items": sum(
                len(v) if isinstance(v, list) else 0 
                for v in session.get("intel", {}).values()
            ),
            "scam_confidence": session.get("scam_score", 0.0)
        }
    }


def _interpret_close_reason(reason: str) -> str:
    """Provide human-readable interpretation of close reasons."""
    interpretations = {
        "hard_limit_reached": "⚠️ Conversation exceeded 30 messages (safety limit)",
        "too_early": "⏳ Too soon to close (minimum 6 messages required)",
        "intel_stagnation": "📉 No new intelligence in last 3 turns, sufficient data collected",
        "scammer_disengaged": "👋 Scammer showing signs of disengagement, finalizing now",
        "high_quality_complete": "✅ High-quality extraction achieved (score > 0.75)",
        "diminishing_returns": "📊 Good intel collected, but novelty rate declining",
        "multiple_warning_signs": "⚡ Multiple closing conditions detected",
        "continue_extraction": "🔄 Continue conversation, still extracting value",
        "normal_flow": "➡️ Normal conversation flow, no closing signal yet"
    }
    return interpretations.get(reason, f"Unknown reason: {reason}")


@app.get("/api/regulatory/evidence/{session_id}")
def get_evidence_packet(session_id: str, mask_pii: bool = True, x_api_key: str = Header(None)):
    """
    📦 EVIDENCE PACKET ENDPOINT: Generate compliance-ready evidence for regulatory filing
    
    Returns structured evidence packet for a session including:
    - Scam summary, risk verdict, conversation timeline
    - Extracted intelligence artifacts
    - Closure reason and classification
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from datetime import datetime
    
    intel = session.get("intel", {})
    history = session.get("history", [])
    
    def _mask(value):
        if not mask_pii or not value or len(str(value)) <= 4:
            return value
        s = str(value)
        return s[:2] + '*' * (len(s) - 4) + s[-2:]

    # Build timeline
    timeline = []
    for i, msg in enumerate(history):
        timeline.append({
            "index": i + 1,
            "role": msg.get("role", "unknown"),
            "text": msg.get("text", ""),
            "timestamp": msg.get("timestamp", None),
        })

    # Build artifacts list
    artifacts = {}
    for key, values in intel.items():
        if isinstance(values, list) and values:
            artifacts[key] = [_mask(v) if mask_pii else v for v in values]

    evidence = {
        "session_id": session_id,
        "generated_at": datetime.now().isoformat(),
        "classification": {
            "scam_score": session.get("scam_score", 0.0),
            "dialogue_state": session.get("dialogue_state", "UNKNOWN"),
            "last_tactic": session.get("last_tactic", "Unknown"),
            "hard_trigger": session.get("hard_trigger", False),
        },
        "summary": {
            "total_messages": len(history),
            "intel_items_extracted": sum(
                len(v) if isinstance(v, list) else 0
                for v in intel.values()
            ),
            "closure_reason": session.get("close_reason", "N/A"),
        },
        "timeline": timeline,
        "artifacts": artifacts,
        "pii_masked": mask_pii,
    }
    
    return {"status": "success", "evidence": evidence}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  
    )