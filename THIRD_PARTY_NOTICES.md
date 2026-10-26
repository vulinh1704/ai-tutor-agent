# Third-party notices

`ai-tutor-agent` is released under the [MIT License](LICENSE). It depends on third-party
software under its own licenses. This file lists the components that need a specific mention;
every dependency's license ships with it in `node_modules/` or the Python environment.

## Animate UI (`@animate-ui/react`)

- Used by: the web UI (`web/`), for animated Radix primitives (dialog, sheet, tabs, toggle
  group, progress, tooltip) and effects (highlight, particles, counting number, auto height,
  fade, theme toggler).
- License: **MIT + Commons Clause**, Copyright (c) 2025 Elliot Sutton.
  <https://github.com/imskyleen/animate-ui/blob/main/LICENSE.md>
- How it is used: as an **npm dependency** only. No Animate UI source code is copied into this
  repository; `npx @animate-ui/cli animate` only rewrote the imports of our shadcn/ui
  components to point at the package.
- What the Commons Clause means here: you may use, modify and ship the web UI as part of an
  application, website or product, including commercially. You may not sell or redistribute
  Animate UI's components themselves, alone or in a bundle. Check the license above before
  reusing the components outside this project.

## shadcn/ui

- Used by: `web/src/components/ui/` (generated with the `shadcn` CLI, then animated as above),
  plus the `shadcn` and `cn` packages for shared styles and class merging.
- License: MIT, Copyright (c) shadcn. <https://github.com/shadcn-ui/ui/blob/main/LICENSE.md>

## Nunito font

- Used by: the web UI, downloaded at build time by `next/font/google` and served with the app.
- License: SIL Open Font License 1.1. <https://fonts.google.com/specimen/Nunito/license>

## Other notable dependencies

| Package | License |
| --- | --- |
| Next.js, React, Radix UI, Motion, next-themes, Tailwind CSS, tw-animate-css | MIT |
| lucide-react (icons) | ISC |
| class-variance-authority | Apache-2.0 |
| MCP Python SDK (`mcp`, optional extra) | MIT |
| tzdata | Apache-2.0 |

Pip the owl (the mascot) and all other illustrations in this repository are original work
under the project's MIT license.
