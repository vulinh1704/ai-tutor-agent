"use client";

import { ArrowRight, MessageCircleQuestion } from "lucide-react";
import { useState } from "react";

import { useI18n } from "@/components/i18n-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { isSubjectKey, problemsFor, SUBJECTS, type PracticeProblem } from "@/lib/practice";
import type { Language, Learner, NewSession, TutorMode } from "@/lib/types";

type SessionSpec = Omit<NewSession, "learner_id">;

/** The session a practice problem starts, in the learner's language. */
export function practiceSession(
  problem: PracticeProblem,
  learner: Learner,
  subjectLabel: string,
): SessionSpec {
  const text = problem.text[learner.preferences.language];
  return {
    subject: subjectLabel,
    level: learner.level,
    mode: "homework",
    assignment: {
      question: text.question,
      rubric: text.rubric,
      reference_answer: problem.referenceAnswer,
      skills: problem.skills,
    },
  };
}

export function ProblemCard({
  problem,
  language,
  subjectLabel,
  onStart,
}: {
  problem: PracticeProblem;
  language: Language;
  subjectLabel: string;
  onStart: () => void;
}) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={onStart}
      className="group flex w-full flex-col items-start gap-2 rounded-3xl bg-card p-4 text-left ring-1 ring-border transition-shadow outline-none hover:shadow-md hover:ring-primary/50 focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <Badge variant="secondary" className="font-bold">
        {subjectLabel}
      </Badge>
      <span className="font-semibold">{problem.text[language].question}</span>
      <span className="mt-auto inline-flex items-center gap-1 text-sm font-bold text-primary">
        {t("home.start")}
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
    </button>
  );
}

export function NewSessionDialog({
  open,
  onOpenChange,
  learner,
  onStart,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  learner: Learner;
  onStart: (spec: SessionSpec) => void;
}) {
  const { t, language } = useI18n();
  const subjects = learner.subjects.filter(isSubjectKey);
  const choices = subjects.length > 0 ? subjects : [...SUBJECTS];
  const [subject, setSubject] = useState<string>(choices[0]);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<TutorMode>("homework");
  const label = (key: string) => (isSubjectKey(key) ? t(`subject.${key}`) : key);

  const start = (spec: SessionSpec) => {
    onStart(spec);
    onOpenChange(false);
    setQuestion("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto rounded-3xl p-6 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl font-extrabold">
            {t("newSession.title")}
          </DialogTitle>
          <DialogDescription>{t("home.body")}</DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="practice">
          <TabsList className="h-10 w-full rounded-full">
            <TabsTrigger value="practice" className="rounded-full font-bold">
              {t("newSession.practice")}
            </TabsTrigger>
            <TabsTrigger value="own" className="rounded-full font-bold">
              {t("newSession.own")}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="practice" className="pt-3">
            <div className="grid gap-3 sm:grid-cols-2">
              {problemsFor(learner.subjects).map((problem) => (
                <ProblemCard
                  key={problem.id}
                  problem={problem}
                  language={language}
                  subjectLabel={label(problem.subject)}
                  onStart={() => start(practiceSession(problem, learner, label(problem.subject)))}
                />
              ))}
            </div>
          </TabsContent>
          <TabsContent value="own" className="space-y-4 pt-3">
            <div className="space-y-2">
              <p className="font-bold">{t("newSession.subject")}</p>
              <ToggleGroup
                type="single"
                value={subject}
                onValueChange={(value: string) => value && setSubject(value)}
                className="flex-wrap"
                aria-label={t("newSession.subject")}
              >
                {choices.map((key) => (
                  <ToggleGroupItem
                    key={key}
                    value={key}
                    className="h-10 rounded-full border-2 px-4 font-bold data-[state=on]:border-primary data-[state=on]:bg-primary-soft"
                  >
                    {label(key)}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>
            <div className="space-y-2">
              <label htmlFor="new-session-question" className="block font-bold">
                {t("newSession.question")}
              </label>
              <Textarea
                id="new-session-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={t("newSession.questionPlaceholder")}
                maxLength={4000}
                className="min-h-24 rounded-2xl text-base"
              />
            </div>
            <div className="space-y-2">
              <p className="font-bold">{t("newSession.mode")}</p>
              <ToggleGroup
                type="single"
                value={mode}
                onValueChange={(value: string) => value && setMode(value as TutorMode)}
                className="grid w-full items-stretch grid-cols-1 sm:grid-cols-2"
                aria-label={t("newSession.mode")}
              >
                {(["homework", "explain"] as const).map((value) => (
                  <ToggleGroupItem
                    key={value}
                    value={value}
                    className="h-auto flex-col items-start rounded-2xl border-2 px-4 py-3 text-left whitespace-normal data-[state=on]:border-primary data-[state=on]:bg-primary-soft"
                  >
                    <span className="font-bold">{t(`newSession.mode.${value}`)}</span>
                    <span className="text-sm text-muted-foreground">
                      {t(`newSession.mode.${value}.desc`)}
                    </span>
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>
            <Button
              className="h-11 w-full rounded-full text-base font-bold"
              onClick={() =>
                start({
                  subject: label(subject),
                  level: learner.level,
                  mode,
                  assignment: question.trim() ? { question: question.trim() } : null,
                })
              }
            >
              <MessageCircleQuestion className="size-5" aria-hidden />
              {t("newSession.start")}
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
