import { render, type RenderOptions } from "@testing-library/react";
import { MotionConfig } from "motion/react";

import { I18nProvider } from "@/components/i18n-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Language } from "@/lib/types";

/** Render with the app's providers, in a fixed language (kept on `rerender` too). */
export function renderWithProviders(
  ui: React.ReactElement,
  { language = "en", ...options }: Omit<RenderOptions, "wrapper"> & { language?: Language } = {},
) {
  function Providers({ children }: { children: React.ReactNode }) {
    return (
      <I18nProvider initialLanguage={language}>
        <MotionConfig reducedMotion="always">
          <TooltipProvider>{children}</TooltipProvider>
        </MotionConfig>
      </I18nProvider>
    );
  }
  return render(ui, { wrapper: Providers, ...options });
}
