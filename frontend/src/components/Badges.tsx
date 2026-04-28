import React from 'react';
import { PLANTS } from '@/data/governance';
import { DIVISIONS } from '@/data/presets';
import { stageMeta } from '@/data/lifecycle';

type SeverityInput = 'error' | 'warning' | 'info';
type BadgeVariant = 'critical' | 'warning' | 'info';

const SEVERITY_MAP: Record<SeverityInput, BadgeVariant> = {
  error:   'critical',
  warning: 'warning',
  info:    'info',
};

const SEVERITY_LABEL: Record<SeverityInput, string> = {
  error:   'Critical',
  warning: 'Warning',
  info:    'Info',
};

interface SeverityBadgeProps {
  severity: SeverityInput;
  label?: string;
}

export function SeverityBadge({ severity, label }: SeverityBadgeProps) {
  const variant = SEVERITY_MAP[severity];
  const text = label ?? SEVERITY_LABEL[severity];
  return (
    <span className={`badge badge--${variant}`}>
      <span className="dot" />
      {text}
    </span>
  );
}

interface PlantTagProps {
  code: string;
}

export function PlantTag({ code }: PlantTagProps) {
  const plant = PLANTS.find(p => p.code === code);
  const label = plant ? `${code} · ${plant.region}` : code;
  return <span className="code mono">{label}</span>;
}

type RunStatus = 'success' | 'error' | 'running';

const RUN_STATUS_VARIANT: Record<RunStatus, string> = {
  success: 'ok',
  error:   'critical',
  running: 'running',
};

const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  success: 'OK',
  error:   'Error',
  running: 'Running',
};

interface RunStatusBadgeProps {
  status: RunStatus;
  label?: string;
}

export function RunStatusBadge({ status, label }: RunStatusBadgeProps) {
  const variant = RUN_STATUS_VARIANT[status];
  const text = label ?? RUN_STATUS_LABEL[status];
  return (
    <span className={`badge badge--${variant}`}>
      <span className="dot" />
      {text}
    </span>
  );
}

interface StagePillProps {
  id: string;
}

export function StagePill({ id }: StagePillProps) {
  const meta = stageMeta(id);
  return (
    <span className={`stage-pill stage-pill--${meta.color}`}>
      {id}
    </span>
  );
}

interface DivisionBadgeProps {
  code: string;
}

export function DivisionBadge({ code }: DivisionBadgeProps) {
  const div = DIVISIONS.find(d => d.code === code);
  if (!div) {
    return (
      <span className="div-badge div-badge--blue">
        <span className="div-badge__code">{code}</span>
      </span>
    );
  }
  return (
    <span className={`div-badge div-badge--${div.color}`}>
      <span className="div-badge__code">{div.code}</span>
      {div.label}
    </span>
  );
}
