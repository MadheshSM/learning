# Frontend `.claude/` — Skills & Agents

Copied from [`Krion6D/ti-frontend/.claude/`](../../Krion6D/ti-frontend/.claude/) on 2026-06-01.
Adapted for `krionb6i_frontend`.

## What's here

```
.claude/
├── skills/
│   ├── stabilize-module/SKILL.md   # /stabilize-module <name> — module hardening
│   ├── refactor/SKILL.md           # /refactor <path> — plan-first refactor with parallel agents
│   └── check-module/SKILL.md       # /check-module <name> — read-only "Done" verification
└── agents/
    ├── stabilize.md                # Master orchestrator (security + modules + verify)
    ├── stabilize-module.md         # Single-module stabilization
    └── check-module.md             # Read-only verification
```

## How to use

In Claude Code, invoke:

- `/stabilize-module workspace` — full stabilization pass on `src/app/modules/workspace/`
- `/refactor src/app/modules/admin/` — plan-first refactor workflow
- `/check-module pipeline` — verify module against the 12-point "Done" criteria

Agents can be spawned via the Agent tool — e.g., `stabilize` orchestrates security fixes + module-by-module stabilization.

## Adaptations needed before first run

These skills came from the Krion6D ti-frontend codebase. Several references in the prompts and the master `stabilize` agent won't match `krionb6i_frontend` — adapt or replace as needed.

### Path aliases

Both projects use the same aliases — no adaptation needed:

| Alias         | Maps to                    |
| ------------- | -------------------------- |
| `@core/*`     | `src/app/@core/*`          |
| `@services/*` | `src/app/@services/*`      |
| `@shared/*`   | `src/app/shared/*`         |
| `@modules/*`  | `src/app/modules/*`        |
| `@layout/*`   | `src/app/layout/*`         |
| `@auth/*`     | `src/app/authentication/*` |
| `@env/*`      | `src/environments/*`       |

**Action:** Verify `tsconfig.json` has these aliases configured. If not, add them — the structure already supports them after the recent refactor.

### Things in the agents/skills that don't apply yet

The `stabilize` agent (`agents/stabilize.md`) references Krion6D-specific security fixes:

| Fix item                                                            | Status in `krionb6i_frontend`                                                                      |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `guard` — isAdminGuard deny-by-default                              | `src/app/@core/isadmin.guard.ts` doesn't exist (we only have `auth.guard.ts`, `guest.guard.ts`)    |
| `redirect` — open redirect in login                                 | May or may not apply — check `src/app/authentication/login.component.ts`                           |
| `keys` — Syncfusion key removal                                     | Doesn't apply — this project doesn't use Syncfusion (no license key)                               |
| `validator` — environment validator                                 | `src/app/@core/environment-validator.ts` doesn't exist                                             |
| `csp` — frame-ancestors header                                      | Applies — `src/index.html` should be reviewed                                                      |
| `dompurify` — `linkify.pipe.ts` cleanup                             | Pipe doesn't exist — skip                                                                          |
| `interceptors` — `req.interceptor.ts` / `permission.interceptor.ts` | These are named `auth.interceptor.ts`, `error.interceptor.ts`, `success-toast.interceptor.ts` here |
| `ip` — hardcoded IP/localhost removal                               | May apply — audit `src/environments/`                                                              |

**Action:** Either rewrite `agents/stabilize.md` security mode to match this project's actual security fix items, or just use `stabilize-module` / `refactor` skills (which are codebase-agnostic).

### Module stabilization "Done" criteria

The 12-point checklist in `check-module` references:

- `BaseHttpService` / `BaseStoreHttpService` / `ProjectEntityService` base classes — **not present here.** Services in `@services/` use plain `HttpClient`. Adapt the check or add the base classes.
- `BaseComponent` with `destroyRef`, `_store`, `_toastService`, etc. — **not present here.** Components in this project inject services directly.
- `handleHttpError` utility — **not present.** Create `src/app/shared/utilities/error-handler.util.ts` if you want to enforce this pattern.
- NgRx store with slices — **not present.** This project doesn't use NgRx (yet). The check on store integration doesn't apply.
- Syncfusion / Bootstrap / Three.js — only some apply. Check actual deps in `package.json`.

### Things that DO match (no adaptation needed)

- `src/app/@core/`, `@services/`, `authentication/`, `layout/`, `modules/`, `shared/` top-level layout (we just refactored to match)
- `src/app/shared/modules/components/` for shared UI components
- Standalone Angular components (no NgModules)
- TypeScript strict mode
- Prettier + ESLint setup

### Stabilization plan reference

The `stabilize` agent reads `docs/plans/2026-03-02-refactor-application-stabilization-modernization-plan-deepened.md`. That plan doesn't exist here. Either create a comparable plan or remove the dependency.

## Recommended first run

Start with the smallest module to validate the workflow:

```
/check-module dashboard
```

This is read-only — it tells you what's broken without changing anything. Use the report to either fix issues manually or run `/stabilize-module dashboard`.

Update this README with anything you learn that's specific to this project.
