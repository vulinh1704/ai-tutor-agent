import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GradePanel, GradeResultView } from "@/components/grade-panel";
import { renderWithProviders } from "@/test/render";
import type { GradeResult, Rubric, Session } from "@/lib/types";

const RUBRIC: Rubric = {
  criteria: [
    {
      id: "method",
      description: "Subtracts 5 from both sides, then divides both sides by 3",
      max_points: 3,
    },
    { id: "answer", description: "States the solution x = 5", max_points: 2 },
  ],
};

const SESSION: Session = {
  session_id: "s1",
  subject: "Math",
  level: "grade 8",
  mode: "homework",
  learner_id: "l1",
  assignment: {
    question: "Solve for x: 3x + 5 = 20",
    rubric: RUBRIC,
    has_reference_answer: true,
    skills: [],
  },
  hint_level: 0,
  max_hint_level: 3,
  created_at: null,
  messages: [],
  last_grade: null,
};

function grade(method: number, answer: number): GradeResult {
  const score = method + answer;
  return {
    score,
    max_score: 5,
    percentage: (100 * score) / 5,
    criteria: [
      { criterion_id: "method", points: method, max_points: 3, feedback: "Method feedback." },
      { criterion_id: "answer", points: answer, max_points: 2, feedback: "Answer feedback." },
    ],
    next_step_hint: "How could you check your answer?",
  };
}

describe("GradeResultView", () => {
  it("shows per-criterion scores with the rubric's wording", () => {
    renderWithProviders(<GradeResultView grade={grade(1, 2)} rubric={RUBRIC} />);

    expect(screen.getByLabelText("3/5")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(
      screen.getByText("Subtracts 5 from both sides, then divides both sides by 3"),
    ).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
    expect(screen.getByText("2/2")).toBeInTheDocument();
    expect(screen.getByText("Method feedback.")).toBeInTheDocument();
    expect(screen.getByText("How could you check your answer?")).toBeInTheDocument();
    expect(screen.getByText("Good effort. Let's improve it together.")).toBeInTheDocument();
  });

  it("celebrates a perfect score", () => {
    renderWithProviders(<GradeResultView grade={grade(3, 2)} rubric={RUBRIC} celebrate />, {
      language: "vi",
    });
    expect(screen.getByText("Điểm tuyệt đối! Bạn làm xuất sắc lắm.")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});

describe("GradePanel", () => {
  it("submits the learner's answer", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <GradePanel session={SESSION} grade={null} celebration={0} busy={false} onSubmit={onSubmit} />,
    );

    const submit = screen.getByRole("button", { name: "Check my answer" });
    expect(submit).toBeDisabled();
    await user.type(screen.getByRole("textbox"), "3x = 15, so x = 5");
    await user.click(submit);

    expect(onSubmit).toHaveBeenCalledWith("3x = 15, so x = 5");
    expect(screen.getByText("Solve for x: 3x + 5 = 20")).toBeInTheDocument();
    expect(screen.getByText("3 pts")).toBeInTheDocument();
  });

  it("says it is checking only while its own submission is graded", () => {
    const { rerender } = renderWithProviders(
      <GradePanel session={SESSION} grade={null} celebration={0} busy onSubmit={() => undefined} />,
    );
    // A chat turn is in flight: the panel waits, but is not "checking".
    expect(screen.getByRole("button", { name: "Check my answer" })).toBeDisabled();
    rerender(
      <GradePanel
        session={SESSION}
        grade={null}
        celebration={0}
        busy
        checking
        onSubmit={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "Checking…" })).toBeDisabled();
  });

  it("explains when a session cannot be graded", () => {
    renderWithProviders(
      <GradePanel
        session={{ ...SESSION, assignment: null }}
        grade={null}
        celebration={0}
        busy={false}
        onSubmit={() => undefined}
      />,
    );
    expect(screen.getByText(/This session has no rubric/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});
