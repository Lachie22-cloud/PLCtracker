import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LC_SKUS, LIFECYCLE_STAGES, type LifecycleSku } from '@/data/lifecycle';
import { DIVISIONS } from '@/data/presets';
import Icon from '@/components/Icon';
import { StagePill } from '@/components/Badges';

const SkuCard = ({ sku, onClick }: { sku: LifecycleSku; onClick: () => void }) => {
  return (
    <div className={"lc-card" + (sku.violations > 0 ? " has-viol" : "")} onClick={onClick}>
      <div className="lc-card__head">
        <span className="mono lc-card__matnr">{sku.matnr}</span>
        <StagePill id={sku.stage}/>
      </div>
      <div className="lc-card__desc">{sku.desc}</div>
      <div className="lc-card__meta">
        <span className="badge"><span className="dot"/> {sku.mtart}</span>
        {sku.plants.length > 0 && (
          <span className="lc-card__plants">
            {sku.plants.slice(0,3).map(p => <span key={p} className="plant-chip mono">{p}</span>)}
            {sku.plants.length > 3 && <span className="muted-text">+{sku.plants.length-3}</span>}
          </span>
        )}
      </div>
      <div className="lc-card__foot">
        {sku.health != null && (
          <div className="health-bar" title={`Health ${sku.health}%`}>
            <div className="health-bar__fill" style={{ width:sku.health+'%',background:sku.health>75?'var(--ok)':sku.health>50?'var(--warning)':'var(--critical)' }}/>
          </div>
        )}
        <span className="lc-card__days mono">{sku.days_in_stage}d</span>
        {sku.violations > 0 && (
          <span className="badge badge--critical lc-card__viol">
            <Icon name="alert" size={9}/> {sku.violations}
          </span>
        )}
      </div>
    </div>
  );
};

export default function LifecycleBoard() {
  const navigate = useNavigate();
  const [division, setDivision] = useState('');

  const filtered = division ? LC_SKUS.filter(s => s.division === division) : LC_SKUS;

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Lifecycle Board</div>
          <div className="page__sub">{filtered.length} SKUs across {LIFECYCLE_STAGES.length} stages</div>
        </div>
        <div className="page__actions">
          <select value={division} onChange={e => setDivision(e.target.value)}>
            <option value="">All divisions</option>
            {DIVISIONS.map(d => (
              <option key={d.code} value={d.code}>{d.code} — {d.label}</option>
            ))}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lifecycle/table')}>
            <Icon name="table" size={14}/> Table view
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/lifecycle/upload')}>
            <Icon name="upload" size={14}/> Upload
          </button>
        </div>
      </div>

      <div className="lc-board">
        {LIFECYCLE_STAGES.map(stage => {
          const skus = filtered.filter(s => s.stage === stage.id);
          return (
            <div key={stage.id} className="lc-col">
              <div className="lc-col__head">
                <span className={"stage-pill stage-pill--"+stage.color}>{stage.id}</span>
                <span className="lc-col__title">{stage.label}</span>
                <span className="lc-col__count">{skus.length}</span>
              </div>
              <div className="lc-col__sub">{stage.desc}</div>
              <div className="lc-col__body">
                {skus.length === 0 && (
                  <div className="kanban-empty">—</div>
                )}
                {skus.map(sku => (
                  <SkuCard
                    key={sku.matnr}
                    sku={sku}
                    onClick={() => navigate('/lifecycle/table')}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
