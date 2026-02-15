from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from detector import detect_scam, detect_scam_detailed
from agent import agent_reply
from memory import get_session, sessions, save_session
from normalizer import get_normalization_report
from telemetry import track_request, track_detection, get_metrics
from llm_engine import analyze_message, get_cache_stats, clear_cache, get_provider_info
from dialogue_strategy import get_state_info
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
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
    # Health check for Railway + warm-up
    return {"status": "ok"}

@app.post("/")
def root_honeypot(payload: dict, x_api_key: str = Header(None)):
    return honeypot(payload, x_api_key)

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
def list_sessions(x_api_key: str = Header(None)):
    """
    📋 LIST SESSIONS: Get all active sessions
    
    Returns list of session summaries with:
    - Session ID, score, state, message count
    - Last activity timestamp
    - Intelligence extraction count
    - Hard trigger status
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    session_list = []
    for session_id, session in sessions.items():
        intel = session.get("intel", {})
        intel_count = sum(
            len(v) if isinstance(v, list) else 0 
            for v in intel.values()
        )
        
        # Determine if hard triggers were hit
        last_analysis = session.get("last_analysis", {})
        hard_trigger = bool(last_analysis.get("hard_triggers"))
        
        # Check for bot accusation defense usage
        bot_accusation = session.get("bot_accusation_count", 0) > 0
        
        session_list.append({
            "id": session_id,
            "score": session.get("scam_score", 0.0),
            "state": session.get("dialogue_state", "INIT"),
            "messages": session.get("messages", 0),
            "intelCount": intel_count,
            "lastActivity": session.get("last_updated", 0),
            "hardTrigger": hard_trigger,
            "botAccusation": bot_accusation,
            "completed": session.get("completed", False),
            "lastTactic": last_analysis.get("intent", {}).get("label", "Unknown"),
        })
    
    return {"sessions": session_list}


@app.get("/session/{session_id}")
def get_session_details(session_id: str, x_api_key: str = Header(None)):
    """
    🔍 SESSION DETAILS: Get full session data
    
    Returns complete session information including:
    - Full conversation history
    - Extracted intelligence
    - Dialogue state and progression
    - Analysis results
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = sessions[session_id]
    
    return {
        "status": "success",
        "session": {
            "id": session_id,
            "scam_score": session.get("scam_score", 0.0),
            "dialogue_state": session.get("dialogue_state", "INIT"),
            "messages": session.get("messages", 0),
            "completed": session.get("completed", False),
            "history": session.get("history", []),
            "intel": session.get("intel", {}),
            "last_analysis": session.get("last_analysis", {}),
            "state_history": session.get("state_history", []),
            "last_updated": session.get("last_updated", 0),
        }
    }


@app.post("/honeypot")
def honeypot(payload: dict, x_api_key: str = Header(None)):
    try:
        with track_request():

            # 🔐 API key validation
            if x_api_key != API_KEY:
                raise HTTPException(status_code=401, detail="Invalid API key")

            session_id = payload["sessionId"]
            message = payload["message"]
            user_text = message["text"]

            session = get_session(session_id)

            # ======================================================
            # 1️⃣ CHECK IF CONVERSATION ALREADY FINISHED
            # ======================================================
            if session.get("completed", False):
                return {
                    "status": "success",
                    "reply": "I have to go now. Goodbye.",
                    "conversation_ended": True
                }

            # ======================================================
            # 2️⃣ FULL STRUCTURED ANALYSIS (LLM + Heuristic)
            # ======================================================
            history = session.get("history", [])
            analysis = analyze_message(user_text, history)
            session["last_analysis"] = analysis

            composite_score = analysis.get("composite_score", 0.0)
            scam_detected = composite_score > 0.5

            # Update session scam_score from actual analysis
            session["scam_score"] = composite_score

            track_detection(scam_detected)

            # ======================================================
            # 3️⃣ NORMAL AGENT EXECUTION
            # (Bot accusation defense is handled inside agent_reply)
            # ======================================================
            if scam_detected or session.get("messages", 0) > 0:
                reply = agent_reply(session_id, session, user_text)
                ended = session.get("completed", False)
                return {
                    "status": "success",
                    "reply": reply,
                    **({
                        "conversation_ended": True
                    } if ended else {})
                }

            # ======================================================
            # 4️⃣ FIRST MESSAGE + BENIGN
            # ======================================================
            session["messages"] = session.get("messages", 0) + 1
            benign_reply = "Okay, thank you."
            if "history" not in session:
                session["history"] = []
            session["history"].append({"sender": "scammer", "text": user_text})
            session["history"].append({"sender": "user", "text": benign_reply})
            save_session(session_id, session)
            return {"status": "success", "reply": benign_reply}

    except HTTPException:
        raise

    except Exception:
        logger.exception("Honeypot endpoint error")
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
    
    Returns detailed report of how text transforms through 10 stages.
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
        "final": report["stage11_final"],
        "transformations": {
            "unicode_changed": report["original"] != report["stage1_unicode"],
            "zero_width_removed": report["stage1_unicode"] != report["stage2_zero_width"],
            "control_chars_removed": report["stage2_zero_width"] != report["stage3_control_chars"],
            "homoglyphs_normalized": report["stage3_control_chars"] != report["stage4_homoglyphs"],
            "hex_urls_decoded": report["stage4_homoglyphs"] != report["stage5_hex_urls"],
            "leetspeak_converted": report["stage5_hex_urls"] != report["stage6_leetspeak"],
            "char_spacing_collapsed": report["stage6_leetspeak"] != report["stage7_char_spacing"],
            "urls_deobfuscated": report["stage7_char_spacing"] != report["stage8_urls"],
            "short_urls_expanded": report["stage8_urls"] != report["stage9_short_urls"],
            "whitespace_normalized": report["stage9_short_urls"] != report["stage10_whitespace"],
            "lowercased": report["stage10_whitespace"] != report["stage11_final"]
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
        "suspicious_keywords": len(intel.get("suspiciousKeywords", [])),
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
    
    # Use the actual extraction pipeline (same as honeypot endpoint)
    from intelligence import (
        extract_intel as _extract_intel,
        extract_obfuscated_urls,
        extract_split_numbers,
        extract_number_words,
        extract_intel_with_llm,
        merge_and_deduplicate,
    )
    from normalizer import (
        normalize_unicode, remove_zero_width,
        remove_control_characters, normalize_homoglyphs,
        decode_hex_urls, deobfuscate_char_spacing,
        deobfuscate_urls, expand_shortened_urls, normalize_whitespace
    )
    import re
    
    # Extraction-safe normalization (same as extract_intel: stages 1-5 + 7-10)
    text_clean = normalize_unicode(text)
    text_clean = remove_zero_width(text_clean)
    text_clean = remove_control_characters(text_clean)
    text_clean = normalize_homoglyphs(text_clean)
    text_clean = decode_hex_urls(text_clean)
    text_clean = deobfuscate_char_spacing(text_clean)
    text_clean = deobfuscate_urls(text_clean)
    text_clean = expand_shortened_urls(text_clean)
    text_clean = normalize_whitespace(text_clean)
    text_lower = text_clean.lower()
    
    # Run extraction on a temporary session to get full results
    temp_session = {
        "intel": {"upiIds": [], "phoneNumbers": [], "phishingLinks": [],
                  "bankAccounts": [], "suspiciousKeywords": []},
        "history": [],
        "messages": 0,
    }
    _extract_intel(temp_session, text)
    
    # Also get per-method breakdown for debug visibility
    _UPI_HANDLES = (
        'paytm', 'ybl', 'okaxis', 'okhdfcbank', 'oksbi', 'okicici',
        'upi', 'apl', 'ibl', 'sbi', 'hdfcbank', 'icici', 'axisbank',
        'axl', 'boi', 'citi', 'citigold', 'dlb', 'fbl', 'federal',
        'idbi', 'idfcbank', 'indus', 'kbl', 'kotak', 'lvb', 'pnb',
        'rbl', 'sib', 'uco', 'union', 'vijb', 'abfspay', 'freecharge',
        'jio', 'airtel', 'postbank', 'waheed', 'slice', 'jupiter',
        'fi', 'gpay', 'phonepe', 'amazonpay', 'mobikwik', 'niyopay',
    )
    _upi_handle_pattern = '|'.join(re.escape(h) for h in _UPI_HANDLES)
    upi_regex = rf"[a-zA-Z0-9.\-_]{{2,}}@(?:{_upi_handle_pattern})\b"
    
    regex_results = {
        "upiIds": re.findall(upi_regex, text_clean, re.IGNORECASE),
        "phoneNumbers": re.findall(r"\+?91\d{10}|\+\d{10,}|(?<![\d])\d{10}(?![\d])", text_clean),
        "phishingLinks": [link.rstrip('.,;:!?)') for link in re.findall(r"https?://\S+", text_clean)],
        "bankAccounts": [acc for acc in re.findall(r"\b\d{9,18}\b", text_clean)],
        "suspiciousKeywords": [kw for kw in ['upi', 'verify', 'urgent', 'blocked', 'otp', 'cvv'] if kw in text_lower]
    }
    
    advanced_results = {
        "upiIds": [],
        "phoneNumbers": extract_split_numbers(text) + extract_number_words(text),
        "phishingLinks": extract_obfuscated_urls(text),
        "bankAccounts": [],
        "suspiciousKeywords": []
    }
    
    llm_results = extract_intel_with_llm(text, [])
    
    return {
        "status": "success",
        "input": text,
        "normalized_input": text_clean,
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
        "final_normalized_intel": temp_session["intel"],
        "extraction_metadata": temp_session.get("extraction_metadata", []),
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
                "suspiciousKeywords": []
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
        "scammer_pressure": "🔴 Scammer repeatedly pressuring, closing strategically",
        "scammer_disengaged": "👋 Scammer showing signs of disengagement, finalizing now",
        "high_quality_complete": "✅ High-quality extraction achieved (score > 0.75)",
        "diminishing_returns": "📊 Good intel collected, but novelty rate declining",
        "multiple_warning_signs": "⚡ Multiple closing conditions detected",
        "continue_extraction": "🔄 Continue conversation, still extracting value",
        "normal_flow": "➡️ Normal conversation flow, no closing signal yet"
    }
    return interpretations.get(reason, f"Unknown reason: {reason}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  
    )