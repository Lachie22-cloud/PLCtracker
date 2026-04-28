import React, { useState, useMemo } from 'react';
import { RUNS, SAP_STATE } from '@/data/governance';
import { fmtRel, fmtAbs, fmtDate } from '@/data/utils';
import Icon from '@/components/Icon';
import { RunStatusBadge } from '@/components/Badges';

export interface LiveRun {
  id: number;
  source: string;
  status: 'running' | 'success' | 'error';
  records: number;
  mara: number;
  marc: number;
  changes: number;
  violations_rebuilt: number;
  started: string;
  finished: string | null;
  duration_s: number;
  records_so_far: number;
  progress: number;
  elapsed_s: number;
  step: string;
  error: string | null;
  user: string;
}

interface RunsScreenProps {
  liveRun: LiveRun | null;
  onRunNow: () => void;
}

export default function RunsScreen({ liveRun, onRunNow }: RunsScreenProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const runs = useMemo(() => {
    if (!liveRun) return RUNS;
    const exists = RUNS.find(r => r.id === liveRun.id);
    if (exists) return RUNS;
    return [
      {
        id: liveRun.id,
        source: liveRun.source,
        status: liveRun.status,
        records: liveRun.records,
        mara: liveRun.mara,
        marc: liveRun.marc,
        changes: liveRun.changes,
        violations_rebuilt: liveRun.violations_rebuilt,
        started: liveRun.started,
        finished: liveRun.finished,
        duration_s: liveRun.duration_s,
        error: liveRun.error,
        user: liveRun.user,
      },
      ...RUNS,
    ];
  }, [liveRun]);

  const toggleExpand = (id: number) => {
    setExpandedId(prev => (prev === id ? null : id));
  };

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <div className="page__title">Extraction Runs</div>
          <div className="page__sub">
            SAP OData pull history · Scheduler: {SAP_STATE.scheduler} · Next: {fmtDate(SAP_STATE.next_run_at)}
          </div>
        </div>
        <div className="page__actions">
          <button className="btn-primary" onClick={onRunNow}>
            <Icon name="play" size={13} />
            Run Now
          </button>
        </div>
      </div>

      <div className="tile-row" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        <div className="tile">
          <div className="tile__label">Last Run</div>
          <div className="tile__value tile__value--sm" style={{ fontSize: 18, marginTop: 6 }}>
            #{SAP_STATE.last_run_id}
          </div>
          <div className="tile__delta">{fmtRel(SAP_STATE.last_run_at)}</div>
        </div>
        <div className={`tile${SAP_STATE.failed_in_last_24h ? ' is-critical' : ' is-ok'}`}>
          <div className="tile__label">Status</div>
          <div className="tile__value" style={{ fontSize: 18, marginTop: 6 }}>
            {SAP_STATE.last_run_status === 'success' ? 'Healthy' : 'Error'}
          </div>
          <div className="tile__delta">{SAP_STATE.failed_in_last_24h ? 'Failed in last 24h' : 'No failures in 24h'}</div>
        </div>
        <div className="tile">
          <div className="tile__label">Last Records</div>
          <div className="tile__value" style={{ fontSize: 22, marginTop: 6 }}>
            {RUNS[0]?.records.toLocaleString() ?? '—'}
          </div>
          <div className="tile__delta">MARA + MARC</div>
        </div>
        <div className="tile">
          <div className="tile__label">Last Changes</div>
          <div className="tile__value" style={{ fontSize: 22, marginTop: 6 }}>
            {RUNS[0]?.changes.toLocaleString() ?? '—'}
          </div>
          <div className="tile__delta">field-level diffs</div>
        </div>
      </div>

      {liveRun && liveRun.status === 'running' && (
        <div className="run-progress">
          <div className="run-progress__head">
            <span className="badge badge--running">
              <span className="dot" />
              RUN #{liveRun.id}
            </span>
            <strong style={{ color: 'var(--text)' }}>SAP OData extraction in progress</strong>
            <span style={{ marginLeft: 'auto' }} className="mono">{liveRun.elapsed_s}s elapsed</span>
          </div>
          <div className="run-progress__bar">
            <div className="run-progress__fill" style={{ width: liveRun.progress + '%' }} />
          </div>
          <div className="run-progress__steps">
            {liveRun.step} · <span style={{ color: 'var(--running)' }}>{liveRun.records_so_far.toLocaleString()}</span> records pulled
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel__head">
          <span className="panel__title">Run History</span>
          <span className="panel__sub" style={{ marginLeft: 8 }}>{runs.length} runs</span>
        </div>
        <div className="panel__body--flush">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Records</th>
                  <th>MARA</th>
                  <th>MARC</th>
                  <th>Changes</th>
                  <th>Violations</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>User</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {runs.map(run => (
                  <React.Fragment key={run.id}>
                    <tr
                      className={run.status === 'error' ? 'severity-error' : ''}
                      onClick={() => run.status === 'error' && toggleExpand(run.id)}
                      style={{ cursor: run.status === 'error' ? 'pointer' : 'default' }}
                    >
                      <td>
                        <span className="mono" style={{ fontWeight: 600 }}>#{run.id}</span>
                      </td>
                      <td>{run.source}</td>
                      <td><RunStatusBadge status={run.status} /></td>
                      <td className="num">{run.records > 0 ? run.records.toLocaleString() : <span style={{ color: 'var(--muted-2)' }}>—</span>}</td>
                      <td className="num">{run.mara > 0 ? run.mara.toLocaleString() : <span style={{ color: 'var(--muted-2)' }}>—</span>}</td>
                      <td className="num">{run.marc > 0 ? run.marc.toLocaleString() : <span style={{ color: 'var(--muted-2)' }}>—</span>}</td>
                      <td className="num">{run.changes > 0 ? run.changes.toLocaleString() : <span style={{ color: 'var(--muted-2)' }}>—</span>}</td>
                      <td className="num">{run.violations_rebuilt > 0 ? run.violations_rebuilt.toLocaleString() : <span style={{ color: 'var(--muted-2)' }}>—</span>}</td>
                      <td>
                        <span title={fmtAbs(run.started)} style={{ color: 'var(--text-2)' }}>
                          {fmtAbs(run.started)}
                        </span>
                      </td>
                      <td className="num">
                        {run.duration_s > 0 ? (
                          <span className="mono" style={{ color: 'var(--muted)' }}>{run.duration_s}s</span>
                        ) : (
                          <span style={{ color: 'var(--muted-2)' }}>—</span>
                        )}
                      </td>
                      <td className="muted">{run.user}</td>
                      <td style={{ width: 32 }}>
                        {run.status === 'error' && (
                          <span style={{ color: 'var(--muted)', display: 'inline-flex' }}>
                            <Icon
                              name={expandedId === run.id ? 'chevron-up' : 'chevron-down'}
                              size={14}
                            />
                          </span>
                        )}
                      </td>
                    </tr>
                    {run.status === 'error' && expandedId === run.id && run.error && (
                      <tr>
                        <td colSpan={12} style={{ padding: '0 14px 12px', background: 'var(--critical-soft)' }}>
                          <pre
                            style={{
                              margin: '8px 0 0',
                              fontFamily: '"JetBrains Mono", monospace',
                              fontSize: 11.5,
                              color: 'var(--critical)',
                              background: 'transparent',
                              border: 'none',
                              padding: 0,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-all',
                            }}
                          >
                            {run.error}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
