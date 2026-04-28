import React, { useState, useMemo } from 'react';
import { MATERIALS, MATERIAL_CHANGES, SNAPSHOTS, PLANTS } from '@/data/governance';
import { fmtRel, fmtDate } from '@/data/utils';
import Icon from '@/components/Icon';
import { PlantTag } from '@/components/Badges';

const DEFAULT_MATNR = 'MAT-000482';

export default function MaterialScreen() {
  const [query, setQuery] = useState('');
  const [selectedMatnr, setSelectedMatnr] = useState(DEFAULT_MATNR);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return MATERIALS;
    return MATERIALS.filter(
      m =>
        m.matnr.toLowerCase().includes(q) ||
        m.maktx.toLowerCase().includes(q) ||
        m.mtart.toLowerCase().includes(q) ||
        m.family.toLowerCase().includes(q) ||
        m.owner.toLowerCase().includes(q),
    );
  }, [query]);

  const selected = MATERIALS.find(m => m.matnr === selectedMatnr) ?? null;

  const groups = useMemo(() => {
    const changes = MATERIAL_CHANGES[selectedMatnr] ?? [];
    const bySnap: Record<string, typeof changes> = {};
    for (const c of changes) {
      if (!bySnap[c.snapshot_id]) bySnap[c.snapshot_id] = [];
      bySnap[c.snapshot_id].push(c);
    }
    const snapMap: Record<string, (typeof SNAPSHOTS)[number]> = {};
    for (const s of SNAPSHOTS) snapMap[s.id] = s;

    return Object.entries(bySnap)
      .map(([snapId, items]) => ({ snap: snapMap[snapId], items }))
      .filter(g => g.snap)
      .sort(
        (a, b) =>
          new Date(b.snap.started).getTime() - new Date(a.snap.started).getTime(),
      );
  }, [selectedMatnr]);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <div className="page__title">Materials</div>
          <div className="page__sub">Change timeline per material across all snapshots</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 14, alignItems: 'start' }}>
        <div className="panel" style={{ marginBottom: 0 }}>
          <div className="panel__head">
            <span className="panel__title">Materials</span>
            <span className="panel__sub" style={{ marginLeft: 'auto' }}>{MATERIALS.length}</span>
          </div>

          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>
            <div className="search" style={{ maxWidth: '100%' }}>
              <Icon name="search" size={13} />
              <input
                type="text"
                placeholder="Search materials…"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
            </div>
          </div>

          <div style={{ maxHeight: 560, overflowY: 'auto' }}>
            {filtered.length === 0 && (
              <div className="empty-state" style={{ padding: '32px 16px' }}>No results</div>
            )}
            {filtered.map(m => (
              <div
                key={m.matnr}
                className={`field-row${selectedMatnr === m.matnr ? ' is-active' : ''}`}
                onClick={() => setSelectedMatnr(m.matnr)}
                style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 3, padding: '9px 14px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                  <span className="code mono" style={{ fontSize: 11 }}>{m.matnr}</span>
                  <span
                    className="badge"
                    style={{ marginLeft: 'auto', fontSize: 10, padding: '0 6px', height: 18 }}
                  >
                    {m.mtart}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.35, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {m.maktx}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{m.family} · {m.owner}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 0 }}>
          {selected ? (
            <>
              <div className="panel__head">
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span className="code mono" style={{ fontSize: 13 }}>{selected.matnr}</span>
                    <span className="badge">{selected.mtart}</span>
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 3 }}>{selected.maktx}</div>
                </div>
                <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>Family</div>
                  <div style={{ fontSize: 12.5, color: 'var(--text)', fontWeight: 600 }}>{selected.family}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>Owner</div>
                  <div style={{ fontSize: 12.5, color: 'var(--text)', fontWeight: 600 }}>{selected.owner}</div>
                </div>
              </div>

              <div className="panel__body">
                {groups.length === 0 ? (
                  <div className="empty-state">
                    <Icon name="history" size={28} />
                    <div style={{ marginTop: 8 }}>No changes recorded for this material</div>
                  </div>
                ) : (
                  <div className="timeline">
                    {groups.map(({ snap, items }) => {
                      const hasViolation = items.some(c => c.violated);
                      return (
                        <div
                          key={snap.id}
                          className={`timeline-group${hasViolation ? ' has-violation' : ''}`}
                        >
                          <div className="timeline-group__head">
                            <span className="timeline-group__when">{fmtDate(snap.started)}</span>
                            <span className="timeline-group__sub">
                              Run #{snap.run_id} · {snap.source} · {fmtRel(snap.started)}
                            </span>
                            {hasViolation && (
                              <span className="badge badge--critical" style={{ marginLeft: 'auto' }}>
                                <span className="dot" />
                                Violation
                              </span>
                            )}
                          </div>

                          <div className="table-wrap">
                            <table className="tbl">
                              <thead>
                                <tr>
                                  <th>Plant</th>
                                  <th>Field</th>
                                  <th>Change</th>
                                  <th>Status</th>
                                  <th>Rule</th>
                                </tr>
                              </thead>
                              <tbody>
                                {items.map((c, idx) => (
                                  <tr key={idx} className={c.violated ? 'severity-error' : ''}>
                                    <td><PlantTag code={c.werks} /></td>
                                    <td><span className="code mono">{c.field}</span></td>
                                    <td>
                                      <span className="diff">
                                        <span className="mono diff__old">{c.old || '∅'}</span>
                                        <Icon name="arrow-right" size={11} className="diff__arrow" />
                                        <span className="mono diff__new">{c.new || '—'}</span>
                                      </span>
                                    </td>
                                    <td>
                                      {c.violated ? (
                                        <span className="badge badge--critical">
                                          <span className="dot" />
                                          Violated
                                        </span>
                                      ) : (
                                        <span className="badge badge--ok">
                                          <span className="dot" />
                                          OK
                                        </span>
                                      )}
                                    </td>
                                    <td className="muted">
                                      {c.rule ? (
                                        <span className="mono" style={{ fontSize: 11.5 }}>{c.rule}</span>
                                      ) : (
                                        <span style={{ color: 'var(--muted-2)' }}>—</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ padding: '64px 24px' }}>
              <Icon name="package" size={32} />
              <div style={{ marginTop: 8 }}>Select a material to view its change timeline</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
