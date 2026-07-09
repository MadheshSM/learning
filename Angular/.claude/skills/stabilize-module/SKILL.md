---
name: stabilize-module
description: >
  Run the full stabilization pass on a feature module following the plan at
  docs/plans/2026-03-02-refactor-application-stabilization-modernization-plan-deepened.md.
  Types all `any`, adds error handling, fixes subscriptions, extracts enums/constants,
  audits naming/spelling, reviews file sizes, removes unused code, simplifies code, writes tests.
argument-hint: <module-name>
---

Stabilize the feature module: **$ARGUMENTS**

## Single-Pass Completeness Principle

**Every issue MUST be caught and fixed on the FIRST run.** To achieve this:

1. **Verify after every phase.** After completing a phase, run the relevant check (grep for `any`, lint, typecheck) and fix ALL remaining issues before moving to the next phase. Never assume a phase is done without automated verification.
2. **Fix-until-clean loops.** When a check finds issues, fix them and re-run the check. Repeat until zero issues remain. Do NOT move on with known failures.
3. **Account for cascading changes.** When you change a service return type, re-check all components that consume that service — the type change will introduce new errors downstream. After fixing components, re-check services too (imports may have changed).
4. **Incremental lint/typecheck.** Run `npm run typecheck` after EVERY phase that edits `.ts` files (not just at the end). This catches cascading type errors early when they're cheap to fix.
5. **Re-read after editing.** After editing a file, re-read it to confirm all issues in that file are resolved. Don't rely on memory of what was there before.
6. **One file, fully clean.** When working on a file, fix ALL issues in it (types, subscriptions, dead code, naming, console.log) in a single pass — don't plan to come back later.

## Reference Plan

Read the stabilization plan for patterns and conventions:
`docs/plans/2026-03-02-refactor-application-stabilization-modernization-plan-deepened.md`

Specifically reference:

- Phase 1.2 (Gold Standard Module pattern)
- Phase 1.1a (API response interfaces)
- Phase 1.1b (Error handling pattern)
- Phase 1.1c (Subscription teardown)

## Step 1 — Analyze the Module

```bash
# Find the module directory
ls src/app/modules/$ARGUMENTS/

# Count any usages
grep -r "any" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v node_modules | grep -v ".spec.ts" | wc -l

# List all TypeScript files with line counts
find src/app/modules/$ARGUMENTS/ -name "*.ts" -not -name "*.spec.ts" -exec wc -l {} + | sort -rn

# List all HTML templates with line counts
find src/app/modules/$ARGUMENTS/ -name "*.html" -exec wc -l {} + | sort -rn

# Check for existing interfaces
ls src/app/modules/$ARGUMENTS/interfaces/ 2>/dev/null

# Check for existing tests
find src/app/modules/$ARGUMENTS/ -name "*.spec.ts" | sort
```

**Report:**

- Total `any` count per file
- **File sizes** (LOC) for every `.ts` and `.html` file — flag files >300 lines (TS) or >200 lines (HTML) for review
- Services found (HTTP methods, error handling)
- Components found (LOC, extends BaseComponent?, subscription pattern)
- Existing interfaces and models
- Existing tests (stub vs meaningful)
- Duplicate services from `project-management` (check `src/app/modules/project-management/services/` for same-named service)

## Step 2 — Check for Duplicate Services

```bash
# Check if this module has a duplicate service in project-management
SERVICE_NAME=$(basename $(ls src/app/modules/$ARGUMENTS/services/*.service.ts 2>/dev/null | head -1) 2>/dev/null)
if [ -n "$SERVICE_NAME" ]; then
  find src/app/modules/project-management/services/ -name "$SERVICE_NAME" 2>/dev/null
fi
```

If a duplicate exists in `project-management/services/`:

1. Verify which one is the canonical version (check import counts)
2. Delete the duplicate
3. Update all imports to use the canonical path

## Step 3 — Create/Update Interfaces

Create interfaces in `src/app/modules/$ARGUMENTS/interfaces/`:

**Naming convention:**

- `I<EntityName>` — full entity (e.g., `IProjectTask`)
- `I<EntityName>Create` / `I<EntityName>Update` — form submission shapes
- `I<EntityName>ListItem` — list view subset
- `I<EntityName>Filter` — search/filter params

**Source of truth:** Inspect actual API responses in browser devtools or coordinate with backend Swagger spec.

**Use shared interfaces from `src/app/shared/interfaces/`:**

- `IApiResponse<T>` for HTTP responses
- `IUser` for assignee/creator fields
- `IAttachment` for file fields
- `IWorkflowState` for workflow transitions
- `IProjectDetails` for project context

## Step 4 — Type the Service

**NOTE (K6AQ-T81 — DONE):** All module-level services now extend `BaseHttpService` or `BaseStoreHttpService` (`src/app/shared/services/base-http.service.ts`). This means:

- All HTTP methods (`this.get`, `this.post`, `this.put`, `this.patch`, `this.delete`) already have built-in `catchError(handleHttpError('ServiceName.methodName'))`.
- Services declare `protected readonly baseUrl = \`\${environment.BASE_URL}\``.
- Cross-cutting methods (`getWorkflowList`, `getActivities`, `getCost`, etc.) are in `ProjectEntityService` (`src/app/shared/services/project-entity.service.ts`).
- `BaseHttpRequestOptions` does NOT support `observe` or `body` in DELETE — those require `this.http` directly with manual `catchError(handleHttpError(...))`.

For each service in `src/app/modules/$ARGUMENTS/services/`:

1. **Replace all `any` return types** with `Observable<IApiResponse<IEntity>>` etc.
2. **Verify `catchError` coverage** — base class methods already include it, but any direct `this.http` calls must add `catchError(handleHttpError('ServiceName.methodName'))` manually
   - CRITICAL: `handleHttpError` MUST re-throw original `HttpErrorResponse` (not transform)
   - Import from `src/app/shared/utilities/error-handler.util.ts`
3. **Type all method parameters** — no implicit `any`
4. **Remove `public data: any = []`** accumulators if present (evaluate if still needed after NgRx reducer fix)
5. **Remove duplicate cross-cutting methods** — use `ProjectEntityService` instead (`getWorkflowList`, `getActivities`, `getCost`, `getAttachments`, `getHistory`, `getComments`, `addComment`, `getStatus`, `getWatcher`, `addWatcher`, `deleteWatcher`)
6. **Remove dead code:**
   - Unused imports (flagged by ESLint `@typescript-eslint/no-unused-vars`)
   - Unused private methods and variables
   - Unused parameters — prefix with `_` if required by interface/override signature, otherwise remove entirely
   - Unused injected services (e.g., `private _foo = inject(FooService)` never referenced)

### Step 4 Verification — Services Clean Check

Before proceeding, verify ALL services are fully typed:

```bash
# Count remaining any in services only
grep -rn ": any\|<any\|as any\| any;\| any)" --include="*.ts" src/app/modules/$ARGUMENTS/services/ | grep -v ".spec.ts" | grep -v "eslint-disable"
```

**Must be 0** (or justified with `eslint-disable`). If not, fix and re-check. Do NOT proceed until clean.

```bash
# Run typecheck to catch cascading errors from return type changes
npm run typecheck
```

Fix any typecheck errors before proceeding. Type changes in services WILL cause errors in components — that's expected, but typecheck surfaces them now so you know what to fix in Step 6.

## Step 5 — Type the Models

For each model in `src/app/modules/$ARGUMENTS/models/`:

- Replace `any` fields with proper types
- Replace `[]` with typed arrays (e.g., `assignedTo: IUser[]`)
- Replace `object[]` with typed arrays (e.g., `attachments: IAttachment[]`)

## Step 6 — Type the Components

For each component in `src/app/modules/$ARGUMENTS/components/`:

1. **Replace `any`** in method signatures, local variables, template bindings
2. **Add loading/error/empty state handling** if missing
3. **Fix subscription teardown:**
   - Use `private destroyRef = inject(DestroyRef);` as field initializer
   - Use `takeUntilDestroyed(this.destroyRef)` in all subscriptions
   - IMPORTANT: `inject(DestroyRef)` must be in field initializer, NOT in `ngOnInit`
4. **Remove `console.log`** calls
5. **Remove dead code in components:**
   - Unused imports (both Angular and third-party)
   - Unused class properties and local variables
   - Unused methods — if a method is defined but never called from template or class, delete it
   - Unused constructor/inject parameters — if an injected service is never referenced, remove it
   - Leftover lifecycle hooks with empty bodies (e.g., `ngOnDestroy() {}` after migrating to `DestroyRef`)
   - Unused `OnDestroy` / `OnInit` interface declarations when the corresponding method is removed
6. **Check template `[innerHTML]` bindings** — verify DOMPurify is used for user content
7. **Review HTML templates** for size and quality:
   - **Large templates (>200 lines):** Flag for review — consider extracting repeated sections into child components
   - **Deep nesting (>6 levels of indentation):** Simplify with `@if`/`@for` or extract into sub-components
   - **Duplicate markup:** If the same block appears 2+ times, extract into a shared component or use `@for`
   - **Inline styles:** Move to SCSS — no `style="..."` in templates
   - **Hardcoded strings:** Move user-facing text to constants if repeated across templates
   - Do NOT rewrite working templates just to reduce lines — only refactor when there's a clear readability or maintenance problem
8. **Add comments only where logic is non-obvious.** Examples of when to comment:
   - `eslint-disable` lines — always explain WHY (e.g., `// eslint-disable-next-line @typescript-eslint/no-unused-vars -- destructured to exclude from spread`)
   - Workarounds or hacks (e.g., `// PowerBI SDK requires this cast — no typed alternative`)
   - Complex business logic that isn't clear from variable/method names
   - Non-obvious type casts (e.g., `as Record<string, unknown>` — explain why the original type is insufficient)
   - Do NOT add comments that restate what the code does (e.g., `// Load grid data` above `loadGrid()`)
   - Do NOT add JSDoc to every method — only where the signature alone is ambiguous

### Step 6 Verification — Components & Models Clean Check

Before proceeding, verify ALL components and models are fully typed and fixed:

```bash
# Count remaining any in the entire module (excluding specs and eslint-disable)
grep -rn ": any\|<any\|as any\| any;\| any)" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v ".spec.ts" | grep -v "eslint-disable"

# Check for remaining console.log
grep -rn "console\.\(log\|warn\|error\)" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v ".spec.ts"

# Run typecheck to catch ALL cascading errors from type changes
npm run typecheck
```

**All must be 0.** If typecheck fails, fix errors now — they will NOT fix themselves later. Common cascading errors:

- Service return type changed → component variable now has wrong type → fix the component
- Interface field renamed → model/component still uses old name → update references
- `any` removed from parameter → callers now have type mismatches → fix callers

**Loop: fix → re-check → fix → re-check until ALL clean.**

## Step 7 — Extract Magic Strings/Numbers to Enums and Constants

Scan every `.ts` file in the module for hardcoded values that should be enums or constants.

### 7a — Magic strings → Enums or Constants

**Check shared enums first** (`src/app/shared/enums/`) — reuse if one already exists:

- `ProjectEntity` — entity type strings (`Role`, `Task`, `RFI`, etc.)
- `Permission` — permission types (`Modify`, `Delete`, `View`)
- `StorageKey` — localStorage key names
- `ProjectStatus`, `ReviewStatus`, `Workflow` — status/workflow values

**Check shared constants** (`src/app/shared/constants/`):

- `MODULE_CONFIG` — module display names, routes
- `AppConstants` — shared limits, lengths
- `pageSettingData` — grid page settings

**What to extract:**

- Repeated string literals used in comparisons (e.g., `"edit"`, `"add"`, `"delete"`, `"Dialog"`) → create a local enum or use an existing shared one
- Route path strings (e.g., `"/admin-role/list"`, `"/admin-role/edit/"`) → extract to a `ROUTES` const object in the module's constants folder
- Toast messages repeated across methods → extract to a `MESSAGES` const object or keep inline if unique
- Grid/table config strings (e.g., `"Shimmer"`, `"Default"`, `"Excel"`, `"Dialog"`) → extract to module-level constants if repeated, or use shared constants if they exist
- CSS class strings used in TS logic → extract to constants
- HTTP endpoint path segments (e.g., `"role/list"`, `"role/create"`) → acceptable inline in service methods (they are unique per method), but the base entity path should be a single constant if repeated

**What NOT to extract:**

- Unique one-off strings (a toast message used exactly once is fine inline)
- Template-only strings (labels in HTML are fine as-is)
- Enum values that are already typed (e.g., `Permission.MODIFY` is already an enum)

### 7b — Magic numbers → Named constants

- Hardcoded numbers like `50` (setTimeout delay), `0.6` (opacity) → extract to named constants if they represent a domain concept
- Array indices, `findIndex !== -1` checks → acceptable as-is
- Page sizes, limits → should already use `AppConstants` or `pageLimitSetting`

### 7c — Boolean/conditional patterns

- Replace `condition ? true : false` with just `condition` (or `!!condition` if coercion needed)
- Replace `value === true` with `value`, `value === false` with `!value`

## Step 8 — Variable Naming, Spelling, and Code Style Audit

### 8a — Naming conventions

Verify every identifier follows Angular/TypeScript conventions:

- **Classes/Interfaces/Enums:** `PascalCase` (e.g., `RoleService`, `IRoleListItem`, `ProjectEntity`)
- **Variables/properties/methods:** `camelCase` (e.g., `roleId`, `getRoleList`, `isLoading`)
- **Constants (module-level):** `camelCase` or `UPPER_SNAKE_CASE` for true constants (e.g., `permissionList`, `ROUTES`, `MAX_RETRIES`)
- **Private fields:** prefix with `_` for injected services (e.g., `private readonly _roleService`), no prefix for component state (e.g., `isLoading`, `destroyRef`)
- **Boolean properties:** should be prefixed with `is`, `has`, `can`, `show` (e.g., `isLoading`, `hasError`, `canEdit`, `showView`)
- **Event handler methods:** should use verb form — `onSubmitForm()`, `handleViewPermission()`, `confirmDelete()`
- **Observable variables:** suffix with `$` if stored as class property (e.g., `data$`, `roleList$`) — NOT needed for inline `.subscribe()` calls

**Flag and fix:**

- Abbreviated names that are unclear: `res` → `response`, `req` → `request` (except in HTTP interceptors/tests where convention), `e` → `error`, `x` → descriptive name
- Single-letter variables outside of arrow functions with obvious context
- Inconsistent naming within the same file (e.g., `detail` vs `roleDetail` for the same concept)

### 8b — Spelling check

Scan all identifiers (variable names, method names, property names, enum values, interface fields) for obvious misspellings:

- Common Angular project misspellings: `attachmnet` → `attachment`, `premission` → `permission`, `conformation` → `confirmation`, `destory` → `destroy`
- Check import paths for misspelled shared component names (e.g., `attachmnet-warning-modal`)
- Check string literals in toast messages, labels, and error messages for typos
- **Do NOT rename shared components** that have misspelled names (e.g., `attachmnet-warning-modal`) — these require a project-wide rename. Just flag them.

### 8c — File size review

| Threshold   | File type        | Action                                                                                     |
| ----------- | ---------------- | ------------------------------------------------------------------------------------------ |
| > 300 lines | `.ts` component  | Consider extracting logic to a service or splitting into sub-components                    |
| > 200 lines | `.html` template | Consider extracting repeated sections into child components                                |
| > 150 lines | `.ts` service    | Review — may be fine if many HTTP methods, but check for logic that belongs in a component |
| > 100 lines | `.scss`          | Check for duplicate styles, consider shared mixins                                         |

**Do NOT split files just to meet a threshold.** Only split when there is a clear separation of concerns. Flag large files in the report with a brief assessment of whether splitting is warranted.

## Step 9 — Unused Code Final Sweep

Run a final comprehensive check for unused code across the entire module:

```bash
# Check for unused imports (ESLint will catch most, but verify manually)
npx eslint "src/app/modules/$ARGUMENTS/**/*.ts" --quiet --rule '{"@typescript-eslint/no-unused-vars": "error"}'

# Check for unused exports — search if module exports are imported anywhere else
grep -rn "from.*$ARGUMENTS" --include="*.ts" src/app/ | grep -v node_modules | grep -v "$ARGUMENTS/"
```

**Checklist:**

- [ ] No unused imports in any `.ts` file
- [ ] No unused class properties (declared but never read in template or class)
- [ ] No unused methods (defined but never called from template or class)
- [ ] No unused injected services (`inject(FooService)` never referenced)
- [ ] No empty lifecycle hooks (`ngOnInit() {}`, `ngOnDestroy() {}` with no body)
- [ ] No commented-out code blocks (delete them — git has the history)
- [ ] No `console.log`, `console.warn`, `console.error` calls
- [ ] No unused interface fields (fields defined but never used in consuming code)
- [ ] No duplicate type declarations (same interface defined in multiple files)

## Step 9b — SCSS Audit (Theming Compliance)

Integrated from the theming plan Phase 3 (`docs/plans/2026-03-06-refactor-theming-system-standardization-plan.md`).

For each `.scss` file in `src/app/modules/$ARGUMENTS/components/`:

### 9b-1 — px-to-rem Conversion

| Convert to `rem`                          | Keep in `px`                            |
| ----------------------------------------- | --------------------------------------- |
| `font-size`                               | `border` / `border-width` (1px, 2px)    |
| `padding` / `margin`                      | `box-shadow` offset/blur/spread         |
| `gap`                                     | `outline` width                         |
| `width` / `height` on layout containers   | Icon sizes (16px, 24px, 28px, 32px)     |
| `top` / `right` / `bottom` / `left`       | Syncfusion component overrides (`.e-*`) |
| `line-height` (when in px)                | Media query breakpoints                 |
| `border-radius`                           | Sub-pixel precision (0.5px)             |
| `min-height` / `max-height` on containers | `transform: translateY(-1px)`           |

**Use design tokens where they match:**

- `border-radius: 8px` → `var(--radius-lg)` (0.5rem)
- `border-radius: 6px` → `var(--radius-md)` (0.375rem)
- `border-radius: 4px` → `var(--radius-sm)` (0.25rem)
- `font-size: 16px` → `var(--font-size-lg)`
- `font-size: 14px` → `var(--font-size-body)`
- `font-size: 13px` → `var(--font-size-sm)`
- `font-size: 12px` → `var(--font-size-xs)`

**Reminder:** All rem values are relative to **16px** (html root), NOT 14px. `1rem = 16px`.

### 9b-2 — Color Token Verification

```bash
# Check for hardcoded hex colors (should be caught by stylelint color-no-hex rule)
grep -rn "#[0-9a-fA-F]\{3,8\}" --include="*.scss" src/app/modules/$ARGUMENTS/
```

All colors MUST use `var(--color-*)` tokens. If hardcoded hex found, replace with the appropriate token from `src/theme/_variables.scss`.

### 9b-3 — Inline Styles in Templates

```bash
# Check for inline style attributes
grep -rn 'style="' --include="*.html" src/app/modules/$ARGUMENTS/
```

Move inline styles to component SCSS. For simple resets like `margin: 0; padding: 0`, use Bootstrap utility classes (`m-0 p-0`) instead.

### 9b-4 — `!important` Review

Flag all `!important` usages. Acceptable cases:

- Syncfusion `.e-*` overrides (required to override Syncfusion specificity)
- Entity lock/disabled state styles (`.locked`, `.disabled-field`, `.disabled-wrapper`)
- `cursor: pointer` on interactive elements (overrides Syncfusion defaults)

Remove `!important` from hover states if the base element already has it — the hover inherits.

### 9b-5 — `::ng-deep` Review

`::ng-deep` is acceptable ONLY for Syncfusion component overrides (e.g., `.e-gantt-dialog`, `.e-grid`). Flag any other usage for review — prefer component-scoped styles or global partials in `src/theme/partials/`.

### 9b-6 — SCSS File Size

Files >100 lines: check for duplicate styles or styles that belong in shared partials (`src/theme/partials/`).

**Run stylelint after all SCSS changes:**

```bash
npx stylelint "src/app/modules/$ARGUMENTS/**/*.scss" --fix
npx stylelint "src/app/modules/$ARGUMENTS/**/*.scss"
```

### Step 9 Verification — Full Module Clean Check

Run ALL automated checks before proceeding to simplification. This catches issues introduced during Steps 7-9b:

```bash
# 1. Format all files first (prevents lint-staged failures later)
npx prettier --write "src/app/modules/$ARGUMENTS/**/*.ts" "src/app/modules/$ARGUMENTS/**/*.html" "src/app/modules/$ARGUMENTS/**/*.scss"

# 2. Lint TS + HTML
npx eslint "src/app/modules/$ARGUMENTS/**/*.ts" --quiet --fix
npx eslint "src/app/modules/$ARGUMENTS/**/*.html" --quiet --fix

# 3. Stylelint SCSS
npx stylelint "src/app/modules/$ARGUMENTS/**/*.scss" --fix

# 4. Typecheck
npm run typecheck

# 5. Verify zero any
grep -rn ": any\|<any\|as any\| any;\| any)" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v ".spec.ts" | grep -v "eslint-disable"

# 6. Verify zero console.log
grep -rn "console\.\(log\|warn\|error\)" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v ".spec.ts"
```

**Fix ANY failures now.** Do NOT defer to Step 13. The simplification pass (Step 10) should operate on already-clean code — otherwise it may mask or reintroduce issues.

## Step 10 — Code Simplification Pass

After all stabilization edits are complete, run the **code-simplifier** agent on all modified files in the module. This catches reuse opportunities, redundant logic, and quality issues that are easy to miss during manual editing.

**Invoke the code-simplifier agent** scoped to the module's recently modified files:

```
Use the Agent tool with subagent_type="pr-review-toolkit:code-simplifier"
Prompt: "Simplify and refine all recently modified code in src/app/modules/$ARGUMENTS/ for clarity, consistency, and maintainability while preserving all functionality."
```

**What the simplifier checks:**

- Redundant or duplicated logic that can be consolidated
- Overly complex expressions that can be simplified
- Opportunities to reuse existing shared utilities, pipes, or components
- Unnecessary type assertions or casts
- Verbose patterns that have cleaner Angular/TypeScript idioms
- Dead branches or unreachable code paths
- Inconsistent patterns within the same file (e.g., mixing `if/else` and early returns)

**What it does NOT do:**

- It does NOT add new features or change behavior
- It does NOT restructure files or move code between files
- It does NOT modify test files

**Review the simplifier's output** — accept changes that improve clarity, reject changes that alter behavior or add unnecessary abstraction.

## Step 11 — Write Service Tests

Create `src/app/modules/$ARGUMENTS/services/<service-name>.service.spec.ts`:

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

describe('ServiceName', () => {
  let service: ServiceName;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ServiceName, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ServiceName);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  // Test each HTTP method: success, error, edge cases
});
```

**Test coverage targets:**

- All HTTP methods (GET, POST, PUT, DELETE)
- Success responses with proper type assertion
- Error responses (400, 401, 403, 404, 500)
- Edge cases (empty lists, null fields)

## Step 12 — Write Component Tests

Create spec files for key components using `createBaseComponentTestBed` from `src/app/shared/testing/test-helpers.ts`:

```typescript
import { createBaseComponentTestBed } from '@shared/testing/test-helpers';
import { provideMockStore } from '@ngrx/store/testing';

describe('ComponentName', () => {
  beforeEach(async () => {
    await createBaseComponentTestBed(ComponentName, {
      providers: [provideMockStore({ initialState: {} })],
    }).compileComponents();
  });
});
```

**Test coverage targets:**

- Component creation
- Data loading on init
- User interactions (click, filter, form submit)
- Error state display
- Loading state display
- Empty state display

### Step 10 Verification — Post-Simplification Re-check

The code-simplifier may have introduced formatting or lint issues. Re-run:

```bash
npx prettier --write "src/app/modules/$ARGUMENTS/**/*.ts" "src/app/modules/$ARGUMENTS/**/*.html" "src/app/modules/$ARGUMENTS/**/*.scss"
npx eslint "src/app/modules/$ARGUMENTS/**/*.ts" --quiet --fix
npm run typecheck
```

Fix any issues before proceeding to tests.

## Step 13 — Final Validation: Format, Lint, Typecheck, Build, Test

**By this point, all checks should already pass** from the intermediate verification steps. This is the final gate — if anything fails here, it means a previous step was incomplete. Fix it now.

Run these in order. Each must pass before proceeding to the next.

### 13a — Format (Prettier)

The pre-commit hook runs `prettier --check` via lint-staged. Fix formatting BEFORE committing to avoid hook failures.

```bash
# Format all changed module files (TS + HTML + SCSS)
npx prettier --write "src/app/modules/$ARGUMENTS/**/*.ts" "src/app/modules/$ARGUMENTS/**/*.html" "src/app/modules/$ARGUMENTS/**/*.scss"

# Verify formatting passes
npx prettier --check "src/app/modules/$ARGUMENTS/**/*.ts" "src/app/modules/$ARGUMENTS/**/*.html" "src/app/modules/$ARGUMENTS/**/*.scss"
```

**NOTE:** `.eslintignore` excludes `*.spec.ts`, so lint-staged will emit "Explicitly specified file was ignored due to negative glob patterns" for spec files. This is a pre-existing issue and does NOT block commits.

### 13b — Lint (ESLint + Stylelint)

```bash
# Lint all module TS files (excludes spec files per .eslintignore)
npx eslint "src/app/modules/$ARGUMENTS/**/*.ts" --quiet

# Lint HTML templates
npx eslint "src/app/modules/$ARGUMENTS/**/*.html" --quiet

# Lint SCSS — auto-fix first, then check remaining
npx stylelint "src/app/modules/$ARGUMENTS/**/*.scss" --fix
npx stylelint "src/app/modules/$ARGUMENTS/**/*.scss"
```

**Known SCSS issues:**

- `::ng-deep` triggers `selector-pseudo-element-no-unknown` — this is a false positive for Angular. Acceptable to leave as-is (Angular-specific pseudo-element).
- `rule-empty-line-before`, `length-zero-no-unit`, `property-no-vendor-prefix` — all auto-fixable via `--fix`

### 13c — Typecheck

```bash
npm run typecheck
```

### 13d — Production Build

The pre-push hook runs `npm run build:prod`. Run it now to catch Angular template type errors that `tsc --noEmit` misses (e.g., pipe argument types, `@Input()` binding types).

```bash
npm run build:prod
```

**Common template errors caught only by build:**

- `string | undefined` passed to a pipe expecting `string` → use `?? ''` fallback
- `string | undefined` bound to `@Input() foo: string` → use `?? ''` fallback
- Unused imports in component `imports` array → remove them

### 13e — Unit Tests

```bash
npm run test -- --no-watch
```

Only the module's tests must pass. Pre-existing failures in other modules are acceptable.

### 13f — Count Remaining `any`

```bash
grep -r "any" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v node_modules | grep -v ".spec.ts" | grep -v "eslint-disable" | grep -c ": any\|<any\|as any\| any;\| any)"
```

Must be **0**.

**Module is "Done" when:**

- [ ] Zero `any` (or justified `eslint-disable`)
- [ ] All services have `catchError` that re-throws `HttpErrorResponse`
- [ ] All components handle loading/error/empty states
- [ ] `takeUntilDestroyed(this.destroyRef)` in all long-lived subscriptions
- [ ] No dead code (unused imports, variables, methods, injected services, commented-out code)
- [ ] No magic strings/numbers — repeated values extracted to enums or constants
- [ ] Proper variable naming (camelCase, PascalCase conventions) and no misspellings
- [ ] File sizes reviewed — large files flagged and split if warranted
- [ ] SCSS audit: px-to-rem (non-Syncfusion), zero hardcoded hex, no inline styles, `!important`/`::ng-deep` justified
- [ ] 80%+ unit test coverage
- [ ] Prettier formatting passes (TS + HTML + SCSS)
- [ ] ESLint passes
- [ ] Stylelint passes (SCSS — `::ng-deep` exception acceptable)
- [ ] Typecheck passes
- [ ] Production build passes (catches template type errors)
- [ ] Tests pass

## Step 14 — Commit and Verify Hooks Pass

The commit MUST pass both the pre-commit hook (`lint-staged` + `typecheck`) and be ready for the pre-push hook (`build:prod`).

```bash
# Stage all module changes + any .claude/ skill/agent updates
git add src/app/modules/$ARGUMENTS/
git add .claude/skills/ .claude/agents/ .claude/settings.json 2>/dev/null

# Commit — hooks will run automatically:
#   pre-commit: lint-staged (eslint + prettier) + typecheck
git commit -m "K6AQ-999: Stabilize $ARGUMENTS module — type safety, error handling, tests"
```

**If the commit fails:**

1. Read the hook output to identify which check failed
2. Fix the issue (usually Prettier formatting or a lint error)
3. Re-stage and create a NEW commit (do NOT amend)

**Do NOT use `--no-verify` to skip hooks.**

NEVER CODE without reading the existing files first. Always understand the current state before making changes.

## Learnings from Previous Stabilizations

These patterns and pitfalls were discovered during actual stabilization runs. Reference them to avoid repeating mistakes.

### SocketService Mocking (Components with Entity Locking)

Components that inject `SocketService` (detail/add-edit components) will fail to create in tests because the constructor reads `AppService.userSubject.value.user.userID`. **Always provide a mock:**

```typescript
const mockSocketService = {
	reviewSocket: { connected: false },
	onEntityAvailable: jasmine.createSpy("onEntityAvailable"),
	onEntityLocked: jasmine.createSpy("onEntityLocked"),
	onEntityLockReleased: jasmine.createSpy("onEntityLockReleased"),
	onLockAcquired: jasmine.createSpy("onLockAcquired"),
	onConnect: jasmine.createSpy("onConnect"),
	onReconnect: jasmine.createSpy("onReconnect"),
	joinEntity: jasmine.createSpy("joinEntity"),
	requestLock: jasmine.createSpy("requestLock"),
	leaveEntity: jasmine.createSpy("leaveEntity"),
	offEntityAvailable: jasmine.createSpy("offEntityAvailable"),
	offEntityLocked: jasmine.createSpy("offEntityLocked"),
	offEntityLockReleased: jasmine.createSpy("offEntityLockReleased"),
	offLockAcquired: jasmine.createSpy("offLockAcquired"),
	offConnect: jasmine.createSpy("offConnect"),
	offReconnect: jasmine.createSpy("offReconnect"),
};
// In providers:
{ provide: SocketService, useValue: mockSocketService }
```

### Syncfusion `any` Types That Cannot Be Removed

These patterns require `eslint-disable` with justification — do NOT spend time trying to type them:

| Pattern                                                        | Justification                                                  |
| -------------------------------------------------------------- | -------------------------------------------------------------- |
| `public toolbar: any = [...]`                                  | Syncfusion toolbar items accept mixed string/object types      |
| `public contextMenuItems: any = [...]`                         | Syncfusion context menu items                                  |
| `public columns: any = [...]`                                  | Column config from shared utility returns mixed types          |
| `(document...as any).ej2_instances[0]`                         | Syncfusion DOM access — no typed alternative                   |
| Event handler args (`onActionBegin`, `queryTaskbarInfo`, etc.) | Syncfusion event args have complex internal types not exported |
| `restrictPermission(project?: any)`                            | `projectDetail$` from shared store emits loosely typed data    |

**Always add `eslint-disable-next-line @typescript-eslint/no-explicit-any -- <reason>`** — never disable globally.

### Common Type Replacements

| Before                   | After                             | Import from                                                    |
| ------------------------ | --------------------------------- | -------------------------------------------------------------- |
| `assignedUsers?: any[]`  | `assignedUsers?: IAssignedUser[]` | `@shared/interfaces/assigned-user`                             |
| `attachments?: any[]`    | `attachments?: IAttachment[]`     | `@shared/models/attachments`                                   |
| `watcher?: any`          | `watcher?: unknown`               | (no import needed)                                             |
| `pageSettings: any`      | `pageSettings: PageSettingsModel` | `@syncfusion/ej2-angular-grids`                                |
| `onTaskDrop(event: any)` | `onTaskDrop(event: DragEvent)`    | (built-in) — use `event.dataTransfer?.` with optional chaining |

### MODULE_CONFIG Entity Casing

`MODULE_CONFIG.<module>.entity` uses **lowercase** (e.g., `"task"`, `"rfi"`, `"issue"`), NOT PascalCase. Tests should assert `toBe("task")` not `toBe("Task")`.

### Common Bugs Found During Stabilization

1. **Operator precedence in math:** `(duration || 1 * 8)` evaluates as `(duration || 8)` because `*` binds tighter than `||`. Fix: `((duration || 1) * 8)`
2. **Duplicate assignments:** `this.projectTask = task` at start AND end of subscribe callback — remove the duplicate
3. **Missing `takeUntilDestroyed`:** Check `filterForm.valueChanges` and `_activatedRoute.params` subscriptions — these are commonly missed
4. **Unused error parameters:** `error: (e) => { showError("msg") }` — the `e` is unused. Use `error: () => { showError("msg") }`
5. **`async` on subscribe callbacks with no `await`:** Remove the `async` keyword

### Code Simplification Patterns to Look For

1. **Repeated URL/query building in services** → Extract `buildQueryParams()` helper
2. **Duplicate `fromDto` logic across model classes** (e.g., `calculateLaggedDays`) → Extract to module-level function
3. **Long if/else-if chains for context menu actions** → Convert to `switch` statement, extract shared `basePath`
4. **Repeated filter/form data building** → Extract `buildFilterData()` helper
5. **Repeated date validation in Gantt handlers** → Extract `validateDateRange()` helper
6. **`.map()` used for side effects** → Replace with `.push(...arr.map(...))` or `if/push` pattern
7. **`.filter(...).length` for boolean check** → Replace with `.some()`
8. **`condition ? value : value` or `x ? x : fallback`** → Simplify to `x || fallback`

### SCSS Audit Patterns (Phase 3 Theming)

1. **Syncfusion overrides (`.e-*`)** — ALWAYS keep px. Do not convert to rem.
2. **Icon sizes (16px, 24px, 28px, 32px)** — Keep px. These are fixed visual sizes.
3. **Borders (1px, 2px, 4px)** — Keep px. Sub-pixel borders don't render consistently.
4. **Box-shadow** — Keep px for offset/blur/spread values.
5. **Media query breakpoints** — Keep px (e.g., `768px`).
6. **`border-radius`** — Convert to rem or use design tokens (`--radius-sm`, `--radius-md`, `--radius-lg`).
7. **Inline `style=""` in templates** — Replace with Bootstrap utility classes (`m-0`, `p-0`, `d-flex`, etc.) or move to component SCSS.
8. **Duplicate `cursor: pointer !important`** on hover — Remove from `&:hover` if base element already has it (hover inherits).
9. **Scrollbar sizes** — Keep `height`/`width` in px (browser-specific), convert `border-radius` to rem.

### Test Assertion Gotchas

- **Kanban columns:** Count the actual columns in the component before asserting (commonly 5: open, in-progress, approved, rejected, unassigned)
- **Review config entity:** Always check actual value — it's lowercase from `MODULE_CONFIG`
- **Pre-existing test failures:** 6 failures in other modules (TableComponent, PasswordComponent, FileAttachmentComponent, AttachmentCardComponent, ToastComponent, BreadcrumbsComponent) are pre-existing and NOT caused by stabilization changes
