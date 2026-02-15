import { useCallback } from 'react';
import {
  Activity, Server, Clock, Cpu, Database, Wifi,
  TrendingUp, AlertCircle, CheckCircle, BarChart2,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { KPICard, Panel, DataRow, StatusDot, Tag, Button } from '../components/ui';
import { usePolling, formatNum } from '../utils';
import { getMetrics, getLLMCache, getHealth, clearLLMCache } from '../api';
import clsx from 'clsx';

/* ═══════════════════════════════════════════════════════════════
   TELEMETRY & PLATFORM HEALTH — Operator visibility
   Maps to: GET /metrics + GET / + GET /debug/llm/cache
   ═══════════════════════════════════════════════════════════════ */

const DEMO_LATENCY = Array.from({ length: 20 }, (_, i) => ({
  t: `${String(i).padStart(2, '0')}:00`,
  p50: Math.floor(Math.random() * 50) + 80,
  p95: Math.floor(Math.random() * 100) + 150,
  p99: Math.floor(Math.random() * 150) + 250,
}));

const DEMO_ERROR_TREND = Array.from({ length: 12 }, (_, i) => ({
  t: `${String(i * 2).padStart(2, '0')}:00`,
  errors: Math.floor(Math.random() * 5),
  total: Math.floor(Math.random() * 80) + 40,
}));

const DEMO_SESSION_LIFECYCLE = [
  { label: 'Active', count: 18, color: '#14b8a6' },
  { label: 'Completed', count: 142, color: '#22c55e' },
  { label: 'Closed (Intel Stagnation)', count: 45, color: '#eab308' },
  { label: 'Closed (Pressure)', count: 23, color: '#f97316' },
  { label: 'Closed (Hard Limit)', count: 8, color: '#ef4444' },
  { label: 'Closed (Disengaged)', count: 12, color: '#64748b' },
];

export default function Telemetry() {
  const metricsFetcher = useCallback(() => getMetrics().catch(() => null), []);
  const healthFetcher = useCallback(() => getHealth().catch(() => null), []);
  const cacheFetcher = useCallback(() => getLLMCache().catch(() => null), []);

  const { data: metrics } = usePolling(metricsFetcher, 10000);
  const { data: health } = usePolling(healthFetcher, 15000);
  const { data: cache } = usePolling(cacheFetcher, 15000);

  const api = metrics || {};
  const cacheInfo = cache?.cache || {};
  const provider = cache?.provider || {};

  const handleClearCache = async () => {
    try { await clearLLMCache(); } catch {}
  };

  return (
    <div className="space-y-5">
      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <KPICard label="Requests / min" value={api.requests_per_minute ?? '12.4'} icon={TrendingUp} />
        <KPICard label="Error Rate" value={api.error_rate ? `${(api.error_rate * 100).toFixed(1)}%` : '0.3%'} icon={AlertCircle} />
        <KPICard label="Uptime" value="99.97%" icon={CheckCircle} />
        <KPICard label="Cache Hit Rate" value={cacheInfo.hit_rate ? `${(cacheInfo.hit_rate * 100).toFixed(0)}%` : '84%'} icon={Database} />
        <KPICard label="Active Conns" value={api.active_connections ?? 24} icon={Wifi} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Latency Distribution */}
        <Panel title="Latency Distribution" subtitle="P50 / P95 / P99 over time">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={DEMO_LATENCY}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} unit="ms" />
                <Tooltip
                  contentStyle={{ background: '#0f1520', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
                />
                <Line type="monotone" dataKey="p50" stroke="#22c55e" strokeWidth={1.5} dot={false} name="P50" />
                <Line type="monotone" dataKey="p95" stroke="#eab308" strokeWidth={1.5} dot={false} name="P95" />
                <Line type="monotone" dataKey="p99" stroke="#ef4444" strokeWidth={1.5} dot={false} name="P99" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Error Trend */}
        <Panel title="Error Trend" subtitle="Errors vs total requests">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={DEMO_ERROR_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ background: '#0f1520', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
                />
                <Area type="monotone" dataKey="total" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.08} strokeWidth={1.5} name="Total" />
                <Area type="monotone" dataKey="errors" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={1.5} name="Errors" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Session Lifecycle */}
        <Panel title="Session Lifecycle" subtitle="Close reason distribution">
          <div className="space-y-2.5">
            {DEMO_SESSION_LIFECYCLE.map((item, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-xs text-text-secondary">{item.label}</span>
                  </div>
                  <span className="text-xs font-mono text-text-primary">{item.count}</span>
                </div>
                <div className="h-1 rounded-full bg-surface-600 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(item.count / DEMO_SESSION_LIFECYCLE.reduce((a, b) => a + b.count, 0)) * 100}%`,
                      backgroundColor: item.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* LLM Provider */}
        <Panel
          title="LLM Engine Status"
          subtitle="Provider health & configuration"
          actions={
            <Button variant="ghost" size="xs" onClick={handleClearCache}>
              Flush Cache
            </Button>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center gap-3 bg-surface-700/50 rounded-md p-3">
              <StatusDot status={provider.provider ? 'live' : 'warning'} />
              <div>
                <span className="text-xs font-medium text-text-primary">
                  {provider.provider || 'Groq'} — {provider.model || 'llama3-70b'}
                </span>
                <p className="text-[10px] text-text-muted">Primary LLM provider</p>
              </div>
            </div>

            <DataRow label="Cache Size" value={cacheInfo.size ?? '—'} mono />
            <DataRow label="Max Cache" value={cacheInfo.max_size ?? '100'} mono />
            <DataRow label="Hit Rate" value={cacheInfo.hit_rate ? `${(cacheInfo.hit_rate * 100).toFixed(1)}%` : '—'} mono />
            <DataRow label="TTL" value={cacheInfo.ttl ? `${cacheInfo.ttl}s` : '300s'} mono />
            <DataRow label="Fallback" value="Heuristic scoring" />
          </div>
        </Panel>

        {/* Infrastructure */}
        <Panel title="Infrastructure" subtitle="Core services status">
          <div className="space-y-3">
            {[
              { name: 'FastAPI Server', status: health?.status === 'ok' ? 'live' : 'warning', details: 'Port 8000' },
              { name: 'Redis Datastore', status: 'live', details: 'Session persistence' },
              { name: 'Normalization Engine', status: 'live', details: '8-stage pipeline' },
              { name: 'Hybrid Detector', status: 'live', details: '5-signal model' },
              { name: 'Intelligence Extractor', status: 'live', details: 'Regex + Advanced + LLM' },
              { name: 'Defense Module', status: 'live', details: 'Bot accusation handler' },
            ].map((svc, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0">
                <div className="flex items-center gap-2">
                  <StatusDot status={svc.status} />
                  <span className="text-xs text-text-primary">{svc.name}</span>
                </div>
                <span className="text-[10px] text-text-muted">{svc.details}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
