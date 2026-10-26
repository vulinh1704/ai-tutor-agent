import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());

// Browser APIs that jsdom does not implement but Radix, Motion and Animate UI use.
if (typeof window !== "undefined") {
  window.matchMedia ??= (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  });

  class NoopObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  }
  globalThis.ResizeObserver ??= NoopObserver as unknown as typeof ResizeObserver;
  globalThis.IntersectionObserver ??= NoopObserver as unknown as typeof IntersectionObserver;
  Element.prototype.scrollIntoView ??= () => undefined;
  // jsdom defines scrollTo but only logs "not implemented" (dialogs restore scroll on close).
  window.scrollTo = () => undefined;
}

// Tests run with reduced motion on purpose (see src/test/render.tsx); skip Motion's notice.
const warn = console.warn.bind(console);
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("Reduced Motion enabled")) return;
  warn(...args);
};
