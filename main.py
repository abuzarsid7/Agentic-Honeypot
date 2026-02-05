from fastapi import FastAPI, Header, HTTPException
from detector import detect_scam
from agent import agent_reply
from memory import get_session, update_session
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

app = FastAPI()


@app.get("/")
def health():
    # Health check for Render + warm-up
    return {"status": "ok"}


@app.post("/honeypot")
def honeypot(payload: dict, x_api_key: str = Header(None)):
    try:
        # 🔐 API key validation
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

        session_id = payload["sessionId"]
        message = payload["message"]
        history = payload.get("conversationHistory", [])

        session = get_session(session_id, history)

        scam_detected = detect_scam(message["text"], history)

        if scam_detected:
            reply = agent_reply(session_id, session, message["text"])
            update_session(session_id, message, reply)
            return {"status": "success", "reply": reply}

        return {"status": "ignored", "reply": "Okay"}

    except HTTPException:
        # Let FastAPI handle auth errors properly
        raise

    except Exception as e:
        # 🚨 SAFETY NET: never return empty response
        return {
            "status": "error",
            "reply": "Temporary issue, please retry"
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