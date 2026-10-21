import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "fnx-accessibility";

/** Text size steps: 1 is the normal size. The page text is multiplied by this number. */
export const TEXT_SCALES = [1, 1.15, 1.3, 1.5];

export const DEFAULT_SETTINGS = { textStep: 0, contrast: false, reduceMotion: false, autoRead: false };

/** Read the saved settings. Anything missing, broken or unexpected falls back to the default. */
export function loadSettings(storage) {
  try {
    const saved = JSON.parse(storage.getItem(STORAGE_KEY) || "{}");
    const step = Number.isInteger(saved.textStep) ? Math.min(Math.max(saved.textStep, 0), TEXT_SCALES.length - 1) : 0;
    return {
      textStep: step,
      contrast: saved.contrast === true,
      reduceMotion: saved.reduceMotion === true,
      autoRead: saved.autoRead === true,
    };
  } catch {
    return { ...DEFAULT_SETTINGS }; // no storage (private window) or broken data: just use the defaults
  }
}

/** Put the settings on the page itself, so the style sheets can react to them. */
export function applySettings(settings, root = document.documentElement) {
  root.style.setProperty("--text-scale", String(TEXT_SCALES[settings.textStep]));
  if (settings.contrast) root.dataset.contrast = "high";
  else delete root.dataset.contrast;
  if (settings.reduceMotion) root.dataset.motion = "reduce";
  else delete root.dataset.motion;
}

// Without a provider (for example in a small test) the hook still works, it just changes nothing.
const AccessibilityContext = createContext({ settings: DEFAULT_SETTINGS, update: () => {}, reset: () => {} });

export function AccessibilityProvider({ children }) {
  const [settings, setSettings] = useState(() => loadSettings(window.localStorage));

  useEffect(() => {
    applySettings(settings);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // the settings still work for this visit, they are just not remembered
    }
  }, [settings]);

  const update = useCallback((change) => setSettings((current) => ({ ...current, ...change })), []);
  const reset = useCallback(() => setSettings({ ...DEFAULT_SETTINGS }), []);
  const value = useMemo(() => ({ settings, update, reset }), [settings, update, reset]);
  return <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>;
}

export function useAccessibility() {
  return useContext(AccessibilityContext);
}
