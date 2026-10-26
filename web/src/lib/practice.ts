import type { Language, Rubric } from "@/lib/types";

export const SUBJECTS = ["math", "physics", "chemistry", "english", "biology", "literature"] as const;
export type SubjectKey = (typeof SUBJECTS)[number];

interface LocalisedProblem {
  question: string;
  rubric: Rubric;
}

export interface PracticeProblem {
  id: string;
  subject: SubjectKey;
  skills: string[];
  referenceAnswer: string;
  text: Record<Language, LocalisedProblem>;
}

/** Built-in practice problems for secondary-school students, each with a rubric. */
export const PRACTICE_PROBLEMS: readonly PracticeProblem[] = [
  {
    id: "linear-equation",
    subject: "math",
    skills: ["linear-equations"],
    referenceAnswer: "x = 5",
    text: {
      en: {
        question: "Solve for x: 3x + 5 = 20",
        rubric: {
          criteria: [
            {
              id: "method",
              description: "Subtracts 5 from both sides, then divides both sides by 3",
              max_points: 3,
            },
            { id: "answer", description: "States the solution x = 5", max_points: 2 },
          ],
        },
      },
      vi: {
        question: "Giải phương trình: 3x + 5 = 20",
        rubric: {
          criteria: [
            {
              id: "method",
              description: "Trừ 5 ở cả hai vế, rồi chia cả hai vế cho 3",
              max_points: 3,
            },
            { id: "answer", description: "Nêu nghiệm x = 5", max_points: 2 },
          ],
        },
      },
    },
  },
  {
    id: "rectangle-perimeter",
    subject: "math",
    skills: ["perimeter", "geometry"],
    referenceAnswer: "6 cm",
    text: {
      en: {
        question: "A rectangle has a perimeter of 30 cm and a length of 9 cm. Find its width.",
        rubric: {
          criteria: [
            {
              id: "formula",
              description: "Uses perimeter = 2 × (length + width)",
              max_points: 2,
            },
            {
              id: "method",
              description: "Halves 30 to get 15, then subtracts 9",
              max_points: 2,
            },
            { id: "answer", description: "States the width is 6 cm", max_points: 1 },
          ],
        },
      },
      vi: {
        question: "Một hình chữ nhật có chu vi 30 cm và chiều dài 9 cm. Tính chiều rộng.",
        rubric: {
          criteria: [
            {
              id: "formula",
              description: "Dùng công thức chu vi = 2 × (dài + rộng)",
              max_points: 2,
            },
            { id: "method", description: "Lấy 30 chia 2 được 15, rồi trừ 9", max_points: 2 },
            { id: "answer", description: "Nêu chiều rộng bằng 6 cm", max_points: 1 },
          ],
        },
      },
    },
  },
  {
    id: "average-speed",
    subject: "physics",
    skills: ["speed", "unit-conversion"],
    referenceAnswer: "24 km/h",
    text: {
      en: {
        question: "A cyclist rides 18 km in 45 minutes. What is her average speed in km/h?",
        rubric: {
          criteria: [
            { id: "formula", description: "Uses speed = distance ÷ time", max_points: 2 },
            { id: "units", description: "Converts 45 minutes to 0.75 hours", max_points: 2 },
            { id: "answer", description: "States the speed is 24 km/h", max_points: 1 },
          ],
        },
      },
      vi: {
        question: "Một bạn đạp xe được 18 km trong 45 phút. Tính tốc độ trung bình theo km/h.",
        rubric: {
          criteria: [
            {
              id: "formula",
              description: "Dùng công thức tốc độ = quãng đường ÷ thời gian",
              max_points: 2,
            },
            { id: "units", description: "Đổi 45 phút thành 0,75 giờ", max_points: 2 },
            { id: "answer", description: "Nêu tốc độ bằng 24 km/h", max_points: 1 },
          ],
        },
      },
    },
  },
  {
    id: "balance-water",
    subject: "chemistry",
    skills: ["balancing-equations"],
    referenceAnswer: "2H2 + O2 → 2H2O",
    text: {
      en: {
        question: "Balance the equation: H2 + O2 → H2O",
        rubric: {
          criteria: [
            {
              id: "coefficients",
              description: "Puts a 2 in front of H2 and a 2 in front of H2O",
              max_points: 3,
            },
            {
              id: "check",
              description: "Checks that hydrogen and oxygen atoms match on both sides",
              max_points: 2,
            },
          ],
        },
      },
      vi: {
        question: "Cân bằng phương trình: H2 + O2 → H2O",
        rubric: {
          criteria: [
            {
              id: "coefficients",
              description: "Đặt hệ số 2 trước H2 và hệ số 2 trước H2O",
              max_points: 3,
            },
            {
              id: "check",
              description: "Kiểm tra số nguyên tử hiđro và oxi ở hai vế bằng nhau",
              max_points: 2,
            },
          ],
        },
      },
    },
  },
  {
    id: "past-simple",
    subject: "english",
    skills: ["past-simple", "irregular-verbs"],
    referenceAnswer: "She walked to school and bought a sandwich.",
    text: {
      en: {
        question: 'Rewrite in the past simple: "She walks to school and buys a sandwich."',
        rubric: {
          criteria: [
            { id: "regular", description: "Changes walks to walked", max_points: 2 },
            {
              id: "irregular",
              description: "Changes buys to the irregular form bought",
              max_points: 2,
            },
          ],
        },
      },
      vi: {
        question: 'Viết lại câu ở thì quá khứ đơn: "She walks to school and buys a sandwich."',
        rubric: {
          criteria: [
            { id: "regular", description: "Đổi walks thành walked", max_points: 2 },
            {
              id: "irregular",
              description: "Đổi buys thành dạng bất quy tắc bought",
              max_points: 2,
            },
          ],
        },
      },
    },
  },
  {
    id: "photosynthesis",
    subject: "biology",
    skills: ["photosynthesis"],
    referenceAnswer: "glucose and oxygen",
    text: {
      en: {
        question: "What does photosynthesis produce, and why does it matter for plants?",
        rubric: {
          criteria: [
            { id: "products", description: "Names glucose and oxygen", max_points: 3 },
            {
              id: "energy",
              description: "Explains that light energy is converted into chemical energy",
              max_points: 3,
            },
          ],
        },
      },
      vi: {
        question: "Quang hợp tạo ra những chất gì, và vì sao quá trình này quan trọng với cây?",
        rubric: {
          criteria: [
            { id: "products", description: "Nêu được glucozơ và oxi", max_points: 3 },
            {
              id: "energy",
              description: "Giải thích quang năng được chuyển thành hóa năng",
              max_points: 3,
            },
          ],
        },
      },
    },
  },
];

export function isSubjectKey(value: string): value is SubjectKey {
  return (SUBJECTS as readonly string[]).includes(value);
}

/** Problems for the learner's subjects (all problems if they picked none). */
export function problemsFor(subjects: readonly string[]): PracticeProblem[] {
  const wanted = subjects.filter(isSubjectKey);
  return PRACTICE_PROBLEMS.filter((p) => wanted.length === 0 || wanted.includes(p.subject));
}
