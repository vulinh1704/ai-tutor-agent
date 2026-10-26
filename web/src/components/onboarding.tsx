"use client";

import { AutoHeight } from "@animate-ui/react/primitives/effects/auto-height";
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { useI18n } from "@/components/i18n-provider";
import { Mascot } from "@/components/mascot";
import {
  GoalField,
  GradeField,
  HintStyleFields,
  LanguageField,
  LookFields,
  NameField,
  SubjectsField,
} from "@/components/profile-fields";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { MessageKey } from "@/lib/i18n";
import { defaultProfile, gradeOf, levelFor } from "@/lib/profile";
import type { Language, LearnerProfile } from "@/lib/types";

const STEPS = ["welcome", "name", "grade", "subjects", "goal", "style", "look", "done"] as const;
type Step = (typeof STEPS)[number];

const TITLES: Record<Step, MessageKey> = {
  welcome: "onboarding.welcome.title",
  name: "onboarding.name.title",
  grade: "onboarding.grade.title",
  subjects: "onboarding.subjects.title",
  goal: "onboarding.goal.title",
  style: "onboarding.style.title",
  look: "onboarding.look.title",
  done: "onboarding.done.title",
};

export function Onboarding({
  onComplete,
}: {
  onComplete: (profile: LearnerProfile) => Promise<void>;
}) {
  const { t, language, setLanguage } = useI18n();
  const [profile, setProfile] = useState<LearnerProfile>(() => defaultProfile(language));
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  const step = STEPS[index];
  const last = index === STEPS.length - 1;
  const canContinue = step !== "name" || profile.display_name.trim().length > 0;
  const name = profile.display_name.trim();

  const go = (delta: number) => {
    setDirection(delta);
    setIndex((current) => Math.min(Math.max(current + delta, 0), STEPS.length - 1));
  };

  const changeLanguage = (next: Language) => {
    setLanguage(next);
    setProfile((current) => ({
      ...current,
      level: levelFor(gradeOf(current.level) ?? 8, next),
      preferences: { ...current.preferences, language: next },
    }));
  };

  const finish = async () => {
    setSaving(true);
    setFailed(false);
    try {
      await onComplete({ ...profile, display_name: name, goal: profile.goal?.trim() || null });
    } catch {
      setFailed(true);
      setSaving(false);
    }
  };

  return (
    <main className="grid min-h-dvh place-items-center px-4 py-8" data-accent={profile.appearance.accent}>
      <div className="w-full max-w-2xl rounded-[2rem] bg-card p-5 shadow-xl ring-1 ring-border sm:p-8">
        <div className="mb-6 space-y-2">
          <div className="flex items-center justify-between text-sm font-semibold text-muted-foreground">
            <span>{t("onboarding.step", { current: index + 1, total: STEPS.length })}</span>
            <span className="inline-flex items-center gap-1.5 text-primary">
              <Sparkles className="size-4" aria-hidden />
              {t("app.name")}
            </span>
          </div>
          <Progress
            value={(100 * (index + 1)) / STEPS.length}
            className="h-2.5"
            aria-label={t("onboarding.step", { current: index + 1, total: STEPS.length })}
          />
        </div>

        <div className="mb-6 flex items-center gap-4">
          <Mascot
            mood={step === "done" ? "happy" : step === "welcome" ? "idle" : "thinking"}
            className="size-20 sm:size-24"
            label={t("mascot.label")}
          />
          <h1 className="relative rounded-3xl rounded-bl-md bg-primary-soft px-5 py-3 font-heading text-xl font-extrabold sm:text-2xl">
            {t(TITLES[step], { name })}
          </h1>
        </div>

        <AutoHeight deps={[index]}>
          <AnimatePresence mode="wait" custom={direction} initial={false}>
            <motion.div
              key={step}
              custom={direction}
              initial={{ opacity: 0, x: direction * 32 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: direction * -32 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="space-y-5 pb-1"
            >
              {step === "welcome" && (
                <>
                  <p className="text-lg leading-relaxed">{t("onboarding.welcome.body")}</p>
                  <LanguageField
                    title={t("onboarding.language")}
                    value={profile.preferences.language}
                    onChange={changeLanguage}
                  />
                </>
              )}
              {step === "name" && (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (canContinue) go(1);
                  }}
                >
                  <NameField profile={profile} onChange={setProfile} />
                </form>
              )}
              {step === "grade" && <GradeField profile={profile} onChange={setProfile} />}
              {step === "subjects" && <SubjectsField profile={profile} onChange={setProfile} />}
              {step === "goal" && <GoalField profile={profile} onChange={setProfile} />}
              {step === "style" && <HintStyleFields profile={profile} onChange={setProfile} />}
              {step === "look" && <LookFields profile={profile} onChange={setProfile} />}
              {step === "done" && (
                <p className="text-lg leading-relaxed">{t("onboarding.done.body")}</p>
              )}
            </motion.div>
          </AnimatePresence>
        </AutoHeight>

        {failed && (
          <p role="alert" className="mt-4 rounded-2xl bg-destructive/10 p-3 text-sm font-semibold text-destructive">
            {t("app.unreachable.body")}
          </p>
        )}

        <div className="mt-8 flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            onClick={() => go(-1)}
            disabled={index === 0 || saving}
            className="h-12 rounded-full px-5 text-base font-bold"
          >
            <ArrowLeft className="size-5" aria-hidden />
            {t("onboarding.back")}
          </Button>
          {last ? (
            <Button
              onClick={finish}
              disabled={saving}
              className="h-12 rounded-full px-7 text-base font-bold"
            >
              {saving ? t("onboarding.saving") : t("onboarding.finish")}
            </Button>
          ) : (
            <Button
              onClick={() => go(1)}
              disabled={!canContinue}
              className="h-12 rounded-full px-7 text-base font-bold"
            >
              {t("onboarding.next")}
              <ArrowRight className="size-5" aria-hidden />
            </Button>
          )}
        </div>
      </div>
    </main>
  );
}
