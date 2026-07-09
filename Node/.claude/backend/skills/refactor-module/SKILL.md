---
name: refactor-module
description: >
  Deep, context-aware refactoring of an entire NestJS feature module: duplicate code extraction,
  dead code removal, interface extraction, constant extraction, type safety (eliminate any/unknown),
  console.log removal, TODO resolution, naming conventions, error handling audit, SQL safety,
  utility consolidation, and readability improvements. Each phase has a build+lint gate with
  auto-fix loop. Runs /simplify as final pass.
  Usage: /refactor-module module-name
---

Refactor a NestJS feature module. The target module is: {{ARGS}}

---

# Argument Parsing

Parse `{{ARGS}}` to extract:

- **moduleName**: The first token (e.g., `review`, `dashboard`, `plan`, `bom`)

The module directory is located by searching:

1. `src/modules/<moduleName>/`
2. If not found, search: `find src/modules -maxdepth 1 -name "*<moduleName>*" -type d`

If the module directory cannot be found, STOP and ask the user for the correct path.

---

# CRITICAL: Verification Gate Protocol

**Every phase ends with a verification gate.** This prevents cascading breakage.

## Gate Definition

A **verification gate** runs these checks in order:

```bash
# 1. TypeScript compilation
npm run build 2>&1 | tail -30

# 2. ESLint on all files touched in this phase
npx eslint <touched-files> --format compact 2>&1
```

## Gate Failure - Self-Healing Loop (max 3 retries)

If ANY gate check fails:

1. **Read the error output** - identify exactly which file:line:rule failed
2. **Fix ONLY the failures** - do not re-run the entire phase
3. **Re-run the gate** - verify the fix didn't introduce new failures
4. **If still failing after 3 retries** - STOP, report what's broken, ask user for guidance

```
GATE LOOP:
  attempt = 0
  while attempt < 3:
    run gate checks
    if all pass -> PROCEED to next phase
    else -> fix failures, attempt++
  if attempt == 3 -> STOP and report
```

**NEVER skip a gate. NEVER proceed to the next phase with failures.**

---

# Phase 0 - Discovery & Analysis

This phase is READ-ONLY. No code changes. Build a complete picture before touching anything.

## Step 0.1 - Inventory all module files

```bash
find src/modules/<moduleName>/ -name "*.ts" -type f | sort
```

Categorize each file:

| Category   | Pattern                             |
| ---------- | ----------------------------------- |
| Controller | `*.controller.ts`                   |
| Service    | `*.service.ts`                      |
| Module     | `*.module.ts`                       |
| DTO        | `dto/*.ts` or `*.dto.ts`            |
| Entity     | Imported from `@entities`           |
| Interface  | `interfaces/*.ts` or inline in code |
| Constants  | `constants/*.ts` or inline in code  |
| Spec/Test  | `*.spec.ts`                         |
| Other      | Everything else                     |

Read EVERY file in the module. Record for each file:

```
FILE INVENTORY:
- <file-path>: <lines> lines, <category>
  Issues: [list each issue type found - see checklist below]
```

## Step 0.2 - Issue detection checklist

For each file, check for ALL of the following:

### Code duplication

- Identical or near-identical code blocks within the module (>5 lines)
- Code that duplicates logic already in `src/shared/utils/` or `src/shared/services/`
- Repeated query patterns, response mappings, or validation logic

### Dead code

- Unused imports (TypeScript compiler will catch most)
- Unused private methods (not called anywhere in the file)
- Unused variables, constants, interfaces, enums, types
- Commented-out code blocks (>3 lines)
- Unreachable code after return/throw

### Type safety violations

- `any` type usage (explicit or implicit)
- `unknown` type without proper narrowing
- Missing return type annotations on public/exported methods
- Inline interface declarations (e.g., `param: { id: number; name: string }`)
- Missing parameter types

### Console statements

- `console.log`, `console.warn`, `console.error`, `console.debug`, `console.info`
- Replace with NestJS Logger: `this.logger.log()`, `this.logger.warn()`, `this.logger.error()`

### Static/magic strings

- Hardcoded error messages not using `@str` (TEXT constants)
- Hardcoded status values, entity names, field names
- String literals used in comparisons that should be enums or constants
- Exception: Swagger decorators, route paths, and SQL column aliases are OK as-is

### TODO comments

- Scan for `// TODO`, `// FIXME`, `// HACK`, `// XXX`
- Assess if each TODO is still relevant and actionable

### Error handling

- Empty catch blocks
- Catch blocks that swallow errors (log but don't re-throw)
- `catch (error)` without `error: unknown` typing
- `error.message` used directly instead of `getErrorMessage(error)` from `@shared`
- `throw new Error()` instead of NestJS HttpException subclasses
- Try/catch wrapping code that cannot throw (unnecessary)

### Naming conventions

- Methods not following camelCase
- Interfaces not prefixed with `I` (project convention: check existing patterns)
- Constants not in UPPER_SNAKE_CASE
- Boolean variables not prefixed with `is`, `has`, `can`, `should`
- Vague names: `data`, `result`, `item`, `obj`, `temp`, `val`, `res`, `info`

### SQL safety (raw queries)

- String interpolation in `.query()` calls (SQL injection risk)
- Inline SQL >50 lines that duplicates an existing stored procedure

### Import hygiene

- Duplicate imports (same symbol from different paths)
- Imports that could use path aliases (`@shared`, `@entities`, `@enum`, `@str`, etc.)
- Barrel imports pulling in too much (`import * as ...`)

## Step 0.3 - Cross-reference with shared utilities

Check if the module duplicates logic already available in shared:

```bash
# Existing shared utilities
cat src/shared/utils/helpers.ts
cat src/shared/utils/error.utils.ts
cat src/shared/utils/constants.ts
cat src/shared/strings/text.string.ts
cat src/shared/strings/database.string.ts

# Existing shared interfaces
ls src/shared/interfaces/

# Existing shared enums
ls src/shared/enum/
```

Flag any module code that reimplements shared functionality.

## Step 0.4 - Cross-reference within module for duplication

Look for:

- Methods in different service files that do the same thing
- Response mapping logic repeated across methods
- Validation logic repeated across methods
- Query construction patterns repeated across methods

## Step 0.5 - Print discovery report

Print a comprehensive report before making any changes:

```
MODULE REFACTOR DISCOVERY: <moduleName>
============================================

FILES: <n> files, <total-lines> total lines

ISSUES FOUND:
- Code duplication: <n> instances
- Dead code: <n> items (unused imports: <n>, unused methods: <n>, commented code: <n>)
- Type safety: <n> issues (any: <n>, missing returns: <n>, inline interfaces: <n>)
- Console statements: <n>
- Static strings: <n>
- TODOs: <n> (actionable: <n>, stale: <n>)
- Error handling: <n> issues
- Naming: <n> issues
- SQL safety: <n> issues
- Import hygiene: <n> issues

PLANNED ACTIONS:
[List each specific change grouped by phase]
```

Wait for user confirmation before proceeding. If the user says to continue, proceed.

---

# Phase 1 - Dead Code & Import Cleanup

The safest changes first - removing things.

## Step 1.1 - Remove unused imports

For each file, remove imports that are not referenced in the code.

## Step 1.2 - Remove dead code

- Remove unused private methods
- Remove unused variables and constants
- Remove commented-out code blocks (>3 lines of commented code)
- Remove unreachable code

## Step 1.3 - Consolidate imports to use path aliases

Replace relative imports with path aliases where applicable:

```typescript
// Before:
import { SomeEntity } from '../../shared/entities/some.entity';
import { constructResponse } from '../../shared/http-response';

// After:
import { SomeEntity } from '@entities';
import { constructResponse } from '@response-map';
```

Standard aliases: `@shared`, `@entities`, `@enum`, `@str`, `@guards`, `@decorators`, `@interceptors`, `@filters`, `@validators`, `@response-map`

## Step 1.4 - Remove duplicate imports

If the same symbol is imported from different paths (e.g., direct file vs barrel), keep only the barrel/alias import.

### GATE 1: Build + ESLint

---

# Phase 2 - Type Safety

## Step 2.1 - Extract inline interfaces

For each inline interface declaration found in Phase 0:

1. Create `src/modules/<moduleName>/interfaces/` directory if it doesn't exist
2. Create an appropriately named file (e.g., `<entity>-response.interface.ts`)
3. Extract the inline type to a named interface
4. Create an `index.ts` barrel in the interfaces directory
5. Update all usages to import the named interface

```typescript
// Before (in service):
async findAll(): Promise<{ id: number; name: string; status: string }[]> { ... }

// After:
// In src/modules/<moduleName>/interfaces/<entity>-list-item.interface.ts:
export interface IEntityListItem {
  id: number;
  name: string;
  status: string;
}

// In service:
import { IEntityListItem } from './interfaces';
async findAll(): Promise<IEntityListItem[]> { ... }
```

**Naming convention**: Use `I` prefix for interfaces. Name by purpose, not structure.

## Step 2.2 - Eliminate `any` type usage

For each `any` found:

1. Determine the actual type by tracing the data flow
2. Replace with the correct type
3. If the type is genuinely dynamic/unknown at compile time, use `unknown` with proper type narrowing

Common replacements in this project:

| `any` context                   | Likely correct type       |
| ------------------------------- | ------------------------- |
| `request.user`                  | User entity type          |
| Entity from `.query()`          | Define a result interface |
| Event payload                   | The specific event class  |
| Error in catch block            | `unknown`                 |
| DTO/body parameter              | The DTO class             |
| Repository generic              | `Repository<EntityClass>` |
| `constructResponse(true, data)` | Type of `data`            |

## Step 2.3 - Add return type annotations

For each public method missing a return type:

- Determine the actual return type from the method body
- Add explicit annotation
- Use `Promise<T>` for async methods
- Use `Promise<void>` for methods that don't return a value

## Step 2.4 - Type catch blocks

```typescript
// Before:
catch (error) {
  this.logger.error(error.message);
}

// After:
catch (error: unknown) {
  this.logger.error(getErrorMessage(error), getErrorStack(error));
}
```

Import `getErrorMessage` and `getErrorStack` from `@shared`.

### GATE 2: Build + ESLint

---

# Phase 3 - Console & Static Strings

## Step 3.1 - Replace console statements

Replace ALL `console.log/warn/error/debug/info` with NestJS Logger:

```typescript
// Ensure logger is declared in the class:
private readonly logger = new Logger(<ClassName>.name);

// Replace:
console.log('something', data);    // -> this.logger.log('something', data);
console.error('failed', error);    // -> this.logger.error('failed', getErrorMessage(error));
console.warn('warning');           // -> this.logger.warn('warning');
```

Import `Logger` from `@nestjs/common`.

## Step 3.2 - Extract static/magic strings to constants

For hardcoded strings that represent business logic or messages:

1. Check if the string already exists in `@str` (TEXT constants) or `src/shared/utils/constants.ts`
2. If it exists, import and use the existing constant
3. If it doesn't exist:
   - For module-specific strings: create `src/modules/<moduleName>/constants/<moduleName>.constants.ts`
   - For validation/error messages shared across modules: add to `src/shared/strings/text.string.ts` under the appropriate category
4. Create an `index.ts` barrel if creating a new constants directory

**Do NOT extract**:

- Swagger decorator strings (`@ApiOperation`, `@ApiResponse` descriptions)
- Route path strings
- SQL column aliases in raw queries
- TypeORM relation names
- Import paths
- Logger context strings (class names)

**DO extract**:

- Error messages thrown to users
- Status string comparisons (e.g., `if (status === 'approved')`)
- Entity type identifiers used in event emissions
- Email template identifiers
- Notification messages

## Step 3.3 - Replace magic numbers

If numeric literals are used for business logic (e.g., page sizes, retry counts, timeouts):

1. Extract to a named constant in the module's constants file
2. Name descriptively: `DEFAULT_PAGE_SIZE`, `MAX_RETRY_ATTEMPTS`, `LOCK_TIMEOUT_MS`

### GATE 3: Build + ESLint

---

# Phase 4 - Error Handling

## Step 4.1 - Replace `throw new Error()` with NestJS exceptions

| Context                        | Replace With                             |
| ------------------------------ | ---------------------------------------- |
| Validation failure (bad input) | `throw new BadRequestException('msg')`   |
| Entity not found               | `throw new NotFoundException('msg')`     |
| Permission denied              | `throw new ForbiddenException('msg')`    |
| Conflict (duplicate, lock)     | `throw new ConflictException('msg')`     |
| External API failure           | Wrap and re-throw with context           |
| Generic/unknown                | `throw new InternalServerErrorException` |

Import from `@nestjs/common`.

## Step 4.2 - Audit try/catch blocks

For each try/catch:

1. **Is the try/catch necessary?** If the code inside cannot throw (e.g., pure synchronous logic, simple assignments), remove the try/catch
2. **Does the catch block re-throw?** If it only logs but doesn't re-throw, add a re-throw unless this is an intentional fire-and-forget (e.g., notification that shouldn't block main flow)
3. **Is the catch block empty?** Add logging + re-throw
4. **Is `error` typed?** Change `catch (error)` to `catch (error: unknown)`

## Step 4.3 - Parameterize unsafe raw SQL

For each raw `.query()` call using string interpolation:

```typescript
// Before (UNSAFE):
await this.entityManager.query(`SELECT * FROM table WHERE id = ${id}`);

// After (SAFE):
await this.entityManager.query(`SELECT * FROM table WHERE id = @0`, [id]);
```

> Only parameterize. Do NOT convert raw SQL to QueryBuilder.

## Step 4.4 - Check for existing stored procedures

For large inline SQL (>50 lines), check `src/database/stored_procedures/` for an existing SP that matches. If found, replace the inline SQL with the SP call. Do NOT create new SPs.

### GATE 4: Build + ESLint

---

# Phase 5 - Duplicate Code Extraction

## Step 5.1 - Extract within-module duplicates

For code blocks duplicated within the module (identified in Phase 0):

1. If the logic is used by 2+ methods in the SAME service, extract to a private method in that service
2. If the logic is used across DIFFERENT services in the module, create a utility in `src/modules/<moduleName>/utils/<moduleName>.utils.ts`
3. If the logic is used across DIFFERENT modules, add to `src/shared/utils/helpers.ts` or an appropriate shared utility

**Naming**: Name extracted functions by what they DO, not where they're called from.

## Step 5.2 - Check for unused utility functions

After extraction, verify:

```bash
# For each function in the module's utils file
grep -rn "<functionName>" src/modules/<moduleName>/ --include="*.ts"
```

If a utility function is only used once, inline it back. Utilities should serve 2+ callers.

## Step 5.3 - Use existing shared utilities

Replace reimplemented logic with calls to existing shared utilities:

- `getErrorMessage(error)` / `getErrorStack(error)` from `@shared` for error handling
- `constructResponse(success, data, statusCode)` from `@response-map` for responses
- Pagination helpers from `src/shared/utils/listapi-pagination.ts`
- File upload utilities from `src/shared/services/file-upload/`

### GATE 5: Build + ESLint

---

# Phase 6 - Naming & Readability

## Step 6.1 - Fix naming conventions

Apply project conventions:

| Element    | Convention               | Example                   |
| ---------- | ------------------------ | ------------------------- |
| Class      | PascalCase               | `ReviewService`           |
| Method     | camelCase                | `findAllReviews()`        |
| Variable   | camelCase                | `projectId`               |
| Constant   | UPPER_SNAKE_CASE         | `DEFAULT_PAGE_SIZE`       |
| Interface  | IPascalCase              | `IReviewListItem`         |
| Enum       | PascalCase               | `ReviewStatus`            |
| Enum value | PascalCase or UPPER      | `Approved` or `APPROVED`  |
| Boolean    | is/has/can/should prefix | `isApproved`, `hasAccess` |
| File       | kebab-case               | `review-crud.service.ts`  |

Rename vague identifiers:

- `data` -> describe what data (e.g., `reviewData`, `projectDetails`)
- `result` -> describe what result (e.g., `savedEntity`, `queryResult`)
- `item` -> describe the item type (e.g., `review`, `attachment`)
- `res` -> `response` (or the specific type)
- `obj` -> name the object type

## Step 6.2 - Add meaningful comments

Add comments ONLY where logic is non-obvious:

- Complex business rules
- Non-trivial SQL query purpose
- Workarounds with context for why
- Algorithm explanations for complex loops/conditions

**Remove**:

- Comments that restate the code (`// get the user` above `getUser()`)
- Outdated comments that no longer match the code
- Commented-out code (already removed in Phase 1)

## Step 6.3 - Resolve TODOs

For each TODO found in Phase 0:

1. If actionable and within scope: implement it
2. If it references a ticket/issue: leave it but add the ticket reference if missing
3. If stale/no longer relevant: remove it

### GATE 6: Build + ESLint

---

# Phase 7 - NestJS Best Practices

## Step 7.1 - Service patterns

- Ensure services use `@Injectable()` decorator
- Ensure constructor injection (not property injection)
- Ensure `RequestService` (scope: REQUEST) is used for request context, not manual param passing
- If a service has >15 constructor dependencies, flag for potential decomposition (use `/refactor-service`)

## Step 7.2 - Controller patterns

- Ensure proper HTTP method decorators (`@Get`, `@Post`, `@Put`, `@Patch`, `@Delete`)
- Ensure `@UseGuards(AuthGuard)` is applied
- Ensure `@Permission()` decorator is used for RBAC
- Ensure responses use `constructResponse()` pattern
- Ensure DTOs have class-validator decorators for input validation
- Controllers should be thin - delegate all logic to services

## Step 7.3 - Module registration

- Verify all services are in the module's `providers` array
- Verify all controllers are in the module's `controllers` array
- Verify `SharedModule` is imported
- Verify the module is registered in `src/modules/screen.module.ts`
- Verify any new entities are registered in `src/shared/modules/db-connection.module.ts`

## Step 7.4 - DTO validation

- Ensure DTOs use `class-validator` decorators (`@IsString`, `@IsNumber`, `@IsOptional`, etc.)
- Ensure DTOs use `class-transformer` decorators where needed (`@Type`, `@Transform`)
- Ensure Swagger decorators (`@ApiProperty`, `@ApiPropertyOptional`) are present

### GATE 7: Build + ESLint

---

# Phase 8 - Final Cleanup

## Step 8.1 - Formatting

```bash
npx prettier --write "src/modules/<moduleName>/**/*.ts"
```

## Step 8.2 - Final build verification

```bash
npm run build 2>&1 | tail -50
npx eslint "src/modules/<moduleName>/**/*.ts" --format compact 2>&1
```

Zero errors required. Zero warnings on touched files preferred.

## Step 8.3 - Run /simplify

Invoke the `/simplify` skill on all modified files for a final readability pass.

---

# Phase 9 - Report Generation

Generate a report file at: `docs/reports/refactor-module-<moduleName>-YYYY-MM-DD.md`

Use today's date for `YYYY-MM-DD`.

## Report Template

```markdown
# <ModuleName> Module Refactor Report - YYYY-MM-DD

## Summary

Refactored `src/modules/<moduleName>/` (N files, N total lines).
All gate checks pass: build OK, ESLint OK.

---

## Metrics

| Metric                | Before | After | Delta |
| --------------------- | ------ | ----- | ----- |
| Total files           | N      | N     | +/-N  |
| Total lines           | N      | N     | +/-N  |
| `any` type usages     | N      | 0     | -N    |
| console.\* statements | N      | 0     | -N    |
| Inline interfaces     | N      | 0     | -N    |
| Missing return types  | N      | 0     | -N    |
| Dead code items       | N      | 0     | -N    |
| Static/magic strings  | N      | 0     | -N    |
| Unsafe raw SQL        | N      | 0     | -N    |
| throw new Error()     | N      | 0     | -N    |
| Naming violations     | N      | 0     | -N    |
| TODOs resolved        | N      | N     |       |

---

## Changes by Phase

### Phase 1 - Dead Code & Import Cleanup

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 2 - Type Safety

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 3 - Console & Static Strings

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 4 - Error Handling

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 5 - Duplicate Code Extraction

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 6 - Naming & Readability

| File | Change |
| ---- | ------ |
| ...  | ...    |

### Phase 7 - NestJS Best Practices

| File | Change |
| ---- | ------ |
| ...  | ...    |

---

## New Files Created

| File | Purpose |
| ---- | ------- |
| ...  | ...     |

## Files Deleted

| File | Reason |
| ---- | ------ |
| ...  | ...    |

---

## Remaining Issues

- [ ] Items that could not be resolved in this pass
- [ ] Items deferred to other skills (/refactor-service, /stabilize-module)

---

## Verification Results

npm run build - OK (0 errors)
ESLint - OK (0 errors on touched files)
Prettier - OK
```

---

# Completion Summary

After Phase 9, print a concise summary:

```
/refactor-module <moduleName> - COMPLETE

Changes:
- Dead code: removed <n> unused imports, <n> dead methods, <n> commented blocks
- Type safety: eliminated <n> `any` usages, added <n> return types, extracted <n> interfaces
- Console: replaced <n> console.* with Logger
- Constants: extracted <n> magic strings, <n> magic numbers
- Errors: replaced <n> throw Error with HttpException, fixed <n> catch blocks
- Duplicates: extracted <n> shared utilities, inlined <n> single-use helpers
- Naming: renamed <n> identifiers
- TODOs: resolved <n>, removed <n> stale
- SQL: parameterized <n> unsafe queries
- Report: docs/reports/refactor-module-<moduleName>-YYYY-MM-DD.md

All verification gates passed.
```
