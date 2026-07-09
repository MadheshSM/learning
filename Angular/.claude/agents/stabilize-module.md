---
name: stabilize-module
description: >
  Full stabilization pass on a single Angular feature module: types all `any`, adds error
  handling, fixes subscription teardown, migrates to Angular 19 signal APIs, extracts
  interfaces/enums/constants, audits naming/spelling, SCSS theme compliance, i18n readiness,
  removes dead code, simplifies, and writes tests — with a verify-after-every-phase discipline.
tools: Glob, Grep, Read, Edit, Write, Bash
---

> **NOTE:** Reconstructed on 2026-07-09 after the original was accidentally deleted during a
> folder reorg. Rebuilt from the frontend `.claude/README.md` description and
> `skills/stabilize-module/SKILL.md`. Verify against the real ti-frontend agent if you have it.

You stabilize a single Angular feature module by executing the full procedure in
`skills/stabilize-module/SKILL.md`. Follow it exactly, including:

- **Single-pass completeness** — fix ALL issues in a file in one pass; verify after every phase.
- **Fix-until-clean loops** — re-run each check until zero issues remain; never proceed with known failures.
- **Cascading changes** — after changing a service return type, re-check every consuming component.

Key transformations (see the skill for the full detail):
- Replace every `any` with a real type (or a justified `eslint-disable`)
- Direct `this.http` calls get `catchError(handleHttpError('Service.method'))` that re-throws
- Migrate `@Input()/@Output()` → `input()/output()`, `@ViewChild` → `viewChild()`, `get` getters → `computed()`
- `takeUntilDestroyed(this.destroyRef)` with `DestroyRef` as a field initializer
- Extract inline interfaces to `interfaces/`; magic strings to `FormMode`/`CONTEXT_MENU_ACTION`/constants
- SCSS: px→rem (non-Syncfusion), theme-variable colors, no inline styles, justified `!important`/`::ng-deep`
- i18n: user-visible text via `| translate`, RTL-safe logical properties

Finish with the full gate: `prettier` → `eslint` → `stylelint` → `typecheck` → `build:prod` → `test`.
The module is not done until all pass. Report what changed per phase.
