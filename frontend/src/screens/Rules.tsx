import React, { useState } from 'react';
import { RULES, FIELDS, PLANTS, MTART, type Rule } from '@/data/governance';
import Icon from '@/components/Icon';
import { SeverityBadge } from '@/components/Badges';

const Pattern = ({ rule }: { rule: Rule }) => {
  const parts = [
    { k: 'mtart', v: rule.mtart || '*' },
    { k: 'werks', v: rule.werks || '*' },
    { k: 'stage', v: rule.stage || '*' },
  ];
  return (
    <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
      {parts.map(p => (
        <span
          key={p.k}
          className="mono"
          style={{
            fontSize: 11,
            background: p.v === '*' ? 'transparent' : 'var(--panel-2)',
            border: '1px solid var(--border)',
            padding: '0 6px',
            borderRadius: 4,
            color: p.v === '*' ? 'var(--muted-2)' : 'var(--text)',
          }}
        >
          {p.k}={p.v}
        </span>
      ))}
    </span>
  );
};

interface RuleFormState {
  field: string;
  severity: Rule['severity'];
  mtart: string;
  werks: string;
  stage: string;
  expected: string;
  allowed: string;
  description: string;
}

const EMPTY_FORM: RuleFormState = {
  field: FIELDS[0].name,
  severity: 'error',
  mtart: '',
  werks: '',
  stage: '',
  expected: '',
  allowed: '',
  description: '',
};

function ruleToForm(rule: Rule): RuleFormState {
  return {
    field: rule.field,
    severity: rule.severity,
    mtart: rule.mtart ?? '',
    werks: rule.werks ?? '',
    stage: rule.stage ?? '',
    expected: rule.expected ?? '',
    allowed: rule.allowed ?? '',
    description: rule.description,
  };
}

interface RuleModalProps {
  editingId: number | 'new';
  rules: Rule[];
  onSave: (form: RuleFormState, id: number | 'new') => void;
  onDelete: (id: number) => void;
  onClose: () => void;
}

function RuleModal({ editingId, rules, onSave, onDelete, onClose }: RuleModalProps) {
  const existing = editingId !== 'new' ? rules.find(r => r.id === editingId) ?? null : null;
  const [form, setForm] = useState<RuleFormState>(existing ? ruleToForm(existing) : EMPTY_FORM);

  const set = <K extends keyof RuleFormState>(k: K, v: RuleFormState[K]) =>
    setForm(prev => ({ ...prev, [k]: v }));

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal__head">
          <Icon name="shield" size={16} style={{ color: 'var(--accent)' }} />
          <span className="modal__title">{editingId === 'new' ? 'New Rule' : `Edit Rule #${editingId}`}</span>
          <button
            className="btn-subtle btn-icon"
            style={{ marginLeft: 'auto' }}
            onClick={onClose}
          >
            <Icon name="x" size={14} />
          </button>
        </div>

        <div className="modal__body">
          <div className="field-grid">
            <div className="field">
              <label>Field</label>
              <select value={form.field} onChange={e => set('field', e.target.value)}>
                {FIELDS.map(f => (
                  <option key={f.name} value={f.name}>{f.name} — {f.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Severity</label>
              <select
                value={form.severity}
                onChange={e => set('severity', e.target.value as Rule['severity'])}
              >
                <option value="error">Error (Critical)</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
            </div>
          </div>

          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
            Scope
          </div>
          <div className="field-grid field-grid--3">
            <div className="field">
              <label>Mtart</label>
              <select value={form.mtart} onChange={e => set('mtart', e.target.value)}>
                <option value="">* (any)</option>
                {MTART.map(m => (
                  <option key={m.code} value={m.code}>{m.code} — {m.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Werks</label>
              <select value={form.werks} onChange={e => set('werks', e.target.value)}>
                <option value="">* (any)</option>
                {PLANTS.map(p => (
                  <option key={p.code} value={p.code}>{p.code} — {p.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Stage</label>
              <select value={form.stage} onChange={e => set('stage', e.target.value)}>
                <option value="">* (any)</option>
                {['P0', 'A1', 'A2', 'O1', 'O2', 'O3'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="field-grid">
            <div className="field">
              <label>Expected value</label>
              <input
                type="text"
                placeholder="e.g. NOPL"
                value={form.expected}
                onChange={e => set('expected', e.target.value)}
              />
              <span className="hint">Exact match — leave blank for no constraint</span>
            </div>
            <div className="field">
              <label>Allowed values</label>
              <input
                type="text"
                placeholder="e.g. P10|P12 or >= 50"
                value={form.allowed}
                onChange={e => set('allowed', e.target.value)}
              />
              <span className="hint">Pipe-separated list or expression</span>
            </div>
          </div>

          <div className="field">
            <label>Description</label>
            <textarea
              rows={3}
              placeholder="Describe what this rule enforces…"
              value={form.description}
              onChange={e => set('description', e.target.value)}
            />
          </div>
        </div>

        <div className="modal__foot">
          {editingId !== 'new' && (
            <button
              className="btn-danger btn-sm"
              style={{ marginRight: 'auto' }}
              onClick={() => onDelete(editingId as number)}
            >
              <Icon name="trash" size={13} />
              Delete
            </button>
          )}
          <button className="btn-secondary btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn-primary btn-sm" onClick={() => onSave(form, editingId)}>
            <Icon name="check" size={13} />
            Save Rule
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RulesScreen() {
  const [rules, setRules] = useState<Rule[]>(RULES);
  const [editing, setEditing] = useState<number | 'new' | null>(null);
  const [filterField, setFilterField] = useState('');
  const [filterSev, setFilterSev] = useState('');

  const filtered = rules.filter(r => {
    if (filterField && r.field !== filterField) return false;
    if (filterSev && r.severity !== filterSev) return false;
    return true;
  });

  const handleSave = (form: RuleFormState, id: number | 'new') => {
    if (id === 'new') {
      const nextId = Math.max(0, ...rules.map(r => r.id)) + 1;
      const newRule: Rule = {
        id: nextId,
        field: form.field,
        mtart: form.mtart || null,
        werks: form.werks || null,
        stage: form.stage || null,
        expected: form.expected || null,
        allowed: form.allowed || null,
        severity: form.severity,
        description: form.description,
        active_violations: 0,
        specificity: 0,
      };
      setRules(prev => [...prev, newRule]);
    } else {
      setRules(prev =>
        prev.map(r =>
          r.id === id
            ? {
                ...r,
                field: form.field,
                mtart: form.mtart || null,
                werks: form.werks || null,
                stage: form.stage || null,
                expected: form.expected || null,
                allowed: form.allowed || null,
                severity: form.severity,
                description: form.description,
              }
            : r,
        ),
      );
    }
    setEditing(null);
  };

  const handleDelete = (id: number) => {
    setRules(prev => prev.filter(r => r.id !== id));
    setEditing(null);
  };

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <div className="page__title">Validation Rules</div>
          <div className="page__sub">
            {rules.length} rules · {rules.reduce((s, r) => s + r.active_violations, 0)} active violations
          </div>
        </div>
        <div className="page__actions">
          <button className="btn-primary" onClick={() => setEditing('new')}>
            <Icon name="plus" size={13} />
            New Rule
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="filter-bar">
          <div className="field" style={{ margin: 0 }}>
            <select value={filterField} onChange={e => setFilterField(e.target.value)}>
              <option value="">All fields</option>
              {FIELDS.map(f => (
                <option key={f.name} value={f.name}>{f.name} — {f.label}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ margin: 0 }}>
            <select value={filterSev} onChange={e => setFilterSev(e.target.value)}>
              <option value="">All severities</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
          {(filterField || filterSev) && (
            <button
              className="btn-subtle btn-sm"
              onClick={() => { setFilterField(''); setFilterSev(''); }}
            >
              <Icon name="x" size={12} />
              Clear
            </button>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 11.5, color: 'var(--muted)' }}>
            {filtered.length} / {rules.length} rules
          </span>
        </div>

        <div className="panel__body--flush">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Field</th>
                  <th>Severity</th>
                  <th>Pattern</th>
                  <th>Expected</th>
                  <th>Allowed</th>
                  <th>Description</th>
                  <th className="num">Violations</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={9} className="empty">No rules match the current filter</td>
                  </tr>
                )}
                {filtered.map(rule => (
                  <tr
                    key={rule.id}
                    className={`severity-${rule.severity === 'error' ? 'error' : rule.severity === 'warning' ? 'warning' : 'info'}`}
                    onClick={() => setEditing(rule.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <span className="mono" style={{ color: 'var(--muted)', fontSize: 11 }}>#{rule.id}</span>
                    </td>
                    <td>
                      <span className="code mono">{rule.field}</span>
                    </td>
                    <td><SeverityBadge severity={rule.severity} /></td>
                    <td><Pattern rule={rule} /></td>
                    <td>
                      {rule.expected ? (
                        <span className="mono" style={{ fontSize: 11.5 }}>{rule.expected}</span>
                      ) : (
                        <span style={{ color: 'var(--muted-2)' }}>—</span>
                      )}
                    </td>
                    <td>
                      {rule.allowed ? (
                        <span className="mono" style={{ fontSize: 11.5 }}>{rule.allowed}</span>
                      ) : (
                        <span style={{ color: 'var(--muted-2)' }}>—</span>
                      )}
                    </td>
                    <td>
                      <span
                        className="cell-truncate"
                        style={{ maxWidth: 320, color: 'var(--text-2)', fontSize: 12 }}
                      >
                        {rule.description}
                      </span>
                    </td>
                    <td className="num">
                      {rule.active_violations > 0 ? (
                        <span style={{ color: 'var(--critical)', fontWeight: 600 }}>
                          {rule.active_violations}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--ok)' }}>0</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn-subtle btn-icon btn-xs"
                        onClick={e => { e.stopPropagation(); setEditing(rule.id); }}
                      >
                        <Icon name="edit" size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {editing !== null && (
        <RuleModal
          editingId={editing}
          rules={rules}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
