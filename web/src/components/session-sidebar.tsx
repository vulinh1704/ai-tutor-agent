"use client";

import { Highlight, HighlightItem } from "@animate-ui/react/primitives/effects/highlight";
import { MessagesSquare, Plus, Trophy } from "lucide-react";

import { useI18n } from "@/components/i18n-provider";
import { ProgressPanel } from "@/components/progress-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Progress, SessionSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SessionSidebar({
  sessions,
  activeId,
  progress,
  onSelect,
  onNew,
  progressFirst = false,
  className,
}: {
  sessions: SessionSummary[];
  activeId: string | null;
  progress: Progress | null;
  onSelect: (sessionId: string) => void;
  onNew: () => void;
  /** Show progress above the session list (the mobile Progress tab). */
  progressFirst?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <aside className={cn("flex h-full min-h-0 flex-col gap-4 p-4", className)}>
      {progressFirst && progress && <ProgressPanel progress={progress} />}
      <Button onClick={onNew} className="h-11 rounded-full text-base font-bold">
        <Plus className="size-5" aria-hidden />
        {t("header.newSession")}
      </Button>

      <nav aria-label={t("sidebar.sessions")} className="flex min-h-0 flex-1 flex-col gap-2">
        <h2 className="px-1 text-xs font-bold tracking-wide text-muted-foreground uppercase">
          {t("sidebar.sessions")}
        </h2>
        {sessions.length === 0 ? (
          <p className="rounded-2xl bg-muted p-3 text-sm text-muted-foreground">
            {t("sidebar.empty")}
          </p>
        ) : (
          <Highlight
            controlledItems
            value={activeId}
            className="inset-0 rounded-2xl bg-primary-soft ring-1 ring-primary/30"
          >
            <ul className="-mx-1 min-h-0 flex-1 space-y-1 overflow-y-auto px-1 py-0.5">
              {sessions.map((item) => (
                <li key={item.session_id}>
                  {/* asChild: the button is the item; its content is wrapped in a span. */}
                  <HighlightItem value={item.session_id} asChild as="span" className="block">
                    <button
                      type="button"
                      onClick={() => onSelect(item.session_id)}
                      aria-current={item.session_id === activeId ? "true" : undefined}
                      className="w-full rounded-2xl px-3 py-2.5 text-left outline-none hover:bg-muted/70 focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <span className="line-clamp-2 text-sm font-bold">{item.title}</span>
                      <span className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        <Badge variant="secondary" className="font-bold">
                          {item.subject}
                        </Badge>
                        <span className="inline-flex items-center gap-1">
                          <MessagesSquare className="size-3.5" aria-hidden />
                          {t("sidebar.turns", { count: item.turns * 2 })}
                        </span>
                        {item.best_percentage !== null && (
                          <span className="inline-flex items-center gap-1 font-semibold text-success">
                            <Trophy className="size-3.5" aria-hidden />
                            {t("sidebar.best", { score: Math.round(item.best_percentage) })}
                          </span>
                        )}
                      </span>
                    </button>
                  </HighlightItem>
                </li>
              ))}
            </ul>
          </Highlight>
        )}
      </nav>

      {!progressFirst && progress && <ProgressPanel progress={progress} />}
    </aside>
  );
}
