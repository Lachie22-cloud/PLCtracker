import React, { useState, useMemo } from 'react';
import { VIOLATIONS, PLANTS, MATERIALS, MTART, FIELDS, RULES, SAP_STATE } from '@/data/governance';
import { fmtRel, fmtAbs } from '@/data/utils';
import Icon from '@/components/Icon';
import { SeverityBadge, PlantTag } from '@/components/Badges';
import type { Violation } from '@/data/governance';

interface SortHeaderProps {
  k: string;
  children: React.ReactNode;
  sortKey: string;
  sortDir: 'asc' | 'desc';
  onSort: (k: string) => void;
}

const SortHeader = ({ k, children, sortKey, sortDir, onSort }: SortHeaderProps) => (
  <th className={sortKey === k ? 'is-sorted' : ''} onClick={() => onSort(k)}>
    {children}
    <span className="sort"><Icon name={sortKey===k&&sortDir==='asc'?'chevron-up':'chevron-down'} size={11}/></span>
  </th>
);

interface ViolationDetailProps {
  v: Violation | null;
  onClose: () => void;
}

function ViolationDetail({ v, onClose }: ViolationDetailProps) {
  const isOpen = v !== null;

  const mat = v ? MATERIALS.find(m => m.matnr === v.matnr) : null;
  const plant = v ? PLANTS.find(p => p.code === v.werks) : null;
  const field = v ? FIELDS.find(f => f.name === v.field) : null;
  const mtart = v ? MTART.find(m => m.code === v.mtart) : null;

  const rule = v ? RULES.find(r =>
    r.field === v.field &&
    (r.mtart == null || r.mtart === v.mtart) &&
    (r.werks == null || r.werks === v.werks) &&
    (r.stage == null || r.stage === v.stage)
  ) : null;

  const calloutClass = v
    ? v.severity === 'error'
      ? 'callout'
      : v.severity === 'warning'
        ? 'callout callout--warning'
        : 'callout callout--info'
    : 'callout';

  const calloutIcon = v
    ? v.severity === 'error'
      ? 'alert'
      : v.severity === 'warning'
        ? 'alert-triangle'
        : 'info'
    : 'info';

  return (
    <>
      <div className={'side-panel__backdrop' + (isOpen ? ' is-open' : '')} onClick={onClose} />
      <div className={'side-panel' + (isOpen ? ' is-open' : '')}>
        {v && (
          <>
            <div className="side-panel__head">
              <SeverityBadge severity={v.severity} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>
                  <span className="code mono">{v.field}</span>
                  {field && <span style={{ color: 'var(--muted)', fontWeight: 400, marginLeft: 8, fontSize: 12.5 }}>{field.label}</span>}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 3 }}>
                  {mat ? mat.maktx : v.matnr}
                </div>
              </div>
              <button className="side-panel__close" onClick={onClose}>
                <Icon name="x" size={14} />
              </button>
            </div>

            <div className="side-panel__body">
              <div className={calloutClass}>
                <Icon name={calloutIcon} size={15} />
                <div>
                  <strong>{v.note}</strong>
                </div>
              </div>

              <div className="section-label">Material</div>
              <dl className="kv">
                <dt>MATNR</dt>
                <dd><span className="code mono">{v.matnr}</span></dd>
                <dt>Description</dt>
                <dd>{mat?.maktx ?? '—'}</dd>
                <dt>Type</dt>
                <dd>{mtart ? `${v.mtart} · ${mtart.label}` : v.mtart}</dd>
                <dt>Family</dt>
                <dd>{mat?.family ?? '—'}</dd>
                <dt>Owner</dt>
                <dd>{mat?.owner ?? '—'}</dd>
                <dt>Stage</dt>
                <dd><span className="code mono">{v.stage}</span></dd>
              </dl>

              <div className="section-label">Plant</div>
              <dl className="kv">
                <dt>WERKS</dt>
                <dd><PlantTag code={v.werks} /></dd>
                <dt>Name</dt>
                <dd>{plant?.name ?? '—'}</dd>
                <dt>Type</dt>
                <dd>{plant?.type ?? '—'}</dd>
                <dt>Region</dt>
                <dd>{plant?.region ?? '—'}</dd>
              </dl>

              <div className="section-label">Violation</div>
              <dl className="kv">
                <dt>Field</dt>
                <dd><span className="code mono">{v.field}</span>{field && <span style={{ color: 'var(--muted)', marginLeft: 6 }}>{field.label}</span>}</dd>
                <dt>Actual</dt>
                <dd>
                  <span className="diff__old">{v.actual || <em style={{ color: 'var(--muted)' }}>empty</em>}</span>
                </dd>
                <dt>Expected</dt>
                <dd>
                  <span className="diff__new">{v.expected}</span>
                </dd>
                <dt>Detected</dt>
                <dd className="mono" style={{ fontSize: 11.5 }}>{fmtAbs(v.detected)}</dd>
                <dt>Detected</dt>
                <dd style={{ color: 'var(--muted)' }}>{fmtRel(v.detected)}</dd>
              </dl>

              {rule && (
                <>
                  <div className="section-label">Matching rule</div>
                  <div className="rule-card">
                    <div className="rule-card__head">
                      <SeverityBadge severity={rule.severity} />
                      <span className="code mono" style={{ fontSize: 11 }}>{rule.field}</span>
                      {rule.mtart && <span className="code mono" style={{ fontSize: 11 }}>{rule.mtart}</span>}
                      {rule.werks && <span className="code mono" style={{ fontSize: 11 }}>{rule.werks}</span>}
                      {rule.stage && <span className="code mono" style={{ fontSize: 11 }}>{rule.stage}</span>}
                    </div>
                    <div className="rule-card__title">{rule.description}</div>
                    {rule.expected && (
                      <div style={{ marginTop: 6 }}>
                        <span style={{ color: 'var(--muted)', fontSize: 11.5 }}>Expected: </span>
                        <span className="code mono" style={{ fontSize: 11 }}>{rule.expected}</span>
                      </div>
                    )}
                    {rule.allowed && (
                      <div style={{ marginTop: 4 }}>
                        <span style={{ color: 'var(--muted)', fontSize: 11.5 }}>Allowed: </span>
                        <span className="code mono" style={{ fontSize: 11 }}>{rule.allowed}</span>
                      </div>
                    )}
                    <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--muted)' }}>
                      {rule.active_violations} active violation{rule.active_violations !== 1 ? 's' : ''} · specificity {(rule.specificity * 100).toFixed(0)}%
                    </div>
                  </div>
                </>
              )}

              <div className="section-label">Recent activity</div>
              <div style={{ color: 'var(--muted)', fontSize: 12, fontStyle: 'italic' }}>
                Detected {fmtRel(v.detected)} · run #{SAP_STATE.last_run_id}
              </div>
            </div>

            <div className="side-panel__foot">
              <button className="btn btn-secondary btn-sm">
                <Icon name="check" size={13} /> Mark resolved
              </button>
              <button className="btn btn-secondary btn-sm">
                <Icon name="send" size={13} /> Assign
              </button>
              <button className="btn btn-subtle btn-sm" style={{ marginLeft: 'auto' }}>
                <Icon name="external" size={13} /> Open in SAP
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default function ViolationsScreen() {
  const [filterPlant, setFilterPlant] = useState('');
  const [filterMtart, setFilterMtart] = useState('');
  const [filterField, setFilterField] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterSearch, setFilterSearch] = useState('');
  const [filterDays, setFilterDays] = useState('7');
  const [sortKey, setSortKey] = useState('detected');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selected, setSelected] = useState<Violation | null>(null);

  const handleSort = (k: string) => {
    if (sortKey === k) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(k);
      setSortDir('desc');
    }
  };

  const filtered = useMemo(() => {
    const cutoff = filterDays
      ? new Date(Date.now() - parseInt(filterDays) * 86400 * 1000).toISOString()
      : null;
    return VIOLATIONS.filter(v => {
      if (filterPlant && v.werks !== filterPlant) return false;
      if (filterMtart && v.mtart !== filterMtart) return false;
      if (filterField && v.field !== filterField) return false;
      if (filterSeverity && v.severity !== filterSeverity) return false;
      if (cutoff && v.detected < cutoff) return false;
      if (filterSearch) {
        const q = filterSearch.toLowerCase();
        if (
          !v.matnr.toLowerCase().includes(q) &&
          !v.field.toLowerCase().includes(q) &&
          !v.werks.toLowerCase().includes(q) &&
          !v.note.toLowerCase().includes(q)
        ) return false;
      }
      return true;
    });
  }, [filterPlant, filterMtart, filterField, filterSeverity, filterSearch, filterDays]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let av: string | number = '';
      let bv: string | number = '';
      if (sortKey === 'detected') { av = a.detected; bv = b.detected; }
      else if (sortKey === 'matnr') { av = a.matnr; bv = b.matnr; }
      else if (sortKey === 'field') { av = a.field; bv = b.field; }
      else if (sortKey === 'werks') { av = a.werks; bv = b.werks; }
      else if (sortKey === 'severity') {
        const order: Record<string, number> = { error: 0, warning: 1, info: 2 };
        av = order[a.severity] ?? 3;
        bv = order[b.severity] ?? 3;
      } else if (sortKey === 'mtart') { av = a.mtart; bv = b.mtart; }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir]);

  const criticalCount = filtered.filter(v => v.severity === 'error').length;
  const warningCount = filtered.filter(v => v.severity === 'warning').length;

  const hasFilters = filterPlant || filterMtart || filterField || filterSeverity || filterSearch;

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Violations</div>
          <div className="page__sub">
            {filtered.length} violations · {criticalCount} critical · {warningCount} warning
          </div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm">
            <Icon name="download" size={14} /> Export
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="filter-bar">
          <div className="search">
            <Icon name="search" size={14} />
            <input
              type="text"
              placeholder="Search matnr, field, note…"
              value={filterSearch}
              onChange={e => setFilterSearch(e.target.value)}
            />
          </div>

          <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
            <option value="">All severities</option>
            <option value="error">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>

          <select value={filterPlant} onChange={e => setFilterPlant(e.target.value)}>
            <option value="">All plants</option>
            {PLANTS.map(p => (
              <option key={p.code} value={p.code}>{p.code} · {p.name}</option>
            ))}
          </select>

          <select value={filterMtart} onChange={e => setFilterMtart(e.target.value)}>
            <option value="">All types</option>
            {MTART.map(m => (
              <option key={m.code} value={m.code}>{m.code} · {m.label}</option>
            ))}
          </select>

          <select value={filterField} onChange={e => setFilterField(e.target.value)}>
            <option value="">All fields</option>
            {FIELDS.map(f => (
              <option key={f.name} value={f.name}>{f.name} · {f.label}</option>
            ))}
          </select>

          <select value={filterDays} onChange={e => setFilterDays(e.target.value)}>
            <option value="7">Last 7 days</option>
            <option value="14">Last 14 days</option>
            <option value="30">Last 30 days</option>
            <option value="">All time</option>
          </select>

          {hasFilters && (
            <button
              className="btn btn-subtle btn-sm"
              onClick={() => {
                setFilterPlant('');
                setFilterMtart('');
                setFilterField('');
                setFilterSeverity('');
                setFilterSearch('');
              }}
            >
              <Icon name="x" size={12} /> Clear
            </button>
          )}
        </div>

        <div className="panel__body--flush">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <SortHeader k="severity" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Severity</SortHeader>
                  <SortHeader k="matnr" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Material</SortHeader>
                  <SortHeader k="field" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Field</SortHeader>
                  <SortHeader k="werks" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Plant</SortHeader>
                  <SortHeader k="mtart" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Type</SortHeader>
                  <th>Actual</th>
                  <th>Expected</th>
                  <SortHeader k="detected" sortKey={sortKey} sortDir={sortDir} onSort={handleSort}>Detected</SortHeader>
                </tr>
              </thead>
              <tbody>
                {sorted.length === 0 && (
                  <tr>
                    <td colSpan={8} className="empty">No violations match the current filters.</td>
                  </tr>
                )}
                {sorted.map(v => {
                  const mat = MATERIALS.find(m => m.matnr === v.matnr);
                  return (
                    <tr
                      key={v.id}
                      className={`severity-${v.severity}${selected?.id === v.id ? ' is-selected' : ''}`}
                      onClick={() => setSelected(selected?.id === v.id ? null : v)}
                    >
                      <td><SeverityBadge severity={v.severity} /></td>
                      <td>
                        <div>
                          <span className="mono" style={{ fontWeight: 600 }}>{v.matnr}</span>
                        </div>
                        {mat && (
                          <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 1 }}>
                            <span className="cell-truncate" style={{ maxWidth: 220 }}>{mat.maktx}</span>
                          </div>
                        )}
                      </td>
                      <td><span className="code mono">{v.field}</span></td>
                      <td><PlantTag code={v.werks} /></td>
                      <td className="muted">{v.mtart}</td>
                      <td>
                        <span className="diff__old">{v.actual || <em style={{ opacity: 0.6 }}>empty</em>}</span>
                      </td>
                      <td>
                        <span className="diff__new">{v.expected}</span>
                      </td>
                      <td className="muted">
                        <span title={fmtAbs(v.detected)}>{fmtRel(v.detected)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <ViolationDetail v={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
