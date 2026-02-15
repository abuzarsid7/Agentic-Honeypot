import { createContext, useContext, useState, useCallback } from 'react';

const SessionContext = createContext(null);

/**
 * Global session store for the analyst console.
 * Tracks all active sessions and their data.
 */
export function SessionProvider({ children }) {
  const [sessions, setSessions] = useState({});
  const [activeSessionId, setActiveSessionId] = useState(null);

  const updateSession = useCallback((id, data) => {
    setSessions(prev => ({
      ...prev,
      [id]: { ...prev[id], ...data, lastUpdated: Date.now() },
    }));
  }, []);

  const addSession = useCallback((id, data = {}) => {
    setSessions(prev => ({
      ...prev,
      [id]: {
        id,
        messages: [],
        score: 0,
        state: 'INIT',
        intel: { phoneNumbers: [], upiIds: [], phishingLinks: [], bankAccounts: [], suspiciousKeywords: [] },
        createdAt: Date.now(),
        lastUpdated: Date.now(),
        ...data,
      },
    }));
  }, []);

  const removeSession = useCallback((id) => {
    setSessions(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (activeSessionId === id) setActiveSessionId(null);
  }, [activeSessionId]);

  return (
    <SessionContext.Provider value={{
      sessions,
      activeSessionId,
      setActiveSessionId,
      updateSession,
      addSession,
      removeSession,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessions() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSessions must be inside SessionProvider');
  return ctx;
}
