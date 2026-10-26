"use client";

import { CountingNumber } from "@animate-ui/react/primitives/texts/counting-number";
import { BookOpen, Flame, Target } from "lucide-react";

import { COUNT } from "@/components/grade-panel";
import { useI18n } from "@/components/i18n-provider";
import type { MessageKey } from "@/lib/i18n";
import { isSubjectKey } from "@/lib/practice";
import type { Progress } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The encouragement line under the streak, from the learner's streak state. */
export function streakMessage(progress: Progress): { key: MessageKey; count: number } {
  if (progress.active_today) return { key: "progress.streak.today", count: progress.current_streak };
  if (progress.current_streak > 0) {
    return { key: "progress.streak.pending", count: progress.current_streak };
  }
  return { key: "progress.streak.none", count: 0 };
}

function Stat({
  icon: Icon,
  label,
  value,
  suffix,
  tone,
}: {
  icon: typeof Flame;
  label: string;
  value: number | null;
  suffix?: string;
  tone: string;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-center gap-1 rounded-2xl bg-card p-3 text-center ring-1 ring-border">
      <span className={cn("grid size-9 place-items-center rounded-full", tone)}>
        <Icon className="size-5" aria-hidden />
      </span>
      <span className="text-2xl leading-none font-extrabold tabular-nums">
        {value === null ? (
          t("progress.noScore")
        ) : (
          <>
            <CountingNumber number={Math.round(value)} transition={COUNT} />
            {suffix}
          </>
        )}
      </span>
      <span className="text-xs font-semibold text-muted-foreground">{label}</span>
    </div>
  );
}

export function ProgressPanel({ progress, className }: { progress: Progress; className?: string }) {
  const { t } = useI18n();
  const message = streakMessage(progress);
  const subjectLabel = (subject: string) =>
    isSubjectKey(subject.toLowerCase()) ? t(`subject.${subject.toLowerCase()}` as MessageKey) : subject;

  return (
    <section aria-label={t("progress.title")} className={cn("space-y-3", className)}>
      <h2 className="font-heading text-base font-extrabold">{t("progress.title")}</h2>
      <div className="grid grid-cols-3 gap-2">
        <Stat
          icon={BookOpen}
          label={t("progress.sessions")}
          value={progress.sessions}
          tone="bg-primary-soft text-primary"
        />
        <Stat
          icon={Target}
          label={t("progress.average")}
          value={progress.average_score}
          suffix="%"
          tone="bg-success-soft text-success"
        />
        <Stat
          icon={Flame}
          label={t("progress.streak")}
          value={progress.current_streak}
          tone="bg-sun-soft text-sun"
        />
      </div>
      <p className="rounded-2xl bg-sun-soft px-3 py-2 text-sm font-semibold" data-testid="streak-message">
        {t(message.key, { count: message.count })}
        {progress.best_streak > 1 && (
          <span className="block text-xs font-normal text-muted-foreground">
            {t("progress.best", { count: progress.best_streak })}
          </span>
        )}
      </p>
      {progress.subjects.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold tracking-wide text-muted-foreground uppercase">
            {t("progress.bySubject")}
          </p>
          <ul className="space-y-1.5">
            {progress.subjects.map((subject) => (
              <li key={subject.subject} className="space-y-1">
                <div className="flex justify-between text-sm font-semibold">
                  <span>{subjectLabel(subject.subject)}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {subject.average_score === null ? t("progress.noScore") : `${Math.round(subject.average_score)}%`}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-700"
                    style={{ width: `${subject.average_score ?? 0}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
