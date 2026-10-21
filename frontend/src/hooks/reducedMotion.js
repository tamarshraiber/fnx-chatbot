/** True when the user wants less motion: the system setting, or our own "reduce motion" switch in the accessibility menu. */
export function prefersReducedMotion() {
  if (typeof document !== "undefined" && document.documentElement.dataset.motion === "reduce") return true;
  return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
}
