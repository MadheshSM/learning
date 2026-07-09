---
name: check-module
description: >
  Verify a stabilized module against the "Done" criteria from the stabilization plan.
  Reports pass/fail for each criterion with evidence.
argument-hint: <module-name>
---

Check the stabilization status of: **$ARGUMENTS**

## Reference Plan

Read the stabilization plan for the full "Done" definition:
`docs/plans/2026-03-02-refactor-application-stabilization-modernization-plan-deepened.md`

## Step 1 — Locate Module Files

```bash
# Find the module directory
ls src/app/modules/$ARGUMENTS/

# List all TypeScript files (excluding specs)
find src/app/modules/$ARGUMENTS/ -name "*.ts" -not -name "*.spec.ts" | sort

# List all spec files
find src/app/modules/$ARGUMENTS/ -name "*.spec.ts" | sort
```

## Step 2 — Check: Zero `any`

```bash
# Count any usages (excluding specs and eslint-disable lines)
grep -rn "any" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v node_modules | grep -v ".spec.ts" | grep -v "eslint-disable"
```

**Pass criteria:** Zero matches, OR every match has a justified `eslint-disable` comment on the preceding line.

**Report format:**

- Total `any` count
- List each remaining `any` with file:line
- Flag unjustified ones as FAIL

## Step 3 — Check: Service Error Handling

For each service in `src/app/modules/$ARGUMENTS/services/`:

1. Every HTTP call (`.get()`, `.post()`, `.put()`, `.delete()`, `.patch()`) must have `.pipe(catchError(handleHttpError('ServiceName.methodName')))`
2. `handleHttpError` must re-throw the original `HttpErrorResponse` (NOT transform it)
3. Verify import: `import { handleHttpError } from '@shared/utilities/error-handler.util';`
4. No `public data: any = []` accumulators

```bash
# Find HTTP calls without catchError
grep -n "\.get\|\.post\|\.put\|\.delete\|\.patch" --include="*.ts" src/app/modules/$ARGUMENTS/services/ | grep -v "catchError"
```

**Pass criteria:** Every HTTP call has `catchError(handleHttpError(...))`.

## Step 4 — Check: Component Loading/Error/Empty States

For each component in `src/app/modules/$ARGUMENTS/components/`:

1. Has a `loading` boolean or similar loading state
2. Has error handling (try/catch, or `.subscribe({ error: ... })`)
3. Template handles empty data (e.g., `*ngIf="items.length === 0"` or empty state component)

```bash
# Check for loading state
grep -rn "loading" --include="*.ts" src/app/modules/$ARGUMENTS/components/

# Check for error handling
grep -rn "error\|catch\|handleError" --include="*.ts" src/app/modules/$ARGUMENTS/components/

# Check for console.log (should be removed)
grep -rn "console.log" --include="*.ts" src/app/modules/$ARGUMENTS/components/
```

**Pass criteria:** Each component handles loading, error, and empty states. No `console.log` calls.

## Step 5 — Check: Subscription Teardown

All long-lived subscriptions must use `takeUntilDestroyed(this.destroyRef)` with `DestroyRef` captured as a **field initializer** (not in constructor body or ngOnInit).

```bash
# Check for DestroyRef field initializer pattern
grep -rn "destroyRef" --include="*.ts" src/app/modules/$ARGUMENTS/

# Check for old takeUntil(this.subscription) pattern (should be migrated)
grep -rn "takeUntil" --include="*.ts" src/app/modules/$ARGUMENTS/

# Check for manual subscribe without takeUntilDestroyed
grep -rn "\.subscribe(" --include="*.ts" src/app/modules/$ARGUMENTS/components/ | grep -v ".spec.ts"
```

**Pass criteria:**

- `private destroyRef = inject(DestroyRef);` as field initializer in every component with subscriptions
- `takeUntilDestroyed(this.destroyRef)` on every long-lived subscription
- No old `takeUntil(this.subscription)` pattern remaining

## Step 6 — Check: No Duplicate Services

```bash
# Check if any service from this module also exists in project-management
for f in $(find src/app/modules/$ARGUMENTS/services/ -name "*.service.ts" 2>/dev/null); do
  basename="$(basename $f)"
  found=$(find src/app/modules/project-management/services/ -name "$basename" 2>/dev/null)
  if [ -n "$found" ]; then
    echo "DUPLICATE: $basename exists in both $ARGUMENTS and project-management"
  fi
done
```

**Pass criteria:** No duplicate services. If duplicates exist, one must be deleted and all imports consolidated.

## Step 7 — Check: Test Coverage

```bash
# Count spec files vs source files
echo "Source files:"
find src/app/modules/$ARGUMENTS/ -name "*.ts" -not -name "*.spec.ts" -not -name "*.module.ts" -not -name "*-routing.module.ts" | wc -l

echo "Spec files:"
find src/app/modules/$ARGUMENTS/ -name "*.spec.ts" | wc -l

# Check if specs are meaningful (not just "should create")
grep -l "should create" --include="*.spec.ts" -r src/app/modules/$ARGUMENTS/ | while read f; do
  lines=$(wc -l < "$f")
  tests=$(grep -c "it(" "$f")
  echo "$f: $lines lines, $tests test(s)"
done
```

**Pass criteria:**

- Every service has a spec file with tests for all HTTP methods + error cases
- Every key component has a spec file with tests for creation, data loading, interactions
- 80%+ coverage (run `npm run test` with coverage to verify)
- No spec files that only test "should create"

## Step 8 — Check: Type Safety

```bash
# Check for untyped function parameters
grep -rn "function\|=>" --include="*.ts" src/app/modules/$ARGUMENTS/ | grep -v ".spec.ts" | grep "(.*: any\|(.*))" | head -20

# Check for untyped model fields
grep -rn ": any\|: object\|: \[\]" --include="*.ts" src/app/modules/$ARGUMENTS/models/ src/app/modules/$ARGUMENTS/interfaces/ 2>/dev/null
```

**Pass criteria:** No `any` in interfaces/models (except justified). All function parameters typed.

## Step 9 — Run Verification

```bash
# Typecheck
npm run typecheck

# Lint
npm run lint

# Test
npm run test
```

**Pass criteria:** All three pass without errors.

## Step 10 — Generate Report

Output a summary table:

```
## Module Check: $ARGUMENTS

| # | Criterion | Status | Details |
|---|-----------|--------|---------|
| 1 | Zero `any` (or justified) | PASS/FAIL | X remaining |
| 2 | Service `catchError` (re-throws) | PASS/FAIL | X/Y services covered |
| 3 | Component loading/error/empty | PASS/FAIL | X/Y components covered |
| 4 | `takeUntilDestroyed` pattern | PASS/FAIL | X components migrated |
| 5 | No duplicate services | PASS/FAIL | X duplicates found |
| 6 | Test coverage 80%+ | PASS/FAIL | X% measured |
| 7 | Meaningful tests (not stub) | PASS/FAIL | X/Y specs meaningful |
| 8 | Type safety (interfaces/models) | PASS/FAIL | X untyped fields |
| 9 | No `console.log` | PASS/FAIL | X remaining |
| 10 | Typecheck passes | PASS/FAIL | |
| 11 | Lint passes | PASS/FAIL | |
| 12 | Tests pass | PASS/FAIL | |

**Overall: X/12 criteria passed**

### Remaining Work
- [ ] Item 1 to fix
- [ ] Item 2 to fix
```

If all 12 criteria pass, the module is **DONE** per the stabilization plan.
If any fail, list specific remaining work items to achieve "Done" status.
