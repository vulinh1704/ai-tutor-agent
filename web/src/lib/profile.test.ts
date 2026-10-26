// @vitest-environment node
import { describe, expect, it } from "vitest";

import { PRACTICE_PROBLEMS, problemsFor } from "@/lib/practice";
import { defaultProfile, gradeOf, levelFor, resumeLink } from "@/lib/profile";

describe("profile helpers", () => {
  it("writes the level in the learner's language and reads the grade back", () => {
    expect(levelFor(8, "en")).toBe("grade 8");
    expect(levelFor(10, "vi")).toBe("lớp 10");
    expect(gradeOf("lớp 10")).toBe(10);
    expect(gradeOf("university")).toBeNull();
  });

  it("starts new learners with gentle, standard hints in their language", () => {
    const profile = defaultProfile("vi");
    expect(profile.preferences).toEqual({ language: "vi", tone: "gentle", scaffolding: "standard" });
    expect(profile.level).toBe("lớp 8");
  });

  it("builds a resume link for another device", () => {
    expect(resumeLink("http://localhost:3000", "abc", "s1")).toBe(
      "http://localhost:3000/?learner=abc&session=s1",
    );
  });
});

describe("practice problems", () => {
  it.each(PRACTICE_PROBLEMS.map((p) => [p.id, p] as const))(
    "%s has matching, valid rubrics in both languages",
    (_, problem) => {
      const ids = (language: "en" | "vi") =>
        problem.text[language].rubric.criteria.map((criterion) => criterion.id);
      expect(ids("vi")).toEqual(ids("en"));
      for (const language of ["en", "vi"] as const) {
        const { question, rubric } = problem.text[language];
        expect(question.length).toBeGreaterThanOrEqual(3);
        for (const criterion of rubric.criteria) {
          expect(criterion.id).toMatch(/^[a-z0-9][a-z0-9_-]{0,39}$/);
          expect(criterion.max_points).toBeGreaterThanOrEqual(1);
        }
      }
    },
  );

  it("offers problems for the learner's subjects, or all of them", () => {
    expect(problemsFor(["physics"]).map((p) => p.subject)).toEqual(["physics"]);
    expect(problemsFor([])).toHaveLength(PRACTICE_PROBLEMS.length);
  });
});
