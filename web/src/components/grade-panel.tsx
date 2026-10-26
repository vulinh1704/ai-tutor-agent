"use client";

import { Particles, ParticlesEffect } from "@animate-ui/react/primitives/effects/particles";
import { CountingNumber } from "@animate-ui/react/primitives/texts/counting-number";
import { ClipboardCheck, Lightbulb, PartyPopper, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";

import { useI18n } from "@/components/i18n-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import type { GradeResult, Rubric, Session } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Small numbers: a short tween reads better than the default slow-settling spring. */
export const COUNT = { duration: 0.7, ease: "easeOut" } as const;

function ScoreRing({ percentage }: { percentage: number }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg viewBox="0 0 80 80" className="size-24 -rotate-90" aria-hidden>
      <circle cx="40" cy="40" r={radius} className="fill-none stroke-muted" strokeWidth="9" />
      <motion.circle
        cx="40"
        cy="40"
        r={radius}
        className={cn("fill-none", percentage === 100 ? "stroke-success" : "stroke-primary")}
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: circumference * (1 - percentage / 100) }}
        transition={{ duration: 0.9, ease: "easeOut" }}
      />
    </svg>
  );
}

/** A graded attempt: total, per-criterion scores and the next step. */
export function GradeResultView({
  grade,
  rubric,
  celebrate = false,
}: {
  grade: GradeResult;
  rubric: Rubric | null;
  celebrate?: boolean;
}) {
  const { t } = useI18n();
  const perfect = grade.percentage === 100;
  const verdict = perfect ? "grade.perfect" : grade.percentage >= 70 ? "grade.good" : "grade.keepGoing";
  const describe = (id: string) =>
    rubric?.criteria.find((criterion) => criterion.id === id)?.description ?? id;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
      data-testid="grade-result"
    >
      <div className="flex items-center gap-4">
        <Particles animate={celebrate && perfect} className="relative shrink-0">
          <div className="relative grid place-items-center">
            <ScoreRing percentage={grade.percentage} />
            <span className="absolute text-lg font-extrabold">{Math.round(grade.percentage)}%</span>
          </div>
          <ParticlesEffect count={10} radius={64} className="size-2 rounded-full bg-sun" />
          <ParticlesEffect
            count={8}
            radius={52}
            delay={0.15}
            className="size-1.5 rounded-full bg-primary"
          />
        </Particles>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-muted-foreground">{t("grade.score")}</p>
          <p className="text-3xl font-extrabold" aria-label={`${grade.score}/${grade.max_score}`}>
            <CountingNumber number={grade.score} transition={COUNT} />
            <span className="text-muted-foreground">/{grade.max_score}</span>
          </p>
          <p className="mt-1 flex items-center gap-1.5 font-bold">
            {perfect ? (
              <PartyPopper className="size-4 text-sun" aria-hidden />
            ) : (
              <Sparkles className="size-4 text-primary" aria-hidden />
            )}
            {t(verdict)}
          </p>
        </div>
      </div>

      <ul className="space-y-3">
        {grade.criteria.map((criterion) => (
          <li key={criterion.criterion_id} className="rounded-2xl bg-muted/60 p-3">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-bold">{describe(criterion.criterion_id)}</p>
              <Badge
                variant={criterion.points === criterion.max_points ? "default" : "secondary"}
                className="shrink-0 font-bold"
              >
                {criterion.points}/{criterion.max_points}
              </Badge>
            </div>
            <Progress
              value={(100 * criterion.points) / criterion.max_points}
              className="my-2 h-2.5"
              aria-label={describe(criterion.criterion_id)}
            />
            <p className="text-sm text-muted-foreground">{criterion.feedback}</p>
          </li>
        ))}
      </ul>

      <div className="flex gap-3 rounded-2xl bg-sun-soft p-3">
        <Lightbulb className="mt-0.5 size-5 shrink-0 text-sun" aria-hidden />
        <div>
          <p className="text-sm font-bold">{t("grade.nextStep")}</p>
          <p className="text-sm">{grade.next_step_hint}</p>
        </div>
      </div>
    </motion.div>
  );
}

export function GradePanel({
  session,
  grade,
  celebration,
  busy,
  checking = false,
  onSubmit,
}: {
  session: Session;
  grade: GradeResult | null;
  /** Increments on every fresh perfect score, so the celebration plays once per attempt. */
  celebration: number;
  /** A turn is in flight (no new submissions meanwhile). */
  busy: boolean;
  /** The turn in flight is this panel's submission. */
  checking?: boolean;
  onSubmit: (answer: string) => void;
}) {
  const { t } = useI18n();
  const [answer, setAnswer] = useState("");
  const rubric = session.assignment?.rubric ?? null;

  return (
    <section aria-label={t("grade.title")} className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-2 border-b px-5 py-4">
        <ClipboardCheck className="size-5 text-primary" aria-hidden />
        <h2 className="font-heading text-lg font-extrabold">{t("grade.title")}</h2>
      </header>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
        {!session.assignment || !rubric ? (
          <p className="rounded-2xl bg-muted p-4 text-sm">{t("grade.noRubric")}</p>
        ) : (
          <>
            <div className="space-y-1">
              <p className="text-xs font-bold tracking-wide text-muted-foreground uppercase">
                {t("grade.question")}
              </p>
              <p className="font-semibold">{session.assignment.question}</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold tracking-wide text-muted-foreground uppercase">
                {t("grade.rubric")}
              </p>
              <ul className="space-y-1.5">
                {rubric.criteria.map((criterion) => (
                  <li key={criterion.id} className="flex items-start gap-2 text-sm">
                    <Badge variant="outline" className="shrink-0 font-bold">
                      {t("grade.points", { points: criterion.max_points })}
                    </Badge>
                    <span>{criterion.description}</span>
                  </li>
                ))}
              </ul>
            </div>
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!answer.trim() || busy) return;
                onSubmit(answer);
              }}
            >
              <Textarea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder={t("grade.placeholder")}
                aria-label={t("grade.placeholder")}
                maxLength={4000}
                className="min-h-28 rounded-2xl text-base"
              />
              <Button
                type="submit"
                className="h-11 w-full rounded-full text-base font-bold"
                disabled={busy || !answer.trim()}
              >
                {checking ? t("grade.checking") : t("grade.submit")}
              </Button>
            </form>
            {grade && (
              <GradeResultView
                key={celebration}
                grade={grade}
                rubric={rubric}
                celebrate={celebration > 0}
              />
            )}
          </>
        )}
      </div>
    </section>
  );
}
