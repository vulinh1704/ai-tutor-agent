# ai-tutor-web

The web UI for [ai-tutor-agent](../README.md): a friendly study space for secondary-school
students (ages 12-18) with Pip the owl, live-streamed Socratic hints, a visible hint ladder,
rubric grading with per-criterion scores and a progress panel. English and Vietnamese.

Built with Next.js 16 (App Router, TypeScript), React 19, Tailwind CSS 4,
[shadcn/ui](https://ui.shadcn.com) and [Animate UI](https://animate-ui.com) on Motion.

## Run it

The UI talks to the API directly from the browser. Start the API in offline mode first (no
API key needed), from the repository root:

```bash
cp .env.example .env            # LLM_PROVIDER=fake
uv run ai-tutor serve           # http://localhost:8000
```

Then, in `web/`:

```bash
npm install
npm run dev                     # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) points the UI at another API; see
[`.env.example`](.env.example). The API must allow the UI's origin in `CORS_ORIGINS` (it
allows `http://localhost:3000` by default). Or run both with `docker compose up --build` from
the repository root.

## What's inside

| Path | Purpose |
| --- | --- |
| `src/components/onboarding.tsx` | Eight-step learner profile: name, grade, subjects, goal, language, hint style, look |
| `src/components/chat-panel.tsx` | Streaming chat (server-sent events), route badges, leak-guard "rewording" notice |
| `src/components/hint-ladder.tsx` | The hint ladder as a stepper (Nudge, Strategy, Worked step, ...) |
| `src/components/grade-panel.tsx` | "Grade my answer": rubric, score ring, per-criterion bars, celebration |
| `src/components/progress-panel.tsx` | Sessions, average rubric score, day streak, per-subject bars |
| `src/hooks/use-tutor.ts` | All client state and the streaming turn loop |
| `src/lib/api.ts`, `src/lib/sse.ts` | Typed API client and a `fetch`-based SSE reader (the chat stream is a POST) |
| `src/lib/i18n.ts` | English and Vietnamese UI strings; the browser language picks the default |
| `src/lib/practice.ts` | Built-in practice problems with rubrics, in both languages |
| `src/components/ui/` | shadcn/ui components, animated with Animate UI primitives |

Design notes: warm, high-contrast palette with six accent colours and three text sizes,
rounded shapes, keyboard-reachable controls, and motion that follows the system "reduce
motion" setting (`AnimateUIProvider` and `MotionConfig` with `reducedMotion="user"`, plus a CSS
fallback). The learner id is kept in `localStorage`; `?learner=<id>` (shown in Settings)
resumes on another device, `?session=<id>` opens a session and `?tab=grade|progress` picks the
mobile tab.

## Scripts

```bash
npm run lint        # ESLint (eslint-config-next)
npm run typecheck   # next typegen && tsc --noEmit
npm test            # Vitest + React Testing Library (jsdom)
npm run build       # production build (standalone server output)
```

## Third-party components

UI components in `src/components/ui/` come from shadcn/ui (MIT). Animations come from the
`@animate-ui/react` npm package, licensed under MIT + Commons Clause: it is used as a
dependency and none of its source is copied into this repository. See
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
