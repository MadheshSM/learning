---
name: refactor
description: >
  Deep refactoring pass on a component or module. Analyzes first, generates a phased plan for
  user approval, then executes with parallel agents for speed. Eliminates duplication, dead code,
  inline types, console.log, any/unknown types, static strings, nested SCSS. Enforces Angular 19
  best practices, project conventions, naming standards, theme compliance, and stabilization criteria.
  Checks for component reuse, inheritance opportunities, proper try-catch placement, comment quality,
  TODO resolution, Angular pattern improvements (guards/pipes/directives), and file size limits.
  Verifies plan completion at the end with /check-module criteria.
argument-hint: <path-to-component-or-module>
---

Refactor: **$ARGUMENTS**

---

## Guiding Principles

- **Do NOT refactor blindly.** Read and understand every file before changing it.
- **Preserve behavior.** Every refactored file must produce the same runtime result.
- **Plan first, execute second.** Generate a phased plan, get user confirmation, THEN implement.
- **Verify after every phase.** Run typecheck/lint after each phase, fix all errors before proceeding.
- **Single-pass completeness.** Fix ALL issues in a file in one pass — don't plan to come back later.
- **Fix-until-clean loops.** When a check finds issues, fix and re-run. Do NOT move on with known failures.
- **Account for cascading changes.** Changing a service return type will break components — re-check downstream.

---

## STEP 1 — ANALYZE (Read-Only — No Changes)

### 1a — Read ALL files

Read every file in `$ARGUMENTS` — `.ts`, `.html`, `.scss`, `.spec.ts`. Build a dependency map.

### 1b — Collect metrics

Use **parallel agents** (subagent_type=Explore) to scan concurrently:

**Agent 1 — TypeScript Analysis:**

```bash
# File list with line counts
find $ARGUMENTS -type f -name "*.ts" -not -name "*.spec.ts" -exec wc -l {} + | sort -rn

# any/unknown count
grep -rn ": any\|: unknown\|as any\|as unknown\|<any>" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# console.log count
grep -rn "console\.\(log\|warn\|error\)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# Inline type declarations (object literals in type positions)
grep -rn "}: {\|: {[^}]*}\|<{[^}]*}>" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# Old subscription pattern
grep -rn "subscription = new Subject\|takeUntil(this.subscription)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# Missing catchError on HTTP calls (services only)
grep -rn "\.get\|\.post\|\.put\|\.delete\|\.patch" --include="*.ts" $ARGUMENTS/services/ 2>/dev/null | grep -v "catchError"

# Unused exports (check project-wide)
grep -rn "export.*function\|export.*class\|export.*interface\|export.*enum\|export.*const" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# TODO/FIXME/HACK/XXX comments — READ each to determine if actionable
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.ts" --include="*.html" --include="*.scss" $ARGUMENTS

# Duplicate services with project-management
for f in $(find $ARGUMENTS/services/ -name "*.service.ts" 2>/dev/null); do
  basename="$(basename $f)"
  found=$(find src/app/modules/project-management/services/ -name "$basename" 2>/dev/null)
  if [ -n "$found" ]; then
    echo "DUPLICATE: $basename"
  fi
done

# Comment quality — find stale, misleading, or trivial comments
grep -rn "^[[:space:]]*//" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "eslint-disable"

# Try-catch blocks — check for blind/empty catches
grep -A3 "} catch" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# Inheritance opportunities — check for repeated base patterns across components
grep -rn "extends\|implements" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# Angular pattern opportunities — custom logic that could be a pipe, directive, or guard
grep -rn "transform(\|CanActivate\|@Directive\|@Pipe" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# Unused imports, variables, functions
# (ESLint will catch most, but scan for obvious dead declarations)
grep -rn "private.*[^=]*$" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "constructor"

# eslint-disable comments — count and categorize (goal: remove ALL, fix root causes)
echo "=== ESLINT-DISABLE COMMENTS ==="
grep -rn "eslint-disable" --include="*.ts" --include="*.html" $ARGUMENTS | grep -v ".spec.ts"
echo "Total:"
grep -rn "eslint-disable" --include="*.ts" --include="*.html" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# Hardcoded format strings / locale — should use AppConstants.API_DATE_FORMAT / API_LOCALE
echo "=== HARDCODED FORMAT STRINGS ==="
grep -rn '"yyyy-MM-dd"\|"HH:mm"\|"en")' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants"

# Hardcoded mode / action strings — should use FormMode enum or CONTEXT_MENU_ACTION constant
echo "=== HARDCODED MODE/ACTION STRINGS ==="
grep -rn 'mode.*=.*"edit"\|=== "edit"\|=== "add"\|case "edit"\|case "delete"\|case "detail"\|case "update_status"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "FormMode\|CONTEXT_MENU_ACTION"
grep -rn "mode === 'edit'\|mode === 'add'" --include="*.html" $ARGUMENTS

# Hardcoded workflow status constants — should use ReviewStatus / WorkflowStatus enums from @shared/enums/review-status
echo "=== HARDCODED WORKFLOW STATUS CONSTANTS ==="
grep -rn 'WORKFLOW_STATUS_\|workflowStatus === "' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ReviewStatus\|WorkflowStatus\|getWorkflowStatus"
echo "Total:"
grep -rn 'WORKFLOW_STATUS_\|workflowStatus === "' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ReviewStatus\|WorkflowStatus\|getWorkflowStatus" | wc -l

# Hardcoded asset/icon paths — should use AppConstants.FALLBACK_DOCUMENT_ICON or shared constants
echo "=== HARDCODED ASSET PATHS ==="
grep -rn '"assets/svg/\|"assets/images/' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants\.\|FALLBACK_"
echo "Total:"
grep -rn '"assets/svg/\|"assets/images/' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants\.\|FALLBACK_" | wc -l

# Legacy Angular decorator usage — should use signal-based input()/output() (Angular 19+)
echo "=== LEGACY @Input/@Output DECORATORS ==="
grep -rn "@Input(\|@Output(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules"
echo "Total:"
grep -rn "@Input(\|@Output(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | wc -l
echo "=== SIGNAL-BASED input()/output() ALREADY USED ==="
grep -rn "= input[<.(]\|= input\.required\|= output[<.(]\|= model[<.(]" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# Legacy @ViewChild/@ViewChildren decorators — should use viewChild()/viewChildren() signals (Angular 19+)
echo "=== LEGACY @ViewChild/@ViewChildren DECORATORS ==="
grep -rn "@ViewChild(\|@ViewChildren(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules"
echo "Total:"
grep -rn "@ViewChild(\|@ViewChildren(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | wc -l
echo "=== SIGNAL-BASED viewChild()/viewChildren() ALREADY USED ==="
grep -rn "= viewChild[<.(]\|= viewChild\.required\|= viewChildren[<.(]" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# get getters that should be computed() — derived state must use computed() not get
echo "=== GET GETTERS (should be computed()) ==="
grep -rn "public get \|private get \|protected get \|	get " --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | grep -v "get()" | grep "): "
echo "Total:"
grep -rn "public get \|private get \|protected get \|	get " --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | grep -v "get()" | grep "): " | wc -l

# Hardcoded ProjectType/enum string comparisons — should use ProjectType enum from @shared/enums/project-type
echo "=== HARDCODED PROJECTTYPE STRING COMPARISONS ==="
grep -rn '=== "design"\|=== "execution"\|=== "Both"\|!== "design"\|!== "execution"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ProjectType\."
echo "Total:"
grep -rn '=== "design"\|=== "execution"\|=== "Both"\|!== "design"\|!== "execution"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ProjectType\." | wc -l
```

**Agent 2 — HTML & SCSS Analysis:**

```bash
# HTML file sizes — flag files >200 LOC
find $ARGUMENTS -type f -name "*.html" -exec wc -l {} + | sort -rn

# Static strings in HTML (not translated) — text content, labels, titles, placeholders
grep -rn ">[A-Z][a-z]" --include="*.html" $ARGUMENTS | grep -v "{{" | grep -v "translate"
grep -rn 'placeholder="[A-Za-z]' --include="*.html" $ARGUMENTS | grep -v "translate"
grep -rn 'title="[A-Za-z]' --include="*.html" $ARGUMENTS | grep -v "translate"
grep -rn 'label="[A-Za-z]' --include="*.html" $ARGUMENTS | grep -v "translate"

# Inline styles in HTML (should be in SCSS)
grep -rn 'style="' --include="*.html" $ARGUMENTS

# Security: innerHTML with translate
grep -rn "innerHTML.*translate\|bypassSecurity\|eval(\|Function(" --include="*.ts" --include="*.html" $ARGUMENTS

# Repeated HTML blocks — look for similar structural patterns that could be shared components
# (Manual review: identify blocks >10 lines that repeat across templates)

# Existing shared components that might replace custom HTML
ls src/app/shared/modules/components/ 2>/dev/null

# Check if any shared component is already imported but not used (or could replace custom markup)
grep -rn "app-common-\|app-shared-\|app-delete-modal\|app-attach-files\|app-conformation" --include="*.html" $ARGUMENTS

# SCSS file sizes — flag files >150 LOC
find $ARGUMENTS -type f -name "*.scss" -exec wc -l {} + | sort -rn

# Hardcoded hex colors in SCSS (should use theme variables)
grep -rn "#[0-9a-fA-F]\{3,8\}" --include="*.scss" $ARGUMENTS

# Static strings in SCSS (hardcoded font families, content strings)
grep -rn "content:" --include="*.scss" $ARGUMENTS
grep -rn "font-family:" --include="*.scss" $ARGUMENTS | grep -v "var(--"

# Hardcoded px values that should be rem (font-size, padding, margin, gap, border-radius)
grep -rn "font-size:.*px\|padding:.*px\|margin:.*px\|gap:.*px\|border-radius:.*px" --include="*.scss" $ARGUMENTS

# Deep SCSS nesting (3+ levels) — max 2 levels allowed
grep -rn "    &" --include="*.scss" $ARGUMENTS

# !important usage (only acceptable for Syncfusion overrides, lock states, cursor)
grep -rn "!important" --include="*.scss" $ARGUMENTS

# ::ng-deep usage (only acceptable for Syncfusion .e-* overrides)
grep -rn "::ng-deep" --include="*.scss" $ARGUMENTS

# Duplicate SCSS patterns — repeated blocks across files
# (Manual review: check for identical selectors/rules that could be extracted)

# i18n readiness — hardcoded text that blocks multi-language support
echo "=== i18n READINESS GAPS ==="
# Hardcoded text in TS (toast, confirm, alert calls with literal strings)
grep -rn "this\._toastService\.\|this\.toastService\.\|\.success(\|\.error(\|\.warning(\|\.info(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep "'[A-Z]"
# Hardcoded text in TS string assignments for UI-visible content
grep -rn "label\s*=\s*'" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "translate"
# RTL issues — hardcoded left/right in SCSS (should use logical properties start/end)
grep -rn "margin-left\|margin-right\|padding-left\|padding-right\|text-align: left\|text-align: right\|float: left\|float: right" --include="*.scss" $ARGUMENTS
# Hardcoded direction
grep -rn "direction: ltr\|direction: rtl" --include="*.scss" $ARGUMENTS
# Date/number formatting without locale pipes
grep -rn "toLocaleDateString\|toLocaleString\|toFixed\|\.format(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules"
# String concatenation for user-visible text
grep -rn "'\s*+\s*.*+\s*'" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "http\|url\|path\|query"
```

**Agent 3 — Test & Shared Resource Audit:**

```bash
# Spec files
find $ARGUMENTS -name "*.spec.ts" | sort

# Source files (non-spec, non-module, non-routing)
find $ARGUMENTS -name "*.ts" -not -name "*.spec.ts" -not -name "*.module.ts" -not -name "*-routing.module.ts" | sort

# Stub-only tests (just "should create")
grep -l "should create" --include="*.spec.ts" -r $ARGUMENTS | while read f; do
  tests=$(grep -c "it(" "$f")
  echo "$f: $tests test(s)"
done

# Check existing shared resources
ls src/app/shared/interfaces/ 2>/dev/null
ls src/app/shared/utilities/ 2>/dev/null
ls src/app/shared/utility/ 2>/dev/null
ls src/app/shared/enums/ 2>/dev/null
ls src/app/shared/modules/components/ 2>/dev/null
ls src/app/shared/constants/ 2>/dev/null
ls src/app/shared/pipes/ 2>/dev/null
ls src/app/shared/directives/ 2>/dev/null

# File size thresholds — flag oversized files
echo "=== FILES EXCEEDING SIZE LIMITS ==="
echo "--- TS components (limit: 300 LOC) ---"
find $ARGUMENTS -name "*.component.ts" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 300 ] && echo "$1: $lines lines"' _ {} \;
echo "--- TS services (limit: 250 LOC) ---"
find $ARGUMENTS -name "*.service.ts" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 250 ] && echo "$1: $lines lines"' _ {} \;
echo "--- HTML templates (limit: 200 LOC) ---"
find $ARGUMENTS -name "*.html" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 200 ] && echo "$1: $lines lines"' _ {} \;
echo "--- SCSS files (limit: 150 LOC) ---"
find $ARGUMENTS -name "*.scss" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 150 ] && echo "$1: $lines lines"' _ {} \;
echo "--- Spec files (limit: 400 LOC) ---"
find $ARGUMENTS -name "*.spec.ts" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 400 ] && echo "$1: $lines lines"' _ {} \;
echo "--- Interface files (limit: 100 LOC) ---"
find $ARGUMENTS -name "*.ts" -path "*/interfaces/*" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 100 ] && echo "$1: $lines lines"' _ {} \;

# Component reuse check — look for patterns in this module's HTML that match shared components
echo "=== COMPONENT REUSE OPPORTUNITIES ==="
# Modal dialogs
grep -rn "modal\|dialog\|popup" --include="*.html" $ARGUMENTS | grep -v "app-common-modal\|app-delete-modal\|app-conformation"
# File attachments
grep -rn "attach\|upload\|file.*input" --include="*.html" $ARGUMENTS | grep -v "app-attach-files"
# Confirmation patterns
grep -rn "confirm\|are.*sure\|yes.*no" --include="*.html" $ARGUMENTS | grep -v "app-conformation"
# Grid/table patterns
grep -rn "ejs-grid\|ejs-treegrid" --include="*.html" $ARGUMENTS

# Cross-module duplication check — similar components in other modules
for comp in $(find $ARGUMENTS/components/ -name "*.component.ts" -exec basename {} \; 2>/dev/null); do
  found=$(find src/app/modules/ -name "$comp" -not -path "$ARGUMENTS/*" 2>/dev/null)
  [ -n "$found" ] && echo "SIMILAR COMPONENT: $comp also exists at: $found"
done
```

### 1c — Reference documents

Read these for conventions (if not already in context):

- `CLAUDE.md` (root)
- `docs/plans/2026-03-02-refactor-application-stabilization-modernization-plan-deepened.md` (stabilization patterns)
- `src/theme/_variables.scss` (theme tokens)
- `src/app/shared/services/base-http.service.ts` (base service pattern)
- `src/app/shared/services/project-entity.service.ts` (cross-cutting methods)

---

## STEP 2 — GENERATE PHASED PLAN (Present to User)

Based on the analysis, generate a concrete, file-by-file plan. **Present this to the user and WAIT for confirmation before implementing.**

### Plan Format

```markdown
## Refactoring Plan: $ARGUMENTS

### Current State

| Metric                                                                                 | Count |
| -------------------------------------------------------------------------------------- | ----- |
| Total files                                                                            | X     |
| `any`/`unknown` usages                                                                 | X     |
| `console.log` calls                                                                    | X     |
| Inline type declarations                                                               | X     |
| Static strings (untranslated)                                                          | X     |
| Hardcoded hex colors (SCSS)                                                            | X     |
| Hardcoded px values (should be rem/var)                                                | X     |
| Old subscription pattern                                                               | X     |
| Missing `catchError`                                                                   | X     |
| TODO/FIXME comments (actionable)                                                       | X     |
| Duplicate services                                                                     | X     |
| Files exceeding size limits                                                            | X     |
| Stale/trivial comments                                                                 | X     |
| Blind try-catch blocks                                                                 | X     |
| Reusable shared components not used                                                    | X     |
| Repeated HTML blocks (component extraction candidates)                                 | X     |
| Inheritance opportunities                                                              | X     |
| `eslint-disable` comments (to be removed)                                              | X     |
| Hardcoded format strings (`"yyyy-MM-dd"`, `"HH:mm"`, `"en"`)                           | X     |
| Hardcoded mode/action strings (`"edit"`, `"delete"`, etc.)                             | X     |
| Legacy `@Input()`/`@Output()` decorators (should be signal-based)                      | X     |
| Legacy `@ViewChild`/`@ViewChildren` decorators (should be signal-based)                | X     |
| Hardcoded `ProjectType` string comparisons (`"design"`, `"execution"`)                 | X     |
| Hardcoded workflow status constants (should use `ReviewStatus`/`WorkflowStatus` enums) | X     |
| Hardcoded asset/icon paths (should use `AppConstants.FALLBACK_DOCUMENT_ICON` etc.)     | X     |
| i18n readiness gaps (hardcoded text, missing keys, RTL issues)                         | X     |

### Phase A — Dead Code, Cleanup, Comments & ESLint Compliance

- [ ] File: `path/to/file.ts` — remove unused imports X, Y, Z; delete dead method `foo()`
- [ ] File: `path/to/file.ts` — remove `console.log` calls on lines X, Y
- [ ] File: `path/to/file.ts` — remove stale/trivial comments (e.g., `// get data` above `getData()`)
- [ ] File: `path/to/file.ts` — remove commented-out code lines M-P
- [ ] File: `path/to/file.ts` — implement TODO on line N: "description" (or remove if no longer relevant)
- [ ] File: `path/to/file.ts` — add meaningful comments where logic is non-obvious (complex conditionals, business rules)
- [ ] **ESLint compliance** — remove ALL `eslint-disable` comments by fixing the underlying issues:
  - [ ] File: `path/to/file.ts:N` — remove `eslint-disable-next-line @typescript-eslint/no-explicit-any` → fix by typing properly
  - [ ] File: `path/to/file.ts:N` — remove `eslint-disable-next-line @typescript-eslint/no-unused-vars` → fix by removing the unused var
  - [ ] File: `path/to/file.ts:N` — remove `eslint-disable no-console` → fix by removing the console.log
  - [ ] Run `npx eslint "$ARGUMENTS/**/*.ts" "$ARGUMENTS/**/*.html"` with **zero suppressions** — all modified files must pass cleanly

### Phase B — Type Safety & Interfaces

- [ ] Create `$ARGUMENTS/interfaces/entity-name.ts` — extract inline types from `component.ts:42`, `service.ts:18`
- [ ] File: `service.ts` — replace `any` on lines X, Y with `IEntityName`
- [ ] File: `component.ts` — replace `any` on lines X, Y with proper types
- [ ] Reuse existing: `IResponse<T>`, `IUser`, `IAttachment` from `@shared/interfaces/`

### Phase C — Duplication, Component Reuse & Shared Resources

- [ ] Extract `helperFunction()` from `component.ts` → `src/app/shared/utilities/helper.util.ts` (used in 3 modules)
- [ ] Replace duplicate HTML block in `template.html:50-80` with existing `<app-shared-component>` (check `src/app/shared/modules/components/`)
- [ ] Extract repeated HTML block (lines X-Y in `a.html`, lines M-N in `b.html`) → new `<app-reusable-component>`
- [ ] Replace custom modal/dialog with existing `<app-common-modal-popup>` or `<app-delete-modal>`
- [ ] Replace custom file upload with existing `<app-attach-files>`
- [ ] Consolidate duplicate SCSS in `component.scss` with theme variables
- [ ] Check utility functions in `src/app/shared/utilities/` — reuse existing before creating new
- [ ] Check pipes in `src/app/shared/pipes/` — use existing pipe instead of custom transform logic
- [ ] Check directives in `src/app/shared/directives/` — use existing directive instead of repeated template logic

### Phase D — Angular 19 Patterns, Error Handling & Architecture

- [ ] File: `component.ts` — migrate `subscription = new Subject()` → `destroyRef = inject(DestroyRef)`
- [ ] File: `service.ts` — add `catchError(handleHttpError('ServiceName.method'))` to `getData()`
- [ ] File: `component.ts` — add loading/error/empty state handling
- [ ] File: `component.ts` — fix blind try-catch on line X: add specific error type, meaningful recovery, or remove if wrapping already-handled observable
- [ ] File: `component.ts` — extract repeated logic into base class / extend existing `BaseComponent` properly
- [ ] File: `component.ts` — replace manual transform logic with Angular pipe (existing or new)
- [ ] File: `component.ts` — replace repeated DOM manipulation with Angular directive
- [ ] File: `component.ts` — use Angular guard/resolver for route-level data loading instead of `ngOnInit` fetch
- [ ] Split oversized file `component.ts` (N LOC > 300) into smaller focused components
- [ ] **Migrate to Angular 19 signal APIs** — replace legacy `@Input()`/`@Output()` with `input()`/`output()`:
  - [ ] File: `component.ts` — `@Input() foo!: string` → `readonly foo = input.required<string>()`
  - [ ] File: `component.ts` — `@Input() bar = false` → `readonly bar = input(false)`
  - [ ] File: `component.ts` — `@Output() readonly change = new EventEmitter<T>()` → `readonly change = output<T>()`
  - [ ] Update template: `foo` → `foo()`, `bar` → `bar()` (signal reads)
  - [ ] Update specs: `component.foo = value` → `fixture.componentRef.setInput("foo", value)`
- [ ] **Migrate `@ViewChild`/`@ViewChildren` to signal-based `viewChild()`/`viewChildren()`:**
  - [ ] File: `component.ts` — `@ViewChild(ChildComponent) child!: ChildComponent` → `readonly child = viewChild.required(ChildComponent)`
  - [ ] File: `component.ts` — `@ViewChild("templateRef") el!: ElementRef` → `readonly el = viewChild.required<ElementRef>("templateRef")`
  - [ ] Remove intermediate `grid!` property if it was only set in `ngAfterViewInit` — access via `this.child().grid` directly
  - [ ] Remove `AfterViewInit` import and `implements` if `ngAfterViewInit` body was only `this.x = this.child.x`
  - [ ] Update all reads: `this.child.method()` → `this.child().method()`
- [ ] **Hardcoded `ProjectType` string comparisons** — replace `=== "design"` / `=== "execution"` with `ProjectType.Design` / `ProjectType.Execution` enum from `@shared/enums/project-type`

### Phase E — Constants, i18n Readiness & Naming

- [ ] Extract repeated string `"someValue"` → `MODULE_CONSTANTS.SOME_VALUE`
- [ ] Replace static HTML text "Submit Form" → `{{ 'MODULE.SUBMIT_FORM' | translate }}`
- [ ] Rename `res` → `response`, `e` → `error` in `component.ts`
- [ ] **Hardcoded format strings** — replace `formatDate(val, "yyyy-MM-dd", "en")` → `formatDate(val, AppConstants.API_DATE_FORMAT, AppConstants.API_LOCALE)` (and `"HH:mm"` → `AppConstants.API_TIME_FORMAT`)
- [ ] **Hardcoded mode strings** — replace `this.mode = "edit"` → `this.mode.set(FormMode.EDIT)` (use `FormMode` enum from `@shared/constants/app.constants`), convert `mode` to `signal<FormMode>()`, and derive `isLockedForEdit = computed(() => this.mode() === FormMode.EDIT && !this.canEdit())` — use `computed()` in template as `isLockedForEdit()`
- [ ] **Hardcoded context menu action strings** — replace `case "edit":` / `case "delete":` → `case CONTEXT_MENU_ACTION.edit:` (use `CONTEXT_MENU_ACTION` from `@shared/constants/app.constants`)
- [ ] **Hardcoded workflow status constants** — do NOT redeclare workflow status ID constants (e.g., `WORKFLOW_STATUS_APPROVED = "2"`); use existing `ReviewStatus` enum from `@shared/enums/review-status` with `String(ReviewStatus.Approved)` for string comparisons against `workflowStatus` fields
- [ ] **Hardcoded asset/icon paths** — replace `"assets/svg/document.svg"` → `AppConstants.FALLBACK_DOCUMENT_ICON`; check for other repeated asset paths and extract to `AppConstants` if used in 2+ files
- [ ] **i18n readiness** — ensure component is fully translatable for multi-language support:
  - [ ] All user-visible text uses `| translate` pipe (labels, headings, placeholders, titles, tooltips, button text, empty states, error messages)
  - [ ] Add missing translation keys to `src/assets/i18n/en.json` under `MODULE_NAME.*` namespace (reuse `COMMON.*` keys for shared terms)
  - [ ] No string concatenation for user-visible text in TS — use parameterized translations: `{{ 'KEY' | translate: { count: total } }}`
  - [ ] Syncfusion component text properties use translate: `[placeholder]="'KEY' | translate"`, not hardcoded strings
  - [ ] Date/number formatting uses Angular pipes (`date`, `number`, `currency`) with locale — no manual formatting like `toLocaleDateString()`
  - [ ] No hardcoded text in TS `toast`, `confirm`, or `alert` calls — use `TranslateService.instant('KEY')`
  - [ ] Check RTL readiness: no hardcoded `left`/`right` in SCSS (use `start`/`end` logical properties); no fixed `direction: ltr`
  - [ ] Check pluralization: if counts are displayed, use ICU format or conditional keys (`ITEM_COUNT_ZERO`, `ITEM_COUNT_ONE`, `ITEM_COUNT_OTHER`)

### Phase F — SCSS & Theme Compliance

- [ ] File: `component.scss` — replace `#333333` → `var(--color-text-primary)` (check `src/theme/_variables.scss` for tokens)
- [ ] File: `component.scss` — convert `font-size: 16px` → `var(--font-size-lg)` or `1rem`
- [ ] File: `component.scss` — convert hardcoded `padding/margin/gap: Xpx` → `rem` values
- [ ] File: `component.scss` — flatten 4-level nesting to 2-level max
- [ ] File: `component.scss` — move inline `style=""` from `template.html:25` to SCSS
- [ ] File: `component.scss` — justify or remove `!important` on line X (only Syncfusion overrides, lock states, cursor)
- [ ] File: `component.scss` — replace hardcoded `font-family` with theme variable
- [ ] File: `component.scss` — replace hardcoded `content: "string"` with SCSS variable or i18n approach
- [ ] File: `component.scss` — consolidate duplicate selectors/rules into shared mixin or parent selector
- [ ] File: `component.scss` — split oversized file (N LOC > 150) into partials or simplify

### Phase G — Security

- [ ] File: `template.html` — replace `[innerHTML]="value | translate"` with `{{ value | translate }}`
- [ ] File: `component.ts` — add DOMPurify to `bypassSecurityTrustHtml` call

### Phase H — Tests (if gaps exist)

- [ ] Create `service.spec.ts` — test all HTTP methods + error cases
- [ ] Improve stub-only `component.spec.ts` — add loading/error/empty state tests

### Estimated Impact

- Files changed: X
- Files created: X (interfaces, utilities, constants, components)
- Files removed: X (dead code)
- Lines removed (net): ~X
- Components extracted: X (from repeated HTML blocks)
- Shared resources reused: X (existing components/pipes/directives/utilities)
```

**ASK:** "Does this plan look good? Should I adjust the scope or priorities before proceeding?"

**WAIT for user confirmation.** Do not implement anything until they approve.

---

## STEP 3 — IMPLEMENT (Parallel Agents Where Possible)

After user approves the plan, execute using parallel agents for independent phases.

### Parallelizable Work (launch simultaneously)

These phases touch different files and can run in parallel:

| Agent                           | Work                                                                            | Files                              |
| ------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------- |
| **Agent 1: TS Cleanup**         | Phase A (dead code, comments, TODOs) + Phase B (type safety) for **services**   | `services/*.ts`, `interfaces/*.ts` |
| **Agent 2: Component Refactor** | Phase A (dead code, comments, TODOs) + Phase B (type safety) for **components** | `components/**/*.ts`               |
| **Agent 3: Template & SCSS**    | Phase C (HTML dedup, component reuse) + Phase F (SCSS theme compliance)         | `**/*.html`, `**/*.scss`           |

### Sequential Work (after parallel agents complete)

These phases depend on the parallel work being done first:

1. **Phase D — Angular Patterns & Error Handling** (depends on typed services/components)
2. **Phase E — Constants & Naming** (depends on cleaned-up code)
3. **Phase G — Security** (final pass)
4. **Phase H — Tests** (needs final code state)

### Implementation Rules

**From stabilize-module learnings:**

1. **BaseHttpService pattern (K6AQ-T81):** All module services extend `BaseHttpService` or `BaseStoreHttpService`. Built-in HTTP methods already include `catchError(handleHttpError(...))`. Only direct `this.http` calls need manual `catchError`.

2. **Cross-cutting methods:** Use `ProjectEntityService` for `getWorkflowList`, `getActivities`, `getCost`, `getAttachments`, `getHistory`, `getComments`, `addComment`, `getStatus`, `getWatcher`, `addWatcher`, `deleteWatcher`. Do NOT duplicate these in module services.

3. **Syncfusion types — properly type instead of `eslint-disable`:**
   - `public toolbar: any = [...]` → `public toolbar: ToolbarItems[] | ItemModel[]` (from `@syncfusion/ej2-angular-grids` or `@syncfusion/ej2-angular-navigations`)
   - `public contextMenuItems: any = [...]` → `public contextMenuItems: ContextMenuItem[] | ContextMenuItemModel[]`
   - `(document...as any).ej2_instances[0]` → cast to specific Syncfusion component type: `(document.getElementById('id') as HTMLElement & { ej2_instances: GridComponent[] }).ej2_instances[0]`
   - Event handler args (`onActionBegin`, `queryTaskbarInfo`, etc.) → import event arg types from Syncfusion: `ActionEventArgs`, `QueryCellInfoEventArgs`, etc.
   - **If a Syncfusion type truly does not exist** (verify in Syncfusion docs/source first), use a module-level `type` alias (e.g., `type SyncfusionToolbarItem = ...`) instead of inline `any`
   - **NEVER use `eslint-disable` to suppress `any` warnings** — always fix the root cause

4. **Common type replacements:**
   - `assignedUsers?: any[]` → `assignedUsers?: IAssignedUser[]` (from `@shared/interfaces/assigned-user`)
   - `attachments?: any[]` → `attachments?: IAttachment[]` (from `@shared/models/attachments`)
   - `pageSettings: any` → `pageSettings: PageSettingsModel` (from `@syncfusion/ej2-angular-grids`)

5. **Boolean/conditional patterns:**
   - `condition ? true : false` → `condition` (or `!!condition`)
   - `value === true` → `value`, `value === false` → `!value`
   - `.filter(...).length` for boolean check → `.some()`

6. **SCSS audit rules (from theming plan):**

   | Convert to `rem`                          | Keep in `px`                         |
   | ----------------------------------------- | ------------------------------------ |
   | `font-size`, `padding`, `margin`, `gap`   | `border` / `border-width` (1px, 2px) |
   | `width`/`height` on layout containers     | `box-shadow` offset/blur/spread      |
   | `border-radius`                           | Icon sizes (16px, 24px, 28px, 32px)  |
   | `min-height` / `max-height` on containers | Syncfusion `.e-*` overrides          |

   **Design tokens:**
   - `border-radius: 8px` → `var(--radius-lg)`, `6px` → `var(--radius-md)`, `4px` → `var(--radius-sm)`
   - `font-size: 16px` → `var(--font-size-lg)`, `14px` → `var(--font-size-body)`, `13px` → `var(--font-size-sm)`, `12px` → `var(--font-size-xs)`

   **`::ng-deep` acceptable ONLY** for Syncfusion `.e-*` overrides. Flag all other usage.

   **`!important` acceptable** for: Syncfusion overrides, entity lock/disabled states, cursor on interactive elements.

7. **Common bugs to watch for:**
   - `(duration || 1 * 8)` → `((duration || 1) * 8)` (operator precedence)
   - Duplicate assignments in subscribe callbacks
   - Missing `takeUntilDestroyed` on `filterForm.valueChanges` and `_activatedRoute.params`
   - `async` on subscribe callbacks with no `await` — remove the `async`

8. **Comment rules:**
   - **Remove:** trivial comments that restate the code (e.g., `// increment counter` above `counter++`)
   - **Remove:** commented-out code blocks — they belong in git history, not the codebase
   - **Remove:** stale TODOs that reference completed work or no longer apply
   - **Add:** comments for non-obvious business logic, complex conditionals, workarounds, and "why" explanations
   - **Implement or remove:** actionable TODOs — read each one, determine if it's still relevant, implement if needed, remove if not
   - **Never:** add JSDoc-style comments to every method — only where the name and signature aren't self-explanatory

9. **Try-catch rules (do NOT add blindly):**
   - **Observable streams:** Do NOT wrap `.subscribe()` in try-catch. Use `catchError` in the pipe chain instead.
   - **HTTP calls in services:** Already handled by `BaseHttpService.catchError(handleHttpError(...))`. Only add try-catch for non-HTTP async operations (file reads, JSON.parse, localStorage access).
   - **Empty catch blocks:** Always handle or log. Never `catch (e) {}`.
   - **Re-throw when appropriate:** If catching to add context, re-throw the original error.
   - **Component `ngOnInit`:** Do NOT wrap entire init in try-catch. Let Angular's error handler handle unexpected failures.

10. **Inheritance & composition rules:**
    - Components SHOULD extend `BaseComponent` if they need `projectId`, `_store`, `_router`, etc.
    - If 3+ components share identical logic (same fields + methods), extract a shared base class.
    - Prefer composition (injected services) over inheritance when only sharing behavior, not state.
    - Do NOT create deep inheritance hierarchies (max 2 levels: `BaseComponent` → `FeatureBaseComponent` → `ConcreteComponent`).

11. **Component extraction rules (for repeated HTML blocks):**
    - If the same HTML block (>10 lines) appears in 2+ templates, extract to a shared component.
    - If a component template exceeds 200 LOC, look for logical sections that can be child components.
    - New shared components go in `src/app/shared/modules/components/` if used across modules.
    - New module-local components go in the module's `components/` directory if only used within the module.
    - Use `@Input()` / `@Output()` for data flow — do NOT share state via services for presentational components.

12. **File size limits (flag and split if exceeded):**

    | File type         | Soft limit | Hard limit | Action                                                  |
    | ----------------- | ---------- | ---------- | ------------------------------------------------------- |
    | `.component.ts`   | 250 LOC    | 300 LOC    | Split into child components or extract logic to service |
    | `.service.ts`     | 200 LOC    | 250 LOC    | Split by responsibility into multiple services          |
    | `.html`           | 150 LOC    | 200 LOC    | Extract child components or use `ng-template`           |
    | `.scss`           | 100 LOC    | 150 LOC    | Extract shared styles to mixins, simplify selectors     |
    | `.spec.ts`        | 300 LOC    | 400 LOC    | Use `describe` blocks, extract test helpers             |
    | `interfaces/*.ts` | 80 LOC     | 100 LOC    | Split by entity into separate files                     |

13. **Angular pattern opportunities (check before custom code):**
    - Repeated template transforms → create/reuse a **Pipe** (`src/app/shared/pipes/`)
    - Repeated DOM behavior (show/hide, focus, tooltip) → create/reuse a **Directive** (`src/app/shared/directives/`)
    - Route-level data fetching in `ngOnInit` → consider a **Resolver** on the route
    - Route-level access checks in component → use existing **Guards** (`@core/guards/`)
    - Repeated string formatting logic in templates → **Pipe** instead of component method (avoids change detection overhead)

14. **i18n / Internationalization readiness rules:**

    The app uses `@ngx-translate/core` with 4 languages: `en`, `ko`, `ms`, `ar` (RTL). Translation files live in `src/assets/i18n/<lang>.json`. `LanguageService` (`@services/language.service.ts`) manages language state.

    **Key namespace convention:** `MODULE_NAME.KEY_NAME` (e.g., `TASK.STATUS_LABEL`). Reuse `COMMON.*` keys for shared terms (`COMMON.SAVE`, `COMMON.CANCEL`, etc.) — check `src/assets/i18n/en.json` before creating duplicates.

    **HTML templates:**
    - Text content: `{{ 'MODULE.KEY' | translate }}` — NEVER hardcode user-visible strings
    - Attributes: `[placeholder]="'MODULE.PLACEHOLDER' | translate"`, `[title]="'MODULE.TOOLTIP' | translate"`
    - Syncfusion properties: `[placeholder]="'MODULE.KEY' | translate"` for dropdowns, inputs, grids
    - **XSS rule (from CLAUDE.md):** NEVER use `[innerHTML]` with `| translate`. Use interpolation `{{ }}` or attribute binding

    **TypeScript:**
    - Inject `TranslateService` and use `this.translateService.instant('KEY')` for toast/confirm/alert messages
    - No string concatenation for UI text — use parameterized translations: `this.translateService.instant('KEY', { name: value })`
    - Date/number formatting: use Angular `DatePipe`, `DecimalPipe`, `CurrencyPipe` (locale-aware) — never `toLocaleDateString()` or `toFixed()`

    **SCSS / RTL support (Arabic):**
    - Replace `margin-left` / `margin-right` → `margin-inline-start` / `margin-inline-end`
    - Replace `padding-left` / `padding-right` → `padding-inline-start` / `padding-inline-end`
    - Replace `text-align: left` → `text-align: start`, `text-align: right` → `text-align: end`
    - Replace `float: left` / `float: right` → `float: inline-start` / `float: inline-end` (or use flexbox)
    - Never hardcode `direction: ltr` — `LanguageService.updateDocumentLanguage()` handles this via `<html lang>`
    - Use `gap` + flexbox/grid instead of directional margins where possible

    **Translation key file updates:**
    - Only add keys to `en.json` during refactoring — other language files (`ko.json`, `ms.json`, `ar.json`) get translated separately
    - Group keys under the module namespace: `"MODULE_NAME": { "KEY": "Value" }`
    - Prefix with `COMMON.` only if the key is truly shared across 3+ modules

15. **Shared constants — eliminate hardcoded strings in TS and templates:**

    **Date/time format strings (`@shared/constants/app.constants`):**
    - `"yyyy-MM-dd"` → `AppConstants.API_DATE_FORMAT`
    - `"HH:mm"` → `AppConstants.API_TIME_FORMAT`
    - `"en"` locale arg → `AppConstants.API_LOCALE`
    - Example: `formatDate(val, "yyyy-MM-dd", "en")` → `formatDate(val, AppConstants.API_DATE_FORMAT, AppConstants.API_LOCALE)`

    **Form mode strings (`FormMode` const enum from `@shared/constants/app.constants`):**
    - `this.mode = "edit"` → `this.mode = FormMode.EDIT`
    - `this.mode = "add"` → `this.mode = FormMode.ADD`
    - `mode?: string` → `mode?: FormMode`
    - **Templates cannot reference const enums.** Instead of `mode === 'edit' && !canEdit` repeated 10+ times, convert `mode`/`canEdit` to `signal()` and derive: `isLockedForEdit = computed(() => this.mode() === FormMode.EDIT && !this.canEdit())`. Use `isLockedForEdit()` in template. **NEVER use `get` getters** — always use `computed()` for derived state (Angular 19 best practice).

    **Context menu action strings (`CONTEXT_MENU_ACTION` from `@shared/constants/app.constants`):**
    - `case "edit":` → `case CONTEXT_MENU_ACTION.edit:`
    - `case "delete":` → `case CONTEXT_MENU_ACTION.delete:`
    - `case "detail":` → `case CONTEXT_MENU_ACTION.detail:`
    - `case "update_status":` → `case CONTEXT_MENU_ACTION.updateStatus:`
    - `it.id === "delete"` → `it.id === CONTEXT_MENU_ACTION.delete`

    **Workflow status constants — reuse existing enums, do NOT redeclare:**
    - `ReviewStatus` enum (`@shared/enums/review-status`): `Approved = 2`, `Rejected = 3` — numeric comparison against `item.reviewStatus`
    - For string comparison against `item.workflowStatus` (API returns `"2"`, `"3"`): use `String(ReviewStatus.Approved)` / `String(ReviewStatus.Rejected)`
    - `WorkflowStatus` enum (`@shared/enums/review-status`): `Approved = "Approved"`, `Rejected = "Rejected"` — for status name comparisons
    - **NEVER** redeclare constants like `WORKFLOW_STATUS_APPROVED = "2"` — these duplicate `ReviewStatus` values

    **Fallback asset paths (`AppConstants` from `@shared/constants/app.constants`):**
    - `"assets/svg/document.svg"` → `AppConstants.FALLBACK_DOCUMENT_ICON`
    - Any asset path used in 2+ files should be extracted to `AppConstants` (e.g., `FALLBACK_FOLDER_ICON`, `FALLBACK_AVATAR`)

16. **Angular 19 signal APIs — use for ALL new and refactored code:**

    **Component inputs/outputs (child components):**
    - `@Input()` → `input()` / `input.required()` / `input<Type>(defaultValue)`
    - `@Output()` → `output()` / `output<Type>()`
    - Two-way bindings `[(prop)]` work with signal `output()` the same as `EventEmitter`

    **Local component state:**
    - `isLocked = false` → `isLocked = signal(false)` — use `signal()` for mutable local state
    - `mode?: string` → `mode = signal<FormMode | undefined>(undefined)`
    - Assign via `.set()`: `this.isLocked.set(true)` not `this.isLocked = true`

    **Derived state — ALWAYS use `computed()`, NEVER use `get` getters:**
    - `get isLockedForEdit(): boolean { ... }` → `isLockedForEdit = computed(() => this.mode() === FormMode.EDIT && !this.canEdit())`
    - `computed()` auto-tracks signal dependencies, is memoized, and integrates with Angular's change detection
    - Read in templates with `()`: `isLockedForEdit()` not `isLockedForEdit`

    **Templates:**
    - Read ALL signals with `()`: `isDisabled()`, `isLocked()`, `lockedBy()?.firstName`
    - Signal reads inside `@if`, `[ngClass]`, `[class.x]`, property bindings all use `()`

    **Specs:**
    - Set signal inputs via `fixture.componentRef.setInput("name", value)` not direct assignment
    - Read signal values via `component.mySignal()` not `component.mySignal`

### Per-Phase Verification Gate

After EACH phase, run:

```bash
npm run typecheck
```

Fix ALL errors before moving to next phase. If type changes cascade (service → component), fix downstream immediately.

---

## STEP 4 — VERIFY IMPLEMENTATION (Run /check-module Criteria)

After all phases complete, verify against the **29-point stabilization checklist**:

### Verification Agents (run in parallel)

**Agent 1 — Code Quality Checks:**

```bash
# 1. Zero any (no eslint-disable workarounds — must be properly typed)
grep -rn ": any\|<any\|as any\| any;\| any)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# 2. Zero console.log
grep -rn "console\.\(log\|warn\|error\)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# 3. Service catchError coverage (for direct this.http calls)
grep -rn "this\.http\.\(get\|post\|put\|delete\|patch\)" --include="*.ts" $ARGUMENTS/services/ 2>/dev/null | grep -v "catchError"

# 4. handleHttpError re-throws original (not transforms)
grep -A2 "handleHttpError" --include="*.ts" $ARGUMENTS/services/ 2>/dev/null

# 5. Component loading/error/empty states
for comp in $(find $ARGUMENTS/components/ -name "*.component.ts" 2>/dev/null); do
  echo "=== $(basename $comp) ==="
  echo "loading: $(grep -c 'loading' $comp)"
  echo "error: $(grep -c 'error\|catch' $comp)"
done

# 6. takeUntilDestroyed pattern
grep -rn "destroyRef.*inject(DestroyRef)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"
grep -rn "takeUntil(this.subscription)" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# 7. No duplicate services
for f in $(find $ARGUMENTS/services/ -name "*.service.ts" 2>/dev/null); do
  basename="$(basename $f)"
  found=$(find src/app/modules/project-management/services/ -name "$basename" 2>/dev/null)
  [ -n "$found" ] && echo "DUPLICATE: $basename"
done
```

**Agent 2 — Build & Lint Checks:**

```bash
# 8. Format
npx prettier --write "$ARGUMENTS/**/*.ts" "$ARGUMENTS/**/*.html" "$ARGUMENTS/**/*.scss"
npx prettier --check "$ARGUMENTS/**/*.ts" "$ARGUMENTS/**/*.html" "$ARGUMENTS/**/*.scss"

# 9. Lint TS + HTML
npx eslint "$ARGUMENTS/**/*.ts" --quiet --fix
npx eslint "$ARGUMENTS/**/*.html" --quiet --fix

# 10. Stylelint SCSS
npx stylelint "$ARGUMENTS/**/*.scss" --fix
npx stylelint "$ARGUMENTS/**/*.scss"

# 11. Typecheck
npm run typecheck

# 12. Production build
npm run build:prod
```

**Agent 3 — Test Checks:**

```bash
# 13. Test files exist for services + key components
echo "Source files:"
find $ARGUMENTS -name "*.ts" -not -name "*.spec.ts" -not -name "*.module.ts" -not -name "*-routing.module.ts" | wc -l
echo "Spec files:"
find $ARGUMENTS -name "*.spec.ts" | wc -l

# 14. Tests are meaningful (not just "should create")
grep -l "should create" --include="*.spec.ts" -r $ARGUMENTS | while read f; do
  tests=$(grep -c "it(" "$f")
  echo "$f: $tests test(s)"
done

# 15. Tests pass
npm run test -- --no-watch
```

**Agent 4 — Extended Quality Checks (criteria 13-22):**

```bash
# 13. No inline type declarations (all named interfaces)
echo "=== INLINE TYPE DECLARATIONS ==="
grep -rn "}: {\|: {[^}]*}\|<{[^}]*}>" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "eslint-disable"

# 14. No stale/trivial comments; meaningful comments where needed
echo "=== COMMENTED-OUT CODE ==="
grep -rn "^[[:space:]]*//.*=\|^[[:space:]]*//.*(\|^[[:space:]]*//.*{" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "eslint-disable"

# 15. All TODOs resolved or removed
echo "=== REMAINING TODOs ==="
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.ts" --include="*.html" --include="*.scss" $ARGUMENTS | grep -v ".spec.ts"

# 16. No blind try-catch blocks (empty or generic catches)
echo "=== BLIND TRY-CATCH ==="
grep -B1 -A3 "} catch" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts"

# 17. All files within size limits
echo "=== FILES EXCEEDING SIZE LIMITS ==="
find $ARGUMENTS -name "*.component.ts" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 300 ] && echo "FAIL: $1: $lines lines (limit: 300)"' _ {} \;
find $ARGUMENTS -name "*.service.ts" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 250 ] && echo "FAIL: $1: $lines lines (limit: 250)"' _ {} \;
find $ARGUMENTS -name "*.html" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 200 ] && echo "FAIL: $1: $lines lines (limit: 200)"' _ {} \;
find $ARGUMENTS -name "*.scss" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 150 ] && echo "FAIL: $1: $lines lines (limit: 150)"' _ {} \;

# 18. No static strings in HTML/SCSS
echo "=== STATIC STRINGS IN HTML ==="
grep -rn ">[A-Z][a-z]" --include="*.html" $ARGUMENTS | grep -v "{{" | grep -v "translate" | grep -v "\.ts:" | head -20
grep -rn 'placeholder="[A-Za-z]' --include="*.html" $ARGUMENTS | grep -v "translate" | head -10

# 19. SCSS uses theme variables (no hardcoded colors/px)
echo "=== HARDCODED COLORS ==="
grep -rn "#[0-9a-fA-F]\{3,8\}" --include="*.scss" $ARGUMENTS
echo "=== HARDCODED PX (should be rem/var) ==="
grep -rn "font-size:.*px\|padding:.*[0-9]px\|margin:.*[0-9]px\|gap:.*px\|border-radius:.*px" --include="*.scss" $ARGUMENTS | grep -v "1px\|2px" | grep -v "\.e-"

# 20. Shared components/pipes/directives reused where applicable
echo "=== COMPONENT REUSE ==="
grep -rn "modal\|dialog\|popup" --include="*.html" $ARGUMENTS | grep -v "app-common-modal\|app-delete-modal\|app-conformation" | head -10
grep -rn "attach\|upload\|file.*input" --include="*.html" $ARGUMENTS | grep -v "app-attach-files" | head -10

# 21. i18n ready: all text translated, RTL-safe SCSS, locale-aware formatting
echo "=== i18n READINESS ==="
echo "--- Hardcoded text in HTML (not translated) ---"
grep -rn ">[A-Z][a-z]" --include="*.html" $ARGUMENTS | grep -v "{{" | grep -v "translate" | grep -v "\.ts:" | head -20
grep -rn 'placeholder="[A-Za-z]' --include="*.html" $ARGUMENTS | grep -v "translate" | head -10
echo "--- Hardcoded text in TS (toast/confirm/alert with literal strings) ---"
grep -rn "this\._toastService\.\|\.success(\|\.error(\|\.warning(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep "'[A-Z]" | head -10
echo "--- RTL-unsafe SCSS (hardcoded left/right) ---"
grep -rn "margin-left\|margin-right\|padding-left\|padding-right\|text-align: left\|text-align: right\|float: left\|float: right" --include="*.scss" $ARGUMENTS | head -10
echo "--- Manual date/number formatting (should use Angular locale pipes) ---"
grep -rn "toLocaleDateString\|toLocaleString\|toFixed\|\.format(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | head -10

# 22. Zero eslint-disable comments — all lint issues fixed at root cause
echo "=== ESLINT-DISABLE COMMENTS (must be zero) ==="
grep -rn "eslint-disable" --include="*.ts" --include="*.html" $ARGUMENTS | grep -v ".spec.ts"
echo "Total eslint-disable count:"
grep -rn "eslint-disable" --include="*.ts" --include="*.html" $ARGUMENTS | grep -v ".spec.ts" | wc -l

# 23. Zero hardcoded format/locale strings — must use AppConstants
echo "=== HARDCODED FORMAT STRINGS (must be zero) ==="
grep -rn '"yyyy-MM-dd"\|"HH:mm"\|, "en")' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants"
echo "Total:"
grep -rn '"yyyy-MM-dd"\|"HH:mm"\|, "en")' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants" | wc -l

# 24. Zero hardcoded mode/action strings — must use FormMode / CONTEXT_MENU_ACTION
echo "=== HARDCODED MODE/ACTION STRINGS (must be zero) ==="
grep -rn 'mode.*=.*"edit"\|=== "edit"\|case "edit"\|case "delete"\|case "detail"\|case "update_status"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "FormMode\|CONTEXT_MENU_ACTION"
grep -rn "mode === 'edit'\|mode === 'add'" --include="*.html" $ARGUMENTS
echo "Total:"
grep -rn 'mode.*=.*"edit"\|=== "edit"\|case "edit"\|case "delete"\|case "detail"\|case "update_status"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "FormMode\|CONTEXT_MENU_ACTION" | wc -l

# 25. Zero legacy @Input()/@Output() decorators — must use signal-based input()/output()
echo "=== LEGACY @Input/@Output DECORATORS (must be zero) ==="
grep -rn "@Input(\|@Output(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules"
echo "Total:"
grep -rn "@Input(\|@Output(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | wc -l

# 26. Zero legacy @ViewChild/@ViewChildren decorators — must use signal-based viewChild()/viewChildren()
echo "=== LEGACY @ViewChild/@ViewChildren DECORATORS (must be zero) ==="
grep -rn "@ViewChild(\|@ViewChildren(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules"
echo "Total:"
grep -rn "@ViewChild(\|@ViewChildren(" --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "node_modules" | wc -l

# 27. Zero hardcoded ProjectType string comparisons — must use ProjectType enum
echo "=== HARDCODED PROJECTTYPE STRINGS (must be zero) ==="
grep -rn '=== "design"\|=== "execution"\|=== "Both"\|!== "design"\|!== "execution"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ProjectType\."
echo "Total:"
grep -rn '=== "design"\|=== "execution"\|=== "Both"\|!== "design"\|!== "execution"' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ProjectType\." | wc -l

# 28. Zero hardcoded workflow status constants — must use ReviewStatus/WorkflowStatus enums
echo "=== HARDCODED WORKFLOW STATUS CONSTANTS (must be zero) ==="
grep -rn 'WORKFLOW_STATUS_\|workflowStatus === "' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ReviewStatus\|WorkflowStatus\|getWorkflowStatus"
echo "Total:"
grep -rn 'WORKFLOW_STATUS_\|workflowStatus === "' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "ReviewStatus\|WorkflowStatus\|getWorkflowStatus" | wc -l

# 27. Zero hardcoded asset/icon paths — must use AppConstants.FALLBACK_DOCUMENT_ICON etc.
echo "=== HARDCODED ASSET PATHS (must be zero) ==="
grep -rn '"assets/svg/\|"assets/images/' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants\.\|FALLBACK_"
echo "Total:"
grep -rn '"assets/svg/\|"assets/images/' --include="*.ts" $ARGUMENTS | grep -v ".spec.ts" | grep -v "AppConstants\.\|FALLBACK_" | wc -l

# Mandatory lint pass on all modified files (no --quiet, catch warnings too)
echo "=== MANDATORY ESLINT (must pass with zero errors AND zero warnings) ==="
npx eslint "$ARGUMENTS/**/*.ts" "$ARGUMENTS/**/*.html" --max-warnings 0
```

---

## STEP 5 — RUN /simplify

After all verification passes, invoke the `/simplify` skill on modified files:

```
Use the Skill tool: skill="simplify"
This reviews changed code for reuse, quality, and efficiency, then fixes any issues found.
```

After simplifier completes, re-run format + lint + typecheck to catch any issues it introduced.

---

## STEP 6 — COMPLETION REPORT

### Plan Verification Matrix

Compare original plan items against final state:

```markdown
## Refactoring Report: $ARGUMENTS

### Plan Completion

| Phase                                                  | Planned Items | Completed | Skipped (with reason) |
| ------------------------------------------------------ | ------------- | --------- | --------------------- |
| A — Dead Code, Cleanup, Comments & ESLint              | X             | X         | 0                     |
| B — Type Safety & Interfaces                           | X             | X         | 0                     |
| C — Duplication, Component Reuse & Shared Resources    | X             | X         | 0                     |
| D — Angular 19 Patterns, Error Handling & Architecture | X             | X         | 0                     |
| E — Constants, i18n & Naming                           | X             | X         | 0                     |
| F — SCSS & Theme Compliance                            | X             | X         | 0                     |
| G — Security                                           | X             | X         | 0                     |
| H — Tests                                              | X             | X         | 0                     |

### Metrics Before → After

| Metric                                         | Before | After |
| ---------------------------------------------- | ------ | ----- |
| `any`/`unknown` count                          | X      | 0     |
| `console.log` calls                            | X      | 0     |
| Inline type declarations                       | X      | 0     |
| Static strings (untranslated)                  | X      | 0     |
| Hardcoded hex colors                           | X      | 0     |
| Hardcoded px values (should be rem/var)        | X      | 0     |
| Old subscription pattern                       | X      | 0     |
| Dead code (lines removed)                      | —      | ~X    |
| SCSS nesting depth (max)                       | X      | ≤2    |
| Stale/trivial comments removed                 | —      | X     |
| TODOs resolved/removed                         | X      | 0     |
| Blind try-catch blocks                         | X      | 0     |
| Files exceeding size limits                    | X      | 0     |
| Shared components reused                       | —      | X     |
| Components extracted                           | —      | X     |
| `eslint-disable` comments                      | X      | 0     |
| Hardcoded format/locale strings                | X      | 0     |
| Hardcoded mode/action strings                  | X      | 0     |
| Legacy `@Input()`/`@Output()` decorators       | X      | 0     |
| Legacy `@ViewChild`/`@ViewChildren` decorators | X      | 0     |
| Hardcoded `ProjectType` string comparisons     | X      | 0     |
| Hardcoded workflow status constants            | X      | 0     |
| Hardcoded asset/icon paths                     | X      | 0     |
| i18n gaps (hardcoded text, RTL issues)         | X      | 0     |

### Stabilization Checklist (29 Criteria)

| #   | Criterion                                                                                   | Status    |
| --- | ------------------------------------------------------------------------------------------- | --------- |
| 1   | Zero `any` (properly typed — no `eslint-disable` workarounds)                               | PASS/FAIL |
| 2   | Service `catchError` on all HTTP calls                                                      | PASS/FAIL |
| 3   | `handleHttpError` re-throws original `HttpErrorResponse`                                    | PASS/FAIL |
| 4   | Component loading/error/empty states                                                        | PASS/FAIL |
| 5   | `takeUntilDestroyed(this.destroyRef)` pattern                                               | PASS/FAIL |
| 6   | No duplicate services (vs project-management)                                               | PASS/FAIL |
| 7   | Test files for services + key components                                                    | PASS/FAIL |
| 8   | Tests are meaningful (not just "should create")                                             | PASS/FAIL |
| 9   | No `console.log` calls                                                                      | PASS/FAIL |
| 10  | Typecheck passes                                                                            | PASS/FAIL |
| 11  | Lint passes (ESLint + Stylelint)                                                            | PASS/FAIL |
| 12  | Tests pass                                                                                  | PASS/FAIL |
| 13  | No inline type declarations (all named interfaces)                                          | PASS/FAIL |
| 14  | No stale/trivial comments; meaningful comments where needed                                 | PASS/FAIL |
| 15  | All TODOs resolved or removed                                                               | PASS/FAIL |
| 16  | No blind try-catch blocks                                                                   | PASS/FAIL |
| 17  | All files within size limits                                                                | PASS/FAIL |
| 18  | No static strings in HTML/SCSS (translated or constant)                                     | PASS/FAIL |
| 19  | SCSS uses theme variables (no hardcoded colors/px where rem/var applies)                    | PASS/FAIL |
| 20  | Shared components/pipes/directives reused where applicable                                  | PASS/FAIL |
| 21  | i18n ready: all text translated, RTL-safe SCSS, locale-aware formatting                     | PASS/FAIL |
| 22  | Zero `eslint-disable` comments — all lint issues fixed at the root cause                    | PASS/FAIL |
| 23  | Zero hardcoded format/locale strings — uses `AppConstants.API_DATE_FORMAT` / `API_LOCALE`   | PASS/FAIL |
| 24  | Zero hardcoded mode/action strings — uses `FormMode` / `CONTEXT_MENU_ACTION` constants      | PASS/FAIL |
| 25  | Zero legacy `@Input()`/`@Output()` — uses signal-based `input()`/`output()`                 | PASS/FAIL |
| 26  | Zero legacy `@ViewChild`/`@ViewChildren` — uses signal-based `viewChild()`/`viewChildren()` | PASS/FAIL |
| 27  | Zero hardcoded `ProjectType` string comparisons — uses `ProjectType` enum                   | PASS/FAIL |
| 28  | Zero hardcoded workflow status constants — uses `ReviewStatus`/`WorkflowStatus` enums       | PASS/FAIL |
| 27  | Zero hardcoded asset/icon paths — uses `AppConstants.FALLBACK_DOCUMENT_ICON` etc.           | PASS/FAIL |

**Overall: X/29 criteria passed**

### Files Changed

- `path/to/file.ts` — description

### Files Created

- `path/to/interface.ts` — extracted interfaces

### Files Removed

- `path/to/dead-file.ts` — unused

### Build Status

- Prettier: ✓/✗
- ESLint: ✓/✗
- Stylelint: ✓/✗
- Typecheck: ✓/✗
- Production Build: ✓/✗
- Tests: ✓/✗

### Remaining Work (if any)

- [ ] Item that could not be completed and why
```

If all 29 criteria pass and the build is green, the refactoring is **COMPLETE**.
If any fail, list specific remaining work items.

---

## Learnings (from stabilize-module runs)

### SocketService Mocking

Components injecting `SocketService` need a full mock in tests — see `stabilize-module` SKILL.md "Learnings" section for the mock object.

### Test Assertion Gotchas

- `MODULE_CONFIG.<module>.entity` uses **lowercase** (e.g., `"task"` not `"Task"`)
- Pre-existing test failures in other modules (TableComponent, PasswordComponent, etc.) are NOT caused by this refactoring

### Code Simplification Patterns

- Repeated URL/query building → extract `buildQueryParams()` helper
- Long if/else-if chains for context menu → convert to `switch`, extract shared `basePath`
- `.map()` used for side effects → replace with `.push(...arr.map(...))` or `if/push`
- `condition ? value : value` → simplify to `value`
- `x ? x : fallback` → `x || fallback`
