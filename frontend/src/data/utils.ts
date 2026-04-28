export const fmtRel = (iso: string): string => {
  const t = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.floor((now - t) / 1000);
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
};

export const fmtAbs = (iso: string): string =>
  new Date(iso).toISOString().replace('T', ' ').slice(0, 16) + ' UTC';

export const fmtDate = (iso: string): string =>
  new Date(iso).toISOString().slice(0, 10);
