import React, { useState } from 'react';
import { LC_UPLOADS, LIFECYCLE_STAGES } from '@/data/lifecycle';
import type { UploadRow } from '@/data/lifecycle';
import Icon from '@/components/Icon';

const STEP_LABELS = [
  'Parsing file…',
  'Validating stage vocabulary…',
  'Checking required columns…',
  'Applying rows…',
  'Done',
];

export default function LifecycleUpload() {
  const [drag, setDrag] = useState(false);
  const [history, setHistory] = useState<UploadRow[]>(LC_UPLOADS);
  const [parsing, setParsing] = useState<{ progress: number; step: string } | null>(null);

  const simulate = () => {
    if (parsing) return;
    let progress = 0;
    setParsing({ progress: 0, step: STEP_LABELS[0] });
    const interval = setInterval(() => {
      progress += 20;
      const stepIndex = Math.min(Math.floor(progress / 20), STEP_LABELS.length - 1);
      if (progress >= 100) {
        clearInterval(interval);
        const newRow: UploadRow = {
          id: history.length > 0 ? history[0].id + 1 : 1,
          file: 'lifecycle-upload.csv',
          rows: 11,
          accepted: 11,
          errors: 0,
          who: 'You',
          when: new Date().toISOString(),
          status: 'success',
        };
        setHistory(prev => [newRow, ...prev]);
        setParsing(null);
      } else {
        setParsing({ progress, step: STEP_LABELS[stepIndex] });
      }
    }, 400);
  };

  return (
    <div>
      <div className="page__head">
        <div>
          <div className="page__title">Upload Lifecycle Data</div>
          <div className="page__sub">Bulk-update stage, target date, and notes via CSV or XLSX</div>
        </div>
      </div>

      <div className="two-pane">
        <div style={{ display:'flex',flexDirection:'column',gap:14 }}>
          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Upload file</span>
            </div>
            <div className="panel__body" style={{ display:'flex',flexDirection:'column',gap:14 }}>
              <div
                className={"upload-zone"+(drag?" is-drag":"")}
                onDragOver={e=>{e.preventDefault();setDrag(true)}}
                onDragLeave={()=>setDrag(false)}
                onDrop={e=>{e.preventDefault();setDrag(false);simulate()}}
                onClick={simulate}
              >
                <Icon name="upload" size={32}/>
                <div className="upload-zone__title">Drop a file or click to upload</div>
                <div className="upload-zone__sub">Required columns: <span className="mono">matnr</span>, <span className="mono">stage</span>, <span className="mono">target_date</span>, <span className="mono">note</span></div>
              </div>

              {parsing && (
                <div className="run-progress">
                  <div className="run-progress__head">
                    <span className="spinner"/>
                    <span style={{ fontWeight:600,fontSize:12.5 }}>Processing…</span>
                    <span className="mono" style={{ marginLeft:'auto',color:'var(--muted)',fontSize:12 }}>{parsing.progress}%</span>
                  </div>
                  <div className="run-progress__bar">
                    <div className="run-progress__fill" style={{ width:parsing.progress+'%' }}/>
                  </div>
                  <div className="run-progress__steps">{parsing.step}</div>
                </div>
              )}

              <div className="callout callout--info">
                <Icon name="info" size={15}/>
                <div>
                  <strong>CSV format:</strong> UTF-8 encoded, comma-separated. First row must be the header.
                  Rows with unknown stage codes will be rejected and counted as errors.
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__title">Stage vocabulary</span>
              <span className="spacer"/>
              <span className="panel__sub">{LIFECYCLE_STAGES.length} stages</span>
            </div>
            <div className="panel__body">
              <div className="stage-grid">
                {LIFECYCLE_STAGES.map(st => (
                  <div key={st.id} className="stage-grid__cell">
                    <span className={"stage-pill stage-pill--"+st.color}>{st.id}</span>
                    <div>
                      <div style={{ fontWeight:600,fontSize:12.5,color:'var(--text)' }}>{st.label}</div>
                      <div style={{ fontSize:11.5,color:'var(--muted)',marginTop:2 }}>{st.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">Upload history</span>
            <span className="spacer"/>
            <span className="panel__sub">{history.length} uploads</span>
          </div>
          <div className="panel__body--flush">
            <div className="upload-history">
              {history.map(row => (
                <div key={row.id} className={"upload-row upload-row--"+row.status}>
                  <div className="upload-row__icon">
                    {row.status === 'success' && <Icon name="check-circle" size={15} style={{ color:'var(--ok)' }}/>}
                    {row.status === 'partial' && <Icon name="alert-triangle" size={15} style={{ color:'var(--warning)' }}/>}
                    {row.status === 'error' && <Icon name="x-circle" size={15} style={{ color:'var(--critical)' }}/>}
                  </div>
                  <div className="upload-row__body">
                    <div className="upload-row__head">
                      <span className="mono">{row.file}</span>
                      <span className="mono muted-text">{new Date(row.when).toISOString().replace('T',' ').slice(0,16)} UTC</span>
                    </div>
                    <div className="upload-row__meta">
                      {row.rows} rows · {row.accepted} accepted · {row.errors} errors · by {row.who}
                    </div>
                    {row.error && (
                      <div className="upload-row__err">{row.error}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
