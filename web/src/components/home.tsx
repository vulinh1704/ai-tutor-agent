"use client";

import { Fade, Fades } from "@animate-ui/react/primitives/effects/fade";
import { MessageCircleQuestion } from "lucide-react";

import { useI18n } from "@/components/i18n-provider";
import { Mascot } from "@/components/mascot";
import { practiceSession, ProblemCard } from "@/components/new-session-dialog";
import { isSubjectKey, problemsFor } from "@/lib/practice";
import type { Learner, NewSession } from "@/lib/types";

/** What a learner sees before opening a session: a friendly greeting and quick starts. */
export function Home({
  learner,
  onStart,
}: {
  learner: Learner;
  onStart: (spec: Omit<NewSession, "learner_id">) => void;
}) {
  const { t, language } = useI18n();
  const label = (key: string) => (isSubjectKey(key) ? t(`subject.${key}`) : key);
  const firstSubject = learner.subjects.find(isSubjectKey) ?? "math";
  const problems = problemsFor(learner.subjects).slice(0, 4);

  return (
    <div className="h-full overflow-y-auto px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <Fade className="flex items-center gap-4">
          <Mascot mood="happy" className="size-24 shrink-0" />
          <div>
            <h1 className="font-heading text-2xl font-black sm:text-3xl">
              {t("home.title", { name: learner.display_name })}
            </h1>
            <p className="mt-1 text-lg text-muted-foreground">{t("home.body")}</p>
          </div>
        </Fade>

        <section className="space-y-3">
          <h2 className="text-xs font-bold tracking-wide text-muted-foreground uppercase">
            {t("home.practice")}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Fades holdDelay={0.06}>
              {problems.map((problem) => (
                <ProblemCard
                  key={problem.id}
                  problem={problem}
                  language={language}
                  subjectLabel={label(problem.subject)}
                  onStart={() => onStart(practiceSession(problem, learner, label(problem.subject)))}
                />
              ))}
            </Fades>
          </div>
        </section>

        <button
          type="button"
          onClick={() =>
            onStart({ subject: label(firstSubject), level: learner.level, mode: "homework" })
          }
          className="flex w-full items-center gap-4 rounded-3xl border-2 border-dashed border-primary/40 bg-primary-soft/50 p-5 text-left outline-none hover:border-primary focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <span className="grid size-12 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
            <MessageCircleQuestion className="size-6" aria-hidden />
          </span>
          <span>
            <span className="block font-heading text-lg font-extrabold">{t("home.freeChat")}</span>
            <span className="text-muted-foreground">
              {t("home.freeChat.desc", { subject: label(firstSubject) })}
            </span>
          </span>
        </button>
      </div>
    </div>
  );
}
