"use client";

import { RotateCcw } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { AppHeader } from "@/components/app-header";
import { ChatPanel } from "@/components/chat-panel";
import { GradePanel } from "@/components/grade-panel";
import { Home } from "@/components/home";
import { I18nProvider, useI18n } from "@/components/i18n-provider";
import { Mascot } from "@/components/mascot";
import { NewSessionDialog } from "@/components/new-session-dialog";
import { Onboarding } from "@/components/onboarding";
import { SessionSidebar } from "@/components/session-sidebar";
import { SettingsDialog } from "@/components/settings-dialog";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTutor } from "@/hooks/use-tutor";
import { gradeOf, levelFor } from "@/lib/profile";
import type { Language, Learner, LearnerProfile } from "@/lib/types";

const WIDE = "(min-width: 1024px)";
const TABS = ["chat", "grade", "progress"] as const;
type Tab = (typeof TABS)[number];

function useIsWide(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia(WIDE);
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia(WIDE).matches,
    () => true,
  );
}

/** The mobile tab to open first: `?tab=grade` deep-links straight to it. */
function initialTab(): Tab {
  const requested = new URLSearchParams(window.location.search).get("tab");
  return (TABS as readonly string[]).includes(requested ?? "") ? (requested as Tab) : "chat";
}

function profileOf(learner: Learner): LearnerProfile {
  const { display_name, level, subjects, goal, preferences, appearance, timezone } = learner;
  return { display_name, level, subjects, goal, preferences, appearance, timezone };
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-dvh place-items-center px-4">
      <div className="flex max-w-md flex-col items-center gap-4 text-center">{children}</div>
    </main>
  );
}

function App() {
  const tutor = useTutor();
  const { t, setLanguage } = useI18n();
  const wide = useIsWide();
  const [tab, setTab] = useState<Tab>(initialTab);
  const [newOpen, setNewOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const look = tutor.learner?.appearance;

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.accent = look?.accent ?? "teal";
    root.dataset.fontScale = look?.font_scale ?? "normal";
  }, [look?.accent, look?.font_scale]);

  if (tutor.phase === "loading") {
    return (
      <CenteredMessage>
        <Mascot mood="thinking" className="size-24" />
        <p className="font-semibold text-muted-foreground">{t("app.loading")}</p>
      </CenteredMessage>
    );
  }

  if (tutor.phase === "unreachable") {
    return (
      <CenteredMessage>
        <Mascot className="size-24" />
        <h1 className="font-heading text-2xl font-black">{t("app.unreachable.title")}</h1>
        <p className="text-muted-foreground">{t("app.unreachable.body")}</p>
        <Button onClick={tutor.retry} className="h-11 rounded-full px-6 font-bold">
          <RotateCcw aria-hidden />
          {t("app.retry")}
        </Button>
      </CenteredMessage>
    );
  }

  if (tutor.phase === "onboarding" || !tutor.learner) {
    return <Onboarding onComplete={tutor.completeOnboarding} />;
  }

  const learner = tutor.learner;
  const session = tutor.session;

  const changeLanguage = (language: Language) => {
    setLanguage(language);
    const profile = profileOf(learner);
    void tutor.updateProfile({
      ...profile,
      level: levelFor(gradeOf(profile.level) ?? 8, language),
      preferences: { ...profile.preferences, language },
    });
  };

  const sidebar = (className?: string, progressFirst = false) => (
    <SessionSidebar
      className={className}
      progressFirst={progressFirst}
      sessions={tutor.sessions}
      activeId={session?.session_id ?? null}
      progress={tutor.progress}
      onSelect={(sessionId) => {
        setMenuOpen(false);
        void tutor.openSession(sessionId);
      }}
      onNew={() => {
        setMenuOpen(false);
        setNewOpen(true);
      }}
    />
  );

  const chat = session && (
    <ChatPanel
      key={session.session_id}
      session={session}
      learner={learner}
      messages={tutor.messages}
      hint={tutor.hint}
      busy={tutor.busy}
      rewording={tutor.rewording}
      error={tutor.error}
      onSend={(text) => void tutor.send(text)}
    />
  );
  const grading = session && (
    <GradePanel
      key={session.session_id}
      session={session}
      grade={tutor.grade}
      celebration={tutor.celebration}
      busy={tutor.busy}
      checking={tutor.checking}
      onSubmit={(answer) => void tutor.send(answer, "submit")}
    />
  );

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader
        learner={learner}
        health={tutor.health}
        onLanguage={changeLanguage}
        onSettings={() => setSettingsOpen(true)}
        onMenu={() => setMenuOpen(true)}
      />
      <div className="flex min-h-0 flex-1">
        {wide && sidebar("w-80 shrink-0 border-r bg-card/40")}
        <main className="min-w-0 flex-1">
          {!session ? (
            <Home learner={learner} onStart={(spec) => void tutor.startSession(spec)} />
          ) : wide ? (
            <div className="grid h-full grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_27rem]">
              {chat}
              <div className="min-h-0 border-l bg-card/40">{grading}</div>
            </div>
          ) : (
            <Tabs
              value={tab}
              onValueChange={(value) => setTab(value as Tab)}
              className="h-full gap-0"
            >
              <TabsList className="mx-3 mt-2 h-10 w-[calc(100%-1.5rem)] rounded-full">
                {TABS.map((value) => (
                  <TabsTrigger key={value} value={value} className="rounded-full font-bold">
                    {t(`tabs.${value}`)}
                  </TabsTrigger>
                ))}
              </TabsList>
              <TabsContent value="chat" className="min-h-0">
                {chat}
              </TabsContent>
              <TabsContent value="grade" className="min-h-0">
                {grading}
              </TabsContent>
              <TabsContent value="progress" className="min-h-0 overflow-y-auto">
                {sidebar("h-auto", true)}
              </TabsContent>
            </Tabs>
          )}
        </main>
      </div>

      {!wide && (
        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetContent side="left" className="w-[min(22rem,90vw)] p-0" aria-describedby={undefined}>
            <SheetHeader className="sr-only">
              <SheetTitle>{t("header.menu")}</SheetTitle>
            </SheetHeader>
            {sidebar("pt-12")}
          </SheetContent>
        </Sheet>
      )}
      <NewSessionDialog
        open={newOpen}
        onOpenChange={setNewOpen}
        learner={learner}
        onStart={(spec) => void tutor.startSession(spec)}
      />
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        learner={learner}
        onSave={tutor.updateProfile}
      />
    </div>
  );
}

export default function TutorApp() {
  return (
    <I18nProvider>
      <App />
    </I18nProvider>
  );
}
