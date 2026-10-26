"use client";

import { AnimateUIProvider } from "@animate-ui/react/provider";
import { MotionConfig } from "motion/react";
import { ThemeProvider } from "next-themes";

import { TooltipProvider } from "@/components/ui/tooltip";

/** App-wide providers. Motion follows the OS "reduce motion" setting everywhere. */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <AnimateUIProvider reducedMotion="user">
        <MotionConfig reducedMotion="user">
          <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
        </MotionConfig>
      </AnimateUIProvider>
    </ThemeProvider>
  );
}
