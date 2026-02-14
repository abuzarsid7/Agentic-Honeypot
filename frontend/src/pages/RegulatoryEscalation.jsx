import { useState, useMemo } from 'react';
import {
  Shield, ExternalLink, Download, FileText, CheckCircle, AlertTriangle,
  Phone, CreditCard, Globe, Mail, ChevronDown, ChevronUp, Clock,
  Landmark, Radio, Banknote, Lock, Info, Copy, Search, Filter,
  CheckSquare, Square, FileWarning, ArrowUpRight, Building2
} from 'lucide-react';
import { Panel, Button, Tag, SeverityBadge } from '../components/ui';

/* ═══════════════════════════════════════════════════════════════
   REGULATORY ESCALATION — Complaint Filing & Authority Handoff
   India-focused fraud reporting compliance assist module
   ═══════════════════════════════════════════════════════════════ */

// ── Authority Portal Definitions ──
const AUTHORITIES = [
  {
    id: 'sanchar-saathi',
    name: 'Sanchar Saathi',
    fullTitle: 'Sanchar Saathi — Telecom Fraud & SIM Abuse',
    badge: 'Telecom / DoT',
    badgeColor: 'accent',
    icon: Radio,
    url: 'https://www.sancharsaathi.gov.in',
    cta: 'Open Sanchar Saathi Portal',
    description: 'Report phone number misuse, SIM fraud, SMS-based scams, and spoofed caller IDs to the Department of Telecommunications.',
    useWhen: [
      'Scam involves phone number misuse',
      'SIM swap or SIM cloning fraud',
      'Unsolicited SMS-based scams',
      'Spoofed or masked caller IDs',
    ],
    requiredData: [
      'Phone numbers (caller/sender)',
      'SMS content & timestamps',
      'Carrier/operator (if known)',
      'Call recordings or screenshots',
    ],
    scamTypes: ['telecom', 'sms', 'sim', 'phone'],
    priority: 1,
  },
  {
    id: 'ncrp',
    name: 'National Cyber Crime Reporting Portal',
    fullTitle: 'National Cyber Crime Reporting Portal (NCRP)',
    badge: 'MHA / Law Enforcement',
    badgeColor: 'critical',
    icon: Shield,
    url: 'https://cybercrime.gov.in',
    cta: 'File Cyber Crime Complaint',
    description: 'File complaints for financial fraud, UPI scams, online impersonation, social media scams, phishing, and identity theft with the Ministry of Home Affairs.',
    useWhen: [
      'Financial fraud or monetary loss',
      'UPI / bank account scams',
      'Online impersonation or identity theft',
      'Social media or phishing scams',
      'Any cyber crime under IT Act',
    ],
    requiredData: [
      'Scam classification & risk score',
      'Extracted intelligence (UPI IDs, URLs, bank details)',
      'Conversation summary & timeline',
      'Evidence ZIP export with artifacts',
      'Financial loss amount (if applicable)',
    ],
    scamTypes: ['upi', 'bank', 'phishing', 'impersonation', 'financial', 'social_media'],
    priority: 2,
  },
  {
    id: 'npci',
    name: 'UPI / NPCI / Bank Fraud Escalation',
    fullTitle: 'UPI / NPCI / Bank Fraud Escalation',
    badge: 'Payments',
    badgeColor: 'high',
    icon: Banknote,
    url: 'https://www.npci.org.in',
    cta: 'Contact Bank / NPCI Flow',
    description: 'Escalate UPI ID misuse, payment redirection, and merchant impersonation. Contact your bank immediately for transaction disputes.',
    useWhen: [
      'UPI ID misuse or fraud',
      'Payment redirection to wrong account',
      'Merchant or business impersonation',
      'Unauthorized UPI transactions',
    ],
    requiredData: [
      'UPI IDs involved',
      'Transaction reference numbers (if any)',
      'Scam narrative & timeline',
      'Bank account details (recipient)',
    ],
    bankNote: 'Also contact your bank immediately — most banks have a 24-hour fraud reporting window for UPI transactions.',
    scamTypes: ['upi', 'payment', 'merchant', 'bank'],
    priority: 3,
  },
];

// ── Scam type → display label mapping ──
const SCAM_TYPE_LABELS = {
  telecom: { label: 'Telecom Fraud', icon: Phone },
  sms: { label: 'SMS Scam', icon: Mail },
  sim: { label: 'SIM Fraud', icon: Radio },
  phone: { label: 'Phone Scam', icon: Phone },
  upi: { label: 'UPI Fraud', icon: CreditCard },
  bank: { label: 'Bank Fraud', icon: Building2 },
  phishing: { label: 'Phishing', icon: Globe },
  impersonation: { label: 'Impersonation', icon: Shield },
  financial: { label: 'Financial Fraud', icon: Banknote },
  social_media: { label: 'Social Media Scam', icon: Globe },
  payment: { label: 'Payment Fraud', icon: CreditCard },
  merchant: { label: 'Merchant Fraud', icon: Building2 },
};

// ── Filing Checklist Items ──
const FILING_CHECKLIST = [
  { id: 'confirmed', label: 'Scam confirmed (High / Critical risk score)', required: true },
  { id: 'financial_loss', label: 'Financial loss occurred?', required: false, isQuestion: true },
  { id: 'within_24h', label: 'Reporting within 24 hours (recommended for UPI)', required: false },
  { id: 'bank_contacted', label: 'Bank contacted (mandatory for UPI fraud)', required: false },
  { id: 'evidence_ready', label: 'Evidence packet downloaded', required: false },
];


export default function RegulatoryEscalation() {
  const [selectedScamType, setSelectedScamType] = useState('all');
  const [expandedAuthority, setExpandedAuthority] = useState(null);
  const [checklist, setChecklist] = useState({});
  const [evidenceOptions, setEvidenceOptions] = useState({
    maskPII: true,
    includeRaw: false,
    includeSummary: true,
    includeTimeline: true,
    includeArtifacts: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSession, setSelectedSession] = useState(null);
  const [copyFeedback, setCopyFeedback] = useState(null);

  // Filter authorities based on selected scam type
  const filteredAuthorities = useMemo(() => {
    if (selectedScamType === 'all') return AUTHORITIES;
    return AUTHORITIES
      .filter(a => a.scamTypes.includes(selectedScamType))
      .sort((a, b) => a.priority - b.priority);
  }, [selectedScamType]);

  // Checklist progress
  const checklistProgress = useMemo(() => {
    const total = FILING_CHECKLIST.length;
    const checked = Object.values(checklist).filter(Boolean).length;
    return { total, checked, pct: total > 0 ? Math.round((checked / total) * 100) : 0 };
  }, [checklist]);

  const toggleChecklist = (id) => {
    setChecklist(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    setCopyFeedback(url);
    setTimeout(() => setCopyFeedback(null), 2000);
  };

  const toggleAuthority = (id) => {
    setExpandedAuthority(prev => prev === id ? null : id);
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
            <Landmark size={20} className="text-accent" />
            Report to Authorities
          </h2>
          <p className="text-xs text-text-muted mt-1">
            Compliance-assisted escalation to Indian regulatory &amp; law enforcement portals
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Tag variant="accent">India Jurisdiction</Tag>
          <Tag>Compliance Assist</Tag>
        </div>
      </div>

      {/* ── Legal Disclaimer Banner ── */}
      <div className="bg-surface-700/50 border border-border rounded-lg px-4 py-3 flex items-start gap-3">
        <Info size={16} className="text-severity-info shrink-0 mt-0.5" />
        <div>
          <p className="text-xs text-text-secondary leading-relaxed">
            <strong className="text-text-primary">Compliance Notice:</strong> This platform assists in reporting by pre-filling evidence and recommending jurisdictions. Final complaint submission occurs on official government portals. This module does not collect Aadhaar, PAN, or other personal identity documents.
          </p>
        </div>
      </div>

      {/* ── Main 2-Column Layout ── */}
      <div className="grid lg:grid-cols-3 gap-5">

        {/* ═══ LEFT COLUMN (2/3) — Authority Engine + Portals ═══ */}
        <div className="lg:col-span-2 space-y-5">

          {/* Section A: Authority Recommendation Engine */}
          <Panel
            title="Recommended Reporting Authorities (India)"
            subtitle="Ranked by relevance to detected scam type"
            actions={
              <div className="flex items-center gap-2">
                <Filter size={13} className="text-text-muted" />
                <select
                  value={selectedScamType}
                  onChange={(e) => setSelectedScamType(e.target.value)}
                  className="bg-surface-700 border border-border rounded px-2 py-1 text-[11px] text-text-secondary focus:outline-none focus:border-accent/50"
                >
                  <option value="all">All Scam Types</option>
                  <option value="telecom">Telecom / SIM / SMS</option>
                  <option value="upi">UPI / Payment</option>
                  <option value="phishing">Phishing / Links</option>
                  <option value="impersonation">Impersonation</option>
                  <option value="financial">Financial Fraud</option>
                  <option value="bank">Bank Fraud</option>
                </select>
              </div>
            }
          >
            <div className="space-y-3">
              {filteredAuthorities.map((authority, idx) => {
                const Icon = authority.icon;
                const isExpanded = expandedAuthority === authority.id;
                const badgeColorMap = {
                  accent: 'bg-accent/15 text-accent border-accent/20',
                  critical: 'bg-severity-critical/15 text-severity-critical border-severity-critical/20',
                  high: 'bg-severity-high/15 text-severity-high border-severity-high/20',
                };
                const badgeClasses = badgeColorMap[authority.badgeColor] || badgeColorMap.accent;

                return (
                  <div
                    key={authority.id}
                    className="bg-surface-700/40 border border-border/60 rounded-lg overflow-hidden hover:border-border-hover transition-colors"
                  >
                    {/* Authority Card Header */}
                    <div
                      className="flex items-start gap-3 p-4 cursor-pointer"
                      onClick={() => toggleAuthority(authority.id)}
                    >
                      {/* Rank */}
                      <div className="flex items-center justify-center w-7 h-7 rounded-full bg-surface-600 text-[11px] font-bold text-text-muted shrink-0 mt-0.5">
                        {idx + 1}
                      </div>

                      {/* Icon */}
                      <div className={`p-2 rounded-lg border shrink-0 ${badgeClasses}`}>
                        <Icon size={18} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-semibold text-text-primary">{authority.fullTitle}</h4>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border ${badgeClasses}`}>
                            {authority.badge}
                          </span>
                        </div>
                        <p className="text-xs text-text-secondary mt-1 leading-relaxed">{authority.description}</p>
                      </div>

                      {/* Expand Toggle */}
                      <button className="text-text-muted hover:text-text-secondary transition-colors shrink-0 mt-1">
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="border-t border-border/50 bg-surface-800/30">
                        <div className="p-4 grid sm:grid-cols-2 gap-4">
                          {/* When to Report */}
                          <div>
                            <h5 className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2 flex items-center gap-1.5">
                              <AlertTriangle size={12} />
                              When to Report Here
                            </h5>
                            <ul className="space-y-1.5">
                              {authority.useWhen.map((item, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                                  <CheckCircle size={12} className="text-severity-low shrink-0 mt-0.5" />
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Required Data */}
                          <div>
                            <h5 className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2 flex items-center gap-1.5">
                              <FileText size={12} />
                              Required Evidence
                            </h5>
                            <ul className="space-y-1.5">
                              {authority.requiredData.map((item, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                                  <div className="w-1.5 h-1.5 rounded-full bg-accent/60 shrink-0 mt-1.5" />
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        {/* Bank Note (NPCI specific) */}
                        {authority.bankNote && (
                          <div className="mx-4 mb-3 px-3 py-2 bg-severity-high/10 border border-severity-high/20 rounded text-xs text-severity-high flex items-start gap-2">
                            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                            <span>{authority.bankNote}</span>
                          </div>
                        )}

                        {/* CTA Row */}
                        <div className="px-4 pb-4 flex items-center gap-3 flex-wrap">
                          <a
                            href={authority.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-text-inverse rounded-md text-xs font-semibold hover:bg-accent-dim transition-colors"
                          >
                            <ExternalLink size={14} />
                            {authority.cta}
                          </a>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleCopyUrl(authority.url); }}
                            className="inline-flex items-center gap-1.5 px-3 py-2 bg-surface-600 text-text-secondary hover:text-text-primary rounded-md text-xs font-medium hover:bg-surface-500 border border-border transition-colors"
                          >
                            <Copy size={12} />
                            {copyFeedback === authority.url ? 'Copied!' : 'Copy Link'}
                          </button>
                          <span className="text-[10px] text-text-muted flex items-center gap-1">
                            <ExternalLink size={10} />
                            Opens external government portal
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {filteredAuthorities.length === 0 && (
                <div className="text-center py-8 text-xs text-text-muted">
                  No authorities match the selected scam type filter.
                </div>
              )}
            </div>
          </Panel>

          {/* ── Evidence Packaging Panel ── */}
          <Panel
            title="Evidence Packet Builder"
            subtitle="Auto-generated compliance-ready evidence for filing"
            actions={
              <div className="flex items-center gap-1.5">
                <Lock size={12} className="text-accent" />
                <span className="text-[10px] text-accent font-medium">Audit-Ready</span>
              </div>
            }
          >
            <div className="space-y-4">
              {/* Evidence Summary Preview */}
              <div className="bg-surface-900/50 border border-border/50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <FileText size={13} className="text-accent" />
                    Evidence Packet Contents
                  </h5>
                  <span className="text-[10px] text-text-muted">Auto-generated from session data</span>
                </div>

                <div className="grid sm:grid-cols-2 gap-2">
                  {[
                    { label: 'Scam Summary', desc: 'Plain language narrative', icon: FileText, included: evidenceOptions.includeSummary },
                    { label: 'Risk Verdict', desc: 'Score + confidence level', icon: AlertTriangle, included: true },
                    { label: 'Conversation Timeline', desc: 'Chronological message log', icon: Clock, included: evidenceOptions.includeTimeline },
                    { label: 'Extracted Artifacts', desc: 'UPI IDs, phones, URLs, accounts', icon: Search, included: evidenceOptions.includeArtifacts },
                    { label: 'Closure Reason', desc: 'Why session was terminated', icon: CheckCircle, included: true },
                    { label: 'Classification Report', desc: 'Scam type & tactic analysis', icon: Shield, included: true },
                  ].map((item, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded border ${
                        item.included
                          ? 'bg-accent/5 border-accent/15 text-text-primary'
                          : 'bg-surface-700/30 border-border/30 text-text-muted'
                      }`}
                    >
                      <item.icon size={14} className={item.included ? 'text-accent' : 'text-text-muted'} />
                      <div>
                        <div className="text-[11px] font-medium">{item.label}</div>
                        <div className="text-[10px] text-text-muted">{item.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidence Options */}
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={evidenceOptions.maskPII}
                    onChange={(e) => setEvidenceOptions(prev => ({ ...prev, maskPII: e.target.checked }))}
                    className="w-3.5 h-3.5 rounded border-border bg-surface-700 text-accent focus:ring-accent/30"
                  />
                  <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Mask PII</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={evidenceOptions.includeRaw}
                    onChange={(e) => setEvidenceOptions(prev => ({ ...prev, includeRaw: e.target.checked }))}
                    className="w-3.5 h-3.5 rounded border-border bg-surface-700 text-accent focus:ring-accent/30"
                  />
                  <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Include Raw Messages</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={evidenceOptions.includeTimeline}
                    onChange={(e) => setEvidenceOptions(prev => ({ ...prev, includeTimeline: e.target.checked }))}
                    className="w-3.5 h-3.5 rounded border-border bg-surface-700 text-accent focus:ring-accent/30"
                  />
                  <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Include Timeline</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={evidenceOptions.includeArtifacts}
                    onChange={(e) => setEvidenceOptions(prev => ({ ...prev, includeArtifacts: e.target.checked }))}
                    className="w-3.5 h-3.5 rounded border-border bg-surface-700 text-accent focus:ring-accent/30"
                  />
                  <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Include Artifacts</span>
                </label>
              </div>

              {/* Download Actions */}
              <div className="flex items-center gap-3 pt-1">
                <Button variant="primary" size="md">
                  <Download size={14} />
                  Download Evidence (PDF)
                </Button>
                <Button variant="secondary" size="md">
                  <Download size={14} />
                  Export as ZIP
                </Button>
                <span className="text-[10px] text-text-muted ml-1">
                  Analysts should never manually copy-paste evidence
                </span>
              </div>
            </div>
          </Panel>
        </div>

        {/* ═══ RIGHT COLUMN (1/3) — Checklist + Quick Links ═══ */}
        <div className="space-y-5">

          {/* Guided Filing Checklist */}
          <Panel
            title="Before You File"
            subtitle="Pre-filing readiness checklist"
            actions={
              <span className={`text-[11px] font-mono font-bold ${
                checklistProgress.pct === 100 ? 'text-severity-low' : 'text-text-muted'
              }`}>
                {checklistProgress.checked}/{checklistProgress.total}
              </span>
            }
          >
            <div className="space-y-3">
              {/* Progress Bar */}
              <div className="h-1.5 rounded-full bg-surface-600 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    checklistProgress.pct === 100 ? 'bg-severity-low' : checklistProgress.pct >= 50 ? 'bg-severity-medium' : 'bg-accent'
                  }`}
                  style={{ width: `${checklistProgress.pct}%` }}
                />
              </div>

              {/* Checklist Items */}
              <div className="space-y-1">
                {FILING_CHECKLIST.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => toggleChecklist(item.id)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 rounded-md text-left transition-colors ${
                      checklist[item.id]
                        ? 'bg-severity-low/8 hover:bg-severity-low/12'
                        : 'hover:bg-surface-700/50'
                    }`}
                  >
                    {checklist[item.id] ? (
                      <CheckSquare size={15} className="text-severity-low shrink-0 mt-0.5" />
                    ) : (
                      <Square size={15} className="text-text-muted shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <span className={`text-xs font-medium ${
                        checklist[item.id] ? 'text-severity-low line-through opacity-70' : 'text-text-secondary'
                      }`}>
                        {item.label}
                      </span>
                      {item.required && !checklist[item.id] && (
                        <span className="ml-1.5 text-[9px] text-severity-critical font-semibold uppercase">Required</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>

              {/* Checklist Complete State */}
              {checklistProgress.pct === 100 && (
                <div className="flex items-center gap-2 px-3 py-2 bg-severity-low/10 border border-severity-low/20 rounded text-xs text-severity-low">
                  <CheckCircle size={14} />
                  <span className="font-medium">Ready to file complaint</span>
                </div>
              )}
            </div>
          </Panel>

          {/* Quick Portal Links */}
          <Panel title="Quick Portal Access" subtitle="Direct links to filing portals">
            <div className="space-y-2">
              {AUTHORITIES.map((authority) => {
                const Icon = authority.icon;
                return (
                  <a
                    key={authority.id}
                    href={authority.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md bg-surface-700/30 border border-border/40 hover:border-accent/30 hover:bg-surface-700/60 transition-all group"
                  >
                    <Icon size={15} className="text-text-muted group-hover:text-accent transition-colors shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-text-secondary group-hover:text-text-primary transition-colors truncate">
                        {authority.name}
                      </div>
                      <div className="text-[10px] text-text-muted truncate">{authority.badge}</div>
                    </div>
                    <ArrowUpRight size={13} className="text-text-muted group-hover:text-accent transition-colors shrink-0" />
                  </a>
                );
              })}
            </div>
          </Panel>

          {/* Analyst Notes */}
          <Panel title="Analyst Notes" subtitle="Optional tracking for filed complaints">
            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-text-muted font-medium block mb-1.5">Complaint Reference</label>
                <input
                  type="text"
                  placeholder="e.g., NCRP-2026-XXXXX"
                  className="w-full bg-surface-700 border border-border rounded px-3 py-2 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/50 transition-colors"
                />
              </div>
              <div>
                <label className="text-[11px] text-text-muted font-medium block mb-1.5">Filed On</label>
                <input
                  type="date"
                  className="w-full bg-surface-700 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent/50 transition-colors"
                />
              </div>
              <div>
                <label className="text-[11px] text-text-muted font-medium block mb-1.5">Notes</label>
                <textarea
                  rows={3}
                  placeholder="Add notes about the filing..."
                  className="w-full bg-surface-700 border border-border rounded px-3 py-2 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/50 transition-colors resize-none"
                />
              </div>
              <Button variant="secondary" size="sm" className="w-full">
                <FileWarning size={13} />
                Save Filing Record
              </Button>
              <p className="text-[10px] text-text-muted text-center">
                Complaint reference numbers are stored locally and not transmitted.
              </p>
            </div>
          </Panel>

          {/* Escalation Flow */}
          <Panel title="Escalation Flow" subtitle="Standard operating procedure">
            <div className="space-y-0">
              {[
                { step: 1, label: 'Detect & Score', desc: 'Automated scam detection', color: 'text-severity-info', done: true },
                { step: 2, label: 'Analyze & Close', desc: 'Analyst investigation', color: 'text-severity-medium', done: true },
                { step: 3, label: 'Package Evidence', desc: 'Export compliance packet', color: 'text-severity-high', done: false },
                { step: 4, label: 'File Complaint', desc: 'Submit to authority portal', color: 'text-accent', done: false },
                { step: 5, label: 'Track Status', desc: 'Manual status updates', color: 'text-severity-low', done: false },
              ].map((s, i, arr) => (
                <div key={s.step} className="flex items-start gap-3">
                  {/* Vertical Line + Step Number */}
                  <div className="flex flex-col items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      s.done
                        ? 'bg-severity-low/20 text-severity-low'
                        : 'bg-surface-600 text-text-muted'
                    }`}>
                      {s.done ? <CheckCircle size={13} /> : s.step}
                    </div>
                    {i < arr.length - 1 && (
                      <div className={`w-px h-8 ${s.done ? 'bg-severity-low/30' : 'bg-border'}`} />
                    )}
                  </div>

                  {/* Step Content */}
                  <div className="pb-4">
                    <div className={`text-xs font-semibold ${s.done ? 'text-text-muted line-through' : 'text-text-primary'}`}>
                      {s.label}
                    </div>
                    <div className="text-[10px] text-text-muted">{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
