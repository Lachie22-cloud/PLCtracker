import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Icon from './Icon';
import { SapState } from '@/data/governance';
import { fmtRel } from '@/data/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SidebarCounts {
  openViolations: number;
  activeRules: number;
  presets: number;
  npd: number;
}

interface SidebarProps {
  counts: SidebarCounts;
}

interface TopbarProps {
  sap: SapState;
  onRunNow: () => void;
}

interface LayoutProps {
  children: React.ReactNode;
  counts: SidebarCounts;
  sap: SapState;
  onRunNow: () => void;
}

// ---------------------------------------------------------------------------
// Breadcrumb map
// ---------------------------------------------------------------------------

function getCrumbs(pathname: string): [string, string] {
  if (pathname === '/overview')          return ['Workspace', 'Overview'];
  if (pathname === '/violations')        return ['Governance', 'Violations'];
  if (pathname === '/material')          return ['Governance', 'Material search'];
  if (pathname === '/runs')              return ['Governance', 'Extraction runs'];
  if (pathname === '/rules')             return ['Governance', 'Rules'];
  if (pathname === '/presets')           return ['Governance', 'Site presets'];
  if (pathname === '/npd/board')         return ['NPD Pipeline', 'Board'];
  if (pathname === '/npd')               return ['NPD Pipeline', 'Requests'];
  if (pathname.startsWith('/npd/'))      return ['NPD Pipeline', 'Request detail'];
  return ['Workspace', 'Overview'];
}

// ---------------------------------------------------------------------------
// NavItem (internal)
// ---------------------------------------------------------------------------

interface NavItemProps {
  to: string;
  icon: string;
  label: string;
  count?: number;
  critical?: boolean;
}

function NavItem({ to, icon, label, count, critical }: NavItemProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive =
    location.pathname === to ||
    (to !== '/overview' && location.pathname.startsWith(to));

  return (
    <div
      className={'nav-item' + (isActive ? ' active' : '')}
      onClick={() => navigate(to)}
    >
      <Icon name={icon} size={16} />
      <span>{label}</span>
      {count != null && (
        <span className={'nav-item__count' + (critical ? ' is-critical' : '')}>
          {count}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export function Sidebar({ counts }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__brand-tile">PL</span>
        <div>
          <div className="sidebar__brand-name">PLCtracker MDG</div>
          <div className="sidebar__brand-sub">Master data governance</div>
        </div>
      </div>

      <div className="sidebar__label">Governance</div>
      <div className="sidebar__section">
        <NavItem to="/overview"   icon="dashboard"    label="Overview" />
        <NavItem
          to="/violations"
          icon="alert"
          label="Violations"
          count={counts.openViolations}
          critical={counts.openViolations > 0}
        />
        <NavItem to="/material"   icon="search"       label="Material search" />
        <NavItem to="/runs"       icon="history"      label="Extraction runs" />
        <NavItem
          to="/rules"
          icon="shield"
          label="Rules"
          count={counts.activeRules}
        />
        <NavItem
          to="/presets"
          icon="settings"
          label="Site presets"
          count={counts.presets}
        />
      </div>

      <div className="sidebar__sep-label" style={{ marginTop: 18 }}>
        <span>NPD Pipeline</span>
      </div>
      <div className="sidebar__section">
        <NavItem
          to="/npd"
          icon="package"
          label="Requests"
          count={counts.npd}
        />
        <NavItem to="/npd/board" icon="kanban" label="Board" />
      </div>

      <div className="sidebar__sep-label" style={{ marginTop: 18 }}>
        <span>Lifecycle board</span>
      </div>
      <div className="sidebar__section">
        <a href="/board"     className="nav-item"><Icon name="kanban"  size={16} /><span>Board</span></a>
        <a href="/table"     className="nav-item"><Icon name="table"   size={16} /><span>Table</span></a>
        <a href="/dashboard" className="nav-item"><Icon name="chart"   size={16} /><span>Dashboard</span></a>
        <a href="/upload"    className="nav-item"><Icon name="upload"  size={16} /><span>Upload</span></a>
      </div>

      <div className="sidebar__user">
        <div className="user-card">
          <span className="avatar">LD</span>
          <div>
            <div className="name">Lena Decker</div>
            <div className="role">Data steward</div>
          </div>
        </div>
        <div className="nav-item" style={{ color: 'var(--muted)' }}>
          <Icon name="logout" size={16} /><span>Sign out</span>
        </div>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Topbar
// ---------------------------------------------------------------------------

export function Topbar({ sap, onRunNow }: TopbarProps) {
  const location = useLocation();
  const crumbs = getCrumbs(location.pathname);

  return (
    <div className="topbar">
      <div className="topbar__crumbs">
        <span>{crumbs[0]}</span>
        <Icon name="chevron-right" size={12} className="sep" />
        <strong>{crumbs[1]}</strong>
      </div>
      <div className="topbar__right">
        {sap.failed_in_last_24h && (
          <div className="warn-pill">
            <Icon name="alert-triangle" size={12} />
            Extraction failed in last 24 h
          </div>
        )}
        <div className={'topbar__sap' + (sap.failed_in_last_24h ? ' is-warn' : '')}>
          <span className="pulse" />
          <span>SAP OData</span>
          <span style={{ color: 'var(--muted-3)' }}>·</span>
          <span>last sync</span>
          <strong className="mono">{fmtRel(sap.last_run_at)}</strong>
        </div>
        <button className="btn btn-secondary btn-sm">
          <Icon name="bell" size={14} /> 3
        </button>
        <button className="btn btn-primary btn-sm" onClick={onRunNow}>
          <Icon name="refresh" size={14} /> Run extraction
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export function Layout({ children, counts, sap, onRunNow }: LayoutProps) {
  return (
    <div className="app">
      <Sidebar counts={counts} />
      <div className="main">
        <Topbar sap={sap} onRunNow={onRunNow} />
        <div className="page">{children}</div>
      </div>
    </div>
  );
}
