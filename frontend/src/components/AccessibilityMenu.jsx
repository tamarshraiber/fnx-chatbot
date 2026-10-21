import { useEffect, useId, useRef, useState } from "react";
import { AccessibilityIcon } from "./Icons";
import { TEXT_SCALES, useAccessibility } from "../hooks/useAccessibility";
import { speechSupported } from "../hooks/useSpeech";
import "./AccessibilityMenu.css";

/** A button in the header that opens the accessibility settings: text size, high contrast, less motion, auto-read. */
export default function AccessibilityMenu() {
  const { settings, update, reset } = useAccessibility();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const wrapper = useRef(null);
  const button = useRef(null);

  // Close with Escape (focus goes back to the button) or by clicking anywhere outside the menu.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    const onClick = (event) => {
      if (wrapper.current && !wrapper.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const lastStep = TEXT_SCALES.length - 1;
  return (
    <div className="a11y" ref={wrapper}>
      <button
        type="button"
        ref={button}
        className="icon-btn"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        title="הגדרות נגישות"
        aria-label="הגדרות נגישות"
      >
        <AccessibilityIcon />
      </button>
      {open && (
        <div className="a11y__panel" id={panelId} role="group" aria-label="הגדרות נגישות">
          <div className="a11y__row">
            <span id={`${panelId}-size`}>גודל טקסט</span>
            <div className="a11y__size" role="group" aria-labelledby={`${panelId}-size`}>
              <button
                type="button"
                onClick={() => update({ textStep: settings.textStep - 1 })}
                disabled={settings.textStep === 0}
                aria-label="הקטנת הטקסט"
              >
                א-
              </button>
              <span aria-live="polite" dir="ltr">{Math.round(TEXT_SCALES[settings.textStep] * 100)}%</span>
              <button
                type="button"
                onClick={() => update({ textStep: settings.textStep + 1 })}
                disabled={settings.textStep === lastStep}
                aria-label="הגדלת הטקסט"
              >
                א+
              </button>
            </div>
          </div>

          <label className="a11y__row a11y__switch">
            <span>ניגודיות גבוהה</span>
            <input type="checkbox" checked={settings.contrast} onChange={(e) => update({ contrast: e.target.checked })} />
          </label>
          <label className="a11y__row a11y__switch">
            <span>הפחתת תנועה</span>
            <input type="checkbox" checked={settings.reduceMotion} onChange={(e) => update({ reduceMotion: e.target.checked })} />
          </label>
          {speechSupported() && (
            <label className="a11y__row a11y__switch">
              <span>הקראה אוטומטית של תשובות</span>
              <input type="checkbox" checked={settings.autoRead} onChange={(e) => update({ autoRead: e.target.checked })} />
            </label>
          )}
          <button type="button" className="a11y__reset" onClick={reset}>איפוס ההגדרות</button>
        </div>
      )}
    </div>
  );
}
