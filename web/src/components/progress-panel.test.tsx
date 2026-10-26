import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressPanel, streakMessage } from "@/components/progress-panel";
import { renderWithProviders } from "@/test/render";
import type { Progress } from "@/lib/types";

const PROGRESS: Progress = {
  sessions: 4,
  graded_attempts: 3,
  average_score: 86.7,
  current_streak: 3,
  best_streak: 5,
  active_today: false,
  last_active_on: "2026-10-25",
  subjects: [{ subject: "math", sessions: 3, graded_attempts: 2, average_score: 90 }],
};

describe("streakMessage", () => {
  it.each([
    [{ active_today: true, current_streak: 3 }, "progress.streak.today"],
    [{ active_today: false, current_streak: 3 }, "progress.streak.pending"],
    [{ active_today: false, current_streak: 0 }, "progress.streak.none"],
  ])("%j -> %s", (state, key) => {
    expect(streakMessage({ ...PROGRESS, ...state }).key).toBe(key);
  });
});

describe("ProgressPanel", () => {
  it("summarises sessions, scores and the streak", () => {
    renderWithProviders(<ProgressPanel progress={PROGRESS} />);

    expect(screen.getByRole("region", { name: "My progress" })).toBeInTheDocument();
    for (const label of ["Sessions", "Average score", "Day streak"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByTestId("streak-message")).toHaveTextContent(
      "Practise today to keep your 3-day streak!",
    );
    expect(screen.getByText("Best streak: 5 days")).toBeInTheDocument();
    expect(screen.getByText("Math")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("shows a dash before the first graded attempt", () => {
    renderWithProviders(
      <ProgressPanel progress={{ ...PROGRESS, average_score: null, subjects: [] }} />,
      { language: "vi" },
    );
    expect(screen.getByText("Điểm trung bình").previousSibling).toHaveTextContent("–");
  });
});
