"use client";

import { motion } from "motion/react";

import { cn } from "@/lib/utils";

export type MascotMood = "idle" | "thinking" | "happy";

const INK = "#2b211c";

function Eye({ cx, mood }: { cx: number; mood: MascotMood }) {
  if (mood === "happy") {
    return (
      <path
        d={`M${cx - 7} 61 q7 -9 14 0`}
        stroke={INK}
        strokeWidth={3.5}
        strokeLinecap="round"
        fill="none"
      />
    );
  }
  const dx = mood === "thinking" ? 3 : 1;
  const dy = mood === "thinking" ? -4 : 1;
  return (
    <g className="pip-eye">
      <circle cx={cx + dx} cy={58 + dy} r={6.5} fill={INK} />
      <circle cx={cx + dx + 2.2} cy={55.5 + dy} r={2} fill="#ffffff" />
    </g>
  );
}

/**
 * Pip, the study-buddy owl. Hand-drawn SVG, so it scales crisply and needs no assets.
 * Decorative by default; pass `label` when it is the only content conveying meaning.
 */
export function Mascot({
  mood = "idle",
  className,
  label,
}: {
  mood?: MascotMood;
  className?: string;
  label?: string;
}) {
  return (
    <motion.svg
      viewBox="0 0 120 120"
      className={cn("shrink-0", className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      data-mood={mood}
      animate={
        mood === "thinking"
          ? { y: [0, -3, 0], transition: { duration: 1.4, repeat: Infinity, ease: "easeInOut" } }
          : mood === "happy"
            ? { y: [0, -8, 0], transition: { duration: 0.5, ease: "easeOut" } }
            : { y: 0 }
      }
    >
      {/* graduation cap */}
      <path d="M42 26v10c0 6 36 6 36 0V26l-18 7z" fill="#4a3b34" />
      <path d="M60 6l38 14-38 14-38-14z" fill="#3b2f2a" />
      <path d="M96 21v15" stroke="#f2b84b" strokeWidth={2.5} strokeLinecap="round" />
      <circle cx={96} cy={38} r={3.5} fill="#f2b84b" />
      {/* ear tufts */}
      <path d="M31 42l-7-18 20 11z" fill="#c97b3f" />
      <path d="M89 42l7-18-20 11z" fill="#c97b3f" />
      {/* body and belly */}
      <ellipse cx={60} cy={72} rx={38} ry={39} fill="#e0954f" />
      <ellipse cx={60} cy={86} rx={24} ry={23} fill="#fbe3c3" />
      <path
        d="M49 84q5 5 11 0q6 5 11 0M53 93q4 4 7 0q4 4 7 0"
        stroke="#e7b98a"
        strokeWidth={2}
        strokeLinecap="round"
        fill="none"
      />
      {/* wings */}
      <path d="M23 66q-7 22 11 35q4-18-11-35z" fill="#c97b3f" />
      <path d="M97 66q7 22-11 35q-4-18 11-35z" fill="#c97b3f" />
      {/* eyes */}
      <circle cx={45} cy={58} r={15} fill="#fff8ec" />
      <circle cx={75} cy={58} r={15} fill="#fff8ec" />
      <Eye cx={45} mood={mood} />
      <Eye cx={75} mood={mood} />
      {mood === "happy" && (
        <>
          <circle cx={33} cy={73} r={5} fill="#f08a7e" opacity={0.55} />
          <circle cx={87} cy={73} r={5} fill="#f08a7e" opacity={0.55} />
        </>
      )}
      {/* beak and feet */}
      <path d="M55 68h10l-5 9z" fill="#f2b84b" />
      <path
        d="M48 109v5M53 109v5M67 109v5M72 109v5"
        stroke="#f2b84b"
        strokeWidth={3}
        strokeLinecap="round"
      />
    </motion.svg>
  );
}
