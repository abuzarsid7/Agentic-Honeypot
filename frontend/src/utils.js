import { useState, useEffect } from 'react';

/* ═══════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS — Shared helpers for the analyst console
   ═══════════════════════════════════════════════════════════════ */

// ── Severity Mapping ──
export function getSeverity(score) {
  if (score >= 0.75) return 'critical';
  if (score >= 0.60) return 'high';
  if (score >= 0.40) return 'medium';
  if (score >= 0.25) return 'low';
  return 'info';
}

export const severityColors = {
  critical: {
    bg: 'bg-severity-critical/15',
    text: 'text-severity-critical',
    dot: 'bg-severity-critical',
    border: 'border-severity-critical/30',
  },
  high: {
    bg: 'bg-severity-high/15',
    text: 'text-severity-high',
    dot: 'bg-severity-high',
    border: 'border-severity-high/30',
  },
  medium: {
    bg: 'bg-severity-medium/15',
    text: 'text-severity-medium',
    dot: 'bg-severity-medium',
    border: 'border-severity-medium/30',
  },
  low: {
    bg: 'bg-severity-low/15',
    text: 'text-severity-low',
    dot: 'bg-severity-low',
    border: 'border-severity-low/30',
  },
  info: {
    bg: 'bg-severity-info/15',
    text: 'text-severity-info',
    dot: 'bg-severity-info',
    border: 'border-severity-info/30',
  },
};

// ── Number Formatting ──
export function formatNum(num) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

// ── Time Formatting ──
export function timeAgo(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return `${seconds}s ago`;
}

// ── PII Masking ──
export function maskPII(text, visible = false) {
  if (visible || !text) return text;
  
  // Mask phone numbers: +919876543210 → +91••••••3210
  text = text.replace(/(\+?\d{2,3})(\d{4,8})(\d{4})/g, '$1••••••$3');
  
  // Mask UPI IDs: abc@ybl → a••@ybl
  text = text.replace(/([a-zA-Z0-9])([a-zA-Z0-9.]+)(@[a-zA-Z0-9]+)/g, '$1••$3');
  
  // Mask account numbers: 1234567890123456 → 1234••••3456
  text = text.replace(/\b(\d{4})\d{8,10}(\d{4})\b/g, '$1••••$2');
  
  return text;
}

// ── Polling Hook ──
export function usePolling(fetchFn, interval = 5000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    let isMounted = true;
    let timeoutId;
    
    const fetch = async () => {
      try {
        const result = await fetchFn();
        if (isMounted) {
          setData(result);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
      
      if (isMounted) {
        timeoutId = setTimeout(fetch, interval);
      }
    };
    
    fetch();
    
    return () => {
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [fetchFn, interval]);
  
  return { data, loading, error };
}

// ── Local Storage Helpers ──
export function getApiKey() {
  return localStorage.getItem('hp_api_key') || '';
}

export function setApiKey(key) {
  localStorage.setItem('hp_api_key', key);
}
