// @vitest-environment jsdom
import { StrictMode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AccessibilityMenu from "./AccessibilityMenu";
import SpeakButton from "./SpeakButton";
import { AccessibilityProvider } from "../hooks/useAccessibility";

let synth;

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.contrast;
  synth = { speak: vi.fn(), cancel: vi.fn(), getVoices: vi.fn().mockReturnValue([{ lang: "he-IL", name: "Hebrew" }]) };
  window.speechSynthesis = synth;
  window.SpeechSynthesisUtterance = function Utterance(text) { this.text = text; };
});
afterEach(() => {
  cleanup();
  delete window.speechSynthesis;
  delete window.SpeechSynthesisUtterance;
});

describe("SpeakButton", () => {
  it("reads the answer aloud in Hebrew, and stops on the second click", () => {
    render(<SpeakButton text="ביטוח חובה הוא חובה על פי חוק" />);
    fireEvent.click(screen.getByRole("button", { name: "הקראת התשובה" }));
    const spoken = synth.speak.mock.calls[0][0];
    expect(spoken.text).toBe("ביטוח חובה הוא חובה על פי חוק");
    expect(spoken.lang).toBe("he-IL");
    const stop = screen.getByRole("button", { name: "עצירת ההקראה" });
    expect(stop.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(stop);
    expect(synth.cancel).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "הקראת התשובה" })).toBeTruthy();
  });

  it("tells the user when the device has no Hebrew voice", () => {
    synth.getVoices.mockReturnValue([{ lang: "en-US", name: "English" }]);
    render(<SpeakButton text="שלום" />);
    fireEvent.click(screen.getByRole("button", { name: "הקראת התשובה" }));
    expect(screen.getByRole("status").textContent).toContain("לא נמצא קול בעברית");
  });

  it("reads by itself only when auto-play is on", async () => {
    const { rerender } = render(<SpeakButton text="שלום" />);
    expect(synth.speak).not.toHaveBeenCalled();
    rerender(<SpeakButton text="שלום" autoPlay />);
    await waitFor(() => expect(synth.speak).toHaveBeenCalledTimes(1));
  });

  it("auto-play is not cancelled by React's double setup in development (StrictMode)", async () => {
    render(<StrictMode><SpeakButton text="שלום" autoPlay /></StrictMode>);
    await waitFor(() => expect(synth.speak).toHaveBeenCalledTimes(1));
    const speakOrder = synth.speak.mock.invocationCallOrder[0];
    const cancelsAfter = synth.cancel.mock.invocationCallOrder.filter((order) => order > speakOrder);
    expect(cancelsAfter).toHaveLength(0);
  });

  it("shows no button when the browser cannot speak", () => {
    delete window.speechSynthesis;
    const { container } = render(<SpeakButton text="שלום" />);
    expect(container.innerHTML).toBe("");
  });
});

describe("AccessibilityMenu", () => {
  const open = () => {
    render(<AccessibilityProvider><AccessibilityMenu /></AccessibilityProvider>);
    fireEvent.click(screen.getByRole("button", { name: "הגדרות נגישות" }));
  };

  it("opens, switches high contrast on, and resets", () => {
    open();
    fireEvent.click(screen.getByLabelText("ניגודיות גבוהה"));
    expect(document.documentElement.dataset.contrast).toBe("high");
    fireEvent.click(screen.getByRole("button", { name: "איפוס ההגדרות" }));
    expect(document.documentElement.dataset.contrast).toBeUndefined();
  });

  it("changes the text size within its limits", () => {
    open();
    const smaller = screen.getByRole("button", { name: "הקטנת הטקסט" });
    expect(smaller.disabled).toBe(true); // already at the normal size
    fireEvent.click(screen.getByRole("button", { name: "הגדלת הטקסט" }));
    expect(screen.getByText("115%")).toBeTruthy();
    expect(document.documentElement.style.getPropertyValue("--text-scale")).toBe("1.15");
  });

  it("closes with Escape and gives the focus back to its button", () => {
    open();
    expect(screen.getByRole("group", { name: "הגדרות נגישות" })).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("group", { name: "הגדרות נגישות" })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "הגדרות נגישות" }));
  });
});
