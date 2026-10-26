"use client";

import { BookOpenText, Check } from "lucide-react";
import { motion } from "motion/react";

import { useI18n } from "@/components/i18n-provider";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { MessageKey } from "@/lib/i18n";
import type { TutorMode } from "@/lib/types";
import { cn } from "@/lib/utils";

const RUNGS: Record<number, [MessageKey, MessageKey]> = {
  1: ["ladder.1", "ladder.1.desc"],
  2: ["ladder.2", "ladder.2.desc"],
  3: ["ladder.3", "ladder.3.desc"],
  4: ["ladder.4", "ladder.4.desc"],
  5: ["ladder.5", "ladder.5.desc"],
};

/**
 * The hint ladder as a stepper: every rung the learner can climb, the current one
 * highlighted. Homework mode only; explain mode has no ladder.
 */
export function HintLadder({
  level,
  max,
  mode,
  className,
}: {
  level: number;
  max: number;
  mode: TutorMode;
  className?: string;
}) {
  const { t } = useI18n();

  if (mode === "explain") {
    return (
      <p
        className={cn(
          "flex items-center gap-2 rounded-2xl bg-sun-soft px-3 py-2 text-sm font-semibold",
          className,
        )}
      >
        <BookOpenText className="size-4 text-sun" aria-hidden />
        {t("ladder.explain")}
      </p>
    );
  }

  const rungs = Array.from({ length: Math.min(Math.max(max, 1), 5) }, (_, i) => i + 1);
  return (
    <nav aria-label={t("ladder.title")} className={cn("w-full", className)}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2 text-xs">
        <span className="font-bold tracking-wide text-muted-foreground uppercase">
          {t("ladder.title")}
        </span>
        <span className="text-muted-foreground" aria-live="polite">
          {level > 0 ? t("ladder.level", { level, max }) : t("ladder.ready")}
        </span>
      </div>
      <ol className="flex items-center gap-1.5">
        {rungs.map((rung) => {
          const state = rung < level ? "done" : rung === level ? "current" : "todo";
          const [name, description] = RUNGS[rung];
          return (
            <li key={rung} className="min-w-0 flex-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span
                    tabIndex={0}
                    data-state={state}
                    aria-current={state === "current" ? "step" : undefined}
                    className={cn(
                      "relative flex h-9 items-center gap-2 overflow-hidden rounded-full px-2 text-sm font-bold outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                      state === "done" && "bg-primary-soft text-foreground",
                      state === "todo" && "bg-muted text-muted-foreground",
                      state === "current" && "text-primary-foreground",
                    )}
                  >
                    {state === "current" && (
                      <motion.span
                        layoutId="hint-ladder-current"
                        className="absolute inset-0 rounded-full bg-primary"
                        transition={{ type: "spring", stiffness: 420, damping: 32 }}
                      />
                    )}
                    <span
                      className={cn(
                        "relative grid size-6 shrink-0 place-items-center rounded-full text-xs",
                        state === "current" ? "bg-primary-foreground/20" : "bg-background/70",
                      )}
                    >
                      {state === "done" ? <Check className="size-3.5" aria-hidden /> : rung}
                    </span>
                    <span className="relative truncate">{t(name)}</span>
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom">{t(description)}</TooltipContent>
              </Tooltip>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
