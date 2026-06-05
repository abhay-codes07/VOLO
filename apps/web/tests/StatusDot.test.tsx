import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusDot } from "@/components/StatusDot";

describe("StatusDot", () => {
  it("renders the label", () => {
    render(<StatusDot status="nominal" label="all systems go" />);
    expect(screen.getByText("all systems go")).toBeInTheDocument();
  });

  it("uses the nominal color class for ship state", () => {
    const { container } = render(<StatusDot status="nominal" label="x" />);
    const dot = container.querySelector("span > span") as HTMLElement;
    expect(dot.className).toContain("bg-signal-nominal");
  });
});
