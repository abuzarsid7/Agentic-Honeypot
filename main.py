from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from detector import detect_scam, detect_scam_detailed
from agent import agent_reply
from memory import get_session, update_session
from normalizer import get_normalization_report
from telemetry import track_request, track_detection, get_metrics
from llm_engine import analyze_message, get_cache_stats, clear_cache, get_provider_info
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

            scam_detected = detect_scam(message["text"], history)
            
            # 📊 Track detection result
            track_detection(scam_detected)

            if scam_detected:
                reply = agent_reply(session_id, session, message["text"])
                update_session(session_id, message, reply)
                return {"status": "success", "reply": reply}
            
            # Even if not detected as scam, engage if conversation already started
            if session["messages"] > 0:
                # Conversation in progress - keep it going
                reply = agent_reply(session_id, session, message["text"])
                update_session(session_id, message, reply)
                return {"status": "success", "reply": reply}

            # First message and not detected as scam - be neutral
            return {"status": "success", "reply": "Okay, thank you."}

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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  
    )