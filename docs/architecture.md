# Agentic Honeypot — Architecture

## Overview

The Agentic Honeypot is a FastAPI backend that impersonates a confused, vulnerable civilian to keep scammers engaged as long as possible while systematically extracting their operational intelligence (UPI IDs, phone numbers, phishing links, bank accounts, names, email addresses, case/reference numbers, etc.). At the end of a session the full intelligence bundle is submitted to a reporting API.

The system is built around three pillars:

1. **Detection** — Multi-signal scoring determines whether an incoming message is a scam attempt.
2. **Dialogue strategy** — A state machine drives the conversation through a deliberate sequence of probing states to maximise intelligence yield.
3. **Extraction** — A hybrid pipeline (regex + advanced pattern matching + LLM) pulls structured artefacts out of every message.

---

## High-Level Request Flow

```
Scammer message
      │
      ▼
┌─────────────┐    API Key     ┌──────────────────────────────────────────────────┐
│  POST       │◄── Header ────►│                  main.py                         │
│ /honeypot   │                │  1. Resolve / generate sessionId                 │
└─────────────┘                │  2. Load session from Redis (memory.py)          │
                               │  3. detect_scam_detailed()  ← detector.py        │
                               │  4. agent_reply()           ← agent.py           │
                               │  5. Accumulate red flags, save session            │
                               │  6. Return JSON response                          │
                               └──────────────────────────────────────────────────┘
```

### Per-turn pipeline inside `agent_reply` (agent.py)

```
scammer_text
     │
     ├─► extract_intel()          ← intelligence.py   (regex + LLM extraction)
     │
     ├─► detect scam type         ← llm_engine.py     (narrative classification)
     │
     ├─► defend_against_bot_accusation()  ← defense.py
     │       │
     │       ├── Bot accusation detected → return canned human-like defence reply
     │       └── No accusation          → continue to dialogue strategy ↓
     │
     ├─► execute_strategy()       ← dialogue_strategy.py
     │       │
     │       ├── get_next_state() → determine next conversation state
     │       └── generate reply   → LLM-crafted / template response for that state
     │
     ├─► infer_asked_field()      ← track which fields have been probed
     │
     ├─► append to history, persist to Redis
     │
     ├─► maybe_finish()           ← only fires at 50-message ceiling
     │       └── if True → send_final_result() → POST to GUVI reporting API
     │
     └─► save_session()           ← memory.py / Redis
```

---

## Component Map

| File | Role |
|---|---|
| `main.py` | FastAPI app, `/honeypot` endpoint, request orchestration, response building |
| `agent.py` | Per-turn orchestrator; calls extraction, defence, strategy, persistence |
| `dialogue_strategy.py` | State machine, state configs, transition logic, LLM reply generation |
| `intelligence.py` | Hybrid intel extraction (regex, obfuscation patterns, LLM), scoring, pattern detection |
| `detector.py` | Scam detection — multi-signal weighted scorer + red flag extractor |
| `llm_engine.py` | Centralised LLM client (Groq / OpenAI), intent classification, TTL cache |
| `defense.py` | Bot-accusation detection and human-like deflection responses |
| `memory.py` | Session CRUD via Redis, local in-process cache |
| `normalizer.py` | Unicode normalisation, homoglyph substitution, whitespace cleanup |
| `telemetry.py` | Request timing, detection counters, in-memory metrics |
| `callback.py` | Final result submission to `hackathon.guvi.in` API |
| `redis_client.py` | Redis connection singleton |

---

## State Machine (dialogue_strategy.py)

The conversation progresses through eight states. Each state has a **goal**, a set of **extraction targets**, a pool of **response templates**, and a **max_turns** budget.

```
                ┌──────┐
     start ────►│ INIT │  max_turns=2
                └──┬───┘
                   │ always
                   ▼
          ┌──────────────┐
          │ PROBE_REASON │  max_turns=5
          │  names, caseIds, phones, emails
          └──────┬───────┘
                 │
       ┌─────────┼──────────┐
       │payment  │link      │default
       ▼         ▼          ▼
┌───────────┐ ┌──────────┐ ┌───────┐
│PROBE_PAYMENT│ │PROBE_LINK│ │ STALL │
│  UPI, acct, │ │ URLs,    │ │phones,│
│  IFSC codes │ │ emails   │ │names  │
│  max=6      │ │ max=5    │ │max=4  │
└─────┬───────┘ └────┬─────┘ └──┬────┘
      └──────────────┴──────────┘
                     │
                     ▼
           ┌─────────────────┐
           │ CONFIRM_DETAILS │  max_turns=4
           │  emails, caseIds, policy/order numbers
           └────────┬────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ ESCALATE_EXTRACTION   │  max_turns=6
        │  phones, names, emails│
        │  caseIds, orderNumbers│
        └───────────┬───────────┘
                    │ when exceeded_turns:
                    │  → has payment intel  → PROBE_PAYMENT
                    │  → has link intel     → PROBE_LINK
                    │  → otherwise          → STALL
                    │  (cycles; never goes to CLOSE before ceiling)
                    │
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
        only when messages >= 50
                    │
                    ▼
                ┌───────┐
                │ CLOSE │  max_turns=2  (final info pass, then ended)
                └───────┘
```

### Transition rules summary

- **INIT → PROBE_REASON**: always after `max_turns`
- **PROBE_REASON → PROBE_PAYMENT**: payment mention detected in scammer text
- **PROBE_REASON → PROBE_LINK**: link/URL mention detected
- **PROBE_REASON → STALL**: neither payment nor link; creates thinking time
- **STALL → CONFIRM_DETAILS**: after `max_turns`
- **CONFIRM_DETAILS → ESCALATE_EXTRACTION**: after `max_turns` or sufficient intel already collected
- **ESCALATE_EXTRACTION**: cycles back to PROBE_PAYMENT / PROBE_LINK / STALL — **never** goes to CLOSE
- **Any state → CLOSE**: only when `session["messages"] >= 50` (hard safety ceiling)

---

## Intelligence Extraction Pipeline (intelligence.py)

Every message passes through four stages that feed into a single merged result:

```
scammer_text
      │
      ├─► Stage 1 — Regex extraction
      │       • Phone numbers (10–12 digit, with country code)
      │       • UPI IDs  (handle@provider pattern)
      │       • URLs / phishing links
      │       • Bank account numbers (9–18 digits)
      │       • IFSC codes (4-letter bank code + 0 + 6 alphanumeric)
      │       • Email addresses
      │       • Case / reference IDs, policy numbers, order numbers
      │
      ├─► Stage 2 — Advanced obfuscation patterns
      │       • Obfuscated URLs (hxxp, [.], "dot", spaced domains)
      │       • Split phone numbers (spaces, dashes, commas)
      │       • Number words ("nine eight seven six five…")
      │
      ├─► Stage 3 — LLM extraction (Groq llama-3.1-8b-instant)
      │       • Understands context the regexes miss
      │       • Extracts all structured fields
      │       • Produces free-form `additionalIntel` dict for
      │         everything else (org names, amounts, threats, dates…)
      │
      └─► Stage 4 — Merge & deduplicate
              • Normalise (lowercase, strip spaces)
              • Union all sources; no duplicates
              • Write back into session["intel"]
```

### Extracted fields

| Field | Type | Description |
|---|---|---|
| `phoneNumbers` | `list[str]` | Callback / helpline numbers |
| `upiIds` | `list[str]` | UPI payment addresses |
| `phishingLinks` | `list[str]` | URLs / links shared by scammer |
| `bankAccounts` | `list[str]` | Account numbers |
| `ifscCodes` | `list[str]` | Bank branch IFSC codes |
| `names` | `list[str]` | Scammer names / supervisor names |
| `emails` | `list[str]` | Email addresses |
| `caseIds` | `list[str]` | Case, reference, FIR, complaint IDs |
| `policyNumbers` | `list[str]` | Insurance/policy numbers |
| `orderNumbers` | `list[str]` | Order / tracking numbers |
| `additionalIntel` | `dict[str, list]` | LLM-detected free-form data (organisations, amounts, threats, etc.) |

---

## Scam Detection (detector.py)

Each incoming message receives a composite `scam_score`:

```
scam_score = 0.25 × keyword_score
           + 0.20 × urgency_score
           + 0.20 × authority_score
           + 0.15 × payment_request_score
           + 0.20 × llm_intent_score
```

| Threshold | Decision |
|---|---|
| `>= 0.40` | Scam detected — engage fully |
| `>= 0.25` | Suspicious — engage if conversation already started |
| `< 0.25` | Benign — no action |

URL presence, phone numbers, and email patterns in the raw text also force `scam_detected = True` regardless of score.

---

## LLM Engine (llm_engine.py)

Single shared client used across the whole system.

- **Provider**: Groq (`llama-3.1-8b-instant`), falls back to OpenAI if configured
- **Two temperature regimes**:
  - `0.1` — deterministic extraction (intelligence.py)
  - `0.8` — creative dialogue generation (dialogue_strategy.py)
- **Caching**: SHA-256 keyed, Redis-backed, 24-hour TTL — identical prompts never hit the API twice
- **Heuristic fallback**: if no API key is set the system continues with regex-only extraction and template responses

---

## Bot Defence (defense.py)

When the scammer accuses the honeypot of being a bot or AI, the defence module intercepts before the dialogue strategy runs and returns a randomised human-like deflection:

- **Light humour** — "Ha, do robots usually ask this many questions?"
- **Mild confusion** — "Bot? I don't understand, I'm just a regular person"
- **Redirect** — immediately asks for another piece of intel to change subject
- **Technical blame** — "My phone is behaving strangely, sorry"
- **Clarifying question** — "What do you mean by bot exactly?"

Detection covers: "are you a bot", "are you real", "is this automated", "robot", "AI", "ChatGPT", "copy paste".

---

## Session & Memory (memory.py + Redis)

```
Redis key            Content                           TTL
─────────────────    ──────────────────────────────    ──────
session:{id}         Full session dict (JSON)          1 hour
intel:{id}           Append-only intel snapshots       —
llm_cache:{hash}     LLM response cache                24 hours
```

### Session document structure

```json
{
  "history":          [...],
  "messages":         12,
  "start_time":       1708531200.0,
  "scam_type":        "bank_impersonation",
  "scam_score":       0.87,
  "dialogue_state":   "ESCALATE_EXTRACTION",
  "state_turn_count": 3,
  "asked_fields":     { "phoneNumbers": 2, "upiIds": 1 },
  "red_flags_log":    [...],
  "response_metadata":[...],
  "conversation_ended": false,
  "intel": {
    "phoneNumbers":   [],
    "upiIds":         [],
    "phishingLinks":  [],
    "bankAccounts":   [],
    "ifscCodes":      [],
    "names":          [],
    "emails":         [],
    "caseIds":        [],
    "policyNumbers":  [],
    "orderNumbers":   [],
    "additionalIntel":{}
  }
}
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Health check |
| `POST` | `/honeypot` | API Key | Main conversation endpoint |
| `GET` | `/metrics` | API Key | Real-time telemetry stats |
| `GET` | `/sessions` | API Key | List all active sessions |
| `GET` | `/sessions/{id}` | API Key | Full session details |
| `POST` | `/debug/score` | API Key | Show weighted scam scoring breakdown |
| `POST` | `/debug/strategy` | API Key | Show dialogue state and extraction progress |

### `/honeypot` response shape

```json
{
  "status":                    "success | ended | error",
  "sessionId":                 "uuid",
  "scamDetected":              true,
  "extractedIntelligence": {
    "phoneNumbers":            [],
    "upiIds":                  [],
    "phishingLinks":           [],
    "bankAccounts":            [],
    "ifscCodes":               [],
    "names":                   [],
    "emails":                  [],
    "caseIds":                 [],
    "policyNumbers":           [],
    "orderNumbers":            [],
    "additionalIntel":         {}
  },
  "engagementDurationSeconds": 47.3,
  "totalMessagesExchanged":    12,
  "agentNotes":                "Shared 1 phishing link(s). Provided 1 IFSC code(s)...",
  "scamType":                  "bank_impersonation",
  "confidenceLevel":           0.91,
  "reply":                     "...",
  "redFlags":                  [...],
  "conversationEnded":         false
}
```

---

## Conversation Lifecycle

```
Turn 1      Scammer sends first message
            └─► sessionId auto-generated (UUID v4)
            └─► Session created in Redis

Turns 1–49  Each turn:
            └─► Intel extracted and merged into session
            └─► State machine advances (never closes early)
            └─► LLM generates contextual, human-like reply
            └─► Session saved back to Redis

Turn 50     Hard ceiling reached
            └─► session["conversation_ended"] = True
            └─► send_final_result() → POST to GUVI reporting API
            └─► Subsequent turns return status="ended" with no reply
```

---

## Frontend (React — frontend/chat-scammer/)

- Development server: `localhost:5173`
- Sends scammer messages to `POST /honeypot` with `X-API-KEY` header
- Captures `sessionId` from first response; sends it on all subsequent turns to maintain session continuity
- Displays session ID badge, full conversation thread, and ended-state banner
- `conversationEnded: true` or `status: "ended"` disables the input

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| No early-close conditions | Maximises intel yield; only a 50-message safety ceiling stops the session |
| `ESCALATE_EXTRACTION` cycles rather than closes | When the state exhausts its turns it rotates back to PROBE states to keep probing |
| LLM extraction always runs | Catches contextual intel that regex misses (org names, amounts, threats, etc.) |
| `_normalize_intel()` on every response | Old Redis sessions pre-date some fields (e.g. `ifscCodes`); backfilling prevents missing keys in the API response |
| `conversation_ended` set on first `maybe_finish` fire | Prevents `send_final_result` from being called multiple times for the same session |
| `sessionId` resolved before `try` block | Guarantees the field appears in every response path — success, ended, and error |
