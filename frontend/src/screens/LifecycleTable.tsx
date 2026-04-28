import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LC_SKUS, LIFECYCLE_STAGES, stageMeta } from '@/data/lifecycle';
import Icon from '@/components/Icon';
import { StagePill } from '@/components/Badges';

export default function LifecycleTable() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('');
  const [mtartFilter, setMtartFilter] = useState('');

  const mtartOptions = useMemo(() => {
    const set = new Set(LC_SKUS.map(s => s.mtart));
    return Array.from(set).sort();
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return LC_SKUS.filter(s => {
      if (stageFilter && s.stage !== stageFilter) return false;
      if (mtartFilter && s.mtart !== mtartFilter) return false;
      if (q && !s.matnr.toLowerCase().includes(q) && !s.desc.toLowerCase().includes(q) && !s.owner.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [search, stageFilter, mtartFilter]);

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Lifecycle Table</div>
          <div className="page__sub">{filtered.length} of {LC_SKUS.length} SKUs</div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lifecycle/board')}>
            <Icon name="kanban" size={14}/> Board view
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/lifecycle/upload')}>
            <Icon name="upload" size={14}/> Upload
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="filter-bar">
          <div className="search">
            <Icon name="search" size={14}/>
            <input
              type="text"
              placeholder="Search matnr, description, owner…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select value={stageFilter} onChange={e => setStageFilter(e.target.value)}>
            <option value="">All stages</option>
            {LIFECYCLE_STAGES.map(s => (
              <option key={s.id} value={s.id}>{s.id} — {s.label}</option>
            ))}
          </select>
          <select value={mtartFilter} onChange={e => setMtartFilter(e.target.value)}>
            <option value="">All types</option>
            {mtartOptions.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          {(search || stageFilter || mtartFilter) && (
            <button className="btn btn-subtle btn-xs" onClick={() => { setSearch(''); setStageFilter(''); setMtartFilter(''); }}>
              <Icon name="x" size={12}/> Clear
            </button>
          )}
        </div>
        <div className="panel__body--flush">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Matnr</th>
                  <th>Description</th>
                  <th>Type</th>
                  <th>Product</th>
                  <th>Owner</th>
                  <th>Plants</th>
                  <th>Stage</th>
                  <th className="right">Health</th>
                  <th className="right">Days</th>
                  <th className="right">Violations</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={10} className="empty">No SKUs match the current filters.</td>
                  </tr>
                )}
                {filtered.map(sku => {
                  const meta = stageMeta(sku.stage);
                  const healthColor = sku.health == null ? 'var(--muted)' : sku.health > 75 ? 'var(--ok)' : sku.health > 50 ? 'var(--warning)' : 'var(--critical)';
                  return (
                    <tr key={sku.matnr} onClick={() => navigate('/lifecycle/board')}>
                      <td><span className="mono" style={{ fontWeight: 600 }}>{sku.matnr}</span></td>
                      <td><span className="cell-truncate" style={{ maxWidth: 200 }}>{sku.desc}</span></td>
                      <td>
                        <span className="badge"><span className="dot"/>{sku.mtart}</span>
                      </td>
                      <td><span className="cell-truncate" style={{ maxWidth: 160 }}>{sku.product}</span></td>
                      <td>{sku.owner}</td>
                      <td>
                        <span style={{ display:'inline-flex',gap:3,flexWrap:'wrap' }}>
                          {sku.plants.slice(0,3).map(p => (
                            <span key={p} className="plant-chip mono">{p}</span>
                          ))}
                          {sku.plants.length > 3 && (
                            <span className="muted-text">+{sku.plants.length-3}</span>
                          )}
                        </span>
                      </td>
                      <td>
                        <span style={{ display:'inline-flex',alignItems:'center',gap:6 }}>
                          <StagePill id={sku.stage}/>
                          <span style={{ fontSize:11.5,color:'var(--muted)' }}>{meta.label}</span>
                        </span>
                      </td>
                      <td className="num">
                        {sku.health != null
                          ? <span style={{ color: healthColor, fontWeight: 600 }}>{sku.health}%</span>
                          : <span className="muted-text">—</span>
                        }
                      </td>
                      <td className="num"><span className="mono">{sku.days_in_stage}</span></td>
                      <td className="num">
                        {sku.violations > 0
                          ? <span className="badge badge--critical"><Icon name="alert" size={9}/> {sku.violations}</span>
                          : <span className="muted-text">—</span>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
