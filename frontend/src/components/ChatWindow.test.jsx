// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatWindow from "./ChatWindow";

afterEach(cleanup);

const chat = { messages: [], loading: false, error: null, send: vi.fn(), retry: vi.fn(), reset: vi.fn() };

describe("keyboard access", () => {
  it("has a skip link as the very first control, and it moves the focus to the question box", () => {
    const { container } = render(<ChatWindow mode="full" chat={chat} onToggleMode={() => {}} />);
    const skip = screen.getByRole("button", { name: "דילוג לתיבת השאלה" });
    expect(container.querySelector("button, a, textarea")).toBe(skip);
    fireEvent.click(skip);
    expect(document.activeElement).toBe(screen.getByLabelText("השאלה שלכם"));
  });
});
