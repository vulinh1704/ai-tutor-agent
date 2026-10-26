"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { useI18n } from "@/components/i18n-provider";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { gradeOf, levelFor, resumeLink } from "@/lib/profile";
import type { Language, Learner, LearnerProfile } from "@/lib/types";

function editable(learner: Learner): LearnerProfile {
  const { display_name, level, subjects, goal, preferences, appearance, timezone } = learner;
  return { display_name, level, subjects, goal, preferences, appearance, timezone };
}

function SettingsForm({
  learner,
  onSave,
}: {
  learner: Learner;
  onSave: (profile: LearnerProfile) => Promise<void>;
}) {
  const { t } = useI18n();
  const [profile, setProfile] = useState<LearnerProfile>(() => editable(learner));
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [copied, setCopied] = useState(false);
  const link = resumeLink(window.location.origin, learner.learner_id);

  const change = (next: LearnerProfile) => {
    setProfile(next);
    setState("idle");
  };
  const changeLanguage = (language: Language) =>
    change({
      ...profile,
      level: levelFor(gradeOf(profile.level) ?? 8, language),
      preferences: { ...profile.preferences, language },
    });

  const save = async () => {
    setState("saving");
    try {
      await onSave({ ...profile, display_name: profile.display_name.trim() });
      setState("saved");
    } catch {
      setState("failed");
    }
  };

  return (
    <>
      <div className="max-h-[60dvh] space-y-6 overflow-y-auto pr-1">
        <NameField profile={profile} onChange={change} />
        <LanguageField
          title={t("header.language")}
          value={profile.preferences.language}
          onChange={changeLanguage}
        />
        <GradeField profile={profile} onChange={change} />
        <SubjectsField profile={profile} onChange={change} />
        <GoalField profile={profile} onChange={change} />
        <Separator />
        <HintStyleFields profile={profile} onChange={change} />
        <Separator />
        <LookFields profile={profile} onChange={change} />
        <Separator />
        <div className="space-y-2">
          <p className="text-sm font-semibold">{t("settings.resume")}</p>
          <div className="flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-xl bg-muted px-3 py-2 text-xs">
              {link}
            </code>
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => {
                void navigator.clipboard?.writeText(link).then(() => setCopied(true));
              }}
            >
              {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
              {copied ? t("settings.copied") : t("settings.copy")}
            </Button>
          </div>
        </div>
      </div>
      <DialogFooter className="-mx-6 -mb-6 rounded-b-3xl px-6">
        {state === "failed" && (
          <p role="alert" className="mr-auto self-center text-sm font-semibold text-destructive">
            {t("app.error")}
          </p>
        )}
        <Button
          onClick={save}
          disabled={state === "saving" || !profile.display_name.trim()}
          className="h-11 rounded-full px-6 text-base font-bold"
        >
          {state === "saved" && <Check className="size-5" aria-hidden />}
          {state === "saved" ? t("settings.saved") : t("settings.save")}
        </Button>
      </DialogFooter>
    </>
  );
}

export function SettingsDialog({
  open,
  onOpenChange,
  learner,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  learner: Learner;
  onSave: (profile: LearnerProfile) => Promise<void>;
}) {
  const { t } = useI18n();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-3xl p-6 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl font-extrabold">
            {t("settings.title")}
          </DialogTitle>
          <DialogDescription>{t("settings.description")}</DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so every visit starts from the saved profile. */}
        {open && <SettingsForm learner={learner} onSave={onSave} />}
      </DialogContent>
    </Dialog>
  );
}
