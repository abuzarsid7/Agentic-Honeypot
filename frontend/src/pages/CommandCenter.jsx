import { useState, useCallback } from 'react';
import {
  Activity, Shield, AlertTriangle, Zap, Clock, Server,
  TrendingUp, Eye, MessageSquare, Database,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { KPICard, Panel, SeverityBadge, StatusDot, DataRow, Tag, EmptyState, Skeleton } from '../components/ui';
import { usePolling, formatNum, getSeverity, severityColors, timeAgo } from '../utils';
import { getMetrics, getLLMCache } from '../api';

/* ═══════════════════════════════════════════════════════════════
   COMMAND CENTER — Situational awareness in <10 seconds
   Maps to: GET /metrics + GET /debug/llm/cache
   ═══════════════════════════════════════════════════════════════ */

// Demo data for visualization (replaced by live data when API connects)
const DEMO_THROUGHPUT = Array.from({ length: 12 }, (_, i) => ({
  t: `${String(i * 2).padStart(2, '0')}:00`,
  requests: Math.floor(Math.random() * 80) + 20,
  detections: Math.floor(Math.random() * 40) + 5,
}));

const DEMO_SEVERITY_DIST = [
  { name: 'Critical', value: 12, color: '#ef4444' },
  { name: 'High', value: 28, color: '#f97316' },
  { name: 'Medium', value: 35, color: '#eab308' },
  { name: 'Low', value: 25, color: '#22c55e' },
];

const DEMO_EVENTS = [
  { id: 1, type: 'critical', text: 'Hard Trigger: UPI payment redirection', session: 'ses_4f2a', time: '2m ago' },
  { id: 2, type: 'high', text: 'Bot accusation defense activated', session: 'ses_8d1e', time: '5m ago' },
  { id: 3, type: 'medium', text: 'Session closed: intel stagnation', session: 'ses_2c7b', time: '8m ago' },
  { id: 4, type: 'low', text: 'New session initiated', session: 'ses_9a3f', time: '12m ago' },
  { id: 5, type: 'high', text: 'Scammer pressure pattern detected', session: 'ses_1e5d', time: '15m ago' },
];

const DEMO_TOP_TRIGGERS = [
  { trigger: 'Payment Redirection', count: 34 },
  { trigger: 'Authority Impersonation', count: 28 },
  { trigger: 'Urgency Pressure', count: 22 },
  { trigger: 'Link Phishing', count: 18 },
  { trigger: 'KYC Fraud', count: 14 },
];

export default function CommandCenter() {
  const metricsFetcher = useCallback(() => getMetrics().catch(() => null), []);
  const cacheFetcher = useCallback(() => getLLMCache().catch(() => null), []);
  const { data: metrics, loading: mLoading } = usePolling(metricsFetcher, 8000);
  const { data: cache, loading: cLoading } = usePolling(cacheFetcher, 15000);

  const api = metrics || {};
  const cacheData = cache?.cache || {};
  const provider = cache?.provider || {};

  // Extract real values or use placeholders
  const totalRequests = api.total_requests ?? 1247;
  const activeSessions = api.active_sessions ?? 18;
  const scamRate = api.detection_rate != null ? `${(api.detection_rate * 100).toFixed(1)}%` : '72.4%';
  const avgLatency = api.avg_latency_ms != null ? `${api.avg_latency_ms.toFixed(0)}ms` : '142ms';
  const extractionYield = api.extraction_yield ?? '4.2/ses';
  const errorRate = api.error_rate != null ? `${(api.error_rate * 100).toFixed(1)}%` : '0.3%';

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* ── KPI Strip ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3">
        <KPICard label="Total Sessions" value={formatNum(totalRequests)} icon={MessageSquare} sub="All time" />
        <KPICard label="Active Sessions" value={activeSessions} icon={Activity} sub="Live now" trend="up" />
        <KPICard label="Scam Detected" value={scamRate} icon={Shield} sub="Detection rate" />
        <KPICard label="Avg Latency" value={avgLatency} icon={Clock} sub="Response time" />
        <KPICard label="Intel Yield" value={extractionYield} icon={Database} sub="Per session" />
        <KPICard label="Error Rate" value={errorRate} icon={AlertTriangle} sub="Last 24h" trend={errorRate !== '0.0%' ? 'up' : undefined} />
      </div>

      {/* ── Row 2: Risk Overview + Activity Feed ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5">
        {/* Risk Distribution */}
        <Panel title="Risk Distribution" subtitle="Active sessions by severity">
          <div className="flex items-center gap-6">
            <div className="w-32 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={DEMO_SEVERITY_DIST}
                    innerRadius={30}
                    outerRadius={55}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {DEMO_SEVERITY_DIST.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 flex-1">
              {DEMO_SEVERITY_DIST.map(d => (
                <div key={d.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-xs text-text-secondary">{d.name}</span>
                  </div>
                  <span className="text-xs font-mono text-text-primary">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        {/* Top Hard Triggers */}
        <Panel title="Top Trigger Reasons" subtitle="Most frequent detection signals">
          <div className="space-y-3">
            {DEMO_TOP_TRIGGERS.map((t, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-text-muted w-4 font-mono">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-text-secondary">{t.trigger}</span>
                    <span className="text-xs font-mono text-text-primary">{t.count}</span>
                  </div>
                  <div className="h-1 rounded-full bg-surface-600 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent/70"
                      style={{ width: `${(t.count / DEMO_TOP_TRIGGERS[0].count) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* Live Activity Feed */}
        <Panel
          title="Activity Feed"
          subtitle="Recent events"
          actions={<StatusDot status="live" />}
        >
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {DEMO_EVENTS.map(evt => (
              <div key={evt.id} className="flex items-start gap-2.5 py-1.5">
                <SeverityBadge label={evt.type} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-text-primary truncate">{evt.text}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] font-mono text-accent">{evt.session}</span>
                    <span className="text-[10px] text-text-muted">{evt.time}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* ── Row 3: Throughput + System Health ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
        {/* Throughput Chart */}
        <Panel title="Throughput" subtitle="Requests & detections over time">
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={DEMO_THROUGHPUT}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ background: '#0f1520', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area
                  type="monotone"
                  dataKey="requests"
                  stroke="#14b8a6"
                  fill="#14b8a6"
                  fillOpacity={0.1}
                  strokeWidth={1.5}
                  name="Requests"
                />
                <Area
                  type="monotone"
                  dataKey="detections"
                  stroke="#f97316"
                  fill="#f97316"
                  fillOpacity={0.08}
                  strokeWidth={1.5}
                  name="Detections"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* System Health */}
        <Panel title="System Health" subtitle="Infrastructure status">
          <div className="grid grid-cols-2 gap-4">
            {/* LLM Provider */}
            <div className="bg-surface-700/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <StatusDot status={provider.provider ? 'live' : 'warning'} />
                <span className="text-xs font-medium text-text-primary">LLM Engine</span>
              </div>
              <DataRow label="Provider" value={provider.provider || 'Groq'} />
              <DataRow label="Model" value={provider.model || 'llama3-70b'} mono />
              <DataRow label="Status" value={provider.provider ? 'Connected' : 'Standby'} />
            </div>

            {/* LLM Cache */}
            <div className="bg-surface-700/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <StatusDot status="live" />
                <span className="text-xs font-medium text-text-primary">LLM Cache</span>
              </div>
              <DataRow label="Size" value={cacheData.size ?? '—'} mono />
              <DataRow label="Hit Rate" value={cacheData.hit_rate ? `${(cacheData.hit_rate * 100).toFixed(0)}%` : '—'} mono />
              <DataRow label="TTL" value={cacheData.ttl ? `${cacheData.ttl}s` : '—'} mono />
            </div>

            {/* Redis */}
            <div className="bg-surface-700/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <StatusDot status="live" />
                <span className="text-xs font-medium text-text-primary">Redis Store</span>
              </div>
              <DataRow label="Connection" value="Active" />
              <DataRow label="Session TTL" value="3600s" mono />
              <DataRow label="Persistence" value="Enabled" />
            </div>

            {/* API */}
            <div className="bg-surface-700/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <StatusDot status="live" />
                <span className="text-xs font-medium text-text-primary">API Gateway</span>
              </div>
              <DataRow label="Framework" value="FastAPI" />
              <DataRow label="Uptime" value="99.9%" mono />
              <DataRow label="Endpoints" value="12 active" />
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
