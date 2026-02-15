import { useState, useRef, useEffect } from "react";

const API_URL = "http://localhost:8000/honeypot";
const API_KEY = "guvi-hackathon-2026";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [ended, setEnded] = useState(false);
  const sessionId = useRef("demo-session-13");
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
          sessionId: sessionId.current,
          message: scammerMessage,
          conversationHistory: [],
        }),
      });

      const data = await res.json();

      if (data.reply) {
        setMessages((prev) => [
          ...prev,
          { sender: "honeypot", text: data.reply },
        ]);
      }
      if (data.conversation_ended) {
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
    border: "1px solid #ccc",
    padding: "10px",
    marginBottom: "10px",
  },
  scammer: {
    background: "#ffe6e6",
    padding: "8px",
    margin: "5px 0",
    borderRadius: "5px",
  },
  honeypot: {
    background: "#e6f7ff",
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
};

export default App;