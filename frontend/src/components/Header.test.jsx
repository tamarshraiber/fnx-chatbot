// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Header from "./Header";

afterEach(cleanup);

const props = { hasMessages: false, onNewChat: () => {}, onToggleMode: () => {}, onClose: () => {} };

describe("quality page link", () => {
  it("shows an icon and the text in the full view", () => {
    const { container } = render(<Header mode="full" {...props} />);
    const link = screen.getByRole("link", { name: "מדד האמינות" });
    expect(link.getAttribute("href")).toBe("#/stats");
    expect(link.querySelector("svg")).toBeTruthy();
    expect(link.className).not.toContain("compact");
    expect(container.querySelector(".header__link-text")).toBeTruthy();
  });

  it("is still there in the small widget, as an icon only", () => {
    render(<Header mode="widget" {...props} />);
    const link = screen.getByRole("link", { name: "מדד האמינות" });
    expect(link.className).toContain("header__link--compact");
    expect(link.getAttribute("title")).toBe("מדד האמינות");
  });
});
