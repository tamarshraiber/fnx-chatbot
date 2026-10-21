// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import AccessibilityMenu from "./AccessibilityMenu";
import AccessibilityStatement from "./AccessibilityStatement";
import App from "../App";
import { fireEvent } from "@testing-library/react";

afterEach(() => {
  cleanup();
  window.location.hash = "";
});

describe("accessibility statement", () => {
  it("has a heading, honest limits, a way to report problems and a way back", () => {
    render(<AccessibilityStatement />);
    expect(screen.getByRole("heading", { level: 1, name: "הצהרת נגישות" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "מגבלות ידועות" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "עמוד יצירת הקשר באתר החברה" }).getAttribute("href")).toMatch(/^https:\/\/www\.fnx\.co\.il\//);
    expect(screen.getByRole("link", { name: "חזרה לצ'אט" }).getAttribute("href")).toBe("#/");
  });

  it("is reachable from the accessibility menu", () => {
    render(<AccessibilityMenu />);
    fireEvent.click(screen.getByRole("button", { name: "הגדרות נגישות" }));
    expect(screen.getByRole("link", { name: "הצהרת נגישות" }).getAttribute("href")).toBe("#/accessibility");
  });

  it("opens at the address #/accessibility", () => {
    window.location.hash = "#/accessibility";
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "הצהרת נגישות" })).toBeTruthy();
  });
});
