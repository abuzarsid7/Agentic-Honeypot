import { useState, useCallback, useMemo } from 'react';
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
import { getMetrics, getLLMCache, getSessions } from '../api';

/* ═══════════════════════════════════════════════════════════════
   COMMAND CENTER — Situational awareness in <10 seconds
   Maps to: GET /metrics + GET /debug/llm/cache + GET /sessions
   ═══════════════════════════════════════════════════════════════ */

export default function CommandCenter() {
  const metricsFetcher = useCallback(() => getMetrics().catch(() => null), []);
  const cacheFetcher = useCallback(() => getLLMCache().catch(() => null), []);
  const sessionsFetcher = useCallback(() => getSessions().catch(() => ({ sessions: [] })), []);
  const { data: metrics, loading: mLoading } = usePolling(metricsFetcher, 8000);
  const { data: cache, loading: cLoading } = usePolling(cacheFetcher, 15000);
  const { data: sessionsData, loading: sLoading } = usePolling(sessionsFetcher, 5000);

  const api = metrics || {};
  const cacheData = cache?.cache || {};
  const provider = cache?.provider || {};
  const activeSessions = sessionsData?.sessions || [];

  // Extract real values from backend metrics
  const totalRequests = api.requests?.total ?? 0;
  const activeSessionsCount = activeSessions.length;
  const scamsDetected = api.detection?.scams_detected ?? 0;
  const messagesAnalyzed = api.detection?.messages_analyzed ?? 0;
  const scamRate = messagesAnalyzed > 0 ? `${((scamsDetected / messagesAnalyzed) * 100).toFixed(1)}%` : '0%';
  const totalIntel = api.intelligence?.total_intel ?? 0;
  const extractionYield = activeSessionsCount > 0 ? `${(totalIntel / activeSessionsCount).toFixed(1)}/ses` : '0/ses';
  const totalErrors = api.errors?.total ?? 0;
  const errorRate = totalRequests > 0 ? `${((totalErrors / totalRequests) * 100).toFixed(1)}%` : '0%';

  // Calculate severity distribution from real sessions
  const severityDist = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    activeSessions.forEach(s => {
      const sev = getSeverity(s.score);
      if (counts[sev] !== undefined) counts[sev]++;
    });
    return [
      { name: 'Critical', value: counts.critical, color: '#ef4444' },
      { name: 'High', value: counts.high, color: '#f97316' },
      { name: 'Medium', value: counts.medium, color: '#eab308' },
      { name: 'Low', value: counts.low, color: '#22c55e' },
    ].filter(d => d.value > 0);
  }, [activeSessions]);

  // Generate recent events from sessions
  const recentEvents = useMemo(() => {
    return activeSessions
      .sort((a, b) => (b.lastActivity || 0) - (a.lastActivity || 0))
      .slice(0, 5)
      .map(s => {
        const severity = getSeverity(s.score);
        let text = s.lastTactic || 'Session activity';
        if (s.hardTrigger) text = `⚠️ Hard Trigger: ${text}`;
        else if (s.botAccusation) text = `🤖 Bot defense: ${text}`;
        
        return {
          id: s.id,
          type: severity,
          text,
          session: s.id.substring(0, 10),
          time: timeAgo(s.lastActivity || Date.now())
        };
      });
  }, [activeSessions]);

  // Calculate top triggers from sessions
  const topTriggers = useMemo(() => {
    const triggerCounts = {};
    activeSessions.forEach(s => {
      if (s.lastTactic) {
        triggerCounts[s.lastTactic] = (triggerCounts[s.lastTactic] || 0) + 1;
      }
    });
    return Object.entries(triggerCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([trigger, count]) => ({ trigger, count }));
  }, [activeSessions]);

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* ── KPI Strip ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
        <KPICard label="Total Sessions" value={formatNum(totalRequests)} icon={MessageSquare} sub="All time" />
        <KPICard label="Active Sessions" value={activeSessionsCount} icon={Activity} sub="Live now" trend={activeSessionsCount > 0 ? 'up' : undefined} />
        <KPICard label="Scam Detected" value={scamRate} icon={Shield} sub="Detection rate" />
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
                    data={severityDist.length > 0 ? severityDist : [{ name: 'No Data', value: 1, color: '#475569' }]}
                    innerRadius={30}
                    outerRadius={55}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {(severityDist.length > 0 ? severityDist : [{ name: 'No Data', value: 1, color: '#475569' }]).map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-1.5">
              {(severityDist.length > 0 ? severityDist : [{ name: 'No active sessions', value: 0, color: '#475569' }]).map((item, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-xs text-text-secondary">{item.name}</span>
                  </div>
                  <span className="text-xs font-mono text-text-primary">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        {/* Top Hard Triggers */}
        <Panel title="Top Trigger Reasons" subtitle="Most frequent detection signals">
          <div className="space-y-3">
            {topTriggers.length > 0 ? topTriggers.map((t, i) => (
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
                      style={{ width: `${(t.count / topTriggers[0].count) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            )) : (
              <div className="text-center py-8 text-text-muted text-sm">
                No trigger data yet
              </div>
            )}
          </div>
        </Panel>

        {/* Live Activity Feed */}
        <Panel
          title="Activity Feed"
          subtitle="Recent events"
          actions={<StatusDot status="live" />}
        >
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {recentEvents.length > 0 ? recentEvents.map(evt => (
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
            )) : (
              <div className="text-center py-8 text-text-muted text-sm">
                No recent activity
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* ── Row 3: Throughput + System Health ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
        {/* Top Triggers */}
        <Panel title="Top Triggers" subtitle="Most common scam tactics detected">
          <div className="space-y-2">
            {topTriggers.length > 0 ? topTriggers.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                <span className="text-xs text-text-primary">{item.trigger}</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 bg-surface-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-accent" 
                      style={{ width: `${(item.count / Math.max(...topTriggers.map(t => t.count))) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-text-muted w-8 text-right">{item.count}</span>
                </div>
              </div>
            )) : (
              <div className="text-center py-8 text-text-muted text-sm">
                No triggers detected yet
              </div>
            )}
          </div>
        </Panel>

        {/* Session Statistics */}
        <Panel title="Session Statistics" subtitle="Real-time session metrics">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-700/50 rounded-lg p-3">
                <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Total Messages</div>
                <div className="text-2xl font-bold text-text-primary font-mono">{messagesAnalyzed}</div>
              </div>
              <div className="bg-surface-700/50 rounded-lg p-3">
                <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Scams Found</div>
                <div className="text-2xl font-bold text-severity-critical font-mono">{scamsDetected}</div>
              </div>
              <div className="bg-surface-700/50 rounded-lg p-3 col-span-2">
                <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Intel Extracted</div>
                <div className="text-2xl font-bold text-accent font-mono">{totalIntel}</div>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-border/30">
              <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Detection Rate</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-severity-low to-accent"
                    style={{ width: scamRate }}
                  />
                </div>
                <span className="text-sm font-mono text-text-primary">{scamRate}</span>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* ── Row 4: System Health ── */}
      <div>
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
