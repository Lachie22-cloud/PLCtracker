import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { NPD, NPD_STEPS, STEP_STATUS_META, stepProgress, type NpdRequest, type StepStatus } from '@/data/npd';
import { DIVISIONS } from '@/data/presets';
import { fmtRel } from '@/data/utils';
import Icon from '@/components/Icon';
import { DivisionBadge } from '@/components/Badges';

const STEP_STATUS_OPTIONS: StepStatus[] = ['not_started', 'in_progress', 'completed', 'blocked', 'n_a'];

function dotClass(status: StepStatus): string {
  const meta = STEP_STATUS_META[status];
  if (!meta) return '';
  return 'step__dot--' + meta.color;
}

function railClass(status: StepStatus): string {
  const meta = STEP_STATUS_META[status];
  if (!meta) return '';
  return 'step__rail--' + meta.color;
}

function isLocked(stepId: string, progress: Record<string, StepStatus>): boolean {
  for (const step of NPD_STEPS) {
    if (step.id === stepId) break;
    const st = progress[step.id];
    if (st !== 'completed' && st !== 'n_a') return true;
  }
  return false;
}

interface StepTrackerProps {
  req: NpdRequest;
  onChange: (stepId: string, status: StepStatus) => void;
}

function StepTracker({ req, onChange }: StepTrackerProps) {
  const [openStep, setOpenStep] = useState<string | null>(null);

  const toggleStep = (stepId: string) => {
    if (isLocked(stepId, req.progress)) return;
    setOpenStep(prev => (prev === stepId ? null : stepId));
  };

  return (
    <div className="step-tracker">
      {NPD_STEPS.map((step, idx) => {
        const status: StepStatus = req.progress[step.id] ?? 'not_started';
        const meta = STEP_STATUS_META[status];
        const locked = isLocked(step.id, req.progress);
        const open = openStep === step.id;
        const isFirst = idx === 0;
        const isLast = idx === NPD_STEPS.length - 1;

        return (
          <div key={step.id} className={'step' + (locked ? ' is-locked' : '')}>
            <div className={'step__rail' + (!isFirst ? '' : '') + ' ' + railClass(status)} />
            <div className={'step__dot ' + dotClass(status)}>
              {status === 'completed' && <Icon name="check" size={10} />}
              {status === 'blocked' && <Icon name="x" size={10} />}
              {status === 'n_a' && <span>—</span>}
              {status === 'not_started' && <span style={{ color: 'var(--muted-2)', fontSize: 9 }}>{idx + 1}</span>}
              {status === 'in_progress' && <span style={{ fontSize: 9 }}>{idx + 1}</span>}
            </div>
            <div
              className={'step__body' + (open ? ' is-open' : '')}
              onClick={() => toggleStep(step.id)}
            >
              <div className="step__head">
                <div>
                  <div className="step__label">
                    {step.label}
                  </div>
                  <div className="step__desc">{step.desc}</div>
                  {req.completed_by[step.id] && (
                    <div className="step__by">{req.completed_by[step.id]}</div>
                  )}
                </div>
                <span className={'badge badge--' + (meta?.color || '')}>
                  <span className="dot" />
                  {meta?.label ?? status}
                </span>
              </div>

              {open && !locked && (
                <div className="step__expand">
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {STEP_STATUS_OPTIONS.map(s => {
                      const sm = STEP_STATUS_META[s];
                      return (
                        <button
                          key={s}
                          className={'btn btn-secondary btn-xs' + (status === s ? ' is-active' : '')}
                          style={status === s ? { borderColor: 'var(--accent)', color: 'var(--accent)', background: 'var(--accent-soft)' } : {}}
                          onClick={e => { e.stopPropagation(); onChange(step.id, s); }}
                        >
                          {sm?.label ?? s}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function NpdDetailScreen() {
  const navigate = useNavigate();
  const { reqNo } = useParams<{ reqNo: string }>();

  const original = NPD.find(r => r.no === reqNo);
  const [req, setReq] = useState<NpdRequest | undefined>(original);
  const [commentText, setCommentText] = useState('');
  const [emailPaste, setEmailPaste] = useState('');

  if (!req) {
    return (
      <div>
        <div className="page__head">
          <div>
            <button className="crumb-link" onClick={() => navigate('/npd')}>
              <Icon name="chevron-left" size={12} /> Back to requests
            </button>
            <div className="page__title" style={{ marginTop: 6 }}>Request not found</div>
          </div>
        </div>
      </div>
    );
  }

  const sp = stepProgress(req);
  const division = DIVISIONS.find(d => d.code === req.division);

  const handleStepChange = (stepId: string, status: StepStatus) => {
    setReq(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        progress: { ...prev.progress, [stepId]: status },
      };
    });
  };

  const handlePostComment = () => {
    if (!commentText.trim()) return;
    const comment = {
      who: 'Lena Decker',
      when: new Date().toISOString(),
      text: commentText.trim(),
    };
    setReq(prev => {
      if (!prev) return prev;
      return { ...prev, comments: [...prev.comments, comment] };
    });
    setCommentText('');
  };

  const handleParseEmail = () => {
    if (!emailPaste.trim()) return;
    const lines = emailPaste.split('\n');
    const subjectLine = lines.find(l => l.toLowerCase().startsWith('subject:'));
    const subject = subjectLine ? subjectLine.replace(/^subject:\s*/i, '') : emailPaste.slice(0, 60);
    const matched = NPD_STEPS.find(s =>
      emailPaste.toLowerCase().includes(s.id.replace('_', ' '))
    );
    const email = {
      when: new Date().toISOString(),
      subject,
      matched_step: matched?.id ?? '',
      note: matched ? `Step matched: ${matched.label}` : 'No step matched automatically.',
    };
    setReq(prev => {
      if (!prev) return prev;
      return { ...prev, emails: [...prev.emails, email] };
    });
    setEmailPaste('');
  };

  return (
    <div>
      <div className="page__head">
        <div>
          <button className="crumb-link" onClick={() => navigate('/npd')}>
            <Icon name="chevron-left" size={12} /> NPD requests
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
            <div className="page__title">{req.no}</div>
            <span className="page__title-sub">{req.type}</span>
            {req.governance_violations > 0 && (
              <span className="badge badge--critical">
                <span className="dot" />
                {req.governance_violations} governance {req.governance_violations === 1 ? 'violation' : 'violations'}
              </span>
            )}
          </div>
        </div>
        <div className="page__actions">
          <DivisionBadge code={req.division} />
          <span className="badge badge--running">
            <span className="dot" />
            {req.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      <div className="npd-detail-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Request details</span>
            </div>
            <div className="panel__body">
              <dl className="kv">
                <dt>Request no</dt>
                <dd><span className="req-no mono">{req.no}</span></dd>
                <dt>Type</dt>
                <dd>{req.type}</dd>
                <dt>Requested by</dt>
                <dd>{req.from}</dd>
                <dt>Division</dt>
                <dd><DivisionBadge code={req.division} /></dd>
                <dt>Bulk SKU</dt>
                <dd><span className="code mono">{req.bulk_sku}</span></dd>
                <dt>FG SKU</dt>
                <dd><span className="code mono">{req.fg_sku}</span></dd>
                <dt>Warehouse</dt>
                <dd>
                  {req.warehouse_plants.length > 0
                    ? req.warehouse_plants.join(', ')
                    : <span style={{ color: 'var(--muted)' }}>None</span>
                  }
                </dd>
                <dt>Target date</dt>
                <dd>{req.target || '—'}</dd>
                <dt>Created</dt>
                <dd>{req.created}</dd>
                <dt>Entered by</dt>
                <dd>{req.entered_by}</dd>
                <dt>Progress</dt>
                <dd>
                  <div className="progress-cell">
                    <div className="progress-cell__bar">
                      <div
                        className="progress-cell__fill"
                        style={{ width: (sp.total > 0 ? Math.round(sp.done / sp.total * 100) : 0) + '%' }}
                      />
                    </div>
                    <div className="progress-cell__text mono">{sp.done}/{sp.total}</div>
                  </div>
                </dd>
              </dl>

              {req.notes && (
                <div style={{ marginTop: 14, padding: '10px 12px', background: 'var(--panel-2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}>
                  {req.notes}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Step tracker</span>
            <span className="spacer" />
            <span className="panel__sub">{sp.done}/{sp.total} complete</span>
          </div>
          <StepTracker req={req} onChange={handleStepChange} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Comments</span>
              <span className="spacer" />
              <span className="panel__sub">{req.comments.length}</span>
            </div>
            <div className="panel__body--flush">
              <div className="comments">
                {req.comments.length === 0 && (
                  <div style={{ padding: '20px 14px', color: 'var(--muted)', fontSize: 12, textAlign: 'center' }}>
                    No comments yet.
                  </div>
                )}
                {req.comments.map((c, idx) => (
                  <div key={idx} className="comment">
                    <span className="avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
                      {c.who.split(' ').map(w => w[0]).join('').slice(0, 2)}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div className="comment__head">
                        <span className="comment__who">{c.who}</span>
                        <span className="comment__when">{fmtRel(c.when)}</span>
                      </div>
                      <div className="comment__text">{c.text}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="comment-form">
                <textarea
                  rows={2}
                  placeholder="Add a comment…"
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                />
                <button className="btn btn-primary btn-sm" onClick={handlePostComment}>
                  <Icon name="send" size={13} /> Post
                </button>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Email log</span>
              <span className="spacer" />
              <span className="panel__sub">{req.emails.length}</span>
            </div>
            <div className="panel__body">
              <textarea
                rows={3}
                placeholder="Paste email content to parse and match to a step…"
                value={emailPaste}
                onChange={e => setEmailPaste(e.target.value)}
                style={{ width: '100%', marginBottom: 8 }}
              />
              <button className="btn btn-secondary btn-sm" onClick={handleParseEmail}>
                <Icon name="zap" size={13} /> Parse &amp; match
              </button>

              {req.emails.length > 0 && (
                <div className="email-list">
                  {req.emails.map((em, idx) => (
                    <div key={idx} className="email-row">
                      <Icon name="send" size={14} style={{ color: 'var(--muted)', marginTop: 2, flexShrink: 0 }} />
                      <div style={{ flex: 1 }}>
                        <div className="email-row__sub">{em.subject}</div>
                        <div className="email-row__meta">
                          <Icon name="clock" size={11} />
                          {fmtRel(em.when)}
                          {em.matched_step && (
                            <>
                              <span style={{ color: 'var(--muted-3)' }}>·</span>
                              <span className="step-chip">{em.matched_step}</span>
                            </>
                          )}
                        </div>
                        {em.note && <div className="email-row__note">{em.note}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
