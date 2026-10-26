import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HintLadder } from "@/components/hint-ladder";
import { renderWithProviders } from "@/test/render";

describe("HintLadder", () => {
  it("shows every rung and marks the current one", () => {
    renderWithProviders(<HintLadder level={2} max={3} mode="homework" />);

    const ladder = screen.getByRole("navigation", { name: "Hint ladder" });
    const rungs = within(ladder).getAllByRole("listitem");
    expect(rungs).toHaveLength(3);
    expect(within(ladder).getByText("Strategy").closest("[aria-current]")).toHaveAttribute(
      "aria-current",
      "step",
    );
    expect(within(ladder).getByText("Nudge").closest("[data-state]")).toHaveAttribute(
      "data-state",
      "done",
    );
    expect(within(ladder).getByText("Worked step").closest("[data-state]")).toHaveAttribute(
      "data-state",
      "todo",
    );
    expect(screen.getByText("Level 2 of 3")).toBeInTheDocument();
  });

  it("invites the learner to climb before the first hint", () => {
    renderWithProviders(<HintLadder level={0} max={2} mode="homework" />);
    expect(screen.getByText("Ask for help to climb")).toBeInTheDocument();
    expect(screen.queryByRole("listitem", { current: "step" })).toBeNull();
  });

  it("speaks Vietnamese", () => {
    renderWithProviders(<HintLadder level={1} max={3} mode="homework" />, { language: "vi" });
    expect(screen.getByRole("navigation", { name: "Thang gợi ý" })).toBeInTheDocument();
    expect(screen.getByText("Gợi mở")).toBeInTheDocument();
    expect(screen.getByText("Mức 1/3")).toBeInTheDocument();
  });

  it("has no ladder in explain mode", () => {
    renderWithProviders(<HintLadder level={0} max={0} mode="explain" />);
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.getByText(/Explain mode/)).toBeInTheDocument();
  });

  it("lets keyboard users reach every rung", () => {
    renderWithProviders(<HintLadder level={1} max={3} mode="homework" />);
    for (const name of ["Nudge", "Strategy", "Worked step"]) {
      expect(screen.getByText(name).closest("[tabindex]")).toHaveAttribute("tabindex", "0");
    }
  });
});
