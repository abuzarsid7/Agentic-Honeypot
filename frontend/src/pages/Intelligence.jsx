import { useState, useMemo } from 'react';
import {
  Database, Search, Phone, Link, CreditCard, Key,
  BarChart2, Network, Download, Filter, Hash,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { Panel, TabGroup, Tag, SeverityBadge, Button, EmptyState, DataTable } from '../components/ui';
import { maskPII } from '../utils';
import clsx from 'clsx';

/* ═══════════════════════════════════════════════════════════════
   INTELLIGENCE REPOSITORY — Cross-session intel aggregation
   Entity tables + correlation + search + export
   ═══════════════════════════════════════════════════════════════ */

const DEMO_UPI = [
  { id: 1, value: 'ramesh.verify@ybl', sessions: ['ses_4f2a8c', 'ses_1e5d7c'], occurrences: 3, firstSeen: '2026-02-12T14:20:00', lastSeen: '2026-02-13T09:15:00', confidence: 'high' },
  { id: 2, value: 'support.rbi@paytm', sessions: ['ses_8d1e3b'], occurrences: 1, firstSeen: '2026-02-13T10:00:00', lastSeen: '2026-02-13T10:00:00', confidence: 'medium' },
  { id: 3, value: 'kyc.verify2024@okaxis', sessions: ['ses_9a3f1d', 'ses_3a9c8e'], occurrences: 4, firstSeen: '2026-02-11T08:30:00', lastSeen: '2026-02-13T11:20:00', confidence: 'high' },
];

const DEMO_PHONES = [
  { id: 1, value: '+919876543210', sessions: ['ses_4f2a8c'], occurrences: 2, firstSeen: '2026-02-12T14:22:00', lastSeen: '2026-02-13T09:00:00', confidence: 'high' },
  { id: 2, value: '+918765432109', sessions: ['ses_2c7b9a', 'ses_6b4e2f'], occurrences: 3, firstSeen: '2026-02-10T16:00:00', lastSeen: '2026-02-13T10:30:00', confidence: 'high' },
];

const DEMO_URLS = [
  { id: 1, value: 'http://rbi-verify-secure.xyz/form', sessions: ['ses_4f2a8c'], occurrences: 1, firstSeen: '2026-02-13T14:24:00', lastSeen: '2026-02-13T14:24:00', confidence: 'high', domain: 'rbi-verify-secure.xyz' },
  { id: 2, value: 'https://kyc-update-sbi.com/verify', sessions: ['ses_9a3f1d'], occurrences: 2, firstSeen: '2026-02-12T09:10:00', lastSeen: '2026-02-13T11:00:00', confidence: 'high', domain: 'kyc-update-sbi.com' },
  { id: 3, value: 'http://secure-banking-alert.in/login', sessions: ['ses_2c7b9a', 'ses_7d2f5a'], occurrences: 3, firstSeen: '2026-02-11T07:00:00', lastSeen: '2026-02-13T08:40:00', confidence: 'medium', domain: 'secure-banking-alert.in' },
];

const DEMO_ACCOUNTS = [
  { id: 1, value: '12345678901234', sessions: ['ses_3a9c8e'], occurrences: 1, firstSeen: '2026-02-13T10:20:00', lastSeen: '2026-02-13T10:20:00', confidence: 'medium' },
];

const DEMO_KEYWORDS_AGG = [
  { keyword: 'verify', count: 18 },
  { keyword: 'urgent', count: 15 },
  { keyword: 'blocked', count: 12 },
  { keyword: 'RBI', count: 10 },
  { keyword: 'KYC', count: 9 },
  { keyword: 'OTP', count: 7 },
  { keyword: 'suspend', count: 6 },
  { keyword: 'payment', count: 5 },
];

const TABS = [
  { key: 'upi', label: 'UPI IDs', count: DEMO_UPI.length },
  { key: 'phone', label: 'Phone Numbers', count: DEMO_PHONES.length },
  { key: 'url', label: 'Phishing URLs', count: DEMO_URLS.length },
  { key: 'account', label: 'Bank Accounts', count: DEMO_ACCOUNTS.length },
  { key: 'keywords', label: 'Keywords' },
];

export default function Intelligence() {
  const [activeTab, setActiveTab] = useState('upi');
  const [search, setSearch] = useState('');
  const [piiVisible, setPiiVisible] = useState(false);

  const artifactColumns = [
    {
      key: 'value',
      label: 'Artifact',
      render: (v) => (
        <span className="font-mono text-xs text-accent">{maskPII(v, piiVisible)}</span>
      ),
    },
    {
      key: 'occurrences',
      label: 'Occurrences',
      render: (v) => <span className="font-mono">{v}</span>,
    },
    {
      key: 'sessions',
      label: 'Linked Sessions',
      render: (v) => (
        <div className="flex gap-1 flex-wrap">
          {(v || []).map(s => (
            <Tag key={s} variant="accent">{s}</Tag>
          ))}
        </div>
      ),
    },
    {
      key: 'confidence',
      label: 'Confidence',
      render: (v) => <SeverityBadge label={v === 'high' ? 'critical' : v === 'medium' ? 'medium' : 'low'} />,
    },
    {
      key: 'lastSeen',
      label: 'Last Seen',
      render: (v) => <span className="text-text-muted">{v ? new Date(v).toLocaleString('en-IN', { hour12: false }) : '—'}</span>,
    },
  ];

  const dataMap = {
    upi: DEMO_UPI,
    phone: DEMO_PHONES,
    url: DEMO_URLS,
    account: DEMO_ACCOUNTS,
  };

  const filteredData = useMemo(() => {
    const data = dataMap[activeTab] || [];
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter(d =>
      d.value.toLowerCase().includes(q) ||
      d.sessions?.some(s => s.toLowerCase().includes(q))
    );
  }, [activeTab, search]);

  return (
    <div className="space-y-4">
      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'UPI IDs', count: DEMO_UPI.length, icon: Key, color: 'text-accent' },
          { label: 'Phone Numbers', count: DEMO_PHONES.length, icon: Phone, color: 'text-severity-info' },
          { label: 'Phishing URLs', count: DEMO_URLS.length, icon: Link, color: 'text-severity-critical' },
          { label: 'Bank Accounts', count: DEMO_ACCOUNTS.length, icon: CreditCard, color: 'text-severity-high' },
        ].map(s => (
          <div key={s.label} className="bg-surface-800 border border-border rounded-lg p-3 flex items-center gap-3">
            <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center bg-surface-700', s.color)}>
              <s.icon size={16} />
            </div>
            <div>
              <span className="text-lg font-semibold font-mono text-text-primary">{s.count}</span>
              <p className="text-[11px] text-text-muted">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main artifact table */}
        <div className="lg:col-span-2">
          <Panel
            title="Intelligence Artifacts"
            subtitle="Cross-session consolidated view"
            actions={
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="xs" onClick={() => setPiiVisible(!piiVisible)}>
                  {piiVisible ? 'Mask PII' : 'Show PII'}
                </Button>
                <Button variant="secondary" size="xs">
                  <Download size={11} />
                  Export
                </Button>
              </div>
            }
          >
            <TabGroup tabs={TABS} active={activeTab} onChange={setActiveTab} />

            <div className="mt-3 mb-3">
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search artifacts..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full bg-surface-700 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50"
                />
              </div>
            </div>

            {activeTab !== 'keywords' ? (
              <DataTable columns={artifactColumns} rows={filteredData} />
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={DEMO_KEYWORDS_AGG} layout="vertical" margin={{ left: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis type="category" dataKey="keyword" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                    <Tooltip
                      contentStyle={{ background: '#0f1520', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
                    />
                    <Bar dataKey="count" fill="#14b8a6" radius={[0, 4, 4, 0]} barSize={16} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {activeTab !== 'keywords' && filteredData.length === 0 && (
              <EmptyState icon={Database} title="No artifacts found" description="Adjust search or check other categories" />
            )}
          </Panel>
        </div>

        {/* Entity correlation sidebar */}
        <div>
          <Panel title="Entity Correlation" subtitle="Shared artifacts across sessions">
            <div className="space-y-3">
              <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Cross-Session Links</div>
              {[
                { artifact: 'ramesh.verify@ybl', sessions: 2, type: 'UPI' },
                { artifact: 'kyc.verify2024@okaxis', sessions: 2, type: 'UPI' },
                { artifact: '+918765432109', sessions: 2, type: 'Phone' },
                { artifact: 'secure-banking-alert.in', sessions: 2, type: 'Domain' },
              ].map((link, i) => (
                <div key={i} className="bg-surface-700/50 rounded-md p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-accent">{maskPII(link.artifact, piiVisible)}</span>
                    <Tag>{link.type}</Tag>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Network size={11} className="text-text-muted" />
                    <span className="text-[11px] text-text-secondary">
                      Seen across {link.sessions} sessions
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Top Domains" subtitle="Most frequently phished" className="mt-4">
            <div className="space-y-2">
              {DEMO_URLS.map((u, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0">
                  <span className="text-xs text-severity-critical font-mono">{u.domain}</span>
                  <span className="text-[10px] text-text-muted">{u.occurrences}x</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
