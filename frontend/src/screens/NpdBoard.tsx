import React from 'react';
import { useNavigate } from 'react-router-dom';
import { NPD, stepProgress, daysOpen } from '@/data/npd';
import { DIVISIONS } from '@/data/presets';
import Icon from '@/components/Icon';
import { DivisionBadge } from '@/components/Badges';

interface KanbanColumn {
  status: string;
  label: string;
  dot: string;
}

const COLUMNS: KanbanColumn[] = [
  { status: 'in_progress', label: 'In Progress', dot: 'info' },
  { status: 'on_hold',     label: 'On Hold',     dot: 'warning' },
  { status: 'completed',   label: 'Completed',   dot: 'ok' },
  { status: 'cancelled',   label: 'Cancelled',   dot: 'muted' },
];

export default function NpdBoardScreen() {
  const navigate = useNavigate();

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">NPD board</div>
          <div className="page__sub">{NPD.length} requests across {COLUMNS.length} columns</div>
        </div>
        <div className="page__actions">
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/npd')}>
            <Icon name="table" size={14} /> List view
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/npd')}>
            <Icon name="plus" size={14} /> New request
          </button>
        </div>
      </div>

      <div className="kanban">
        {COLUMNS.map(col => {
          const cards = NPD.filter(r => r.status === col.status);
          return (
            <div key={col.status} className="kanban-col">
              <div className="kanban-col__head">
                <div className="kanban-col__title">
                  <span className={'kanban-col__dot kanban-col__dot--' + col.dot} />
                  {col.label}
                </div>
                <span className="kanban-col__count">{cards.length}</span>
              </div>
              <div className="kanban-col__body">
                {cards.length === 0 && (
                  <div className="kanban-empty">No requests</div>
                )}
                {cards.map(req => {
                  const sp = stepProgress(req);
                  const pct = sp.total > 0 ? Math.round((sp.done / sp.total) * 100) : 0;
                  const days = daysOpen(req.created);
                  return (
                    <div
                      key={req.no}
                      className="kanban-card"
                      onClick={() => navigate('/npd/' + req.no)}
                    >
                      <div className="kanban-card__head">
                        <span className="req-no mono">{req.no}</span>
                        <DivisionBadge code={req.division} />
                      </div>

                      <div className="kanban-card__skus">
                        {req.bulk_sku !== '—' && (
                          <span className="code mono" style={{ fontSize: 10.5 }}>{req.bulk_sku}</span>
                        )}
                        {req.fg_sku !== '—' && (
                          <span className="code mono" style={{ fontSize: 10.5, color: 'var(--text-2)' }}>{req.fg_sku}</span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-cell" style={{ flex: 1 }}>
                          <div className="progress-cell__bar">
                            <div className="progress-cell__fill" style={{ width: pct + '%' }} />
                          </div>
                          <div className="progress-cell__text mono">{sp.done}/{sp.total}</div>
                        </div>
                      </div>

                      <div className="kanban-card__foot">
                        {sp.next && (
                          <span className="step-chip" style={{ fontSize: 10.5 }}>{sp.next.label}</span>
                        )}
                        <span className="kanban-card__days" style={{ marginLeft: 'auto' }}>
                          {days}d open
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
