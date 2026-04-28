import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LC_SKUS, LC_PRODUCTS, LIFECYCLE_STAGES, LC_ACTIVITY, stageMeta } from '@/data/lifecycle';
import { fmtRel } from '@/data/utils';
import Icon from '@/components/Icon';

export default function LifecycleDashboard() {
  const navigate = useNavigate();

  const totalSkus = LC_SKUS.length;
  const phasingOut = LC_SKUS.filter(s => s.stage === 'O1' || s.stage === 'O2').length;
  const openViolations = LC_SKUS.reduce((sum, s) => sum + s.violations, 0);
  const healthSkus = LC_SKUS.filter(s => s.health != null);
  const avgHealth = healthSkus.length > 0
    ? Math.round(healthSkus.reduce((sum, s) => sum + (s.health ?? 0), 0) / healthSkus.length)
    : null;

  const byStage = LIFECYCLE_STAGES.map(st => ({
    ...st,
    count: LC_SKUS.filter(s => s.stage === st.id).length,
  }));
  const maxStage = Math.max(...byStage.map(s => s.count), 1);

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Lifecycle Dashboard</div>
          <div className="page__sub">{LC_PRODUCTS.length} products · {totalSkus} tracked SKUs</div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lifecycle/board')}>
            <Icon name="kanban" size={14}/> Board
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lifecycle/table')}>
            <Icon name="table" size={14}/> Table
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/lifecycle/upload')}>
            <Icon name="upload" size={14}/> Upload
          </button>
        </div>
      </div>

      <div className="tile-row">
        <div className="tile">
          <div className="tile__label">
            <Icon name="package" size={13}/> Tracked SKUs
          </div>
          <div className="tile__value">{totalSkus}</div>
          <div className="tile__delta">
            <Icon name="database" size={12}/> {LC_PRODUCTS.length} products
          </div>
        </div>

        <div className="tile is-warning">
          <div className="tile__label">
            <Icon name="alert-triangle" size={13}/> Phasing out
          </div>
          <div className="tile__value">{phasingOut}</div>
          <div className="tile__delta">
            <Icon name="info" size={12}/> O1 + O2 stages
          </div>
        </div>

        <div className={"tile" + (openViolations > 0 ? " is-critical" : " is-ok")}>
          <div className="tile__label">
            <Icon name="alert" size={13}/> Open violations
          </div>
          <div className="tile__value">{openViolations}</div>
          <div className="tile__delta">
            across {LC_SKUS.filter(s => s.violations > 0).length} SKUs
          </div>
        </div>

        <div className={"tile" + (avgHealth != null && avgHealth > 75 ? " is-ok" : avgHealth != null && avgHealth > 50 ? " is-warning" : " is-critical")}>
          <div className="tile__label">
            <Icon name="chart" size={13}/> Avg health
          </div>
          <div className="tile__value">{avgHealth != null ? avgHealth + '%' : '—'}</div>
          <div className="tile__delta">
            across {healthSkus.length} SKUs with health data
          </div>
        </div>
      </div>

      <div className="two-pane">
        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Stage distribution</span>
            <span className="spacer"/>
            <button className="btn btn-subtle btn-xs" onClick={() => navigate('/lifecycle/board')}>
              Open board <Icon name="arrow-right" size={12}/>
            </button>
          </div>
          <div className="panel__body">
            <div className="lc-stage-bars">
              {byStage.map(st => (
                <div key={st.id} className="lc-stage-bar" onClick={() => navigate('/lifecycle/board')}>
                  <div className="lc-stage-bar__label">
                    <span className={"stage-pill stage-pill--"+st.color}>{st.id}</span>
                    <span>{st.label}</span>
                  </div>
                  <div className="lc-stage-bar__track">
                    <div className={"lc-stage-bar__fill lc-fill--"+st.color} style={{ width:(st.count/maxStage*100)+'%' }}/>
                  </div>
                  <div className="lc-stage-bar__count mono">{st.count}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Recent activity</span>
            <span className="spacer"/>
            <span className="panel__sub">{LC_ACTIVITY.length} events</span>
          </div>
          <div className="panel__body--flush">
            <div className="activity-list">
              {LC_ACTIVITY.map((a, i) => (
                <div key={i} className="activity-row">
                  <span className="avatar">{a.who.split(' ').map((s:string)=>s[0]).join('').slice(0,2)}</span>
                  <div className="activity-row__body">
                    <div className="activity-row__head">
                      <span className="activity-row__who">{a.who}</span>
                      <span className="activity-row__when mono">{fmtRel(a.when)}</span>
                    </div>
                    <div className="activity-row__text">
                      {a.action==='create'?'logged':'moved'} <span className="mono">{a.matnr}</span>
                      {a.from&&<> from <span className={"stage-pill stage-pill--"+stageMeta(a.from).color}>{a.from}</span></>}
                      {a.to&&<> to <span className={"stage-pill stage-pill--"+stageMeta(a.to).color}>{a.to}</span></>}
                    </div>
                    {a.note&&<div className="activity-row__note">{a.note}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
