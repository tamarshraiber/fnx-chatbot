// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AccessibilityProvider, applySettings, DEFAULT_SETTINGS, loadSettings, TEXT_SCALES, useAccessibility } from "./useAccessibility";
import { cleanForSpeech, pickHebrewVoice } from "./useSpeech";

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.contrast;
  delete document.documentElement.dataset.motion;
  document.documentElement.style.removeProperty("--text-scale");
});
afterEach(cleanup);

describe("loadSettings", () => {
  it("uses the defaults when nothing is saved", () => {
    expect(loadSettings(localStorage)).toEqual(DEFAULT_SETTINGS);
  });

  it("ignores broken or out-of-range saved data", () => {
    localStorage.setItem("fnx-accessibility", "{not json");
    expect(loadSettings(localStorage)).toEqual(DEFAULT_SETTINGS);
    localStorage.setItem("fnx-accessibility", JSON.stringify({ textStep: 99, contrast: "yes" }));
    expect(loadSettings(localStorage)).toEqual({ ...DEFAULT_SETTINGS, textStep: TEXT_SCALES.length - 1 });
  });

  it("falls back to the defaults when the storage cannot be used", () => {
    const broken = { getItem: () => { throw new Error("blocked"); } };
    expect(loadSettings(broken)).toEqual(DEFAULT_SETTINGS);
  });
});

describe("applySettings", () => {
  it("puts the text size and the switches on the page", () => {
    applySettings({ textStep: 2, contrast: true, reduceMotion: true, autoRead: false });
    const root = document.documentElement;
    expect(root.style.getPropertyValue("--text-scale")).toBe(String(TEXT_SCALES[2]));
    expect(root.dataset.contrast).toBe("high");
    expect(root.dataset.motion).toBe("reduce");
    applySettings(DEFAULT_SETTINGS);
    expect(root.dataset.contrast).toBeUndefined();
    expect(root.dataset.motion).toBeUndefined();
  });
});

describe("AccessibilityProvider", () => {
  it("applies a change at once and remembers it", () => {
    const { result } = renderHook(() => useAccessibility(), { wrapper: AccessibilityProvider });
    act(() => result.current.update({ contrast: true }));
    expect(document.documentElement.dataset.contrast).toBe("high");
    expect(JSON.parse(localStorage.getItem("fnx-accessibility")).contrast).toBe(true);
    act(() => result.current.reset());
    expect(document.documentElement.dataset.contrast).toBeUndefined();
  });
});

describe("speech helpers", () => {
  it("removes marks and web addresses before reading aloud", () => {
    expect(cleanForSpeech("**חשוב**: ראו https://www.fnx.co.il/a\n• פריט ראשון\n- פריט שני")).toBe("חשוב: ראו פריט ראשון פריט שני");
    expect(cleanForSpeech(null)).toBe("");
  });

  it("picks a Hebrew voice, or none", () => {
    const he = { lang: "he-IL", name: "Hebrew" };
    expect(pickHebrewVoice([{ lang: "en-US" }, he])).toBe(he);
    expect(pickHebrewVoice([{ lang: "en-US" }, { lang: "fr-FR" }])).toBeNull();
    expect(pickHebrewVoice([])).toBeNull();
  });
});
