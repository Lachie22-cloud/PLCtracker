import { useState, useEffect } from 'react';

export type Theme = 'dark' | 'light';
export type Accent = 'amber' | 'blue' | 'violet' | 'green';
export type Density = 'compact' | 'comfortable';

export interface ThemePrefs {
  theme: Theme;
  accent: Accent;
  density: Density;
}

const DEFAULTS: ThemePrefs = { theme: 'dark', accent: 'amber', density: 'compact' };

const load = (): ThemePrefs => {
  try {
    const s = localStorage.getItem('mdg-prefs');
    return s ? { ...DEFAULTS, ...JSON.parse(s) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
};

export const useTheme = () => {
  const [prefs, setPrefs] = useState<ThemePrefs>(load);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', prefs.theme);
    root.setAttribute('data-accent', prefs.accent);
    root.setAttribute('data-density', prefs.density);
    localStorage.setItem('mdg-prefs', JSON.stringify(prefs));
  }, [prefs]);

  const set = <K extends keyof ThemePrefs>(k: K, v: ThemePrefs[K]) =>
    setPrefs(p => ({ ...p, [k]: v }));

  return { prefs, set };
};
