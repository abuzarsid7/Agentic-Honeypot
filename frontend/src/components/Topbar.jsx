import { useLocation } from 'react-router-dom';
import { Bell, Clock, Eye, EyeOff, Menu } from 'lucide-react';
import { useState } from 'react';

const PAGE_TITLES = {
  '/dashboard': 'Command Center',
  '/sessions': 'Live Sessions Queue',
  '/investigate': 'Session Investigation',
  '/intelligence': 'Intelligence Repository',
  '/explainability': 'Detection Explainability',
  '/telemetry': 'Platform Health',
  '/regulatory': 'Report to Authorities',
  '/admin': 'Administration',
};

export default function Topbar({ onMobileMenuToggle }) {
  const location = useLocation();
  const [piiVisible, setPiiVisible] = useState(false);
  const title = PAGE_TITLES[location.pathname] || 'Agentic HoneyPot';

  return (
    <header className="h-12 sm:h-14 bg-surface-800 border-b border-border flex items-center justify-between px-3 sm:px-5 shrink-0">
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Mobile Menu Button */}
        <button
          onClick={onMobileMenuToggle}
          className="lg:hidden p-1.5 rounded hover:bg-surface-700 transition-colors text-text-muted hover:text-text-primary"
        >
          <Menu size={20} />
        </button>
        
        <h1 className="text-sm sm:text-base font-semibold text-text-primary truncate">{title}</h1>
        <div className="hidden sm:block h-4 w-px bg-border" />
        <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-text-muted">
          <Clock size={12} />
          <span>{new Date().toLocaleTimeString('en-IN', { hour12: false })}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* PII toggle */}
        <button
          onClick={() => setPiiVisible(!piiVisible)}
          className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded text-[11px] text-text-muted hover:text-text-secondary hover:bg-surface-700 transition-colors"
          title={piiVisible ? 'Hide PII' : 'Reveal PII'}
        >
          {piiVisible ? <Eye size={13} /> : <EyeOff size={13} />}
          <span>PII {piiVisible ? 'Visible' : 'Masked'}</span>
        </button>

        {/* Alerts */}
        <button className="relative p-1.5 rounded hover:bg-surface-700 transition-colors text-text-muted">
          <Bell size={15} />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-severity-critical rounded-full" />
        </button>

        {/* Operator badge */}
        <div className="hidden sm:flex items-center gap-2 px-2 py-1 rounded bg-surface-700">
          <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-bold text-accent">A</div>
          <span className="text-[11px] text-text-secondary">Analyst</span>
        </div>
      </div>
    </header>
  );
}
