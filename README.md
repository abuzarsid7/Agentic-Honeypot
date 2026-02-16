# 🛡️ Agentic Honeypot
### An Intelligent Scam Engagement & Intelligence Extraction System

Agentic Honeypot is an AI-powered defensive system designed to **engage scammers in conversation**, extract actionable intelligence, and prevent real victims from being targeted.

Instead of blocking scammers instantly, this system intelligently:
- Detects scam intent
- Engages naturally
- Extracts intelligence (links, payment info, case IDs, etc.)
- Defends against bot accusations
- Logs structured telemetry
- Stores conversation state in Redis

---

## 🚀 Why This Project?

Online scams are increasing rapidly:
- Phishing links
- Fake cybercrime cases
- Reward scams
- WhatsApp redirects
- Shortened URLs
- Obfuscated messages

Traditional systems block scams.

**Agentic Honeypot traps them.**

---

## 🧠 How It Works (Architecture Overview)
Incoming Scam Message  
↓  
Normalizer Layer  
↓  
Intent Detector  
↓  
Defense Layer (if bot accusation)  
↓  
LLM Response Engine  
↓  
Intelligence Extractor  
↓  
Memory + Redis Storage  
↓  
Telemetry Logging  
### Core Layers

- **Normalizer** → Cleans & decodes obfuscated text
- **Detector** → Detects scam intent patterns
- **Dialogue Strategy** → Controls conversational flow
- **Defense Engine** → Handles "Are you a bot?" accusations
- **LLM Engine** → Generates human-like responses
- **Intelligence Extractor** → Extracts:
  - URLs (including shortened)
  - Case IDs
  - Phone numbers
  - Payment info
- **Memory Layer** → Maintains session state in Redis
- **Telemetry** → Logs system events and risk levels

---

## 🏗️ Tech Stack

- **FastAPI** – Backend API
- **Uvicorn** – ASGI Server
- **Redis** – Session memory storage
- **Requests** – External calls
- **Python Dotenv** – Environment management
- **LLM Provider** – Groq / OpenAI compatible

From `requirements.txt`:
fastapi
uvicorn
requests
redis  
python-dotenv

---

## 📂 Project Structure
# 📂 Project Architecture

## 🧠 Core Agent Layer
- **agent.py** → Core agent orchestration  
- **dialogue_strategy.py** → Conversation flow logic  
- **defense.py** → Bot accusation defense layer  

---

## 🚀 Application Entry
- **main.py** → FastAPI entrypoint  
- **callback.py** → External callback handler  

---

## 🔎 Processing & Detection
- **normalizer.py** → Message cleaning & decoding  
- **detector.py** → Scam detection logic  
- **intelligence.py** → Data extraction engine  

---

## 🗄️ Memory & Storage
- **memory.py** → Redis memory management  
- **redis_client.py** → Redis connection layer  

---

## 📊 Observability
- **telemetry.py** → Logging & tracking  

---

## 🤖 AI Integration
- **llm_engine.py** → LLM provider wrapper  

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/agentic-honeypot.git
cd agentic-honeypot
```
## 2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
---
## 3️⃣ Install dependencies
pip install -r requirements.txt

### Configure by putting keys in .env

## ▶️ Running the Server
python main.py
