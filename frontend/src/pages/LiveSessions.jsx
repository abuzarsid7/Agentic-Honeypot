import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Filter, ArrowUpDown, Clock, MessageSquare,
  ChevronRight, AlertTriangle, Shield, Zap, Plus, X,
} from 'lucide-react';
import { Panel, SeverityBadge, Button, Tag, StatusDot, EmptyState, DataTable } from '../components/ui';
import { useSessions } from '../SessionContext';
import { getSeverity, timeAgo, maskPII, usePolling } from '../utils';
import { getSessions as fetchSessions, sendMessage } from '../api';
import clsx from 'clsx';

/* ═══════════════════════════════════════════════════════════════
   LIVE SESSIONS QUEUE — Triage view for rapid prioritization
   ═══════════════════════════════════════════════════════════════ */

// Demo sessions for when no live data exists
const DEMO_SESSIONS = [
  {
    id: 'ses_4f2a8c',
    score: 0.87,
    state: 'PROBE_PAYMENT',
    lastTactic: 'UPI payment redirect',
    intelCount: 6,
    messages: 14,
    lastActivity: Date.now() - 120000,
    hardTrigger: true,
    botAccusation: false,
  },
  {
    id: 'ses_8d1e3b',
    score: 0.72,
    state: 'STALL',
    lastTactic: 'Authority impersonation (RBI)',
    intelCount: 4,
    messages: 9,
    lastActivity: Date.now() - 300000,
    hardTrigger: false,
    botAccusation: true,
  },
  {
    id: 'ses_2c7b9a',
    score: 0.65,
    state: 'PROBE_LINK',
    lastTactic: 'Phishing link delivery',
    intelCount: 3,
    messages: 7,
    lastActivity: Date.now() - 480000,
    hardTrigger: false,
    botAccusation: false,
  },
  {
    id: 'ses_9a3f1d',
    score: 0.53,
    state: 'PROBE_REASON',
    lastTactic: 'KYC verification scam',
    intelCount: 2,
    messages: 5,
    lastActivity: Date.now() - 720000,
    hardTrigger: false,
    botAccusation: false,
  },
  {
    id: 'ses_1e5d7c',
    score: 0.91,
    state: 'ESCALATE_EXTRACTION',
    lastTactic: 'Repeated payment pressure',
    intelCount: 8,
    messages: 22,
    lastActivity: Date.now() - 60000,
    hardTrigger: true,
    botAccusation: false,
  },
  {
    id: 'ses_6b4e2f',
    score: 0.45,
    state: 'INIT',
    lastTactic: 'Urgency language',
    intelCount: 1,
    messages: 3,
    lastActivity: Date.now() - 900000,
    hardTrigger: false,
    botAccusation: false,
  },
  {
    id: 'ses_3a9c8e',
    score: 0.78,
    state: 'CONFIRM_DETAILS',
    lastTactic: 'Bank account extraction',
    intelCount: 5,
    messages: 16,
    lastActivity: Date.now() - 180000,
    hardTrigger: true,
    botAccusation: false,
  },
  {
    id: 'ses_7d2f5a',
    score: 0.38,
    state: 'PROBE_REASON',
    lastTactic: 'Suspicious keywords detected',
    intelCount: 1,
    messages: 4,
    lastActivity: Date.now() - 1200000,
    hardTrigger: false,
    botAccusation: false,
  },
];

const STATE_LABELS = {
  INIT: 'Initial Contact',
  PROBE_REASON: 'Probing Narrative',
  PROBE_PAYMENT: 'Probing Payment',
  PROBE_LINK: 'Probing Links',
  STALL: 'Stalling',
  CONFIRM_DETAILS: 'Confirming Details',
  ESCALATE_EXTRACTION: 'Escalated Extraction',
  CLOSE: 'Closing',
};

const FILTERS = ['All', 'Critical', 'High', 'Medium', 'Low'];

export default function LiveSessions() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('score');
  const [sortAsc, setSortAsc] = useState(false);
  const [showNewSessionModal, setShowNewSessionModal] = useState(false);
  const [newSessionText, setNewSessionText] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Fetch real sessions from backend
  const sessionsFetcher = useCallback(() => fetchSessions().catch(() => ({ sessions: [] })), []);
  const { data: sessionsData, loading } = usePolling(sessionsFetcher, 5000);
  
  const allSessions = sessionsData?.sessions || [];

  const handleCreateSession = async () => {
    if (!newSessionText.trim()) return;
    
    setIsCreating(true);
    try {
      // Generate unique session ID
      const sessionId = `ses_${Math.random().toString(36).substring(2, 8)}`;
      
      // Send first message to create session
      await sendMessage(sessionId, newSessionText.trim(), []);
      
      // Close modal and reset
      setShowNewSessionModal(false);
      setNewSessionText('');
      
      // Navigate to Investigation page for the new session
      navigate(`/investigate?sid=${sessionId}`);
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const filtered = useMemo(() => {
    let result = allSessions;
    if (filter !== 'All') {
      result = result.filter(s => getSeverity(s.score) === filter.toLowerCase());
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s => s.id.toLowerCase().includes(q) || s.lastTactic.toLowerCase().includes(q));
    }
    result.sort((a, b) => {
      const va = a[sortKey] ?? 0;
      const vb = b[sortKey] ?? 0;
      return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
    return result;
  }, [allSessions, filter, search, sortKey, sortAsc]);

  const handleSort = (key) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const criticalCount = allSessions.filter(s => getSeverity(s.score) === 'critical').length;
  const highCount = allSessions.filter(s => getSeverity(s.score) === 'high').length;

  return (
    <div className="space-y-4">
      {/* Summary strip */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-surface-800 border border-border rounded-lg px-3 py-2">
            <StatusDot status="live" />
            <span className="text-xs text-text-primary font-medium">{allSessions.length} Active Sessions</span>
          </div>
          {criticalCount > 0 && (
            <div className="flex items-center gap-1.5 bg-severity-critical/10 border border-severity-critical/20 rounded-lg px-3 py-2">
              <AlertTriangle size={13} className="text-severity-critical" />
              <span className="text-xs text-severity-critical font-medium">{criticalCount} Critical</span>
            </div>
          )}
          {highCount > 0 && (
            <div className="flex items-center gap-1.5 bg-severity-high/10 border border-severity-high/20 rounded-lg px-3 py-2">
              <Zap size={13} className="text-severity-high" />
              <span className="text-xs text-severity-high font-medium">{highCount} High</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setShowNewSessionModal(true)}
          className="flex items-center gap-2 bg-accent hover:bg-accent/90 text-surface-900 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Session
        </button>
      </div>

      {/* Filters + Search */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-1.5">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                filter === f
                  ? 'bg-accent/15 text-accent'
                  : 'text-text-muted hover:text-text-secondary hover:bg-surface-700'
              )}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search session ID or tactic..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-surface-700 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted w-64 focus:outline-none focus:border-accent/50"
            />
          </div>
        </div>
      </div>

      {/* Sessions Table */}
      <Panel>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                {[
                  { key: 'id', label: 'Session ID' },
                  { key: 'score', label: 'Risk Score' },
                  { key: 'state', label: 'State' },
                  { key: 'lastTactic', label: 'Latest Tactic' },
                  { key: 'intelCount', label: 'Intel Items' },
                  { key: 'messages', label: 'Messages' },
                  { key: 'lastActivity', label: 'Last Activity' },
                  { key: 'flags', label: 'Flags' },
                  { key: 'action', label: '' },
                ].map(col => (
                  <th
                    key={col.key}
                    onClick={() => col.key !== 'flags' && col.key !== 'action' && handleSort(col.key)}
                    className={clsx(
                      'text-left py-2.5 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted whitespace-nowrap',
                      col.key !== 'flags' && col.key !== 'action' && 'cursor-pointer hover:text-text-secondary'
                    )}
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      {sortKey === col.key && <ArrowUpDown size={10} className="text-accent" />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(session => (
                <tr
                  key={session.id}
                  onClick={() => navigate(`/investigate?sid=${session.id}`)}
                  className="border-b border-border/30 hover:bg-surface-700/50 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-3">
                    <span className="font-mono text-accent">{session.id}</span>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <SeverityBadge score={session.score} />
                      <span className="font-mono text-text-primary">{session.score.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <Tag variant={session.state === 'ESCALATE_EXTRACTION' ? 'critical' : 'default'}>
                      {STATE_LABELS[session.state] || session.state}
                    </Tag>
                  </td>
                  <td className="py-3 px-3 text-text-secondary max-w-[200px] truncate">
                    {session.lastTactic}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={clsx('font-mono', session.intelCount > 4 ? 'text-accent' : 'text-text-secondary')}>
                      {session.intelCount}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center font-mono text-text-secondary">{session.messages}</td>
                  <td className="py-3 px-3 text-text-muted">{timeAgo(session.lastActivity)}</td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-1">
                      {session.hardTrigger && (
                        <Tag variant="critical">Hard Trigger</Tag>
                      )}
                      {session.botAccusation && (
                        <Tag variant="high">Bot Defense</Tag>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <ChevronRight size={14} className="text-text-muted" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      {/* New Session Modal */}
      {showNewSessionModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-800 border border-border rounded-xl shadow-2xl w-full max-w-lg">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="text-lg font-semibold text-text-primary">Create New Session</h3>
              <button
                onClick={() => {
                  setShowNewSessionModal(false);
                  setNewSessionText('');
                }}
                className="text-text-muted hover:text-text-primary transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Initial Message (Scammer's First Text)
                </label>
                <textarea
                  value={newSessionText}
                  onChange={(e) => setNewSessionText(e.target.value)}
                  placeholder="e.g., Hi, your account has been blocked. Click here to verify..."
                  className="w-full bg-surface-700 border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 min-h-[120px] resize-none"
                  autoFocus
                />
              </div>
              <p className="text-xs text-text-muted">
                The honeypot agent will analyze this message and respond automatically if it appears suspicious.
              </p>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
              <button
                onClick={() => {
                  setShowNewSessionModal(false);
                  setNewSessionText('');
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSession}
                disabled={!newSessionText.trim() || isCreating}
                className="flex items-center gap-2 bg-accent hover:bg-accent/90 disabled:bg-surface-600 disabled:text-text-muted text-surface-900 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {isCreating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-surface-900/20 border-t-surface-900 rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus size={16} />
                    Create Session
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

        {filtered.length === 0 && (
          <EmptyState
            icon={Shield}
            title="No sessions match filters"
            description="Adjust severity filter or search query"
          />
        )}
      </Panel>
    </div>
  );
}
