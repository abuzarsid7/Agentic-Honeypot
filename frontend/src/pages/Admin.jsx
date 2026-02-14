import { useState } from 'react';
import {
  Settings, Key, Users, Shield, Sliders, Eye, EyeOff,
  Save, AlertTriangle, Lock, History, Trash2, Send,
} from 'lucide-react';
import { Panel, Button, DataRow, Tag, TabGroup } from '../components/ui';
import { sendMessage } from '../api';
import clsx from 'clsx';

/* ═══════════════════════════════════════════════════════════════
   ADMIN / SETTINGS — Access control, thresholds, audit
   ═══════════════════════════════════════════════════════════════ */

export default function Admin() {
  const [activeTab, setActiveTab] = useState('api');
  const [apiKey, setApiKey] = useState(localStorage.getItem('hp_api_key') || '');
  const [showKey, setShowKey] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [testMessage, setTestMessage] = useState('Congratulations! You won ₹50,000. Send your UPI ID to claim prize money.');
  const [testResponse, setTestResponse] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [thresholds, setThresholds] = useState({
    scamThreshold: 0.40,
    urgencyWeight: 0.20,
    authorityWeight: 0.20,
    keywordWeight: 0.25,
    paymentWeight: 0.15,
    llmWeight: 0.20,
    maxTurns: 30,
    sessionTTL: 3600,
  });

  const saveApiKey = () => {
    localStorage.setItem('hp_api_key', apiKey);
    setSaveMessage('✓ API key saved successfully');
    setTimeout(() => setSaveMessage(''), 3000);
  };

  const handleTestMessage = async () => {
    if (!testMessage.trim()) return;
    
    setTestLoading(true);
    setTestResponse(null);
    
    try {
      const result = await sendMessage(`test-${Date.now()}`, testMessage, []);
      setTestResponse({
        success: true,
        data: result
      });
    } catch (error) {
      setTestResponse({
        success: false,
        error: error.message
      });
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="space-y-4 max-w-4xl">
      <TabGroup
        tabs={[
          { key: 'api', label: 'API Configuration' },
          { key: 'thresholds', label: 'Detection Thresholds' },
          { key: 'access', label: 'Access Control' },
          { key: 'audit', label: 'Audit Log' },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* ── API Key ── */}
      {activeTab === 'api' && (
        <Panel title="API Key Configuration" subtitle="Backend authentication key">
          <div className="space-y-4">
            <div>
              <label className="text-xs text-text-muted block mb-1.5">API Key</label>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder="Enter your API key..."
                    className="w-full bg-surface-700 border border-border rounded-md px-3 py-2 text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 pr-10"
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                  >
                    {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <Button onClick={saveApiKey}>
                  <Save size={13} />
                  Save
                </Button>
              </div>
              {saveMessage && (
                <p className="text-xs text-severity-low mt-2">{saveMessage}</p>
              )}
              <p className="text-[11px] text-text-muted mt-1.5">
                This key is stored in browser localStorage and sent as X-API-Key header.
              </p>
            </div>

            <div className="bg-surface-700/50 rounded-md p-3">              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">Test Connection</span>
                {testResponse && (
                  <span className={`text-xs ${testResponse.success ? 'text-severity-low' : 'text-severity-critical'}`}>
                    {testResponse.success ? '✓ Connected' : '✗ Failed'}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                <textarea
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  placeholder="Enter a test scam message..."
                  className="w-full bg-surface-600 border border-border rounded-md px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 resize-none"
                  rows={3}
                />
                <Button 
                  onClick={handleTestMessage} 
                  disabled={testLoading || !testMessage.trim()}
                  className="w-full"
                >
                  <Send size={13} />
                  {testLoading ? 'Sending...' : 'Send Test Message'}
                </Button>
                
                {testResponse && (
                  <div className={`mt-2 p-3 rounded-md text-xs ${
                    testResponse.success 
                      ? 'bg-severity-low/10 border border-severity-low/20 text-severity-low' 
                      : 'bg-severity-critical/10 border border-severity-critical/20 text-severity-critical'
                  }`}>
                    {testResponse.success ? (
                      <>
                        <div className="font-bold mb-1">Agent Reply:</div>
                        <div className="text-text-primary">{testResponse.data.reply}</div>
                      </>
                    ) : (
                      <>
                        <div className="font-bold mb-1">Error:</div>
                        <div>{testResponse.error}</div>
                        <div className="mt-2 text-[10px]">
                          Make sure your API key is correct and the backend is running on port 8000.
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-surface-700/50 rounded-md p-3">              <span className="text-[10px] uppercase tracking-wider text-text-muted">Backend Endpoints</span>
              <div className="mt-2 space-y-1.5">
                {[
                  { method: 'POST', path: '/honeypot', desc: 'Message ingestion' },
                  { method: 'GET', path: '/metrics', desc: 'Platform telemetry' },
                  { method: 'POST', path: '/debug/score', desc: 'Score decomposition' },
                  { method: 'POST', path: '/debug/llm', desc: 'LLM analysis' },
                  { method: 'POST', path: '/debug/normalize', desc: 'Normalization trace' },
                  { method: 'POST', path: '/debug/strategy', desc: 'Dialogue state' },
                  { method: 'POST', path: '/debug/intelligence', desc: 'Intel extraction' },
                  { method: 'POST', path: '/debug/intel_score', desc: 'Intel quality score' },
                  { method: 'GET', path: '/debug/llm/cache', desc: 'Cache stats' },
                ].map((ep, i) => (
                  <div key={i} className="flex items-center gap-3 py-1 border-b border-border/30 last:border-0">
                    <Tag variant={ep.method === 'POST' ? 'accent' : 'default'}>{ep.method}</Tag>
                    <span className="text-xs font-mono text-text-primary flex-1">{ep.path}</span>
                    <span className="text-[11px] text-text-muted">{ep.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>
      )}

      {/* ── Detection Thresholds ── */}
      {activeTab === 'thresholds' && (
        <Panel
          title="Detection Thresholds"
          subtitle="Scoring model weights (read-only view)"
          actions={
            <div className="flex items-center gap-1.5 text-xs text-severity-medium">
              <Lock size={12} />
              <span>Read Only</span>
            </div>
          }
        >
          <div className="space-y-4">
            <div className="bg-severity-medium/8 border border-severity-medium/20 rounded-md px-3 py-2 flex items-center gap-2">
              <AlertTriangle size={13} className="text-severity-medium shrink-0" />
              <span className="text-[11px] text-severity-medium">
                Threshold changes require backend deployment. Frontend display only.
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {Object.entries(thresholds).map(([key, value]) => (
                <div key={key} className="bg-surface-700/50 rounded-md p-3">
                  <label className="text-[10px] uppercase tracking-wider text-text-muted">
                    {key.replace(/([A-Z])/g, ' $1').trim()}
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    <input
                      type="number"
                      value={value}
                      readOnly
                      step={key.includes('eight') ? 0.05 : key.includes('TTL') || key.includes('Turns') ? 1 : 0.05}
                      className="w-full bg-surface-600 border border-border rounded px-2.5 py-1.5 text-sm font-mono text-text-primary cursor-not-allowed"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      )}

      {/* ── Access Control ── */}
      {activeTab === 'access' && (
        <Panel title="Role-Based Access" subtitle="Permission matrix">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">Permission</th>
                  <th className="text-center py-2 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">Analyst</th>
                  <th className="text-center py-2 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">Team Lead</th>
                  <th className="text-center py-2 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">Admin</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { perm: 'View sessions', analyst: true, lead: true, admin: true },
                  { perm: 'View masked PII', analyst: true, lead: true, admin: true },
                  { perm: 'Reveal PII', analyst: false, lead: true, admin: true },
                  { perm: 'Export intelligence', analyst: true, lead: true, admin: true },
                  { perm: 'Close sessions', analyst: true, lead: true, admin: true },
                  { perm: 'Escalate sessions', analyst: true, lead: true, admin: true },
                  { perm: 'View detection debug', analyst: false, lead: true, admin: true },
                  { perm: 'View telemetry', analyst: false, lead: true, admin: true },
                  { perm: 'Modify thresholds', analyst: false, lead: false, admin: true },
                  { perm: 'Manage API keys', analyst: false, lead: false, admin: true },
                  { perm: 'Flush caches', analyst: false, lead: false, admin: true },
                  { perm: 'View audit logs', analyst: false, lead: true, admin: true },
                ].map((row, i) => (
                  <tr key={i} className="border-b border-border/30">
                    <td className="py-2 px-3 text-text-secondary">{row.perm}</td>
                    {['analyst', 'lead', 'admin'].map(role => (
                      <td key={role} className="py-2 px-3 text-center">
                        {row[role] ? (
                          <span className="text-severity-low">Granted</span>
                        ) : (
                          <span className="text-text-muted">Denied</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Audit Log ── */}
      {activeTab === 'audit' && (
        <Panel title="Audit Trail" subtitle="Recent system actions">
          <div className="space-y-2">
            {[
              { time: '14:45:22', actor: 'admin', action: 'Cleared LLM cache', ip: '10.0.1.5' },
              { time: '14:30:15', actor: 'analyst_1', action: 'Exported intel for ses_4f2a8c', ip: '10.0.1.12' },
              { time: '14:22:08', actor: 'system', action: 'Session ses_2c7b9a auto-closed: intel stagnation', ip: 'internal' },
              { time: '14:15:00', actor: 'analyst_2', action: 'Escalated ses_1e5d7c to team lead', ip: '10.0.1.8' },
              { time: '14:00:00', actor: 'system', action: 'Platform health check passed', ip: 'internal' },
              { time: '13:45:30', actor: 'admin', action: 'Updated API key rotation', ip: '10.0.1.5' },
            ].map((log, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-border/30 last:border-0">
                <span className="text-[10px] font-mono text-text-muted w-16">{log.time}</span>
                <Tag variant={log.actor === 'system' ? 'default' : log.actor === 'admin' ? 'critical' : 'accent'}>
                  {log.actor}
                </Tag>
                <span className="text-xs text-text-secondary flex-1">{log.action}</span>
                <span className="text-[10px] font-mono text-text-muted">{log.ip}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
