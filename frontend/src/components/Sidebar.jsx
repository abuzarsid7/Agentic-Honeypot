import { NavLink, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import {
  LayoutDashboard,
  List,
  Search,
  Database,
  ShieldCheck,
  Activity,
  Settings,
  Shield,
  ChevronLeft,
  ChevronRight,
  X,
  Landmark,
} from 'lucide-react';
import { useState } from 'react';

const NAV = [
  { to: '/dashboard',      label: 'Command Center',    icon: LayoutDashboard, group: 'operations' },
  { to: '/sessions',       label: 'Live Sessions',      icon: List,            group: 'operations' },
  { to: '/investigate',    label: 'Investigation',      icon: Search,          group: 'operations' },
  { to: '/intelligence',   label: 'Intel Repository',   icon: Database,        group: 'analysis' },
  { to: '/explainability', label: 'Explainability',     icon: ShieldCheck,     group: 'analysis' },
  { to: '/regulatory',     label: 'Report to Authorities', icon: Landmark,     group: 'compliance' },
  { to: '/telemetry',      label: 'Platform Health',    icon: Activity,        group: 'system' },
  { to: '/admin',          label: 'Admin',              icon: Settings,        group: 'system' },
];

const GROUPS = {
  operations: 'OPERATIONS',
  analysis: 'ANALYSIS',
  compliance: 'COMPLIANCE',
  system: 'SYSTEM',
};

export default function Sidebar({ mobileOpen, onMobileClose }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const grouped = {};
  NAV.forEach(n => {
    if (!grouped[n.group]) grouped[n.group] = [];
    grouped[n.group].push(n);
  });

  return (
    <>
      {/* Mobile Overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'h-screen bg-surface-800 border-r border-border flex flex-col transition-all duration-300 shrink-0',
          'fixed lg:relative z-50',
          collapsed ? 'w-16' : 'w-56',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border shrink-0">
        <Shield size={20} className="text-accent shrink-0" />
        {!collapsed && (
          <div className="flex flex-col flex-1">
            <span className="text-sm font-bold text-text-primary tracking-tight">Agentic HoneyPot</span>
            <span className="text-[9px] text-text-muted uppercase tracking-widest">Analyst Console</span>
          </div>
        )}
        {/* Mobile Close Button */}
        {!collapsed && (
          <button
            onClick={onMobileClose}
            className="lg:hidden text-text-muted hover:text-text-primary transition-colors"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            {!collapsed && (
              <div className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                {GROUPS[group]}
              </div>
            )}
            <div className="space-y-0.5">
              {items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onMobileClose}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-colors',
                      isActive
                        ? 'bg-accent/10 text-accent'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                    )
                  }
                >
                  <item.icon size={16} className="shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle - Desktop only */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex items-center justify-center h-10 border-t border-border text-text-muted hover:text-text-secondary transition-colors"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
    </>
  );
}
