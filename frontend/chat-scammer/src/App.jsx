import { useState, useRef, useEffect } from "react";

const API_URL = "http://localhost:8000/honeypot";
const API_KEY = "guvi-hackathon-2026";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [ended, setEnded] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const chatRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim() || ended) return;

    const scammerMessage = {
      sender: "scammer",
      text: input,
    };

    setMessages((prev) => [...prev, scammerMessage]);
    setInput("");

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-KEY": API_KEY,
        },
        body: JSON.stringify({
          // Send existing sessionId on follow-up turns; omit on first turn
          // so the backend auto-generates one and returns it.
          ...(sessionId ? { sessionId } : {}),
          message: scammerMessage,
          conversationHistory: [],
        }),
      });

      const data = await res.json();

      // Capture the sessionId returned by the backend on every response
      if (data.sessionId) {
        setSessionId(data.sessionId);
      }

      if (data.reply) {
        setMessages((prev) => [
          ...prev,
          { sender: "honeypot", text: data.reply },
        ]);
      }
      if (data.conversationEnded || data.status === "ended") {
        setEnded(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    chatRef.current?.scrollTo(0, chatRef.current.scrollHeight);
  }, [messages]);

  return (
    <div style={styles.container}>
      <h2>Agentic Honeypot Demo</h2>

      {sessionId && (
        <div style={styles.sessionBadge}>
          <span style={styles.sessionLabel}>Session ID:</span>
          <code style={styles.sessionValue}>{sessionId}</code>
        </div>
      )}

      <div style={styles.chat} ref={chatRef}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={
              msg.sender === "scammer"
                ? styles.scammer
                : styles.honeypot
            }
          >
            <strong>{msg.sender}:</strong> {msg.text}
          </div>
        ))}
      </div>

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={ended ? "Conversation ended" : "Type scammer message..."}
          disabled={ended}
        />
        <button style={styles.button} onClick={sendMessage} disabled={ended}>
          Send
        </button>
      </div>
      {ended && <p style={{ color: "green", textAlign: "center" }}>Conversation closed by honeypot agent.</p>}
    </div>
  );
}

const styles = {
  container: {
    width: "600px",
    margin: "40px auto",
    fontFamily: "sans-serif",
  },
  chat: {
    height: "400px",
    overflowY: "auto",
    border: "1px solid #fff",
    padding: "10px",
    marginBottom: "10px",
  },
  scammer: {
    background: "#00008B",
    padding: "8px",
    margin: "5px 0",
    borderRadius: "5px",
  },
  honeypot: {
    background: "#08b1ff",
    padding: "8px",
    margin: "5px 0",
    borderRadius: "5px",
  },
  inputRow: {
    display: "flex",
  },
  input: {
    flex: 1,
    padding: "8px",
  },
  button: {
    padding: "8px 16px",
  },
  sessionBadge: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "#1a1a2e",
    border: "1px solid #444",
    borderRadius: "5px",
    padding: "6px 12px",
    marginBottom: "10px",
    fontSize: "12px",
  },
  sessionLabel: {
    color: "#aaa",
    fontWeight: "bold",
    whiteSpace: "nowrap",
  },
  sessionValue: {
    color: "#08b1ff",
    wordBreak: "break-all",
  },
};

export default App;