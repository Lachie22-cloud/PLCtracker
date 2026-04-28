import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { NPD, NPD_STATUS_META, stepProgress, daysOpen, type NpdRequest, type NpdStatus } from '@/data/npd';
import { DIVISIONS } from '@/data/presets';
import { NPD_PLANTS } from '@/data/presets';
import Icon from '@/components/Icon';
import { DivisionBadge } from '@/components/Badges';

interface NewRequestModalProps {
  onClose: () => void;
  onSave: (req: NpdRequest) => void;
  nextNo: string;
}

function NewRequestModal({ onClose, onSave, nextNo }: NewRequestModalProps) {
  const [type, setType] = useState<'Bulk + FG' | 'FG Only' | 'Bulk Only'>('Bulk + FG');
  const [from, setFrom] = useState('');
  const [division, setDivision] = useState('54');
  const [bulkSku, setBulkSku] = useState('');
  const [fgSku, setFgSku] = useState('');
  const [warehousePlants, setWarehousePlants] = useState<string[]>([]);
  const [target, setTarget] = useState('');
  const [notes, setNotes] = useState('');

  const warehouseOptions = NPD_PLANTS.filter(p =>
    ['DC10', 'DC20', 'DC30'].includes(p.code)
  );

  const togglePlant = (code: string) => {
    setWarehousePlants(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleSave = () => {
    const now = new Date().toISOString().slice(0, 10);
    const req: NpdRequest = {
      no: nextNo,
      type,
      from,
      division,
      bulk_sku: type === 'FG Only' ? '—' : bulkSku,
      fg_sku: type === 'Bulk Only' ? '—' : fgSku,
      warehouse_plants: warehousePlants,
      target,
      entered_by: 'Lena Decker',
      created: now,
      status: 'in_progress',
      notes,
      progress: {
        intake: 'in_progress',
        spec: 'not_started',
        spec_signoff: 'not_started',
        matnr: 'not_started',
        governance: 'not_started',
        batch: type === 'FG Only' ? 'n_a' : 'not_started',
        batch_sched: type === 'FG Only' ? 'n_a' : 'not_started',
        batch_done: type === 'FG Only' ? 'n_a' : 'not_started',
        warehouse: warehousePlants.length === 0 ? 'n_a' : 'not_started',
        live: 'not_started',
      },
      governance_violations: 0,
      completed_by: {},
      comments: [],
      emails: [],
    };
    onSave(req);
  };

  return (
    <>
      <div className="slide-backdrop" onClick={onClose} />
      <div className="slide-over">
        <div className="slide-over__head">
          <div>
            <div className="slide-over__title">New NPD request</div>
            <div className="slide-over__sub">{nextNo}</div>
          </div>
          <button className="side-panel__close" style={{ marginLeft: 'auto' }} onClick={onClose}>
            <Icon name="x" size={14} />
          </button>
        </div>

        <div className="slide-over__body">
          <div className="field">
            <label>Request type</label>
            <div className="seg">
              {(['Bulk + FG', 'FG Only', 'Bulk Only'] as const).map(t => (
                <button
                  key={t}
                  className={'seg__btn' + (type === t ? ' is-active' : '')}
                  onClick={() => setType(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="field-grid">
            <div className="field">
              <label>Requested by</label>
              <input
                type="text"
                value={from}
                onChange={e => setFrom(e.target.value)}
                placeholder="Full name"
              />
            </div>
            <div className="field">
              <label>Division</label>
              <select value={division} onChange={e => setDivision(e.target.value)}>
                {DIVISIONS.map(d => (
                  <option key={d.code} value={d.code}>{d.code} — {d.label}</option>
                ))}
              </select>
            </div>
          </div>

          {type !== 'FG Only' && (
            <div className="field">
              <label>Bulk SKU</label>
              <input
                type="text"
                value={bulkSku}
                onChange={e => setBulkSku(e.target.value)}
                placeholder="MAT-XXXXXX"
              />
            </div>
          )}

          {type !== 'Bulk Only' && (
            <div className="field">
              <label>FG SKU</label>
              <input
                type="text"
                value={fgSku}
                onChange={e => setFgSku(e.target.value)}
                placeholder="MAT-XXXXXX"
              />
            </div>
          )}

          <div className="field">
            <label>Warehouse plants</label>
            <div className="plant-pick">
              {warehouseOptions.map(p => (
                <button
                  key={p.code}
                  className={'plant-pick__btn' + (warehousePlants.includes(p.code) ? ' is-active' : '')}
                  onClick={() => togglePlant(p.code)}
                >
                  {p.code}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Target date</label>
            <input
              type="date"
              value={target}
              onChange={e => setTarget(e.target.value)}
            />
          </div>

          <div className="field">
            <label>Notes</label>
            <textarea
              rows={3}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Any context or constraints…"
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <div className="slide-over__foot">
          <button className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave}>
            <Icon name="plus" size={14} /> Create request
          </button>
        </div>
      </div>
    </>
  );
}

export default function NpdListScreen() {
  const navigate = useNavigate();
  const [statusF, setStatusF] = useState('');
  const [typeF, setTypeF] = useState('');
  const [divF, setDivF] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [requests, setRequests] = useState<NpdRequest[]>(NPD);

  const filtered = useMemo(() => {
    return requests.filter(r => {
      if (statusF && r.status !== statusF) return false;
      if (typeF && r.type !== typeF) return false;
      if (divF && r.division !== divF) return false;
      return true;
    });
  }, [requests, statusF, typeF, divF]);

  const nextNo = useMemo(() => {
    const nums = requests
      .map(r => parseInt(r.no.split('-')[2] ?? '0', 10))
      .filter(n => !isNaN(n));
    const max = nums.length > 0 ? Math.max(...nums) : 0;
    return `NPD-2026-${String(max + 1).padStart(3, '0')}`;
  }, [requests]);

  const handleSave = (req: NpdRequest) => {
    setRequests(prev => [req, ...prev]);
    setShowNew(false);
  };

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">NPD requests</div>
          <div className="page__sub">{requests.length} total · {requests.filter(r => r.status === 'in_progress').length} in progress</div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/npd/board')}>
            <Icon name="kanban" size={14} /> Board view
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowNew(true)}>
            <Icon name="plus" size={14} /> New request
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="filter-bar">
          <select value={statusF} onChange={e => setStatusF(e.target.value)}>
            <option value="">All statuses</option>
            <option value="in_progress">In Progress</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select value={typeF} onChange={e => setTypeF(e.target.value)}>
            <option value="">All types</option>
            <option value="Bulk + FG">Bulk + FG</option>
            <option value="FG Only">FG Only</option>
            <option value="Bulk Only">Bulk Only</option>
          </select>
          <select value={divF} onChange={e => setDivF(e.target.value)}>
            <option value="">All divisions</option>
            {DIVISIONS.map(d => (
              <option key={d.code} value={d.code}>{d.code} — {d.label}</option>
            ))}
          </select>
          {(statusF || typeF || divF) && (
            <button
              className="btn btn-subtle btn-xs"
              onClick={() => { setStatusF(''); setTypeF(''); setDivF(''); }}
            >
              <Icon name="x" size={12} /> Clear
            </button>
          )}
          <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 11.5 }}>
            {filtered.length} results
          </span>
        </div>

        <div className="panel__body--flush">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Request no</th>
                  <th>SKUs</th>
                  <th>Division</th>
                  <th>Progress</th>
                  <th>Next step</th>
                  <th>Target</th>
                  <th>Days open</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="empty">No requests match the current filters.</td>
                  </tr>
                )}
                {filtered.map(req => {
                  const sp = stepProgress(req);
                  const pct = sp.total > 0 ? Math.round((sp.done / sp.total) * 100) : 0;
                  const meta = NPD_STATUS_META[req.status];
                  const days = daysOpen(req.created);
                  return (
                    <tr key={req.no} onClick={() => navigate('/npd/' + req.no)}>
                      <td>
                        <span className="req-no mono">{req.no}</span>
                      </td>
                      <td>
                        <div className="sku-stack">
                          {req.bulk_sku !== '—' && <span className="mono" style={{ color: 'var(--text)' }}>{req.bulk_sku}</span>}
                          {req.fg_sku !== '—' && <span className="mono" style={{ color: 'var(--text-2)' }}>{req.fg_sku}</span>}
                          {req.bulk_sku === '—' && req.fg_sku === '—' && <span className="muted">—</span>}
                        </div>
                      </td>
                      <td>
                        <DivisionBadge code={req.division} />
                      </td>
                      <td>
                        <div className="progress-cell">
                          <div className="progress-cell__bar">
                            <div className="progress-cell__fill" style={{ width: pct + '%' }} />
                          </div>
                          <div className="progress-cell__text mono">{sp.done}/{sp.total}</div>
                        </div>
                      </td>
                      <td>
                        {sp.next ? (
                          <span className="step-chip">{sp.next.label}</span>
                        ) : (
                          <span style={{ color: 'var(--muted)' }}>—</span>
                        )}
                      </td>
                      <td className="muted">
                        {req.target || '—'}
                      </td>
                      <td className="muted num">
                        {days}d
                      </td>
                      <td>
                        <span className={'badge badge--' + (meta?.badge || '')}>
                          <span className="dot" />
                          {meta?.label ?? req.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showNew && (
        <NewRequestModal
          onClose={() => setShowNew(false)}
          onSave={handleSave}
          nextNo={nextNo}
        />
      )}
    </div>
  );
}
