import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { VIOLATIONS, MATERIALS, PLANTS, RULES, SAP_STATE, RUNS } from '@/data/governance';
import { fmtRel, fmtAbs } from '@/data/utils';
import Icon from '@/components/Icon';
import { SeverityBadge, PlantTag, RunStatusBadge } from '@/components/Badges';

const Sparkline = ({ data, color = 'var(--accent)' }: { data: number[]; color?: string }) => {
  const max = Math.max(...data, 1);
  const w = 80, h = 28, pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - (v / max) * (h - pad * 2);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} className="tile__spark" viewBox={`0 0 ${w} ${h}`}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5"/>
    </svg>
  );
};

export default function OverviewScreen() {
  const navigate = useNavigate();

  const criticalCount = useMemo(() => VIOLATIONS.filter(v => v.severity === 'error').length, []);
  const warningCount = useMemo(() => VIOLATIONS.filter(v => v.severity === 'warning').length, []);
  const openTotal = VIOLATIONS.length;
  const activeRules = RULES.length;

  const fieldCounts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const v of VIOLATIONS) {
      map[v.field] = (map[v.field] || 0) + 1;
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, []);

  const plantCounts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const v of VIOLATIONS) {
      map[v.werks] = (map[v.werks] || 0) + 1;
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, []);

  const fieldMax = fieldCounts[0]?.[1] ?? 1;
  const plantMax = plantCounts[0]?.[1] ?? 1;

  const sparkData = useMemo(() => {
    const byDay: Record<string, number> = {};
    for (const v of VIOLATIONS) {
      const day = v.detected.slice(0, 10);
      byDay[day] = (byDay[day] || 0) + 1;
    }
    const days = Object.keys(byDay).sort();
    return days.map(d => byDay[d]);
  }, []);

  const recentViolations = VIOLATIONS.slice(0, 6);
  const recentRuns = RUNS.slice(0, 5);

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">MDG overview</div>
          <div className="page__sub">
            {PLANTS.length} plants · {MATERIALS.length} materials · last sync {fmtRel(SAP_STATE.last_run_at)}
          </div>
        </div>
        <div className="page__actions">
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/violations')}>
            <Icon name="alert" size={14} /> Open violations
          </button>
        </div>
      </div>

      <div className="tile-row">
        <div className="tile is-critical">
          <div className="tile__label">
            <Icon name="alert" size={13} /> Open violations
          </div>
          <div className="tile__value">{openTotal}</div>
          <div className="tile__delta up">
            <Icon name="arrow-up" size={12} /> {criticalCount} critical
          </div>
          <Sparkline data={sparkData} color="var(--critical)" />
        </div>

        <div className="tile is-warning">
          <div className="tile__label">
            <Icon name="alert-triangle" size={13} /> Critical / Warning
          </div>
          <div className="tile__value">{criticalCount} / {warningCount}</div>
          <div className="tile__delta">
            <Icon name="info" size={12} /> {VIOLATIONS.filter(v => v.severity === 'info').length} info
          </div>
          <Sparkline data={sparkData} color="var(--warning)" />
        </div>

        <div className="tile">
          <div className="tile__label">
            <Icon name="database" size={13} /> Last extraction
          </div>
          <div className="tile__value is-ok" style={{ color: 'var(--ok)', fontSize: 18, paddingTop: 4 }}>
            {fmtRel(SAP_STATE.last_run_at)}
          </div>
          <div className="tile__delta">
            <span className="mono" style={{ fontSize: 11 }}>#{SAP_STATE.last_run_id}</span>
            <span style={{ margin: '0 4px', color: 'var(--muted-3)' }}>·</span>
            {RUNS[0]?.records?.toLocaleString()} records
          </div>
        </div>

        <div className="tile">
          <div className="tile__label">
            <Icon name="shield" size={13} /> Active rules
          </div>
          <div className="tile__value">{activeRules}</div>
          <div className="tile__delta">
            <Icon name="check-circle" size={12} /> {RULES.filter(r => r.active_violations > 0).length} firing
          </div>
          <Sparkline data={RULES.map(r => r.active_violations)} color="var(--accent)" />
        </div>
      </div>

      <div className="two-pane" style={{ marginBottom: 14 }}>
        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Top firing fields</span>
            <span className="spacer" />
            <span className="panel__sub">{fieldCounts.length} fields</span>
          </div>
          <div className="panel__body">
            <div className="bar-list">
              {fieldCounts.map(([field, n]) => (
                <div key={field} className={"bar-row" + (n >= 3 ? " is-critical" : "")}>
                  <div className="lbl">{field}</div>
                  <div className="bar"><div className="fill" style={{ width: (n / fieldMax * 100) + "%" }}/></div>
                  <div className="cnt">{n}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Violations by plant</span>
            <span className="spacer" />
            <span className="panel__sub">{plantCounts.length} plants</span>
          </div>
          <div className="panel__body">
            <div className="bar-list">
              {plantCounts.map(([werks, n]) => (
                <div key={werks} className={"bar-row" + (n >= 3 ? " is-critical" : "")}>
                  <div className="lbl">{werks}</div>
                  <div className="bar"><div className="fill" style={{ width: (n / plantMax * 100) + "%" }}/></div>
                  <div className="cnt">{n}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="two-pane">
        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Most recent violations</span>
            <span className="spacer" />
            <button className="btn btn-subtle btn-xs" onClick={() => navigate('/violations')}>
              View all <Icon name="arrow-right" size={12} />
            </button>
          </div>
          <div className="panel__body--flush">
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Material</th>
                    <th>Field</th>
                    <th>Plant</th>
                    <th>Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {recentViolations.map(v => (
                    <tr
                      key={v.id}
                      className={`severity-${v.severity}`}
                      onClick={() => navigate('/violations')}
                    >
                      <td><SeverityBadge severity={v.severity} /></td>
                      <td><span className="mono" style={{ fontWeight: 600 }}>{v.matnr}</span></td>
                      <td><span className="code mono">{v.field}</span></td>
                      <td><PlantTag code={v.werks} /></td>
                      <td className="muted">{fmtRel(v.detected)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Recent extraction runs</span>
            <span className="spacer" />
            <button className="btn btn-subtle btn-xs" onClick={() => navigate('/runs')}>
              View all <Icon name="arrow-right" size={12} />
            </button>
          </div>
          <div className="panel__body" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentRuns.map(r => (
              <div key={r.id} style={{ display:'flex',alignItems:'center',gap:10,padding:'10px 12px',border:'1px solid var(--border)',borderRadius:6,background:r.status==='error'?'var(--critical-soft)':'var(--panel-2)' }}>
                <RunStatusBadge status={r.status}/>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:12.5 }}><span className="mono" style={{ fontWeight:600 }}>#{r.id}</span><span style={{ color:'var(--muted)',margin:'0 8px' }}>·</span><span>{r.source}</span></div>
                  <div style={{ color:'var(--muted)',fontSize:11,marginTop:2 }} className="mono">{fmtAbs(r.started)} · {r.duration_s}s · {r.changes||0} changes</div>
                </div>
                <div className="mono" style={{ color:'var(--muted)',fontSize:11.5 }}>{r.records?r.records.toLocaleString():'—'}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
