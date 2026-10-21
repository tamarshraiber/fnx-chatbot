// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Logo from "./Logo";

afterEach(cleanup);

describe("Logo", () => {
  it("has a readable label and the requested size", () => {
    render(<Logo size={48} />);
    const logo = screen.getByRole("img", { name: "עוזר וירטואלי" });
    expect(logo.getAttribute("width")).toBe("48");
    expect(logo.getAttribute("class")).not.toContain("thinking");
  });

  it("twinkles only while the bot is thinking", () => {
    render(<Logo thinking />);
    expect(screen.getByRole("img", { name: "עוזר וירטואלי" }).getAttribute("class")).toContain("logo--thinking");
  });

  it("gives every copy its own gradient ids, so several logos on one page do not clash", () => {
    const { container } = render(<><Logo /><Logo /></>);
    const ids = [...container.querySelectorAll("[id]")].map((element) => element.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
