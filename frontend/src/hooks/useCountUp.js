import { useEffect, useState } from "react";
import { prefersReducedMotion } from "./reducedMotion";

const DURATION_MS = 1100;

const easeOut = (t) => 1 - (1 - t) ** 3; // fast at first, then slows down near the final number

/**
 * Counts from 0 up to `target`, so a number on the page feels alive.
 * With "reduce motion" on, or when `target` is not a number, the final value is returned at once.
 */
export function useCountUp(target) {
  const isNumber = typeof target === "number" && Number.isFinite(target);
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!isNumber) return undefined;
    if (prefersReducedMotion()) {
      setValue(target);
      return undefined;
    }

    const start = performance.now();
    let frame = 0;
    const tick = (now) => {
      const progress = Math.min((now - start) / DURATION_MS, 1);
      setValue(Math.round(target * easeOut(progress)));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, isNumber]);

  if (!isNumber) return target;
  return prefersReducedMotion() ? target : value;
}
