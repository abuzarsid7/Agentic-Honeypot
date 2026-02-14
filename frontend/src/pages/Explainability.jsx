import { useState, useCallback } from 'react';
import {
  ShieldCheck, Layers, FlaskConical, Send, AlertTriangle,
  CheckCircle, XCircle, ArrowRight, Info,
} from 'lucide-react';
import { Panel, Button, Tag, ScoreBar, DataRow, SeverityBadge, TabGroup } from '../components/ui';
import { getScoreBreakdown, getNormalization, getLLMAnalysis } from '../api';
import clsx from 'clsx';

/* ═══════════════════════════════════════════════════════════════
   DETECTION EXPLAINABILITY — Trust & audit defensibility
   Score decomposition + normalization trace + LLM diagnostics
   Maps to: POST /debug/score, /debug/normalize, /debug/llm
   ═══════════════════════════════════════════════════════════════ */

const NORM_STAGES = [
  { key: 'stage1_unicode', label: 'Unicode Normalize', stage: 1 },
  { key: 'stage2_zero_width', label: 'Zero-Width Removal', stage: 2 },
  { key: 'stage3_control_chars', label: 'Control Chars', stage: 3 },
  { key: 'stage4_homoglyphs', label: 'Homoglyph Mapping', stage: 4 },
  { key: 'stage5_leetspeak', label: 'Leetspeak Decode', stage: 5 },
  { key: 'stage6_urls', label: 'URL Deobfuscation', stage: 6 },
  { key: 'stage7_whitespace', label: 'Whitespace Normalize', stage: 7 },
  { key: 'stage8_final', label: 'Lowercase (Final)', stage: 8 },
];

export default function Explainability() {
  const [input, setInput] = useState('');
  const [activeTab, setActiveTab] = useState('scoring');
  const [scoreResult, setScoreResult] = useState(null);
  const [normResult, setNormResult] = useState(null);
  const [llmResult, setLlmResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyze = useCallback(async () => {
    if (!input.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const [score, norm, llm] = await Promise.allSettled([
        getScoreBreakdown(input),
        getNormalization(input),
        getLLMAnalysis(input),
      ]);
      if (score.status === 'fulfilled') setScoreResult(score.value);
      if (norm.status === 'fulfilled') setNormResult(norm.value);
      if (llm.status === 'fulfilled') setLlmResult(llm.value);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }, [input]);

  // Demo fallback data
  const demoScore = scoreResult || {
    scam_score: 0.87,
    is_scam: true,
    threshold: 0.40,
    signals: {
      keyword_score: { score: 0.75, weight: 0.25, weighted: 0.1875, triggered: ['verify', 'blocked', 'urgent', 'upi'] },
      urgency_score: { score: 0.90, weight: 0.20, weighted: 0.18, triggered: ['30 minutes', 'immediately'] },
      authority_score: { score: 0.95, weight: 0.20, weighted: 0.19, triggered: ['RBI', 'fraud department'] },
      payment_score: { score: 0.80, weight: 0.15, weighted: 0.12, triggered: ['UPI ID', 'send Rs 1'] },
      llm_intent_score: { score: 0.85, weight: 0.20, weighted: 0.17 },
    },
    hard_triggers: ['authority_impersonation'],
    emotional_manipulation: { detected: true, patterns: ['fear', 'urgency'] },
    payment_redirection: { detected: true, method: 'UPI' },
  };

  const demoNorm = normResult || {
    stages: {
      original: 'Ur acc0unt wil be bl0cked​! Visit h​t​t​p​s​:​/​/​r​b​i​-​v​e​r​i​f​y.xyz',
      stage1_unicode: 'Ur acc0unt wil be bl0cked! Visit https://rbi-verify.xyz',
      stage2_zero_width: 'Ur acc0unt wil be bl0cked! Visit https://rbi-verify.xyz',
      stage3_control_chars: 'Ur acc0unt wil be bl0cked! Visit https://rbi-verify.xyz',
      stage4_homoglyphs: 'Ur acc0unt wil be bl0cked! Visit https://rbi-verify.xyz',
      stage5_leetspeak: 'Ur account wil be blocked! Visit https://rbi-verify.xyz',
      stage6_urls: 'Ur account wil be blocked! Visit https://rbi-verify.xyz',
      stage7_whitespace: 'Ur account wil be blocked! Visit https://rbi-verify.xyz',
      stage8_final: 'ur account wil be blocked! visit https://rbi-verify.xyz',
    },
    transformations: {
      unicode_changed: false,
      zero_width_removed: true,
      control_chars_removed: false,
      homoglyphs_normalized: false,
      leetspeak_converted: true,
      urls_deobfuscated: false,
      whitespace_normalized: false,
      lowercased: true,
    },
  };

  return (
    <div className="space-y-4">
      {/* Input bar */}
      <Panel>
        <div className="flex items-center gap-3">
          <FlaskConical size={16} className="text-accent shrink-0" />
          <input
            type="text"
            placeholder="Enter a scam message to analyze detection signals..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && analyze()}
            className="flex-1 bg-surface-700 border border-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50"
          />
          <Button onClick={analyze} disabled={loading || !input.trim()}>
            <Send size={13} />
            {loading ? 'Analyzing...' : 'Analyze'}
          </Button>
        </div>
        {error && (
          <div className="mt-2 flex items-center gap-2 text-xs text-severity-critical">
            <XCircle size={12} />
            {error}
          </div>
        )}
      </Panel>

      {/* Tabs */}
      <TabGroup
        tabs={[
          { key: 'scoring', label: 'Score Decomposition' },
          { key: 'normalization', label: 'Normalization Trace' },
          { key: 'llm', label: 'LLM Diagnostics' },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* ── Score Decomposition ── */}
      {activeTab === 'scoring' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Composite Score" subtitle="Multi-signal weighted model">
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className={clsx(
                  'w-20 h-20 rounded-xl flex items-center justify-center text-2xl font-bold font-mono',
                  demoScore.is_scam !== false
                    ? 'bg-severity-critical/15 text-severity-critical'
                    : 'bg-severity-low/15 text-severity-low'
                )}>
                  {(demoScore.scam_score ?? 0).toFixed(2)}
                </div>
                <div className="space-y-1">
                  <SeverityBadge score={demoScore.scam_score ?? 0} />
                  <p className="text-xs text-text-muted">
                    Threshold: {demoScore.threshold ?? 0.40} | Verdict: {demoScore.is_scam !== false ? 'SCAM DETECTED' : 'Below threshold'}
                  </p>
                </div>
              </div>

              <div className="text-[10px] text-text-muted font-mono bg-surface-700/50 rounded-md p-2">
                score = 0.25*keyword + 0.20*urgency + 0.20*authority + 0.15*payment + 0.20*llm_intent
              </div>
            </div>
          </Panel>

          <Panel title="Per-Signal Breakdown" subtitle="Individual signal contributions">
            <div className="space-y-3">
              {Object.entries(demoScore.signals || {}).map(([key, sig]) => (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-secondary capitalize">{key.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-text-muted">w={sig.weight}</span>
                      <span className="text-xs font-mono text-text-primary">{sig.score?.toFixed(2)}</span>
                      <span className="text-[10px] text-text-muted">(={sig.weighted?.toFixed(3)})</span>
                    </div>
                  </div>
                  <ScoreBar score={sig.score || 0} />
                  {sig.triggered && sig.triggered.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {sig.triggered.map((t, i) => <Tag key={i}>{t}</Tag>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Panel>

          {/* Hard Triggers */}
          {demoScore.hard_triggers && demoScore.hard_triggers.length > 0 && (
            <Panel title="Hard Triggers" subtitle="Immediate escalation signals">
              <div className="space-y-2">
                {demoScore.hard_triggers.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 bg-severity-critical/10 border border-severity-critical/20 rounded-md px-3 py-2">
                    <AlertTriangle size={13} className="text-severity-critical shrink-0" />
                    <span className="text-xs text-severity-critical">{t}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {/* Emotional patterns */}
          {demoScore.emotional_manipulation?.detected && (
            <Panel title="Emotional Manipulation" subtitle="Detected psychological patterns">
              <div className="flex flex-wrap gap-1.5">
                {(demoScore.emotional_manipulation.patterns || []).map((p, i) => (
                  <Tag key={i} variant="high">{p}</Tag>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}

      {/* ── Normalization Trace ── */}
      {activeTab === 'normalization' && (
        <Panel title="8-Stage Normalization Pipeline" subtitle="Text deobfuscation trace">
          <div className="space-y-2">
            {NORM_STAGES.map((stage) => {
              const stageVal = demoNorm.stages?.[stage.key] || '';
              const prevKey = stage.stage === 1 ? 'original' : NORM_STAGES[stage.stage - 2]?.key;
              const prevVal = demoNorm.stages?.[prevKey] || '';
              const changed = stageVal !== prevVal;
              const transformKey = Object.keys(demoNorm.transformations || {})[stage.stage - 1];
              const didTransform = demoNorm.transformations?.[transformKey];

              return (
                <div key={stage.key} className={clsx(
                  'rounded-md px-3 py-2.5 border',
                  didTransform
                    ? 'bg-severity-medium/5 border-severity-medium/20'
                    : 'bg-surface-700/30 border-border/50'
                )}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-text-muted bg-surface-600 rounded px-1.5 py-0.5">
                        S{stage.stage}
                      </span>
                      <span className="text-xs font-medium text-text-secondary">{stage.label}</span>
                    </div>
                    {didTransform ? (
                      <Tag variant="high">Modified</Tag>
                    ) : (
                      <span className="text-[10px] text-text-muted">No change</span>
                    )}
                  </div>
                  <div className="font-mono text-[11px] text-text-primary bg-surface-800/80 rounded px-2 py-1.5 break-all">
                    {stageVal || '(empty)'}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── LLM Diagnostics ── */}
      {activeTab === 'llm' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Intent Classification" subtitle="LLM-powered analysis">
            <div className="space-y-2">
              <DataRow label="Label" value={llmResult?.intent?.label || 'financial_fraud'} />
              <DataRow label="Confidence" value={`${((llmResult?.intent?.confidence || 0.92) * 100).toFixed(0)}%`} mono />
              <DataRow label="Source" value={llmResult?.source || 'groq/llama3-70b'} />
              <DataRow label="Cache" value={llmResult?.cache_hit ? 'HIT' : 'MISS'} />
              <div className="mt-2">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Reasoning</span>
                <p className="text-[11px] text-text-secondary mt-1">
                  {llmResult?.intent?.reasoning || 'Authority impersonation combined with payment extraction and artificial urgency'}
                </p>
              </div>
            </div>
          </Panel>

          <Panel title="Social Engineering Tactics" subtitle="Detected manipulation methods">
            <div className="space-y-2">
              {(llmResult?.social_engineering?.tactics || ['Authority Impersonation', 'Urgency/Fear', 'Trust Exploitation']).map((t, i) => (
                <div key={i} className="flex items-center gap-2 bg-severity-high/8 border border-severity-high/15 rounded-md px-3 py-2">
                  <AlertTriangle size={12} className="text-severity-high shrink-0" />
                  <span className="text-xs text-text-primary">{t}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Narrative Classification" subtitle="Scam campaign stage" className="lg:col-span-2">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-surface-700/50 rounded-md p-3 text-center">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Category</span>
                <p className="text-sm font-medium text-text-primary mt-1">
                  {llmResult?.narrative?.category || 'bank_fraud'}
                </p>
              </div>
              <div className="bg-surface-700/50 rounded-md p-3 text-center">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Stage</span>
                <p className="text-sm font-medium text-severity-high mt-1">
                  {llmResult?.narrative?.stage || 'exploitation'}
                </p>
              </div>
              <div className="bg-surface-700/50 rounded-md p-3 text-center">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Composite Score</span>
                <p className="text-sm font-medium font-mono text-text-primary mt-1">
                  {llmResult?.composite_score?.toFixed(2) || '0.85'}
                </p>
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
