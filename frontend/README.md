# Agentic HoneyPot - Intelligence Console

> **AI-Powered Threat Intelligence Platform**  
> Turn scam messages into actionable intelligence through autonomous agent engagement.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![React](https://img.shields.io/badge/React-18.3-61dafb.svg)
![Vite](https://img.shields.io/badge/Vite-5.4-646cff.svg)

---

## 🚀 Overview

Agentic HoneyPot is a sophisticated threat intelligence platform that deploys AI agents to engage scammers in real-time conversations, extract structured intelligence (UPI IDs, phone numbers, phishing links, bank accounts), and build attribution networks.

### Key Features

- **🧠 Adaptive AI Agent** — Context-aware responses that maintain believable conversations
- **🔍 Real-time Entity Extraction** — Auto-detects UPI, phones, URLs, accounts with confidence scoring
- **🎯 Risk Assessment Engine** — Multi-factor threat scoring (0-100) based on entities + tactics
- **🕸️ Threat Graph Visualization** — Interactive network maps showing entity relationships
- **⚙️ API Playground** — Test endpoints with live request/response inspection
- **📊 Session History** — Track completed sessions with full intelligence reports
- **📤 Export Intelligence** — JSON/CSV export for SIEM integration

---

## 🎨 UI/UX Design Philosophy

### Design Principles

1. **Trust Through Clarity** — Technical aesthetic that communicates seriousness and reliability
2. **Progressive Disclosure** — Simple interface that reveals depth on demand
3. **Agentic Feel** — Visual feedback showing AI actively reasoning and extracting intelligence
4. **Data First** — Intelligence panels prioritized over decorative elements
5. **Professional Dark Mode** — Reduced eye strain for SOC analysts during extended sessions

### Color System

- **Accent Green (#5ef1c2)** — Honeypot agent responses, success states, primary actions
- **Amber (#f4b44a)** — Warnings, medium-risk entities, verification tactics
- **Red (#ff6b6b)** — Critical threats, scammer messages, urgency indicators
- **Blue (#5eaaff)** — UPI IDs, info states, secondary actions
- **Purple (#c084fc)** — Bank accounts, advanced features

### Typography

- **Inter** — Primary UI font (clean, professional, excellent readability)
- **JetBrains Mono** — Code blocks, session IDs, entity values (monospace for data)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Landing Page → Console Tabs → Intelligence Views │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓ HTTP POST /honeypot
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI / Python)             │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Scam Detection → Agent Engagement → Intel Extract │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Local Development

### Prerequisites

- **Node.js** 18+ and npm
- Backend API running (see main project README)

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create `.env` file:

```env
VITE_API_BASE=http://localhost:8000
VITE_API_KEY=your-api-key-here
```

### Run Development Server

```bash
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173)

---

## 📦 Production Build

```bash
npm run build
```

Outputs to `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

---

## 🚢 Deployment

### Vercel (Recommended for Frontend)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-repo/agentic-honeypot)

1. **Connect Repository** — Link your GitHub repo
2. **Configure Build**:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. **Add Environment Variables**:
   - `VITE_API_BASE`: Your backend API URL (e.g., `https://your-api.onrender.com`)
   - `VITE_API_KEY`: Your API key
4. **Deploy**

### Other Platforms

| Platform | Config |
|----------|--------|
| **Netlify** | `netlify.toml` included |
| **GitHub Pages** | Build to `dist/`, deploy via Actions |
| **AWS S3 + CloudFront** | Static site hosting |

---

## 🎯 Usage Guide

### 1. Landing Page

- **Hero Section** — Value proposition, stats, primary CTA
- **How It Works** — 6-step visual process flow
- **Features** — Technical capabilities with tags
- **Use Cases** — Target audience personas
- **CTA** — Launch console button

### 2. Live Analysis Tab

**Workflow:**
1. Paste scam SMS/WhatsApp message in composer
2. AI agent responds automatically (200-500ms latency)
3. Watch intelligence extraction in real-time
4. Review risk score (updates live as conversation progresses)
5. Export JSON report when session completes

**Right Sidebar:**
- **Risk Gauge** — Visual 0-100 risk score with breakdown
- **Extracted Intelligence** — Entity cards with confidence levels
- **Tactics Detected** — Behavioral patterns with confidence bars
- **Event Timeline** — Chronological intel extraction log

### 3. Threat Graph Tab

Visualizes entity relationships:
- **Central Node** — Current session
- **Category Nodes** — UPI, Phone, Link, Account
- **Entity Nodes** — Specific extracted values
- **Edges** — Attribution links

Hover for details, click to filter.

### 4. API Playground

Test API requests:
- **Code Examples** — cURL, Python, JavaScript
- **Live Request Editor** — JSON body with validation
- **Response Inspector** — Formatted response with status
- **Schema Docs** — Request/response contracts

### 5. History Tab

View completed sessions:
- Session ID, risk score, message count
- Entities extracted, tactics detected
- Timestamp, export actions

---

## 🔧 Configuration

### API Connection

Update in Settings overlay (⚙️ icon in navbar):

```json
{
  "apiBase": "https://your-backend.com",
  "apiKey": "your-secret-key",
  "sessionId": "custom-session-id"
}
```

### Customization

Edit `src/styles.css` for theme customization:

```css
:root {
  --accent: #5ef1c2;      /* Primary brand color */
  --bg-root: #06080d;     /* Background */
  --text-primary: #ecf0f6;/* Main text */
}
```

---

## 📊 Intelligence Report Schema

Exported JSON structure:

```json
{
  "sessionId": "hp_abc123",
  "timestamp": "2026-02-10T14:30:00Z",
  "riskScore": 87,
  "riskLevel": "CRITICAL",
  "extractedIntelligence": {
    "upiIds": ["scammer@paytm"],
    "phoneNumbers": ["+919876543210"],
    "phishingLinks": ["https://fake-bank.com"],
    "bankAccounts": ["1234567890123456"]
  },
  "tacticsDetected": ["Urgency", "Verification / KYC", "Payment Push"],
  "totalMessages": 14,
  "conversation": [
    {
      "role": "scammer",
      "text": "Your account is blocked...",
      "time": "2026-02-10T14:28:30Z"
    }
  ]
}
```

---

## 🎓 Best Practices

### For SOC Analysts

1. **Session Hygiene** — Click "New Session" after each case to archive history
2. **Export Early** — Download JSON before closing browser (no server persistence yet)
3. **Risk Context** — Risk score is relative; cross-reference with entity types
4. **Tactic Confidence** — Higher confidence bars = more keyword matches

### For Developers

1. **API Rate Limits** — Backend may throttle concurrent requests
2. **Session IDs** — Use unique IDs per conversation thread
3. **Error Handling** — Check response status; retry on 5xx errors
4. **CORS** — Backend must allow your frontend origin

---

## 🔐 Security Considerations

- **API Keys** — Never commit `.env` to version control
- **Data Handling** — Intelligence may contain sensitive scammer data; comply with data protection laws
- **Deployment** — Use HTTPS in production; enable CSP headers
- **Backend Auth** — Always validate `x-api-key` header on backend

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- **Persistence** — Add Redis/PostgreSQL session storage
- **Enrichment** — Integrate VirusTotal, Shodan, WHOIS APIs for URL/phone enrichment
- **ML Models** — Train custom transformers for better tactic detection
- **Visualization** — 3D force-directed graphs, heat maps, timeseries analytics
- **Export Formats** — PDF reports, STIX/TAXII threat feeds

---

## 📝 License

MIT License — See [LICENSE](../LICENSE) for details.

---

## 🙏 Acknowledgments

Built for **GUVI Hackathon 2026** — International-level cybersecurity challenge.

**Tech Stack:**
- React 18.3 + Vite 5.4
- Canvas API (threat graphs)
- FastAPI backend (Python)
- Inter + JetBrains Mono fonts

---

## 📞 Support

- **Issues** — Open GitHub issue with `[Frontend]` tag
- **Discussions** — Use GitHub Discussions for questions
- **Security** — Email security@yourproject.com for vulnerabilities

---

**Built with ❤️ by the Agentic HoneyPot Team**
