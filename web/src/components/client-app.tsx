"use client";

import dynamic from "next/dynamic";

import { Mascot } from "@/components/mascot";

function Splash() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <Mascot mood="thinking" className="size-24" />
    </div>
  );
}

// The app lives in the browser (learner id in local storage, live API calls), so it renders
// on the client only; the server sends a light splash screen.
const TutorApp = dynamic(() => import("@/components/tutor-app"), {
  ssr: false,
  loading: Splash,
});

export function ClientApp() {
  return <TutorApp />;
}
