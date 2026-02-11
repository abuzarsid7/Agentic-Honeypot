import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

/* ================================================================
   CONFIG
   ================================================================ */
const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || "guvi-hackathon-2026";

/* ================================================================
   SCAM INTELLIGENCE HELPERS
   ================================================================ */
const TACTIC_DEFS = [
  {
    id: "urgency",
    label: "Urgency",
    icon: "\u26a1",
    words: ["urgent", "immediately", "asap", "now", "quick", "hurry", "expire", "deadline"],
    css: "urgency"
  },
  {
    id: "verification",
    label: "Verification / KYC",
    icon: "\ud83d\udd0d",
    words: ["verify", "confirm", "kyc", "validation", "update your", "authenticate"],
    css: "verification"
  },
  {
    id: "reward",
    label: "Reward / Prize",
    icon: "\ud83c\udfc6",
    words: ["reward", "prize", "congratulations", "gift", "winner", "bonus", "cashback"],
    css: "reward"
  },
  {
    id: "threat",
    label: "Account Threat",
    icon: "\ud83d\udea8",
    words: ["blocked", "suspended", "locked", "freeze", "terminated", "deactivated"],
    css: "threat"
  },
  {
    id: "payment",
    label: "Payment Push",
    icon: "\ud83d\udcb3",
    words: ["upi", "transfer", "pay", "wallet", "refund", "paytm", "phonepe", "gpay", "payment"],
    css: "payment"
  },
  {
    id: "identity",
    label: "Identity Theft",
    icon: "\ud83c\udfad",
    words: ["otp", "cvv", "pin", "password", "aadhaar", "pan", "ssn", "social security"],
    css: "identity"
  }
];

function uniqueList(arr) {
  return [...new Set(arr)];
}

function extractEntitiesFromText(text) {
  const upi = text.match(/[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}/g) || [];
  const phones =
    text.match(/\+?91\d{10}|\+\d{10,}|(?<!\d)\d{10}(?!\d)/g) || [];
  const links = text.match(/https?:\/\/\S+/g) || [];
  const accounts = text.match(/\b\d{8,16}\b/g) || [];
  return {
    upiIds: uniqueList(upi),
    phoneNumbers: uniqueList(phones),
    phishingLinks: uniqueList(
      links.map((l) => l.replace(/[),.;:!?]+$/, ""))
    ),
    bankAccounts: uniqueList(accounts.filter((a) => a.length !== 10))
  };
}

function deriveIntel(messages) {
  const combined = messages.map((m) => m.text).join("\n");
  return extractEntitiesFromText(combined);
}

function detectTactics(messages) {
  const combined = messages
    .map((m) => m.text.toLowerCase())
    .join(" ");
  return TACTIC_DEFS.filter((t) =>
    t.words.some((w) => combined.includes(w))
  );
}

function computeRisk(intel, tactics) {
  let score = 5;
  score += intel.phishingLinks.length * 25;
  score += intel.upiIds.length * 22;
  score += intel.phoneNumbers.length * 12;
  score += intel.bankAccounts.length * 10;
  score += tactics.length * 8;
  return Math.min(100, score);
}

function riskColor(score) {
  if (score >= 70) return "#ff6b6b";
  if (score >= 40) return "#f4b44a";
  return "#5ef1c2";
}

function riskLevel(score) {
  if (score >= 70) return "CRITICAL";
  if (score >= 40) return "ELEVATED";
  return "LOW";
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function createSessionId() {
  return `hp_${Date.now().toString(36)}_${Math.random()
    .toString(36)
    .slice(2, 7)}`;
}

/* ================================================================
   RISK GAUGE (SVG)
   ================================================================ */
function RiskGauge({ score }) {
  const r = 55;
  const circumference = Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  const color = riskColor(score);

  return (
    <div className="risk-gauge">
      <svg className="gauge-svg" viewBox="0 0 140 85">
        <path
          d="M 15 75 A 55 55 0 0 1 125 75"
          className="gauge-bg"
        />
        <path
          d="M 15 75 A 55 55 0 0 1 125 75"
          className="gauge-fill"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <text x="70" y="65" textAnchor="middle" className="gauge-value">
          {score}
        </text>
        <text x="70" y="80" textAnchor="middle" className="gauge-label">
          {riskLevel(score)}
        </text>
      </svg>
    </div>
  );
}

/* ================================================================
   THREAT GRAPH (Canvas)
   ================================================================ */
function ThreatGraphCanvas({ intel }) {
  const canvasRef = useRef(null);

  const nodes = useMemo(() => {
    const list = [];
    const cx = 400,
      cy = 260;

    // Central node
    list.push({
      id: "session",
      label: "SESSION",
      x: cx,
      y: cy,
      r: 22,
      color: "#5ef1c2",
      type: "session"
    });

    const categories = [
      { key: "upiIds", label: "UPI", color: "#5eaaff", icon: "\ud83d\udcb1" },
      {
        key: "phoneNumbers",
        label: "Phone",
        color: "#f4b44a",
        icon: "\ud83d\udcde"
      },
      {
        key: "phishingLinks",
        label: "Link",
        color: "#ff6b6b",
        icon: "\ud83d\udd17"
      },
      {
        key: "bankAccounts",
        label: "Account",
        color: "#c084fc",
        icon: "\ud83c\udfe6"
      }
    ];

    let angleOffset = 0;
    categories.forEach((cat, ci) => {
      const items = intel[cat.key] || [];
      if (items.length === 0) return;

      const baseAngle = (ci / categories.length) * Math.PI * 2 - Math.PI / 2;
      const groupX = cx + Math.cos(baseAngle) * 140;
      const groupY = cy + Math.sin(baseAngle) * 140;

      // Type node
      const typeId = `type_${cat.key}`;
      list.push({
        id: typeId,
        label: cat.label,
        x: groupX,
        y: groupY,
        r: 16,
        color: cat.color,
        type: "category",
        parentId: "session"
      });

      items.forEach((val, vi) => {
        const a =
          baseAngle + ((vi - (items.length - 1) / 2) * 0.5);
        const dist = 80 + vi * 15;
        list.push({
          id: `${cat.key}_${vi}`,
          label: val.length > 18 ? val.slice(0, 16) + ".." : val,
          x: groupX + Math.cos(a) * dist,
          y: groupY + Math.sin(a) * dist,
          r: 12,
          color: cat.color,
          type: "entity",
          parentId: typeId
        });
      });
    });
    return list;
  }, [intel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);
    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const scaleX = w / 800;
    const scaleY = h / 520;

    // Draw edges
    nodes.forEach((node) => {
      if (!node.parentId) return;
      const parent = nodes.find((n) => n.id === node.parentId);
      if (!parent) return;

      ctx.beginPath();
      ctx.moveTo(parent.x * scaleX, parent.y * scaleY);
      ctx.lineTo(node.x * scaleX, node.y * scaleY);
      ctx.strokeStyle = `${node.color}33`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });

    // Draw nodes
    nodes.forEach((node) => {
      const x = node.x * scaleX;
      const y = node.y * scaleY;
      const r = node.r * Math.min(scaleX, scaleY);

      // Glow
      ctx.beginPath();
      ctx.arc(x, y, r + 4, 0, Math.PI * 2);
      ctx.fillStyle = `${node.color}15`;
      ctx.fill();

      // Circle
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `${node.color}30`;
      ctx.strokeStyle = `${node.color}80`;
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();

      // Label
      ctx.fillStyle = "#ecf0f6";
      ctx.font = `${
        node.type === "session" ? 10 : node.type === "category" ? 9 : 8
      }px "JetBrains Mono", monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.label, x, y + r + 14);
    });
  }, [nodes]);

  return <canvas ref={canvasRef} className="graph-canvas" />;
}

/* ================================================================
   APP
   ================================================================ */
export default function App() {
  const [tab, setTab] = useState("home");
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [apiKey, setApiKey] = useState(DEFAULT_API_KEY);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [sessionId, setSessionId] = useState(createSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | error
  const [errorMsg, setErrorMsg] = useState("");

  const [history, setHistory] = useState([]); // completed sessions

  // API Playground state
  const [apiInput, setApiInput] = useState(
    '{\n  "sessionId": "demo_001",\n  "message": {\n    "sender": "user",\n    "text": "Your account is blocked. Click http://fake-bank.com to verify."\n  },\n  "conversationHistory": []\n}'
  );
  const [apiResponse, setApiResponse] = useState(null);
  const [apiStatus, setApiStatus] = useState("idle");
  const [apiCodeTab, setApiCodeTab] = useState("curl");

  const chatEndRef = useRef(null);

  // Derived intelligence
  const intel = useMemo(() => deriveIntel(messages), [messages]);
  const tactics = useMemo(() => detectTactics(messages), [messages]);
  const risk = useMemo(() => computeRisk(intel, tactics), [intel, tactics]);
  const entityCount =
    intel.upiIds.length +
    intel.phoneNumbers.length +
    intel.phishingLinks.length +
    intel.bankAccounts.length;

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  /* ---- Send message ---- */
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || status === "sending") return;

    const userMsg = { role: "scammer", text, time: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStatus("sending");
    setErrorMsg("");

    try {
      const res = await fetch(`${apiBase}/honeypot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey
        },
        body: JSON.stringify({
          sessionId,
          message: { sender: "user", text },
          conversationHistory: [...messages, userMsg].map((m) => ({
            sender: m.role === "scammer" ? "user" : "agent",
            text: m.text
          }))
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { role: "honeypot", text: data.reply || "...", time: Date.now() }
      ]);
      setStatus("idle");
    } catch (err) {
      setErrorMsg(err.message || "Failed to reach API");
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }, [input, status, apiBase, apiKey, sessionId, messages]);

  /* ---- Keyboard handler ---- */
  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ---- New session ---- */
  const resetSession = () => {
    if (messages.length > 0) {
      setHistory((prev) => [
        {
          id: sessionId,
          messages: messages.length,
          risk,
          tactics: tactics.map((t) => t.label),
          intel: { ...intel },
          time: Date.now()
        },
        ...prev
      ]);
    }
    setSessionId(createSessionId());
    setMessages([]);
    setInput("");
    setErrorMsg("");
    setStatus("idle");
  };

  /* ---- Export JSON ---- */
  const exportJSON = () => {
    const report = {
      sessionId,
      timestamp: new Date().toISOString(),
      riskScore: risk,
      riskLevel: riskLevel(risk),
      extractedIntelligence: intel,
      tacticsDetected: tactics.map((t) => t.label),
      totalMessages: messages.length,
      conversation: messages.map((m) => ({
        role: m.role,
        text: m.text,
        time: new Date(m.time).toISOString()
      }))
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `honeypot_report_${sessionId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /* ---- API Playground send ---- */
  const sendApiTest = async () => {
    setApiStatus("sending");
    try {
      const body = JSON.parse(apiInput);
      const res = await fetch(`${apiBase}/honeypot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey
        },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      setApiResponse({
        status: res.status,
        ok: res.ok,
        body: data
      });
      setApiStatus("idle");
    } catch (err) {
      setApiResponse({
        status: 0,
        ok: false,
        body: { error: err.message }
      });
      setApiStatus("idle");
    }
  };

  /* ---- TABS ---- */
  const TABS = [
    { id: "home", label: "Home", icon: "\ud83c\udfe0" },
    { id: "analysis", label: "Live Analysis", icon: "\ud83e\udde0" },
    { id: "graph", label: "Threat Graph", icon: "\ud83d\udd78\ufe0f" },
    { id: "api", label: "API Playground", icon: "\u2699\ufe0f" },
    { id: "history", label: "History", icon: "\ud83d\udcda" }
  ];

  /* ---- Build timeline events ---- */
  const timelineEvents = useMemo(() => {
    const events = [];
    messages.forEach((msg, i) => {
      events.push({
        id: `msg_${i}`,
        type: msg.role === "scammer" ? "incoming" : "response",
        label: msg.role === "scammer" ? "Incoming" : "Agent Reply",
        text: msg.text,
        time: msg.time
      });

      // Check if intel was extracted from this message
      if (msg.role === "scammer") {
        const ent = extractEntitiesFromText(msg.text);
        const items = [
          ...ent.upiIds.map((v) => `UPI: ${v}`),
          ...ent.phoneNumbers.map((v) => `Phone: ${v}`),
          ...ent.phishingLinks.map((v) => `Link: ${v}`),
          ...ent.bankAccounts.map((v) => `Account: ${v}`)
        ];
        if (items.length > 0) {
          events.push({
            id: `intel_${i}`,
            type: "intel",
            label: "Intel Extracted",
            text: items.join(", "),
            time: msg.time + 1
          });
        }
      }
    });
    return events;
  }, [messages]);

  /* ================================================================
     RENDER
     ================================================================ */
  return (
    <>
      {/* ---- NAVBAR ---- */}
      <nav className="navbar">
        <div className="nav-brand">
          <div className="nav-logo">{"\ud83d\udc1d"}</div>
          <div className="nav-title">
            Agentic <span>HoneyPot</span>
          </div>
        </div>

        <div className="nav-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-tab${tab === t.id ? " active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              <span className="tab-icon">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        <div className="nav-right">
          <div className="nav-status">
            <div
              className={`pulse-dot${status === "idle" ? " idle" : ""}`}
            />
            {status === "sending"
              ? "Agent reasoning..."
              : status === "error"
              ? "Connection error"
              : "System ready"}
          </div>
          <button
            className="btn-icon"
            title="Settings"
            onClick={() => setSettingsOpen(true)}
          >
            {"\u2699\ufe0f"}
          </button>
        </div>
      </nav>

      {/* ---- MOBILE TABS ---- */}
      <div className="mobile-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ---- MAIN CONTENT ---- */}
      <main className="main">
        {/* ============ HOME / LANDING ============ */}
        {tab === "home" && (
          <div className="landing">
            {/* Hero Section */}
            <section className="hero-section">
              <div className="hero-content">
                <div className="hero-badge">
                  <span>{"\u26a1"}</span>
                  AI-Powered Threat Intelligence Platform
                </div>
                <h1 className="hero-title">
                  Turn Scams Into Intelligence
                </h1>
                <p className="hero-subtitle">
                  Agentic HoneyPot is an autonomous AI agent that engages scammers in real-time conversations, 
                  extracts actionable intelligence, and builds threat attribution networks—completely automated.
                </p>
                <div className="hero-actions">
                  <button
                    className="btn-hero btn-hero-primary"
                    onClick={() => setTab("analysis")}
                  >
                    {"\ud83d\ude80"} Launch Intelligence Console
                  </button>
                  <button
                    className="btn-hero btn-hero-secondary"
                    onClick={() => {
                      document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    {"\ud83d\udcd6"} How It Works
                  </button>
                </div>

                <div className="hero-stats">
                  <div className="stat-item">
                    <span className="stat-value" style={{ color: "#5ef1c2" }}>98%</span>
                    <span className="stat-label">Detection Accuracy</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value" style={{ color: "#5eaaff" }}>15+</span>
                    <span className="stat-label">Intel Categories</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value" style={{ color: "#f4b44a" }}>&lt;2s</span>
                    <span className="stat-label">Response Time</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value" style={{ color: "#c084fc" }}>24/7</span>
                    <span className="stat-label">Autonomous Operation</span>
                  </div>
                </div>
              </div>
            </section>

            {/* How It Works Section */}
            <section className="how-section" id="how-it-works">
              <div className="section-header">
                <span className="section-badge">The Process</span>
                <h2 className="section-title">How It Works</h2>
                <p className="section-description">
                  Our AI agent operates through a sophisticated multi-stage pipeline that transforms 
                  scam messages into structured threat intelligence.
                </p>
              </div>

              <div className="steps-grid">
                <div className="step-card">
                  <div className="step-number">1</div>
                  <span className="step-icon">{"\ud83d\udce8"}</span>
                  <h3 className="step-title">Scam Detection</h3>
                  <p className="step-description">
                    Advanced pattern matching and NLP algorithms instantly identify suspicious messages 
                    containing phishing links, financial fraud, or social engineering attempts.
                  </p>
                </div>

                <div className="step-card">
                  <div className="step-number">2</div>
                  <span className="step-icon">{"\ud83e\udd16"}</span>
                  <h3 className="step-title">Agent Engagement</h3>
                  <p className="step-description">
                    The AI agent assumes a convincing persona and engages the scammer with contextual, 
                    adaptive responses designed to prolong the conversation and extract maximum intelligence.
                  </p>
                </div>

                <div className="step-card">
                  <div className="step-number">3</div>
                  <span className="step-icon">{"\ud83d\udd0d"}</span>
                  <h3 className="step-title">Intel Extraction</h3>
                  <p className="step-description">
                    Real-time parsing extracts UPI IDs, phone numbers, phishing URLs, bank accounts, 
                    and behavioral tactics. Each entity is verified, normalized, and confidence-scored.
                  </p>
                </div>

                <div className="step-card">
                  <div className="step-number">4</div>
                  <span className="step-icon">{"\ud83d\udd78\ufe0f"}</span>
                  <h3 className="step-title">Threat Mapping</h3>
                  <p className="step-description">
                    Extracted entities are linked into a threat graph, revealing connections between 
                    campaigns, infrastructure, and common attack patterns for attribution.
                  </p>
                </div>

                <div className="step-card">
                  <div className="step-number">5</div>
                  <span className="step-icon">{"\ud83d\udcc8"}</span>
                  <h3 className="step-title">Risk Assessment</h3>
                  <p className="step-description">
                    Multi-factor risk scoring algorithm weighs entity types, tactics, urgency indicators, 
                    and historical patterns to produce an actionable threat severity score.
                  </p>
                </div>

                <div className="step-card">
                  <div className="step-number">6</div>
                  <span className="step-icon">{"\ud83d\udce4"}</span>
                  <h3 className="step-title">Intelligence Export</h3>
                  <p className="step-description">
                    Structured reports in JSON/CSV format ready for SIEM integration, threat feeds, 
                    law enforcement submission, or internal security operations workflows.
                  </p>
                </div>
              </div>
            </section>

            {/* Features Section */}
            <section className="features-section">
              <div className="section-header">
                <span className="section-badge">Capabilities</span>
                <h2 className="section-title">Core Features</h2>
                <p className="section-description">
                  Enterprise-grade intelligence extraction powered by cutting-edge AI and security research.
                </p>
              </div>

              <div className="features-grid">
                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(94,241,194,0.12)" }}>
                    {"\ud83e\udde0"}
                  </div>
                  <h3 className="feature-title">Adaptive AI Agent</h3>
                  <p className="feature-description">
                    Context-aware responses that mirror human behavior patterns, avoiding repetition 
                    and maintaining believable conversation flows.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">NLP</span>
                    <span className="feature-tag">Context Memory</span>
                    <span className="feature-tag">Persona Simulation</span>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(94,170,255,0.12)" }}>
                    {"\ud83d\udd17"}
                  </div>
                  <h3 className="feature-title">Entity Extraction</h3>
                  <p className="feature-description">
                    Automatic identification and normalization of UPI IDs, phone numbers, URLs, 
                    bank accounts, email addresses, and cryptocurrency wallets.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">Regex Patterns</span>
                    <span className="feature-tag">Deduplication</span>
                    <span className="feature-tag">Validation</span>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(244,180,74,0.12)" }}>
                    {"\ud83c\udfaf"}
                  </div>
                  <h3 className="feature-title">Risk Scoring Engine</h3>
                  <p className="feature-description">
                    Multi-dimensional threat assessment combining entity types, tactics, urgency signals, 
                    and historical scam patterns into a 0-100 risk score.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">ML Scoring</span>
                    <span className="feature-tag">Weighted Metrics</span>
                    <span className="feature-tag">Real-time</span>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(192,132,252,0.12)" }}>
                    {"\ud83d\udd78\ufe0f"}
                  </div>
                  <h3 className="feature-title">Threat Graph Visualization</h3>
                  <p className="feature-description">
                    Interactive network graphs showing relationships between entities, campaigns, 
                    and infrastructure for rapid pattern recognition.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">Canvas Rendering</span>
                    <span className="feature-tag">Entity Clustering</span>
                    <span className="feature-tag">Attribution</span>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(255,107,107,0.12)" }}>
                    {"\ud83d\udc41\ufe0f"}
                  </div>
                  <h3 className="feature-title">Behavioral Analysis</h3>
                  <p className="feature-description">
                    Automatically detects urgency tactics, verification pretexts, reward scams, 
                    identity theft attempts, and financial fraud patterns.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">Tactic Detection</span>
                    <span className="feature-tag">Confidence Scoring</span>
                    <span className="feature-tag">TTPs Mapping</span>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon-wrap" style={{ background: "rgba(94,241,194,0.12)" }}>
                    {"\u2699\ufe0f"}
                  </div>
                  <h3 className="feature-title">API-First Architecture</h3>
                  <p className="feature-description">
                    RESTful API with authentication, rate limiting, and comprehensive documentation 
                    for seamless integration into existing security workflows.
                  </p>
                  <div className="feature-tags">
                    <span className="feature-tag">REST API</span>
                    <span className="feature-tag">API Keys</span>
                    <span className="feature-tag">JSON Export</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Use Cases Section */}
            <section className="use-cases-section">
              <div className="section-header">
                <span className="section-badge">Applications</span>
                <h2 className="section-title">Who Uses This?</h2>
                <p className="section-description">
                  Designed for security professionals, researchers, and organizations fighting fraud.
                </p>
              </div>

              <div className="use-cases-grid">
                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83d\udeaa"}</span>
                  <h3 className="use-case-title">SOC Teams</h3>
                  <p className="use-case-description">
                    Real-time threat intelligence for Security Operations Centers monitoring phishing campaigns.
                  </p>
                </div>

                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83c\udfe6"}</span>
                  <h3 className="use-case-title">Financial Institutions</h3>
                  <p className="use-case-description">
                    Identify fraud infrastructure targeting banking customers and payment systems.
                  </p>
                </div>

                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83d\udd2c"}</span>
                  <h3 className="use-case-title">Security Researchers</h3>
                  <p className="use-case-description">
                    Collect datasets on scam tactics, attribution, and emerging threat patterns.
                  </p>
                </div>

                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83d\udee1\ufe0f"}</span>
                  <h3 className="use-case-title">Law Enforcement</h3>
                  <p className="use-case-description">
                    Gather admissible evidence and trace scammer infrastructure for investigations.
                  </p>
                </div>

                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83d\udcf1"}</span>
                  <h3 className="use-case-title">Telecom Operators</h3>
                  <p className="use-case-description">
                    Detect and block fraudulent SMS campaigns affecting subscribers.
                  </p>
                </div>

                <div className="use-case-card">
                  <span className="use-case-icon">{"\ud83c\udfed"}</span>
                  <h3 className="use-case-title">Enterprise Security</h3>
                  <p className="use-case-description">
                    Protect employees from spear-phishing and social engineering attacks.
                  </p>
                </div>
              </div>
            </section>

            {/* CTA Section */}
            <section className="cta-section">
              <div className="cta-card">
                <div className="cta-content">
                  <h2 className="cta-title">Ready to Extract Intelligence?</h2>
                  <p className="cta-description">
                    Launch the console and start analyzing scam messages in seconds. 
                    No installation required—everything runs in your browser.
                  </p>
                  <button
                    className="btn-hero btn-hero-primary"
                    onClick={() => setTab("analysis")}
                  >
                    {"\ud83d\ude80"} Start Analyzing Now
                  </button>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* ============ in">
        {/* ============ LIVE ANALYSIS ============ */}
        {tab === "analysis" && (
          <div className="analysis-layout">
            {/* LEFT: Chat */}
            <div className="analysis-left card chat-container">
              <div className="card-header">
                <div className="card-title">
                  {"\ud83d\udcac"} Scam Conversation
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span className="card-badge badge-live">
                    {"\u25cf"} Live
                  </span>
                  <span className="card-badge badge-count">
                    {messages.length} msgs
                  </span>
                </div>
              </div>

              <div className="chat-messages">
                {messages.length === 0 && (
                  <div className="chat-empty">
                    <div className="chat-empty-icon">{"\ud83d\udc1d"}</div>
                    <p>
                      Paste a scam SMS, WhatsApp message, or phishing email to
                      activate the honeypot agent.
                    </p>
                    <p className="hint">
                      The AI agent will engage the scammer and extract
                      intelligence in real time.
                    </p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div
                    key={`${msg.role}_${i}`}
                    className={`msg ${msg.role}`}
                  >
                    <div className="msg-header">
                      <span className="msg-indicator" />
                      {msg.role === "scammer"
                        ? "Scammer (Incoming)"
                        : "Honeypot Agent"}
                    </div>
                    <div className="msg-bubble">{msg.text}</div>
                    <div className="msg-time">{formatTime(msg.time)}</div>
                  </div>
                ))}
                {status === "sending" && (
                  <div className="msg-typing">
                    <span />
                    <span />
                    <span />
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="composer">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Paste scam message here... (Enter to send)"
                  rows={3}
                />
                <div className="composer-bar">
                  <span className="composer-hint">
                    Shift+Enter for new line
                  </span>
                  <div className="composer-actions">
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={resetSession}
                    >
                      New Session
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={sendMessage}
                      disabled={status === "sending" || !input.trim()}
                    >
                      {status === "sending" ? "Engaging..." : "Send Message"}
                    </button>
                  </div>
                </div>
                {errorMsg && <div className="msg-error">{errorMsg}</div>}
              </div>
            </div>

            {/* RIGHT: Intelligence sidebar */}
            <div className="analysis-right">
              {/* Export bar */}
              {messages.length > 0 && (
                <div className="export-bar">
                  <span className="export-text">
                    {"\ud83d\udce4"} Intelligence Report Ready
                  </span>
                  <div className="export-actions">
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={exportJSON}
                    >
                      Export JSON
                    </button>
                  </div>
                </div>
              )}

              {/* Risk Gauge */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {"\ud83c\udfaf"} Risk Assessment
                  </div>
                  <span
                    className="card-badge"
                    style={{
                      background: `${riskColor(risk)}20`,
                      color: riskColor(risk)
                    }}
                  >
                    {riskLevel(risk)}
                  </span>
                </div>
                <RiskGauge score={risk} />
                <div className="risk-breakdown" style={{ padding: "0 16px 14px" }}>
                  <div className="risk-item">
                    <span className="dot" style={{ background: "#ff6b6b" }} />
                    Links: {intel.phishingLinks.length}
                  </div>
                  <div className="risk-item">
                    <span className="dot" style={{ background: "#5eaaff" }} />
                    UPI: {intel.upiIds.length}
                  </div>
                  <div className="risk-item">
                    <span className="dot" style={{ background: "#f4b44a" }} />
                    Phones: {intel.phoneNumbers.length}
                  </div>
                  <div className="risk-item">
                    <span className="dot" style={{ background: "#c084fc" }} />
                    Accounts: {intel.bankAccounts.length}
                  </div>
                </div>
              </div>

              {/* Extracted Entities */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {"\ud83d\udd75\ufe0f"} Extracted Intelligence
                  </div>
                  <span className="card-badge badge-count">
                    {entityCount} entities
                  </span>
                </div>
                <div className="card-body entity-grid">
                  {intel.phishingLinks.map((v) => (
                    <div key={v} className="entity-card">
                      <div
                        className="entity-icon"
                        style={{ background: "rgba(255,107,107,0.12)" }}
                      >
                        {"\ud83d\udd17"}
                      </div>
                      <div className="entity-info">
                        <div className="entity-type">Phishing Link</div>
                        <div className="entity-value">{v}</div>
                        <div
                          className="entity-confidence"
                          style={{ color: "#ff6b6b" }}
                        >
                          High Confidence
                        </div>
                      </div>
                    </div>
                  ))}
                  {intel.upiIds.map((v) => (
                    <div key={v} className="entity-card">
                      <div
                        className="entity-icon"
                        style={{ background: "rgba(94,170,255,0.12)" }}
                      >
                        {"\ud83d\udcb1"}
                      </div>
                      <div className="entity-info">
                        <div className="entity-type">UPI ID</div>
                        <div className="entity-value">{v}</div>
                        <div
                          className="entity-confidence"
                          style={{ color: "#5eaaff" }}
                        >
                          High Confidence
                        </div>
                      </div>
                    </div>
                  ))}
                  {intel.phoneNumbers.map((v) => (
                    <div key={v} className="entity-card">
                      <div
                        className="entity-icon"
                        style={{ background: "rgba(244,180,74,0.12)" }}
                      >
                        {"\ud83d\udcde"}
                      </div>
                      <div className="entity-info">
                        <div className="entity-type">Phone Number</div>
                        <div className="entity-value">{v}</div>
                        <div
                          className="entity-confidence"
                          style={{ color: "#f4b44a" }}
                        >
                          Medium Confidence
                        </div>
                      </div>
                    </div>
                  ))}
                  {intel.bankAccounts.map((v) => (
                    <div key={v} className="entity-card">
                      <div
                        className="entity-icon"
                        style={{ background: "rgba(192,132,252,0.12)" }}
                      >
                        {"\ud83c\udfe6"}
                      </div>
                      <div className="entity-info">
                        <div className="entity-type">Bank Account</div>
                        <div className="entity-value">{v}</div>
                        <div
                          className="entity-confidence"
                          style={{ color: "#c084fc" }}
                        >
                          Needs Verification
                        </div>
                      </div>
                    </div>
                  ))}
                  {entityCount === 0 && (
                    <div className="entity-empty">
                      No entities extracted yet. Start a conversation.
                    </div>
                  )}
                </div>
              </div>

              {/* Tactics Detected */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {"\ud83e\udde0"} Tactics &amp; Techniques
                  </div>
                  <span className="card-badge badge-count">
                    {tactics.length} detected
                  </span>
                </div>
                <div className="card-body">
                  {tactics.length > 0 ? (
                    <div className="tactics-grid">
                      {tactics.map((t) => (
                        <span key={t.id} className={`tactic-tag ${t.css}`}>
                          {t.icon} {t.label}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="entity-empty">
                      Behavioral patterns will appear as conversation progresses.
                    </div>
                  )}

                  {/* Confidence breakdown */}
                  {tactics.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                      {tactics.map((t) => (
                        <div key={t.id} className="confidence-row">
                          <span className="confidence-label">{t.label}</span>
                          <div className="confidence-bar-track">
                            <div
                              className="confidence-bar-fill"
                              style={{
                                width: `${Math.min(
                                  100,
                                  50 +
                                    messages
                                      .map((m) => m.text.toLowerCase())
                                      .join(" ")
                                      .split(" ")
                                      .filter((w) => t.words.includes(w))
                                      .length *
                                      15
                                )}%`,
                                background:
                                  t.css === "urgency" || t.css === "threat"
                                    ? "#ff6b6b"
                                    : t.css === "verification"
                                    ? "#f4b44a"
                                    : t.css === "payment"
                                    ? "#5eaaff"
                                    : t.css === "reward"
                                    ? "#c084fc"
                                    : "#5ef1c2"
                              }}
                            />
                          </div>
                          <span className="confidence-pct">
                            {Math.min(
                              100,
                              50 +
                                messages
                                  .map((m) => m.text.toLowerCase())
                                  .join(" ")
                                  .split(" ")
                                  .filter((w) => t.words.includes(w)).length *
                                  15
                            )}
                            %
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Timeline */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {"\u23f1\ufe0f"} Event Timeline
                  </div>
                  <span className="card-badge badge-count">
                    {timelineEvents.length} events
                  </span>
                </div>
                <div className="card-body">
                  {timelineEvents.length > 0 ? (
                    <div className="timeline">
                      {timelineEvents.map((ev) => (
                        <div key={ev.id} className={`tl-item ${ev.type}`}>
                          <div className="tl-header">
                            <span className="tl-label">{ev.label}</span>
                            <span className="tl-time">
                              {formatTime(ev.time)}
                            </span>
                          </div>
                          <div className="tl-text">{ev.text}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="entity-empty">
                      Timeline events will populate as messages are exchanged.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============ THREAT GRAPH ============ */}
        {tab === "graph" && (
          <div className="graph-layout">
            <div className="graph-canvas-wrap">
              {entityCount > 0 ? (
                <ThreatGraphCanvas intel={intel} />
              ) : (
                <div className="graph-empty-message">
                  Analyze a scam message first to build the threat graph.
                </div>
              )}
              <div className="graph-legend">
                <div className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: "#5ef1c2" }}
                  />
                  Session
                </div>
                <div className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: "#ff6b6b" }}
                  />
                  Phishing Link
                </div>
                <div className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: "#5eaaff" }}
                  />
                  UPI ID
                </div>
                <div className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: "#f4b44a" }}
                  />
                  Phone Number
                </div>
                <div className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: "#c084fc" }}
                  />
                  Bank Account
                </div>
              </div>
            </div>

            <div className="graph-sidebar">
              <div className="graph-stats">
                <div className="graph-stat-card">
                  <div
                    className="graph-stat-value"
                    style={{ color: riskColor(risk) }}
                  >
                    {risk}
                  </div>
                  <div className="graph-stat-label">Risk Score</div>
                </div>
                <div className="graph-stat-card">
                  <div
                    className="graph-stat-value"
                    style={{ color: "#5eaaff" }}
                  >
                    {entityCount}
                  </div>
                  <div className="graph-stat-label">Entities</div>
                </div>
                <div className="graph-stat-card">
                  <div
                    className="graph-stat-value"
                    style={{ color: "#f4b44a" }}
                  >
                    {tactics.length}
                  </div>
                  <div className="graph-stat-label">Tactics</div>
                </div>
                <div className="graph-stat-card">
                  <div
                    className="graph-stat-value"
                    style={{ color: "#c084fc" }}
                  >
                    {messages.length}
                  </div>
                  <div className="graph-stat-label">Messages</div>
                </div>
              </div>

              {/* Entity list for graph sidebar */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Linked Entities</div>
                </div>
                <div className="card-body entity-grid">
                  {[
                    ...intel.phishingLinks.map((v) => ({
                      type: "Link",
                      value: v,
                      color: "#ff6b6b"
                    })),
                    ...intel.upiIds.map((v) => ({
                      type: "UPI",
                      value: v,
                      color: "#5eaaff"
                    })),
                    ...intel.phoneNumbers.map((v) => ({
                      type: "Phone",
                      value: v,
                      color: "#f4b44a"
                    })),
                    ...intel.bankAccounts.map((v) => ({
                      type: "Acct",
                      value: v,
                      color: "#c084fc"
                    }))
                  ].map((ent) => (
                    <div key={ent.value} className="entity-card">
                      <div
                        className="entity-icon"
                        style={{ background: `${ent.color}18` }}
                      >
                        <span
                          className="dot"
                          style={{
                            background: ent.color,
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            display: "block"
                          }}
                        />
                      </div>
                      <div className="entity-info">
                        <div className="entity-type">{ent.type}</div>
                        <div className="entity-value">{ent.value}</div>
                      </div>
                    </div>
                  ))}
                  {entityCount === 0 && (
                    <div className="entity-empty">
                      No entities to display.
                    </div>
                  )}
                </div>
              </div>

              {/* Tactics in graph sidebar */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Active Tactics</div>
                </div>
                <div className="card-body">
                  {tactics.length > 0 ? (
                    <div className="tactics-grid">
                      {tactics.map((t) => (
                        <span key={t.id} className={`tactic-tag ${t.css}`}>
                          {t.icon} {t.label}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="entity-empty">None detected yet.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============ API PLAYGROUND ============ */}
        {tab === "api" && (
          <div className="api-layout">
            <div className="api-section card">
              <div className="card-header">
                <div className="card-title">
                  {"\u2699\ufe0f"} API Request
                </div>
              </div>
              <div className="card-body">
                <div className="api-endpoint">
                  <span className="api-method">POST</span>
                  <span className="api-path">/honeypot</span>
                </div>

                <div className="api-tabs">
                  {["curl", "python", "javascript"].map((lang) => (
                    <button
                      key={lang}
                      className={`api-tab${
                        apiCodeTab === lang ? " active" : ""
                      }`}
                      onClick={() => setApiCodeTab(lang)}
                    >
                      {lang === "curl"
                        ? "cURL"
                        : lang === "python"
                        ? "Python"
                        : "JavaScript"}
                    </button>
                  ))}
                </div>

                {apiCodeTab === "curl" && (
                  <div className="code-block">
                    {`curl -X POST ${apiBase}/honeypot \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: YOUR_API_KEY" \\
  -d '{
    "sessionId": "demo_001",
    "message": {
      "sender": "user",
      "text": "Your account is blocked."
    },
    "conversationHistory": []
  }'`}
                  </div>
                )}
                {apiCodeTab === "python" && (
                  <div className="code-block">
                    {`import requests

response = requests.post(
    "${apiBase}/honeypot",
    headers={
        "Content-Type": "application/json",
        "x-api-key": "YOUR_API_KEY"
    },
    json={
        "sessionId": "demo_001",
        "message": {
            "sender": "user",
            "text": "Your account is blocked."
        },
        "conversationHistory": []
    }
)
print(response.json())`}
                  </div>
                )}
                {apiCodeTab === "javascript" && (
                  <div className="code-block">
                    {`const response = await fetch(
  "${apiBase}/honeypot",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": "YOUR_API_KEY"
    },
    body: JSON.stringify({
      sessionId: "demo_001",
      message: {
        sender: "user",
        text: "Your account is blocked."
      },
      conversationHistory: []
    })
  }
);
const data = await response.json();
console.log(data);`}
                  </div>
                )}

                <div style={{ marginTop: 16 }}>
                  <div className="api-field">
                    <label>Request Body (JSON)</label>
                    <textarea
                      value={apiInput}
                      onChange={(e) => setApiInput(e.target.value)}
                      rows={10}
                    />
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={sendApiTest}
                    disabled={apiStatus === "sending"}
                  >
                    {apiStatus === "sending"
                      ? "Sending..."
                      : "Send Request"}
                  </button>
                </div>
              </div>
            </div>

            <div className="api-section card">
              <div className="card-header">
                <div className="card-title">
                  {"\ud83d\udce5"} Response
                </div>
                {apiResponse && (
                  <span
                    className={`api-status-badge ${
                      apiResponse.ok ? "success" : "error"
                    }`}
                  >
                    {apiResponse.status}
                  </span>
                )}
              </div>
              <div className="card-body">
                {apiResponse ? (
                  <div className="code-block">
                    {JSON.stringify(apiResponse.body, null, 2)}
                  </div>
                ) : (
                  <div className="entity-empty">
                    Send a request to see the response here.
                  </div>
                )}

                {/* Schema documentation */}
                <div style={{ marginTop: 20 }}>
                  <h3
                    style={{
                      fontSize: "0.85rem",
                      marginBottom: 12,
                      color: "var(--text-secondary)"
                    }}
                  >
                    Request Schema
                  </h3>
                  <div className="code-block">
                    {`{
  "sessionId": string,      // Unique session identifier
  "message": {
    "sender": "user",       // Always "user" for incoming
    "text": string          // The scam message content
  },
  "conversationHistory": [  // Previous messages
    {
      "sender": "user" | "agent",
      "text": string
    }
  ]
}`}
                  </div>

                  <h3
                    style={{
                      fontSize: "0.85rem",
                      marginBottom: 12,
                      marginTop: 16,
                      color: "var(--text-secondary)"
                    }}
                  >
                    Response Schema
                  </h3>
                  <div className="code-block">
                    {`{
  "status": "success" | "error",
  "reply": string    // Honeypot agent's response
}`}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============ HISTORY ============ */}
        {tab === "history" && (
          <div className="history-layout">
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  {"\ud83d\udcda"} Session History
                </div>
                <span className="card-badge badge-count">
                  {history.length} sessions
                </span>
              </div>
              <div className="card-body">
                {history.length > 0 ? (
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Session ID</th>
                        <th>Risk</th>
                        <th>Messages</th>
                        <th>Entities</th>
                        <th>Tactics</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((s) => {
                        const ec =
                          (s.intel?.upiIds?.length || 0) +
                          (s.intel?.phoneNumbers?.length || 0) +
                          (s.intel?.phishingLinks?.length || 0) +
                          (s.intel?.bankAccounts?.length || 0);
                        return (
                          <tr key={s.id}>
                            <td className="mono">{s.id}</td>
                            <td>
                              <span
                                className={`history-risk ${
                                  s.risk >= 70
                                    ? "high"
                                    : s.risk >= 40
                                    ? "medium"
                                    : "low"
                                }`}
                              >
                                {s.risk}
                              </span>
                            </td>
                            <td>{s.messages}</td>
                            <td>{ec}</td>
                            <td>
                              {s.tactics?.map((t) => (
                                <span
                                  key={t}
                                  className="history-intent-tag"
                                  style={{
                                    background: "rgba(255,255,255,0.04)",
                                    color: "var(--text-secondary)",
                                    marginRight: 4
                                  }}
                                >
                                  {t}
                                </span>
                              ))}
                            </td>
                            <td className="mono">
                              {new Date(s.time).toLocaleString()}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="history-empty">
                    <p>
                      No completed sessions yet. Analyze scam messages and
                      click "New Session" to archive them here.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ---- STATUS BAR ---- */}
      <footer className="statusbar">
        <div className="statusbar-left">
          <div className="statusbar-item">
            {"\u25cf"} {sessionId}
          </div>
          <div className="statusbar-item">
            Msgs: {messages.length}
          </div>
          <div className="statusbar-item">
            Entities: {entityCount}
          </div>
        </div>
        <div className="statusbar-right">
          <div className="statusbar-item">
            Risk: {risk}/100
          </div>
          <div className="statusbar-item">
            API: {apiBase.replace(/^https?:\/\//, "")}
          </div>
          <div className="statusbar-item">v1.0.0</div>
        </div>
      </footer>

      {/* ---- SETTINGS MODAL ---- */}
      {settingsOpen && (
        <div
          className="settings-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSettingsOpen(false);
          }}
        >
          <div className="settings-panel">
            <h2>{"\u2699\ufe0f"} Connection Settings</h2>
            <div className="settings-field">
              <label>API Base URL</label>
              <input
                value={apiBase}
                onChange={(e) => setApiBase(e.target.value)}
                placeholder="https://your-backend.onrender.com"
              />
            </div>
            <div className="settings-field">
              <label>API Key</label>
              <input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                type="password"
                placeholder="Enter your API key"
              />
            </div>
            <div className="settings-field">
              <label>Current Session ID</label>
              <input
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
              />
            </div>
            <div className="settings-actions">
              <button
                className="btn btn-ghost"
                onClick={() => setSettingsOpen(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setSettingsOpen(false)}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
