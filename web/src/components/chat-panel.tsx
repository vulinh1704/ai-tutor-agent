"use client";

import { AlertCircle, SendHorizontal, ShieldCheck } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { HintLadder } from "@/components/hint-ladder";
import { useI18n } from "@/components/i18n-provider";
import { LearnerAvatar } from "@/components/learner-avatar";
import { Mascot } from "@/components/mascot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { HintState, UIMessage } from "@/hooks/use-tutor";
import type { MessageKey } from "@/lib/i18n";
import type { Learner, Route, Session } from "@/lib/types";
import { cn } from "@/lib/utils";

const ROUTE_LABEL: Record<Route, MessageKey> = {
  tutor: "chat.route.tutor",
  grader: "chat.route.grader",
  clarify: "chat.route.clarify",
};

const QUICK_PROMPTS: MessageKey[] = ["chat.prompt.start", "chat.prompt.stuck", "chat.prompt.check"];

function Bubble({ message, learner }: { message: UIMessage; learner: Learner }) {
  const { t } = useI18n();
  const mine = message.role === "student";
  const waiting = message.streaming && !message.content;
  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn("flex items-end gap-2.5", mine && "flex-row-reverse")}
    >
      {mine ? (
        <LearnerAvatar learner={learner} className="size-9" />
      ) : (
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-sun-soft">
          <Mascot mood={message.streaming ? "thinking" : "idle"} className="size-8" />
        </span>
      )}
      <div className={cn("flex max-w-[min(42rem,85%)] flex-col gap-1", mine && "items-end")}>
        <span className="sr-only">{mine ? t("chat.you") : t("chat.tutor")}:</span>
        {!mine && message.route && (
          <Badge variant="secondary" className="font-bold">
            {t(ROUTE_LABEL[message.route])}
          </Badge>
        )}
        <div
          className={cn(
            "rounded-3xl px-4 py-2.5 leading-relaxed whitespace-pre-wrap",
            mine
              ? "rounded-br-lg bg-primary text-primary-foreground"
              : "rounded-bl-lg bg-card ring-1 ring-border",
            message.failed && "ring-destructive/40",
          )}
        >
          {waiting ? (
            <span className="text-muted-foreground italic">{t("chat.thinking")}</span>
          ) : (
            message.content
          )}
          {message.streaming && message.content && (
            <span
              className="typing-caret ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 rounded-full bg-primary"
              aria-hidden
            />
          )}
        </div>
      </div>
    </motion.li>
  );
}

export function ChatPanel({
  session,
  learner,
  messages,
  hint,
  busy,
  rewording,
  error,
  onSend,
}: {
  session: Session;
  learner: Learner;
  messages: UIMessage[];
  hint: HintState;
  busy: boolean;
  rewording: boolean;
  error: string | null;
  onSend: (text: string) => void;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const lastContent = messages.at(-1)?.content;

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, lastContent]);

  const submit = (text: string) => {
    if (!text.trim() || busy) return;
    onSend(text);
    setDraft("");
  };

  return (
    <section aria-label={t("tabs.chat")} className="flex h-full min-h-0 flex-col">
      <header className="space-y-3 border-b px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="font-bold">{session.subject}</Badge>
          <h2 className="min-w-0 flex-1 truncate font-heading text-lg font-extrabold">
            {session.assignment?.question ?? t("home.freeChat")}
          </h2>
        </div>
        <HintLadder level={hint.level} max={hint.max} mode={session.mode} />
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6" aria-live="polite">
        {messages.length === 0 ? (
          <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-10 text-center">
            <Mascot className="size-24" />
            <p className="text-lg font-semibold">{t("chat.empty")}</p>
            <div className="flex flex-wrap justify-center gap-2">
              {QUICK_PROMPTS.map((key) => (
                <Button
                  key={key}
                  variant="outline"
                  className="h-auto rounded-full px-4 py-2 font-semibold"
                  onClick={() => submit(t(key))}
                  disabled={busy}
                >
                  {t(key)}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="mx-auto flex max-w-3xl flex-col gap-4">
            {messages.map((message) => (
              <Bubble key={message.id} message={message} learner={learner} />
            ))}
          </ol>
        )}
        <div ref={endRef} />
      </div>

      <footer className="border-t px-4 py-3 sm:px-6">
        <AnimatePresence>
          {(rewording || error) && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              role="status"
              className={cn(
                "mx-auto mb-2 flex max-w-3xl items-center gap-2 rounded-2xl px-3 py-2 text-sm font-semibold",
                error ? "bg-destructive/10 text-destructive" : "bg-sun-soft",
              )}
            >
              {error ? (
                <AlertCircle className="size-4 shrink-0" aria-hidden />
              ) : (
                <ShieldCheck className="size-4 shrink-0 text-sun" aria-hidden />
              )}
              {error ?? t("chat.reset")}
            </motion.p>
          )}
        </AnimatePresence>
        <form
          className="mx-auto flex max-w-3xl items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            submit(draft);
          }}
        >
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                submit(draft);
              }
            }}
            placeholder={t("chat.placeholder")}
            aria-label={t("chat.placeholder")}
            rows={1}
            maxLength={4000}
            className="max-h-40 min-h-12 rounded-3xl px-4 py-3 text-base"
          />
          <Button
            type="submit"
            size="icon-lg"
            className="size-12 shrink-0 rounded-full"
            disabled={busy || !draft.trim()}
            aria-label={t("chat.send")}
          >
            <SendHorizontal className="size-5" aria-hidden />
          </Button>
        </form>
      </footer>
    </section>
  );
}
