import { useState, useCallback, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import {
  MessageSquare, Shield, Target, Brain, Eye, EyeOff,
  Clock, ArrowRight, AlertTriangle, Send, ChevronDown,
  ChevronUp, ExternalLink, Copy, Download, AlertCircle,
} from 'lucide-react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import {
  Panel, SeverityBadge, Button, Tag, ScoreBar, DataRow,
  TabGroup, StatusDot, EmptyState,
} from '../components/ui';
import { getSeverity, maskPII, timeAgo, usePolling } from '../utils';
import { 
  sendMessage, 
  getScoreBreakdown, 
  getStrategy, 
  getIntelScore, 
  getSessionDetails,
  getLLMAnalysis,
  getIntelExtraction
} from '../api';

/* ═══════════════════════════════════════════════════════════════
   SESSION INVESTIGATION WORKSPACE — Real-time Scam Analysis
   - Live conversation timeline
   - Threat intelligence extraction
   - Detection signal breakdown
   ═══════════════════════════════════════════════════════════════ */

export default function Investigation() {
  const [searchParams] = useSearchParams();
  // Generate a new session ID for each page load if not provided in URL
  const sessionId = useMemo(() => {
    const sidFromUrl = searchParams.get('sid');
    if (sidFromUrl) return sidFromUrl;
    // Generate unique session ID with timestamp
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }, [searchParams]);
  const [piiVisible, setPiiVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('signals');
  const [messageInput, setMessageInput] = useState('');
  const [sending, setSending] = useState(false);
  const [collapsed, setCollapsed] = useState({});
  
  // Real-time session state
  const [sessionData, setSessionData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [scoreData, setScoreData] = useState(null);
  const [strategyData, setStrategyData] = useState(null);
  const [intelData, setIntelData] = useState(null);
  const [llmData, setLLMData] = useState(null);

  const toggleSection = (key) => setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));

  // Fetch session details and update state
  const fetchSessionData = useCallback(async () => {
    try {
      const session = await getSessionDetails(sessionId);
      if (session && session.session) {
        setSessionData(session.session);
        
        // Extract messages from history
        const history = session.session.history || [];
        const formattedMessages = history.map((msg, i) => ({
          role: msg.sender === 'scammer' ? 'scammer' : 'agent',
          text: msg.text,
          time: new Date(session.session.last_updated * 1000 + i * 1000).toLocaleTimeString(),
          stage: msg.stage || null,
          tactics: msg.tactics || []
        }));
        setMessages(formattedMessages);
        
        // Get intelligence data
        const intel = session.session.intel || {};
        setIntelData({
          phoneNumbers: intel.phoneNumbers || [],
          upiIds: intel.upiIds || [],
          phishingLinks: intel.phishingLinks || [],
          bankAccounts: intel.bankAccounts || [],
          suspiciousKeywords: intel.suspiciousKeywords || []
        });
        
        // Fetch strategy data
        if (sessionId) {
          try {
            const strat = await getStrategy(sessionId);
            if (strat && strat.status === 'success') {
              setStrategyData(strat);
            }
          } catch (e) {
            console.log('Strategy data not available');
          }
        }
        
        // Get score breakdown for latest scammer message
        const lastScammerMsg = history.filter(m => m.sender === 'scammer').pop();
        if (lastScammerMsg) {
          try {
            const scoreBreakdown = await getScoreBreakdown(lastScammerMsg.text, history);
            if (scoreBreakdown && scoreBreakdown.status === 'success') {
              setScoreData(scoreBreakdown);
            }
          } catch (e) {
            console.log('Score data not available');
          }
          
          // Get LLM analysis
          try {
            const llmAnalysis = await getLLMAnalysis(lastScammerMsg.text, history);
            if (llmAnalysis && llmAnalysis.status === 'success') {
              setLLMData(llmAnalysis);
            }
          } catch (e) {
            console.log('LLM data not available');
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch session:', error);
    }
  }, [sessionId]);

  // Poll for updates
  useEffect(() => {
    fetchSessionData();
    const interval = setInterval(fetchSessionData, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [fetchSessionData]);

  // Send message handler
  const handleSendMessage = async () => {
    if (!messageInput.trim() || sending) return;
    
    setSending(true);
    try {
      const history = messages.map(m => ({
        role: m.role === 'scammer' ? 'scammer' : 'user',
        text: m.text
      }));
      
      const result = await sendMessage(sessionId, messageInput, history);
      
      // Add new messages to UI
      const newScammerMsg = {
        role: 'scammer',
        text: messageInput,
        time: new Date().toLocaleTimeString(),
        stage: null,
        tactics: []
      };
      
      const newAgentMsg = {
        role: 'agent',
        text: result.reply,
        time: new Date().toLocaleTimeString(),
        stage: null,
        tactics: []
      };
      
      setMessages(prev => [...prev, newScammerMsg, newAgentMsg]);
      setMessageInput('');
      
      // Refresh all data
      setTimeout(fetchSessionData, 500);
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message: ' + error.message);
    } finally {
      setSending(false);
    }
  };

  // Extract data with fallbacks
  const score = scoreData ? {
    scam_score: scoreData.scam_score || 0,
    keyword_score: scoreData.scores?.keyword || 0,
    urgency_score: scoreData.scores?.urgency || 0,
    authority_score: scoreData.scores?.authority || 0,
    payment_score: scoreData.scores?.payment || 0,
    llm_intent_score: scoreData.scores?.llm || 0,
    hard_trigger: scoreData.hard_trigger ? 'Yes' : 'No',
  } : {
    scam_score: sessionData?.scam_score || 0,
    keyword_score: 0,
    urgency_score: 0,
    authority_score: 0,
    payment_score: 0,
    llm_intent_score: 0,
    hard_trigger: 'Unknown',
  };

  const strategy = strategyData ? {
    current_state: strategyData.current_state || 'INIT',
    state_goal: strategyData.state_goal || 'Analyzing conversation',
    turn_count: strategyData.state_turn_count || 0,
    max_turns: strategyData.max_turns_in_state || 5,
    state_history: strategyData.state_history || [],
  } : {
    current_state: sessionData?.dialogue_state || 'INIT',
    state_goal: 'Analyzing conversation',
    turn_count: sessionData?.state_turn_count || 0,
    max_turns: 5,
    state_history: sessionData?.state_history || [],
  };

  const intel = intelData || {
    phoneNumbers: [],
    upiIds: [],
    phishingLinks: [],
    bankAccounts: [],
    suspiciousKeywords: [],
  };

  const llm = llmData ? {
    intent: llmData.intent || { label: 'analyzing', confidence: 0, reasoning: 'Processing...' },
    social_engineering: llmData.social_engineering || { tactics: [], severity: 'unknown' },
    narrative: llmData.narrative || { category: 'unknown', stage: 'analyzing', description: 'Processing conversation...' },
  } : {
    intent: { label: 'analyzing', confidence: 0, reasoning: 'Processing...' },
    social_engineering: { tactics: [], severity: 'unknown' },
    narrative: { category: 'unknown', stage: 'analyzing', description: 'Processing conversation...' },
  };

  const closeDecision = {
    should_close: false,
    reason: 'continue_extraction',
    interpretation: 'Continue conversation, still extracting value',
  };

  const SIGNAL_RADAR = [
    { signal: 'Keywords', value: Math.round(score.keyword_score * 100), fullMark: 100 },
    { signal: 'Urgency', value: Math.round(score.urgency_score * 100), fullMark: 100 },
    { signal: 'Authority', value: Math.round(score.authority_score * 100), fullMark: 100 },
    { signal: 'Payment', value: Math.round(score.payment_score * 100), fullMark: 100 },
    { signal: 'LLM Intent', value: Math.round(score.llm_intent_score * 100), fullMark: 100 },
  ];

  const severity = getSeverity(score.scam_score);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:h-[calc(100vh-10rem)]">
      {/* ═══ LEFT PANEL: Conversation Timeline ═══ */}
      <div className="lg:col-span-4 flex flex-col bg-surface-800 border border-border rounded-lg overflow-hidden min-h-[500px] lg:min-h-0">
        {/* Timeline header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <MessageSquare size={14} className="text-accent" />
            <span className="text-sm font-semibold text-text-primary">Conversation Timeline</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusDot status="live" />
            <span className="text-[10px] text-text-muted font-mono">{sessionId}</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <EmptyState
                icon={MessageSquare}
                title="No messages yet"
                subtitle="Send a test scam message below to start the conversation"
              />
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className="space-y-1.5">
                {/* Stage label (only on stage transitions) */}
                {msg.stage && (i === 0 || messages[i-1].stage !== msg.stage) && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-px flex-1 bg-border"></div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-accent px-2">
                      {msg.stage}
                    </span>
                    <div className="h-px flex-1 bg-border"></div>
                  </div>
                )}
                
                <div className={clsx('flex', msg.role === 'agent' ? 'justify-end' : 'justify-start')}>
                  <div className={clsx(
                    'max-w-[85%] rounded-lg px-3 py-2',
                    msg.role === 'scammer'
                      ? 'bg-severity-critical/8 border border-severity-critical/20'
                      : 'bg-accent/8 border border-accent/20'
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={clsx(
                        'text-[10px] font-semibold uppercase',
                        msg.role === 'scammer' ? 'text-severity-critical' : 'text-accent'
                      )}>
                        {msg.role === 'scammer' ? 'THREAT ACTOR' : 'HONEYPOT AGENT'}
                      </span>
                      <span className="text-[10px] text-text-muted font-mono">{msg.time}</span>
                    </div>
                    <p className="text-xs text-text-primary leading-relaxed mb-2">{msg.text}</p>
                    
                    {/* Tactics badges (only for scammer messages) */}
                    {msg.role === 'scammer' && msg.tactics && msg.tactics.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {msg.tactics.map((tactic, ti) => (
                          <span key={ti} className="px-1.5 py-0.5 bg-severity-high/10 border border-severity-high/30 rounded text-[9px] font-mono text-severity-high">
                            {tactic}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Message input */}
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Send scammer message..."
              value={messageInput}
              onChange={e => setMessageInput(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleSendMessage()}
              disabled={sending}
              className="flex-1 bg-surface-700 border border-border rounded-md px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 disabled:opacity-50"
            />
            <Button 
              size="xs" 
              variant="secondary" 
              onClick={handleSendMessage}
              disabled={sending || !messageInput.trim()}
            >
              <Send size={12} />
              {sending ? 'Sending...' : 'Send'}
            </Button>
          </div>
        </div>
      </div>

      {/* ═══ CENTER PANEL: Risk + Strategy Analysis ═══ */}
      <div className="lg:col-span-4 flex flex-col gap-4 overflow-y-auto min-h-[500px] lg:min-h-0">
        {/* Risk Decision Card */}
        <Panel
          title="Risk Assessment"
          actions={<SeverityBadge score={score.scam_score} />}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold font-mono text-text-primary">{score.scam_score.toFixed(2)}</span>
              <span className="text-xs text-text-muted">/ 1.00</span>
            </div>
            <ScoreBar score={score.scam_score} />
            {score.hard_trigger && (
              <div className="flex items-center gap-2 bg-severity-critical/10 border border-severity-critical/20 rounded-md px-3 py-2">
                <AlertTriangle size={13} className="text-severity-critical shrink-0" />
                <span className="text-[11px] text-severity-critical">Hard Trigger: {score.hard_trigger}</span>
              </div>
            )}
          </div>
        </Panel>

        {/* Signal Breakdown */}
        <Panel title="Signal Breakdown" subtitle="Weighted scoring model">
          <TabGroup
            tabs={[
              { key: 'signals', label: 'Weights' },
              { key: 'radar', label: 'Radar' },
            ]}
            active={activeTab}
            onChange={setActiveTab}
          />
          <div className="mt-3">
            {activeTab === 'signals' ? (
              <div className="space-y-2.5">
                {[
                  { label: 'Keyword Score', value: score.keyword_score, weight: '0.25' },
                  { label: 'Urgency Score', value: score.urgency_score, weight: '0.20' },
                  { label: 'Authority Score', value: score.authority_score, weight: '0.20' },
                  { label: 'Payment Score', value: score.payment_score, weight: '0.15' },
                  { label: 'LLM Intent Score', value: score.llm_intent_score, weight: '0.20' },
                ].map(s => (
                  <div key={s.label} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-text-secondary">{s.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-text-muted">w={s.weight}</span>
                        <span className="text-xs font-mono text-text-primary">{s.value.toFixed(2)}</span>
                      </div>
                    </div>
                    <ScoreBar score={s.value} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={SIGNAL_RADAR}>
                    <PolarGrid stroke="#1e293b" />
                    <PolarAngleAxis dataKey="signal" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                    <Radar dataKey="value" stroke="#14b8a6" fill="#14b8a6" fillOpacity={0.15} strokeWidth={1.5} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Panel>

        {/* LLM Analysis */}
        <Panel title="LLM Analysis" subtitle="AI-powered classification">
          <div className="space-y-3">
            <div className="bg-surface-700/50 rounded-md p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Intent</span>
                <Tag variant="critical">{llm.intent.label}</Tag>
              </div>
              <DataRow label="Confidence" value={`${(llm.intent.confidence * 100).toFixed(0)}%`} mono />
              <p className="text-[11px] text-text-secondary mt-1">{llm.intent.reasoning}</p>
            </div>

            <div className="bg-surface-700/50 rounded-md p-3 space-y-1.5">
              <span className="text-[10px] uppercase tracking-wider text-text-muted">Social Engineering</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {llm.social_engineering.tactics.map((t, i) => (
                  <Tag key={i} variant="high">{t}</Tag>
                ))}
              </div>
            </div>

            <div className="bg-surface-700/50 rounded-md p-3 space-y-1.5">
              <span className="text-[10px] uppercase tracking-wider text-text-muted">Narrative</span>
              <DataRow label="Category" value={llm.narrative.category} />
              <DataRow label="Stage" value={llm.narrative.stage} />
              <p className="text-[11px] text-text-secondary mt-1">{llm.narrative.description}</p>
            </div>
          </div>
        </Panel>

        {/* Dialogue Strategy */}
        <Panel title="Dialogue Strategy" subtitle="State machine progression">
          <div className="space-y-3">
            <div className="flex items-center gap-3 bg-accent/8 border border-accent/20 rounded-md px-3 py-2">
              <Target size={14} className="text-accent shrink-0" />
              <div>
                <span className="text-xs font-medium text-accent">{strategy.current_state}</span>
                <p className="text-[11px] text-text-secondary mt-0.5">{strategy.state_goal}</p>
              </div>
            </div>
            <DataRow label="Turn Count" value={`${strategy.turn_count} / ${strategy.max_turns}`} mono />

            {/* State History */}
            <div className="space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-text-muted">State History</span>
              <div className="relative pl-4 space-y-2 mt-1">
                <div className="absolute left-1.5 top-1 bottom-1 w-px bg-border" />
                {strategy.state_history.map((h, i) => (
                  <div key={i} className="relative flex items-start gap-2">
                    <div className={clsx(
                      'absolute -left-2.5 top-1 w-2 h-2 rounded-full border',
                      i === strategy.state_history.length - 1
                        ? 'bg-accent border-accent'
                        : 'bg-surface-600 border-border'
                    )} />
                    <div className="ml-1">
                      <span className="text-xs font-mono text-text-primary">{h.state}</span>
                      <span className="text-[10px] text-text-muted ml-2">({h.turns} turns)</span>
                      <p className="text-[10px] text-text-muted">{h.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* ═══ RIGHT PANEL: Intelligence + Actions ═══ */}
      <div className="lg:col-span-4 flex flex-col gap-4 overflow-y-auto min-h-[500px] lg:min-h-0">
        {/* Extracted Intelligence */}
        <Panel
          title="Extracted Intelligence"
          actions={
            <button
              onClick={() => setPiiVisible(!piiVisible)}
              className="flex items-center gap-1 text-[11px] text-text-muted hover:text-text-secondary"
            >
              {piiVisible ? <Eye size={12} /> : <EyeOff size={12} />}
              {piiVisible ? 'Hide' : 'Reveal'}
            </button>
          }
        >
          <div className="space-y-3">
            {/* UPI IDs */}
            <IntelSection
              title="UPI IDs"
              items={intel.upiIds}
              piiVisible={piiVisible}
              source="regex + llm"
            />
            {/* Phone Numbers */}
            <IntelSection
              title="Phone Numbers"
              items={intel.phoneNumbers}
              piiVisible={piiVisible}
              source="regex"
              empty="None extracted"
            />
            {/* Phishing Links */}
            <IntelSection
              title="Phishing Links"
              items={intel.phishingLinks}
              piiVisible={piiVisible}
              source="regex + advanced"
              variant="critical"
            />
            {/* Bank Accounts */}
            <IntelSection
              title="Bank Accounts"
              items={intel.bankAccounts}
              piiVisible={piiVisible}
              source="regex"
            />
            {/* Suspicious Keywords */}
            <div>
              <span className="text-[10px] uppercase tracking-wider text-text-muted">Suspicious Keywords</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {intel.suspiciousKeywords.map((kw, i) => (
                  <Tag key={i}>{kw}</Tag>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        {/* Closing Decision */}
        <Panel title="Closing Decision" subtitle="Intelligent conversation management">
          <div className={clsx(
            'rounded-md px-3 py-3 border',
            closeDecision.should_close
              ? 'bg-severity-high/10 border-severity-high/20'
              : 'bg-severity-low/10 border-severity-low/20'
          )}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-text-primary">
                {closeDecision.should_close ? 'Recommend: Close & Export' : 'Recommend: Continue'}
              </span>
              <Tag variant={closeDecision.should_close ? 'high' : 'accent'}>
                {closeDecision.reason}
              </Tag>
            </div>
            <p className="text-[11px] text-text-secondary">{closeDecision.interpretation}</p>
          </div>
        </Panel>
      </div>
    </div>
    </div>
  );
}

// ── Intel Section Sub-Component ──
function IntelSection({ title, items, piiVisible, source, empty, variant }) {
  if (!items || items.length === 0) {
    return (
      <div>
        <span className="text-[10px] uppercase tracking-wider text-text-muted">{title}</span>
        <p className="text-[11px] text-text-muted mt-0.5">{empty || 'None extracted'}</p>
      </div>
    );
  }
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-text-muted">{title}</span>
        {source && <span className="text-[9px] text-text-muted">src: {source}</span>}
      </div>
      <div className="space-y-1 mt-1">
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between bg-surface-700/50 rounded px-2.5 py-1.5">
            <span className={clsx(
              'text-xs font-mono',
              variant === 'critical' ? 'text-severity-critical' : 'text-text-primary'
            )}>
              {maskPII(item, piiVisible)}
            </span>
            <button className="text-text-muted hover:text-text-secondary">
              <Copy size={11} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
