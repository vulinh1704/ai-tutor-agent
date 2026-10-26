"use client";

import {
  ThemeToggler,
  type Resolved,
  type ThemeSelection,
} from "@animate-ui/react/primitives/effects/theme-toggler";
import { Menu, Moon, Sun, WifiOff } from "lucide-react";
import { useTheme } from "next-themes";

import { useI18n } from "@/components/i18n-provider";
import { LearnerAvatar } from "@/components/learner-avatar";
import { Mascot } from "@/components/mascot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { LANGUAGES } from "@/lib/i18n";
import type { Health, Language, Learner } from "@/lib/types";

export function ThemeToggle() {
  const { t } = useI18n();
  const { theme, resolvedTheme, setTheme } = useTheme();
  return (
    <ThemeToggler
      theme={(theme ?? "system") as ThemeSelection}
      resolvedTheme={(resolvedTheme ?? "light") as Resolved}
      setTheme={setTheme}
      direction="ltr"
    >
      {({ resolved, toggleTheme }) => (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-lg"
              className="rounded-full"
              aria-label={t("header.theme")}
              onClick={() => toggleTheme(resolved === "dark" ? "light" : "dark")}
            >
              {resolved === "dark" ? <Sun aria-hidden /> : <Moon aria-hidden />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t("header.theme")}</TooltipContent>
        </Tooltip>
      )}
    </ThemeToggler>
  );
}

export function LanguageSwitch({ onChange }: { onChange: (language: Language) => void }) {
  const { t, language } = useI18n();
  return (
    <ToggleGroup
      type="single"
      value={language}
      onValueChange={(value: string) => value && onChange(value as Language)}
      aria-label={t("header.language")}
      spacing={0}
      className="rounded-full bg-muted p-0.5"
    >
      {LANGUAGES.map((code) => (
        <ToggleGroupItem
          key={code}
          value={code}
          aria-label={t(`lang.${code}`)}
          className="h-8 rounded-full! px-3 text-xs font-extrabold uppercase data-[state=on]:bg-card data-[state=on]:shadow-sm"
        >
          {code}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export function AppHeader({
  learner,
  health,
  onLanguage,
  onSettings,
  onMenu,
}: {
  learner: Learner;
  health: Health | null;
  onLanguage: (language: Language) => void;
  onSettings: () => void;
  onMenu: () => void;
}) {
  const { t } = useI18n();
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-card/70 px-3 backdrop-blur sm:px-5">
      <Button
        variant="ghost"
        size="icon-lg"
        className="rounded-full lg:hidden"
        onClick={onMenu}
        aria-label={t("header.menu")}
      >
        <Menu aria-hidden />
      </Button>
      <div className="flex min-w-0 items-center gap-2">
        <Mascot className="size-10" />
        <div className="min-w-0 leading-tight">
          <p className="font-heading text-lg font-black">{t("app.name")}</p>
          <p className="hidden truncate text-xs text-muted-foreground sm:block">
            {t("app.tagline")}
          </p>
        </div>
      </div>
      {health?.llm_provider === "fake" && (
        <Badge variant="outline" className="ml-1 hidden gap-1 font-bold md:inline-flex">
          <WifiOff aria-hidden />
          {t("app.offline")}
        </Badge>
      )}
      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <LanguageSwitch onChange={onLanguage} />
        <ThemeToggle />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              className="h-11 gap-2 rounded-full px-1.5 sm:pr-4"
              onClick={onSettings}
              aria-label={t("header.settings")}
            >
              <LearnerAvatar learner={learner} className="size-8" />
              <span className="hidden max-w-32 truncate font-bold sm:inline">
                {learner.display_name}
              </span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t("header.settings")}</TooltipContent>
        </Tooltip>
      </div>
    </header>
  );
}
