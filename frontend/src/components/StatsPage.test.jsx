// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { percentOf } from "./AccuracyRing";
import StatsPage from "./StatsPage";

vi.mock("../api", async (importOriginal) => ({ ...(await importOriginal()), fetchStats: vi.fn() }));
const { fetchStats } = await import("../api");

const STATS = {
  pages: 1075,
  chunks: 9315,
  last_refresh: "2026-10-21T13:07:32+00:00",
  eval: {
    date: "2026-10-21",
    answerable_correct: 19,
    answerable_total: 20,
    unanswerable_rejected: 7,
    unanswerable_total: 10,
    retrieval_top5: 20,
    retrieval_total: 20,
  },
};

beforeEach(() => {
  fetchStats.mockReset();
  // Turn "reduce motion" on, so the numbers show their final value at once.
  window.matchMedia = vi.fn().mockReturnValue({ matches: true });
});
afterEach(cleanup);

describe("percentOf", () => {
  it("rounds to a whole percent", () => {
    expect(percentOf(19, 20)).toBe(95);
    expect(percentOf(7, 10)).toBe(70);
    expect(percentOf(1, 3)).toBe(33);
  });

  it("is 0 when there is no total, and never goes above 100", () => {
    expect(percentOf(0, 0)).toBe(0);
    expect(percentOf(5, undefined)).toBe(0);
    expect(percentOf(25, 20)).toBe(100);
  });
});

describe("StatsPage", () => {
  it("shows the loading placeholders until the data arrives", async () => {
    fetchStats.mockReturnValue(new Promise(() => {}));
    render(<StatsPage />);
    expect(screen.getByRole("status", { name: "טוען נתונים" })).toBeTruthy();
  });

  it("shows the totals, the rings and the comparison once loaded", async () => {
    fetchStats.mockResolvedValue(STATS);
    render(<StatsPage />);
    await waitFor(() => expect(screen.getByText("1,075")).toBeTruthy());
    expect(screen.getByText("9,315")).toBeTruthy();
    expect(screen.getByText("כ-8.7 קטעים לכל עמוד")).toBeTruthy();
    expect(screen.getByText("95%", { selector: ".ring__percent" })).toBeTruthy();
    expect(screen.getByText("70%", { selector: ".ring__percent" })).toBeTruthy();
    expect(screen.getByText("השוואה בין הבדיקות")).toBeTruthy();
    expect(screen.queryByRole("status", { name: "טוען נתונים" })).toBeNull();
  });

  it("explains each graph, using the numbers from the data", async () => {
    fetchStats.mockResolvedValue(STATS);
    render(<StatsPage />);
    await waitFor(() => expect(screen.getByText("השוואה בין הבדיקות")).toBeTruthy());
    expect(screen.getByText(/מתוך 20 שאלות שהתשובה להן באתר/)).toBeTruthy();
    expect(screen.getByText(/מתוך 10 שאלות שאין להן תשובה באתר/)).toBeTruthy();
    expect(screen.getByText(/בכמה מ-20 השאלות/)).toBeTruthy();
    expect(screen.getByText(/הפס הכתום הוא הנקודה החלשה ביותר/)).toBeTruthy();
  });

  it("marks only the weakest bar", async () => {
    fetchStats.mockResolvedValue(STATS);
    const { container } = render(<StatsPage />);
    await waitFor(() => expect(screen.getByText("השוואה בין הבדיקות")).toBeTruthy());
    const weak = container.querySelectorAll(".bar__fill--weak");
    expect(weak).toHaveLength(1);
    expect(weak[0].style.width).toBe("70%");
  });

  it("still opens when the database totals are missing", async () => {
    fetchStats.mockResolvedValue({ pages: null, chunks: null, last_refresh: null, eval: STATS.eval });
    render(<StatsPage />);
    await waitFor(() => expect(screen.getByText("השוואה בין הבדיקות")).toBeTruthy());
    expect(screen.queryByText(/קטעים לכל עמוד/)).toBeNull();
  });

  it("shows the error message when loading fails", async () => {
    fetchStats.mockRejectedValue(new Error("down"));
    render(<StatsPage />);
    await waitFor(() => expect(screen.getByText(/לא הצלחנו לטעון את הנתונים/)).toBeTruthy());
  });
});
