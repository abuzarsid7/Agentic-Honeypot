import clsx from 'clsx';
import { getSeverity, severityColors } from '../utils';

/* ═══════════════════════════════════════════════════════════════
   SHARED UI COMPONENTS — SOC Design System
   ═══════════════════════════════════════════════════════════════ */

// ── KPI Card ──
export function KPICard({ label, value, sub, icon: Icon, trend }) {
  return (
    <div className="bg-surface-800 border border-border rounded-lg p-3 sm:p-4 flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] sm:text-[11px] font-medium uppercase tracking-wider text-text-muted truncate">{label}</span>
        {Icon && <Icon size={14} className="text-text-muted shrink-0" />}
      </div>
      <div className="text-xl sm:text-2xl font-semibold text-text-primary font-mono">{value}</div>
      {sub && (
        <span className={clsx('text-xs', trend === 'up' ? 'text-severity-critical' : trend === 'down' ? 'text-severity-low' : 'text-text-muted')}>
          {sub}
        </span>
      )}
    </div>
  );
}

// ── Severity Badge ──
export function SeverityBadge({ score, label }) {
  const level = label || getSeverity(score);
  const c = severityColors[level] || severityColors.info;
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium', c.bg, c.text)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', c.dot)} />
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}

// ── Score Bar (horizontal weighted bar) ──
export function ScoreBar({ score, max = 1 }) {
  const pct = Math.min((score / max) * 100, 100);
  const level = getSeverity(score);
  const colorMap = {
    critical: 'bg-severity-critical',
    high: 'bg-severity-high',
    medium: 'bg-severity-medium',
    low: 'bg-severity-low',
    info: 'bg-severity-info',
  };
  return (
    <div className="h-1.5 rounded-full bg-surface-600 overflow-hidden w-full">
      <div className={clsx('h-full rounded-full transition-all duration-500', colorMap[level])} style={{ width: `${pct}%` }} />
    </div>
  );
}

// ── Panel (card wrapper) ──
export function Panel({ title, subtitle, children, actions, className }) {
  return (
    <div className={clsx('bg-surface-800 border border-border rounded-lg', className)}>
      {(title || actions) && (
        <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 sm:py-3 border-b border-border">
          <div className="min-w-0 flex-1">
            {title && <h3 className="text-sm font-semibold text-text-primary truncate">{title}</h3>}
            {subtitle && <p className="text-[11px] text-text-muted mt-0.5 truncate">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0 ml-2">{actions}</div>}
        </div>
      )}
      <div className="p-3 sm:p-4">{children}</div>
    </div>
  );
}

// ── Status Indicator (live dot) ──
export function StatusDot({ status }) {
  const map = {
    live: 'bg-severity-low pulse-live',
    warning: 'bg-severity-medium',
    error: 'bg-severity-critical',
    idle: 'bg-text-muted',
  };
  return <span className={clsx('w-2 h-2 rounded-full inline-block', map[status] || map.idle)} />;
}

// ── Tag / Chip ──
export function Tag({ children, variant = 'default' }) {
  const variants = {
    default: 'bg-surface-600 text-text-secondary',
    accent: 'bg-accent/15 text-accent',
    critical: 'bg-severity-critical/15 text-severity-critical',
    high: 'bg-severity-high/15 text-severity-high',
  };
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium', variants[variant])}>
      {children}
    </span>
  );
}

// ── Button ──
export function Button({ children, variant = 'primary', size = 'sm', className, ...props }) {
  const base = 'inline-flex items-center justify-center gap-1.5 font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:opacity-50 disabled:cursor-not-allowed';
  const sizes = {
    xs: 'px-2 py-1 text-[11px]',
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
  };
  const variants = {
    primary: 'bg-accent text-text-inverse hover:bg-accent-dim',
    secondary: 'bg-surface-600 text-text-secondary hover:bg-surface-500 border border-border',
    danger: 'bg-severity-critical/15 text-severity-critical hover:bg-severity-critical/25 border border-severity-critical/30',
    ghost: 'text-text-secondary hover:text-text-primary hover:bg-surface-700',
  };
  return (
    <button className={clsx(base, sizes[size], variants[variant], className)} {...props}>
      {children}
    </button>
  );
}

// ── Empty State ──
export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && <Icon size={32} className="text-text-muted mb-3" />}
      <h4 className="text-sm font-medium text-text-secondary">{title}</h4>
      {description && <p className="text-xs text-text-muted mt-1 max-w-xs">{description}</p>}
    </div>
  );
}

// ── Loading Skeleton ──
export function Skeleton({ className }) {
  return <div className={clsx('animate-pulse bg-surface-600 rounded', className)} />;
}

// ── Data Row (key-value) ──
export function DataRow({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={clsx('text-xs text-text-primary', mono && 'font-mono')}>{value ?? '—'}</span>
    </div>
  );
}

// ── Table wrapper ──
export function DataTable({ columns, rows, onRowClick }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            {columns.map(col => (
              <th key={col.key} className="text-left py-2 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted whitespace-nowrap">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id || i}
              className={clsx(
                'border-b border-border/30 hover:bg-surface-700/50 transition-colors',
                onRowClick && 'cursor-pointer'
              )}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map(col => (
                <td key={col.key} className="py-2.5 px-3 whitespace-nowrap">
                  {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab Groups ──
export function TabGroup({ tabs, active, onChange }) {
  return (
    <div className="flex border-b border-border">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={clsx(
            'px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px',
            active === t.key
              ? 'border-accent text-accent'
              : 'border-transparent text-text-muted hover:text-text-secondary'
          )}
        >
          {t.label}
          {t.count != null && (
            <span className="ml-1.5 px-1.5 py-0.5 rounded bg-surface-600 text-[10px]">{t.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}
