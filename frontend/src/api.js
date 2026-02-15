/* ═══════════════════════════════════════════════════════════════
   API CLIENT — Backend communication layer
   Base URL: /api (proxied to http://localhost:8000 by Vite)
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = '/api';

// Get API key from localStorage
function getApiKey() {
  return localStorage.getItem('hp_api_key') || '';
}

// Generic fetch wrapper with error handling
async function apiFetch(endpoint, options = {}) {
  const apiKey = getApiKey();
  
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
      ...options.headers,
    },
  };
  
  const response = await fetch(`${API_BASE}${endpoint}`, config);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} - ${errorText}`);
  }
  
  return response.json();
}

// ── Health & Metrics ──
export async function getHealth() {
  return apiFetch('/');
}

export async function getMetrics() {
  return apiFetch('/metrics');
}

// ── LLM Cache ──
export async function getLLMCache() {
  return apiFetch('/debug/llm/cache');
}

export async function clearLLMCache() {
  return apiFetch('/debug/llm/cache/clear', { method: 'POST' });
}

// ── Message Sending ──
export async function sendMessage(sessionId, text, conversationHistory = []) {
  return apiFetch('/honeypot', {
    method: 'POST',
    body: JSON.stringify({
      sessionId,
      message: { text },
      conversationHistory,
    }),
  });
}

// ── Debug Endpoints ──
export async function getScoreBreakdown(text, conversationHistory = []) {
  return apiFetch('/debug/score', {
    method: 'POST',
    body: JSON.stringify({
      text,
      conversationHistory,
    }),
  });
}

export async function getNormalization(text) {
  return apiFetch('/debug/normalize', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function getLLMAnalysis(text, conversationHistory = []) {
  return apiFetch('/debug/llm', {
    method: 'POST',
    body: JSON.stringify({
      text,
      conversationHistory,
    }),
  });
}

export async function getStrategy(sessionId) {
  return apiFetch('/debug/strategy', {
    method: 'POST',
    body: JSON.stringify({ sessionId }),
  });
}

export async function getIntelScore(sessionId) {
  return apiFetch('/debug/intel_score', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getIntelExtraction(text) {
  return apiFetch('/debug/intelligence', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// ── Session Management ──
export async function getSessions() {
  return apiFetch('/sessions');
}

export async function getSessionDetails(sessionId) {
  return apiFetch(`/session/${sessionId}`);
}
