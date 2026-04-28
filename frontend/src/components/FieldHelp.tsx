import React, { createContext, useContext, useEffect, useState } from 'react';
import { fieldKb } from '@/data/presets';
import Icon from './Icon';

interface FieldHelpContextValue {
  open: (code: string) => void;
  close: () => void;
}

const FieldHelpContext = createContext<FieldHelpContextValue>({
  open: () => {},
  close: () => {},
});

interface FieldHelpProviderProps {
  children: React.ReactNode;
}

export default function FieldHelpProvider({ children }: FieldHelpProviderProps) {
  const [code, setCode] = useState<string | null>(null);

  const open = (fieldCode: string) => setCode(fieldCode);
  const close = () => setCode(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, []);

  const kb = code ? fieldKb(code) : null;

  return (
    <FieldHelpContext.Provider value={{ open, close }}>
      {children}

      <div
        className={`fh-backdrop${code ? ' is-open' : ''}`}
        onClick={close}
      />

      <aside className={`fh-panel${code ? ' is-open' : ''}`}>
        {kb && (
          <>
            <div className="fh-panel__head">
              <div>
                <div className="fh-panel__code mono">{kb.code}</div>
                <div className="fh-panel__label">{kb.label}</div>
                <div className="fh-panel__table">
                  SAP table · <span className="mono">{kb.table}</span>
                </div>
              </div>
              <button className="side-panel__close" onClick={close}>
                <Icon name="x" size={14} />
              </button>
            </div>

            <div className="fh-panel__body">
              <div className="fh-section">
                <div className="fh-section__h">What is it?</div>
                <p className="fh-section__p">{kb.what}</p>
              </div>

              <div className="fh-section">
                <div className="fh-section__h">Why does it matter?</div>
                <p className="fh-section__p">{kb.why}</p>
              </div>

              <div className="fh-section">
                <div className="fh-section__h">Example values</div>
                <p className="fh-section__p">{kb.example}</p>
                {kb.allowed_examples && kb.allowed_examples.length > 0 && (
                  <div className="fh-pills">
                    {kb.allowed_examples.map(v => (
                      <span key={v} className="fh-pill">{v}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="fh-foot">
                <Icon name="info" size={12} />
                <span>
                  Field metadata is editable in <strong>Admin → Rules</strong>.
                </span>
              </div>
            </div>
          </>
        )}
      </aside>
    </FieldHelpContext.Provider>
  );
}

export function useFieldHelp(): FieldHelpContextValue {
  return useContext(FieldHelpContext);
}

interface FieldChipProps {
  code: string;
  className?: string;
}

export function FieldChip({ code, className }: FieldChipProps) {
  const help = useFieldHelp();
  const combined = className ? `code mono fh-chip ${className}` : 'code mono fh-chip';
  return (
    <button className={combined} onClick={() => help.open(code)}>
      {code}
    </button>
  );
}
