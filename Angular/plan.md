# Angular 19 Frontend Learning Plan

> **The stack.** The `.claude/` skills in this folder (`refactor`, `stabilize-module`,
> `check-module`) target **Angular 19** — standalone components, **signals**, RxJS,
> `@ngx-translate` i18n, SCSS theming — the Krion / ti-frontend / krionb6i frontend codebases.
>
> This plan is reverse-engineered from the "Done" criteria those skills enforce, so that by the
> end you understand *why* every rule `/stabilize-module` and `/refactor` apply exists.

**Goal:** Read, build, and refactor an Angular 19 feature module (component → template → service →
SCSS) to the standard the skills in `.claude/skills/` demand.

**Assumes** you're learning (or have) the NestJS backend in the sibling `Node/` folder — the two
halves talk to each other. TypeScript carries over; this plan focuses on the Angular-specific parts.

**Pace:** ~1 concept per session. Check boxes as you go. Log progress at the bottom.

---

## The Target: What "Done" Looks Like

Before learning, know what you're aiming at. A module is "done" (per `stabilize-module` /
`check-module`) when:

- Zero `any` types (or justified `eslint-disable` with a reason)
- No `console.log`
- Every service HTTP call has `catchError(handleHttpError('Service.method'))` that **re-throws** the original error
- Every component handles **loading / error / empty** states
- `takeUntilDestroyed(this.destroyRef)` on all long-lived subscriptions (`DestroyRef` as a field initializer)
- **Angular 19 signal APIs everywhere** — `input()` / `output()` / `viewChild()`, `signal()` for state, `computed()` for derived state (**never** `get` getters), decorators gone
- Inline interfaces extracted to `interfaces/`; magic strings → `FormMode` / `CONTEXT_MENU_ACTION` / constants/enums
- SCSS: px→rem (except borders/icons/Syncfusion), theme-variable colors (no hardcoded hex), no inline styles, `!important` / `::ng-deep` justified
- i18n: all user-visible text via `| translate`; RTL-safe logical properties (`margin-inline-start`, `text-align: start`)
- File sizes within limits; oversized components split
- 80%+ unit-test coverage; prettier / eslint / stylelint / typecheck / build:prod / test all pass

Keep this list open. Every phase teaches a slice of it.

---

## Phase 0 — Setup & TypeScript Essentials (1–2 sessions)

- [ ] Node LTS + Angular CLI (`npm i -g @angular/cli`), `ng version`, `ng new`, `ng serve`
- [ ] Workspace layout: `src/app/`, `angular.json`, `tsconfig.json`, path aliases (`@core`, `@shared`, `@services`, `@modules`)
- [ ] TypeScript essentials that Angular leans on: strict mode, interfaces, generics, `unknown` vs `any`, type narrowing
- [ ] Decorators (Angular is decorator-based: `@Component`, `@Injectable`, `@Directive`, `@Pipe`)

---

## Phase 1 — Angular Core (4–5 sessions) ⭐

- [ ] **Standalone components** — `@Component({ standalone: true, imports: [...] })`, no NgModules
- [ ] Templates & binding: interpolation `{{ }}`, property `[x]`, event `(x)`, two-way `[(x)]`
- [ ] **Built-in control flow** — `@if` / `@else`, `@for` (with `track`), `@switch` (Angular 17+)
- [ ] **Dependency injection with `inject()`** — the modern function form, not constructor params
- [ ] Component lifecycle + `DestroyRef` (`inject(DestroyRef)` as a field initializer)
- [ ] Pipes & directives (built-in and custom) — when to reach for one instead of component logic

**Project:** Scaffold a `notes` feature: a list component + detail component + a service, standalone,
following the layout the skills assume (`components/`, `services/`, `interfaces/`).

---

## Phase 2 — Signals: the Angular 19 Core (3–4 sessions) ⭐

This is the single biggest thing the refactor skills enforce. Master it.

- [ ] `signal()` for mutable local state — `.set()`, `.update()` (not direct assignment)
- [ ] **`computed()` for derived state** — memoized, auto-tracked; **the skills forbid `get` getters** for this
- [ ] `input()` / `input.required()` / `input(default)` — replaces `@Input()`
- [ ] `output()` — replaces `@Output() ... = new EventEmitter()`
- [ ] `model()` for two-way binding
- [ ] `viewChild()` / `viewChildren()` — replaces `@ViewChild` / `@ViewChildren`
- [ ] `effect()` — for side effects when signals change (use sparingly)
- [ ] **Reading signals with `()`** everywhere — in TS and templates (`isLocked()`, `user()?.name`)

**Practice:** Build a small parent→child pair using `input()`/`output()` and a `computed()`
`isLockedForEdit` derived from `mode()` + `canEdit()`. Update a spec with `setInput()`.

---

## Phase 3 — RxJS & Data Layer (3–4 sessions) ⭐

- [ ] Observables vs Promises; core operators: `map`, `filter`, `switchMap`, `tap`, `finalize`
- [ ] **`HttpClient`** — `provideHttpClient()`, typed GET/POST/PUT/DELETE, `HttpParams`
- [ ] Typed services — `Observable<IApiResponse<T>>`, no `any`
- [ ] **`catchError(handleHttpError('Service.method'))`** — the skills require it on every direct `this.http` call, and it must **re-throw** the original `HttpErrorResponse`, not transform it
- [ ] **Subscription teardown** — `takeUntilDestroyed(this.destroyRef)`; why `DestroyRef` must be a field initializer, not set in `ngOnInit`
- [ ] Component **loading / error / empty** states (a required "Done" criterion)

**Practice:** Wire your `notes` service to the `Node/` NestJS API. Handle loading/error/empty in the
list component.

---

## Phase 4 — Forms & Routing (2 sessions)

- [ ] Reactive forms — `FormGroup`, `FormControl`, validators, `valueChanges` (+ `takeUntilDestroyed`)
- [ ] Router — routes, `routerLink`, params, lazy loading, **guards** (`CanActivate`) & **resolvers**

---

## Phase 5 — Styling & i18n (2–3 sessions)

The refactor skill is dense on SCSS and translation — real "Done" criteria live here.

- [ ] **SCSS theming** — CSS-variable design tokens (`var(--color-*)`, `var(--radius-*)`, `var(--font-size-*)`)
- [ ] **px → rem** rules: convert font-size/padding/margin/gap/border-radius; keep px for borders (1–2px), icon sizes, box-shadow, Syncfusion `.e-*`
- [ ] No hardcoded hex, no inline `style=""`, max 2-level nesting
- [ ] `!important` / `::ng-deep` only where justified (Syncfusion overrides, lock states)
- [ ] **i18n with `@ngx-translate`** — `{{ 'MODULE.KEY' | translate }}`, `[placeholder]="'KEY' | translate"`, `TranslateService.instant()` in TS; never `[innerHTML]` with translate (XSS)
- [ ] **RTL support** — logical properties (`margin-inline-start`, `text-align: start`), no hardcoded `left`/`right` or `direction`

---

## Phase 6 — Conventions & Refactor (2–3 sessions) ⭐ the payoff

Connect learning to the skills. This is why the plan exists.

- [ ] Read [.claude/skills/stabilize-module/SKILL.md](.claude/skills/stabilize-module/SKILL.md) end to end — a checklist of what makes Angular code good or bad here
- [ ] Read [.claude/skills/refactor/SKILL.md](.claude/skills/refactor/SKILL.md) — the phased, plan-first refactor workflow
- [ ] Read [.claude/skills/check-module/SKILL.md](.claude/skills/check-module/SKILL.md) — the read-only "Done" verification
- [ ] Interface extraction to `interfaces/` + barrel `index.ts`; use path aliases over relative imports
- [ ] Magic strings → constants/enums: `FormMode`, `CONTEXT_MENU_ACTION`, `ReviewStatus`, `AppConstants` fallback assets
- [ ] Component reuse — replace custom markup with shared components (`app-common-modal`, `app-attach-files`, etc.)
- [ ] File-size limits (component 300, template 200, service 250, scss 150 LOC) and when to split
- [ ] **Hands-on:** write a "bad" component (an `any`, a `console.log`, `@Input()`, a `get` getter, a hardcoded hex, an untranslated label) and fix each by the skill's rules

---

## Phase 7 — Testing & Quality (2 sessions)

- [ ] **Jasmine + Karma** (Angular default) — service specs with `HttpTestingController`
- [ ] Component specs — `TestBed`, `fixture.componentRef.setInput()` for signal inputs, mocking services
- [ ] Meaningful tests: loading/error/empty states, interactions — not stub-only "should create"
- [ ] The full gate: `prettier` → `eslint` → `stylelint` → `typecheck` → `build:prod` → `test`

---

## Capstone

Build a small Angular feature to your own standard, then run the skills on it:

1. **Feature module** — list + detail + add/edit, standalone, signals throughout, typed `HttpClient`
   service against the `Node/` API, full loading/error/empty, i18n keys, themed SCSS
2. Run `/check-module <name>` (read-only) and see how many of the 12 criteria you already pass
3. Run `/stabilize-module <name>` (or fix by hand) to close the gaps

---

## Reference Resources

- **Read first (in this repo):** the three `.claude/skills/*/SKILL.md` files + `.claude/README.md`
- [Angular docs](https://angular.dev/) — signals, standalone, control flow (primary source)
- [Angular signals guide](https://angular.dev/guide/signals)
- [RxJS docs](https://rxjs.dev/)
- [@ngx-translate](https://github.com/ngx-translate/core)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

---

## Progress Log

| Date | Phase | What I learned / built |
|------|-------|------------------------|
|      |       |                        |
