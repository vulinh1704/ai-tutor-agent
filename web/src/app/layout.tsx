import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

// Rounded, friendly and fully Vietnamese-ready.
const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin", "vietnamese"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Tutor · Hints, not answers",
  description:
    "A Socratic AI tutor for secondary-school students: hints that climb one step at a time, rubric grading and progress you can see.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbf7ef" },
    { media: "(prefers-color-scheme: dark)", color: "#221c17" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${nunito.variable} h-full`} suppressHydrationWarning>
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
