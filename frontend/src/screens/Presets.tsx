import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PRESETS, NPD_PLANTS, FIELD_KB, fieldKb, type Preset, type PresetField } from '@/data/presets';
import Icon from '@/components/Icon';
import { useFieldHelp, FieldChip } from '@/components/FieldHelp';

interface PresetCardProps {
  preset: Preset;
  onEdit: () => void;
}

function PresetCard({ preset, onEdit }: PresetCardProps) {
  return (
    <div className="preset-card">
      <div className="preset-card__head">
        <div>
          <div className="preset-card__title">{preset.name}</div>
          <div className="preset-card__order">#{preset.display_order}</div>
        </div>
        <button className="btn btn-secondary btn-xs" onClick={onEdit}>
          <Icon name="edit" size={12} /> Edit
        </button>
      </div>

      <div className="preset-card__desc">{preset.description}</div>

      <div className="preset-card__row">
        <div className="preset-card__lbl">Plants</div>
        <div className="preset-card__plants">
          {preset.plants.map(code => (
            <span key={code} className="plant-chip">{code}</span>
          ))}
        </div>
      </div>

      <div className="preset-card__stats">
        <div className="preset-stat">
          <span className="preset-stat__dot is-critical" />
          <strong>{preset.critical.length}</strong> critical
        </div>
        <div className="preset-stat">
          <span className="preset-stat__dot is-warning" />
          <strong>{preset.guidance.length}</strong> guidance
        </div>
      </div>
    </div>
  );
}

export default function PresetsListScreen() {
  const navigate = useNavigate();

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Site presets</div>
          <div className="page__sub">{PRESETS.length} presets · define critical and guidance fields per material type</div>
        </div>
        <div className="page__actions">
          <button className="btn btn-primary btn-sm">
            <Icon name="plus" size={14} /> New preset
          </button>
        </div>
      </div>

      <div className="preset-grid">
        {PRESETS.map(preset => (
          <PresetCard
            key={preset.id}
            preset={preset}
            onEdit={() => navigate('/presets/' + preset.id)}
          />
        ))}
      </div>
    </div>
  );
}

interface FieldsBuilderProps {
  fields: PresetField[];
  tier: 'critical' | 'guidance';
  activeField: string | null;
  onSelect: (code: string) => void;
  onChange: (fields: PresetField[]) => void;
}

function FieldsBuilder({ fields, tier, activeField, onSelect, onChange }: FieldsBuilderProps) {
  const [addField, setAddField] = useState('');
  const [addAllowed, setAddAllowed] = useState('');

  const availableCodes = Object.keys(FIELD_KB);

  const handleAdd = () => {
    if (!addField) return;
    const kb = fieldKb(addField);
    const allowed = addAllowed.split(',').map(s => s.trim()).filter(Boolean);
    onChange([...fields, { field: addField, label: kb.label, allowed }]);
    setAddField('');
    setAddAllowed('');
  };

  const handleRemove = (idx: number) => {
    onChange(fields.filter((_, i) => i !== idx));
  };

  return (
    <div>
      {fields.map((f, idx) => (
        <div
          key={f.field + idx}
          className={'field-row' + (activeField === f.field ? ' is-active' : '')}
          onClick={() => onSelect(f.field)}
        >
          <FieldChip code={f.field} />
          <div className="field-row__label">{f.label}</div>
          <div className="field-row__pills">
            {f.allowed.map(v => (
              <span key={v} className="value-pill">{v}</span>
            ))}
          </div>
          <div className="field-row__actions">
            <button
              className="btn btn-subtle btn-icon btn-xs"
              onClick={e => { e.stopPropagation(); handleRemove(idx); }}
            >
              <Icon name="trash" size={12} />
            </button>
          </div>
        </div>
      ))}

      <div className="field-row field-row--add">
        <select value={addField} onChange={e => setAddField(e.target.value)}>
          <option value="">Add {tier} field…</option>
          {availableCodes.map(code => (
            <option key={code} value={code}>{code} — {FIELD_KB[code].label}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Allowed values (comma-separated)"
          value={addAllowed}
          onChange={e => setAddAllowed(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn btn-secondary btn-xs" onClick={handleAdd}>
          <Icon name="plus" size={12} /> Add
        </button>
      </div>
    </div>
  );
}

interface FieldExplanationCardProps {
  code: string | null;
}

function FieldExplanationCard({ code }: FieldExplanationCardProps) {
  if (!code) {
    return (
      <div className="panel__body" style={{ color: 'var(--muted)', fontSize: 12.5 }}>
        Click a field row to see its knowledge-base entry.
      </div>
    );
  }

  const kb = fieldKb(code);

  return (
    <div className="panel__body">
      <div className="fh-card__head">
        <span className="code mono fh-card__code">{kb.code}</span>
        <span className="fh-card__label">{kb.label}</span>
        <span className="fh-card__table mono">SAP · {kb.table}</span>
      </div>

      <div className="fh-card__sec">
        <div className="fh-card__h">What is it?</div>
        <p>{kb.what}</p>
      </div>

      <div className="fh-card__sec">
        <div className="fh-card__h">Why does it matter?</div>
        <p>{kb.why}</p>
      </div>

      <div className="fh-card__sec">
        <div className="fh-card__h">Example values</div>
        <p>{kb.example}</p>
        {kb.allowed_examples && kb.allowed_examples.length > 0 && (
          <div className="fh-pills" style={{ marginTop: 8 }}>
            {kb.allowed_examples.map(v => (
              <span key={v} className="fh-pill">{v}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function PresetEditScreen() {
  const navigate = useNavigate();
  const { presetId } = useParams<{ presetId: string }>();

  const original = PRESETS.find(p => p.id === presetId);
  const [preset, setPreset] = useState<Preset>(
    original ?? {
      id: '',
      name: '',
      description: '',
      plants: [],
      display_order: PRESETS.length + 1,
      critical: [],
      guidance: [],
    }
  );
  const [activeField, setActiveField] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const togglePlant = (code: string) => {
    setPreset(p => ({
      ...p,
      plants: p.plants.includes(code)
        ? p.plants.filter(c => c !== code)
        : [...p.plants, code],
    }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!original) {
    return (
      <div>
        <div className="page__head">
          <div>
            <button className="crumb-link" onClick={() => navigate('/presets')}>
              <Icon name="chevron-left" size={12} /> Back to presets
            </button>
            <div className="page__title" style={{ marginTop: 6 }}>Preset not found</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page__head">
        <div>
          <button className="crumb-link" onClick={() => navigate('/presets')}>
            <Icon name="chevron-left" size={12} /> Site presets
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
            <div className="page__title">{preset.name}</div>
            <span className="page__title-sub">Edit preset</span>
          </div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/presets')}>
            Cancel
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleSave}>
            {saved ? <><Icon name="check" size={14} /> Saved</> : <><Icon name="check" size={14} /> Save changes</>}
          </button>
        </div>
      </div>

      <div className="preset-edit-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Metadata</span>
            </div>
            <div className="panel__body">
              <div className="field-grid">
                <div className="field">
                  <label>Name</label>
                  <input
                    type="text"
                    value={preset.name}
                    onChange={e => setPreset(p => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label>Display order</label>
                  <input
                    type="number"
                    value={preset.display_order}
                    onChange={e => setPreset(p => ({ ...p, display_order: Number(e.target.value) }))}
                  />
                </div>
              </div>
              <div className="field">
                <label>Description</label>
                <textarea
                  rows={2}
                  value={preset.description}
                  onChange={e => setPreset(p => ({ ...p, description: e.target.value }))}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Critical fields</span>
              <span className="spacer" />
              <span className="panel__sub">{preset.critical.length} fields</span>
            </div>
            <div className="panel__body--flush">
              <FieldsBuilder
                fields={preset.critical}
                tier="critical"
                activeField={activeField}
                onSelect={setActiveField}
                onChange={fields => setPreset(p => ({ ...p, critical: fields }))}
              />
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Guidance fields</span>
              <span className="spacer" />
              <span className="panel__sub">{preset.guidance.length} fields</span>
            </div>
            <div className="panel__body--flush">
              <FieldsBuilder
                fields={preset.guidance}
                tier="guidance"
                activeField={activeField}
                onSelect={setActiveField}
                onChange={fields => setPreset(p => ({ ...p, guidance: fields }))}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Plant assignment</span>
              <span className="spacer" />
              <span className="panel__sub">{preset.plants.length} selected</span>
            </div>
            <div className="panel__body">
              {NPD_PLANTS.map(plant => (
                <div
                  key={plant.code}
                  className="plant-row"
                  onClick={() => togglePlant(plant.code)}
                >
                  <input
                    type="checkbox"
                    checked={preset.plants.includes(plant.code)}
                    onChange={() => togglePlant(plant.code)}
                    onClick={e => e.stopPropagation()}
                  />
                  <span className="plant-row__code">{plant.code}</span>
                  <span className="plant-row__name">{plant.name}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Field reference</span>
            </div>
            <FieldExplanationCard code={activeField} />
          </div>
        </div>
      </div>
    </div>
  );
}
