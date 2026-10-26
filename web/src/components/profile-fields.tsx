"use client";

import { Check } from "lucide-react";
import { useId } from "react";

import { useI18n } from "@/components/i18n-provider";
import { AvatarIcon } from "@/components/learner-avatar";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { MessageKey } from "@/lib/i18n";
import { LANGUAGES } from "@/lib/i18n";
import { SUBJECTS } from "@/lib/practice";
import { ACCENTS, AVATARS, GRADES, gradeOf, levelFor } from "@/lib/profile";
import type { FontScale, Language, LearnerProfile, Scaffolding, Tone } from "@/lib/types";
import { cn } from "@/lib/utils";

type Change = (profile: LearnerProfile) => void;

const CARD =
  "h-auto min-h-12 flex-col items-start justify-center gap-0.5 rounded-2xl border-2 border-border bg-card px-4 py-3 text-left text-base font-bold whitespace-normal hover:border-primary/50 hover:bg-card data-[state=on]:border-primary data-[state=on]:bg-primary-soft";
const CHIP =
  "h-11 rounded-full border-2 border-border bg-card px-4 text-base font-bold hover:border-primary/50 hover:bg-card data-[state=on]:border-primary data-[state=on]:bg-primary-soft";

function Field({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: (labelId: string) => React.ReactNode;
}) {
  const id = useId();
  return (
    <div className="space-y-2.5">
      <div>
        <p id={id} className="font-heading text-base font-extrabold">
          {title}
        </p>
        {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      </div>
      {children(id)}
    </div>
  );
}

/** A single choice that can't be cleared (Radix sends "" when the active item is pressed). */
function single<T extends string>(onPick: (value: T) => void) {
  return (value: string) => {
    if (value) onPick(value as T);
  };
}

export function NameField({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  const id = useId();
  return (
    <div className="space-y-2.5">
      <label htmlFor={id} className="block font-heading text-base font-extrabold">
        {t("onboarding.name.title")}
      </label>
      <Input
        id={id}
        value={profile.display_name}
        onChange={(event) => onChange({ ...profile, display_name: event.target.value })}
        placeholder={t("onboarding.name.placeholder")}
        maxLength={40}
        autoComplete="nickname"
        className="h-12 rounded-2xl px-4 text-lg md:text-lg"
      />
    </div>
  );
}

export function LanguageField({
  value,
  onChange,
  title,
}: {
  value: Language;
  onChange: (language: Language) => void;
  title: string;
}) {
  const { t } = useI18n();
  return (
    <Field title={title}>
      {(labelId) => (
        <ToggleGroup
          type="single"
          value={value}
          onValueChange={single(onChange)}
          aria-labelledby={labelId}
          className="flex-wrap"
        >
          {LANGUAGES.map((language) => (
            <ToggleGroupItem key={language} value={language} className={CHIP}>
              {t(`lang.${language}`)}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </Field>
  );
}

export function GradeField({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  const grade = gradeOf(profile.level);
  return (
    <Field title={t("onboarding.grade.title")}>
      {(labelId) => (
        <ToggleGroup
          type="single"
          value={grade === null ? "" : String(grade)}
          onValueChange={single((value: string) =>
            onChange({ ...profile, level: levelFor(Number(value), profile.preferences.language) }),
          )}
          aria-labelledby={labelId}
          className="flex-wrap"
        >
          {GRADES.map((n) => (
            <ToggleGroupItem key={n} value={String(n)} className={CHIP}>
              {t("grade.label", { n })}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </Field>
  );
}

export function SubjectsField({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  return (
    <Field title={t("onboarding.subjects.title")} hint={t("onboarding.subjects.hint")}>
      {(labelId) => (
        <ToggleGroup
          type="multiple"
          value={profile.subjects}
          onValueChange={(subjects: string[]) => onChange({ ...profile, subjects })}
          aria-labelledby={labelId}
          className="flex-wrap"
        >
          {SUBJECTS.map((subject) => (
            <ToggleGroupItem key={subject} value={subject} className={CHIP}>
              {profile.subjects.includes(subject) && <Check className="size-4" aria-hidden />}
              {t(`subject.${subject}`)}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </Field>
  );
}

const GOAL_SUGGESTIONS: MessageKey[] = [
  "onboarding.goal.test",
  "onboarding.goal.homework",
  "onboarding.goal.basics",
];

export function GoalField({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  const id = useId();
  return (
    <div className="space-y-2.5">
      <div>
        <label htmlFor={id} className="block font-heading text-base font-extrabold">
          {t("onboarding.goal.title")}
        </label>
        <p className="text-sm text-muted-foreground">{t("onboarding.goal.hint")}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {GOAL_SUGGESTIONS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => onChange({ ...profile, goal: t(key) })}
            className="rounded-full bg-sun-soft px-3 py-1.5 text-sm font-semibold outline-none hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            {t(key)}
          </button>
        ))}
      </div>
      <Textarea
        id={id}
        value={profile.goal ?? ""}
        onChange={(event) => onChange({ ...profile, goal: event.target.value || null })}
        placeholder={t("onboarding.goal.placeholder")}
        maxLength={280}
        className="min-h-20 rounded-2xl px-4 text-base"
      />
    </div>
  );
}

const TONES: { value: Tone; label: MessageKey; desc: MessageKey }[] = [
  { value: "gentle", label: "pref.tone.gentle", desc: "pref.tone.gentle.desc" },
  { value: "direct", label: "pref.tone.direct", desc: "pref.tone.direct.desc" },
];

const SCAFFOLDING: { value: Scaffolding; label: MessageKey; desc: MessageKey }[] = [
  { value: "less", label: "pref.scaffolding.less", desc: "pref.scaffolding.less.desc" },
  { value: "standard", label: "pref.scaffolding.standard", desc: "pref.scaffolding.standard.desc" },
  { value: "more", label: "pref.scaffolding.more", desc: "pref.scaffolding.more.desc" },
];

export function HintStyleFields({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  const prefs = profile.preferences;
  return (
    <div className="space-y-5">
      <Field title={t("pref.tone")}>
        {(labelId) => (
          <ToggleGroup
            type="single"
            value={prefs.tone}
            onValueChange={single((tone: Tone) =>
              onChange({ ...profile, preferences: { ...prefs, tone } }),
            )}
            aria-labelledby={labelId}
            className="grid w-full items-stretch grid-cols-2"
          >
            {TONES.map((option) => (
              <ToggleGroupItem key={option.value} value={option.value} className={CARD}>
                {t(option.label)}
                <span className="text-sm font-normal text-muted-foreground">{t(option.desc)}</span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        )}
      </Field>
      <Field title={t("pref.scaffolding")}>
        {(labelId) => (
          <ToggleGroup
            type="single"
            value={prefs.scaffolding}
            onValueChange={single((scaffolding: Scaffolding) =>
              onChange({ ...profile, preferences: { ...prefs, scaffolding } }),
            )}
            aria-labelledby={labelId}
            className="grid w-full items-stretch grid-cols-1 sm:grid-cols-3"
          >
            {SCAFFOLDING.map((option) => (
              <ToggleGroupItem key={option.value} value={option.value} className={CARD}>
                {t(option.label)}
                <span className="text-sm font-normal text-muted-foreground">{t(option.desc)}</span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        )}
      </Field>
    </div>
  );
}

const FONT_SCALES: FontScale[] = ["normal", "large", "x-large"];

export function LookFields({ profile, onChange }: { profile: LearnerProfile; onChange: Change }) {
  const { t } = useI18n();
  const look = profile.appearance;
  return (
    <div className="space-y-5">
      <Field title={t("pref.avatar")}>
        {(labelId) => (
          <ToggleGroup
            type="single"
            value={look.avatar}
            onValueChange={single((avatar: string) =>
              onChange({ ...profile, appearance: { ...look, avatar } }),
            )}
            aria-labelledby={labelId}
            className="flex-wrap"
          >
            {AVATARS.map((avatar) => (
              <ToggleGroupItem
                key={avatar}
                value={avatar}
                aria-label={avatar}
                className="size-14 rounded-full border-2 border-transparent p-0 hover:bg-transparent data-[state=on]:border-primary data-[state=on]:bg-transparent"
              >
                <AvatarIcon avatar={avatar} className="size-12" />
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        )}
      </Field>
      <Field title={t("pref.accent")}>
        {(labelId) => (
          <ToggleGroup
            type="single"
            value={look.accent}
            onValueChange={single((accent: string) =>
              onChange({ ...profile, appearance: { ...look, accent } }),
            )}
            aria-labelledby={labelId}
            className="flex-wrap"
          >
            {ACCENTS.map((accent) => (
              <ToggleGroupItem
                key={accent}
                value={accent}
                aria-label={accent}
                data-accent={accent}
                className="size-11 rounded-full border-2 border-transparent p-1 hover:bg-transparent data-[state=on]:border-foreground data-[state=on]:bg-transparent"
              >
                <span className="grid size-full place-items-center rounded-full bg-primary text-primary-foreground">
                  {look.accent === accent && <Check className="size-4" aria-hidden />}
                </span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        )}
      </Field>
      <Field title={t("pref.fontScale")}>
        {(labelId) => (
          <ToggleGroup
            type="single"
            value={look.font_scale}
            onValueChange={single((font_scale: FontScale) =>
              onChange({ ...profile, appearance: { ...look, font_scale } }),
            )}
            aria-labelledby={labelId}
            className="flex-wrap"
          >
            {FONT_SCALES.map((scale, index) => (
              <ToggleGroupItem key={scale} value={scale} className={cn(CHIP, "gap-2")}>
                <span aria-hidden style={{ fontSize: `${1 + index * 0.2}rem` }}>
                  Aa
                </span>
                {t(`pref.fontScale.${scale}`)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        )}
      </Field>
    </div>
  );
}
