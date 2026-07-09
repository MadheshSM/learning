---
name: refactor-service
description: >
  Refactor a single NestJS service: code cleanup (unused code, console.log, constants, interfaces,
  duplicates, TODOs), async/await migration, error handling standardization, SQL query simplification,
  auto-detected service decomposition (facade + sub-services), type safety improvements (including
  "any" elimination), comment pass, and change report generation. Each phase has a build+lint+prettier
  gate with auto-fix loop. Complements /stabilize-module by going deeper on code quality within
  a single service file.
  Usage: /refactor-service <service-name> [--no-split] [--force-split]
---

Refactor a NestJS service. The target is: {{ARGS}}

---

# Argument Parsing

Parse `{{ARGS}}` to extract:

- **serviceName**: The first token (e.g., `review`, `dashboard`, `plan`)
- **--no-split**: If present, skip Phase 4 (service decomposition) entirely
- **--force-split**: If present, force Phase 4 even if auto-detection says no

The service file is located by searching:

1. `src/modules/<serviceName>/<serviceName>.service.ts`
2. `src/modules/<serviceName>/services/<serviceName>.service.ts`
3. If neither exists, search: `find src/modules -name "<serviceName>.service.ts" -type f`

If the service file cannot be found, STOP and ask the user for the correct path.

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

# 3. Prettier formatting check
npx prettier --check <touched-files> 2>&1
```

## Gate Failure → Self-Healing Loop (max 3 retries)

If ANY gate check fails:

1. **Read the error output** — identify exactly which file:line:rule failed
2. **Fix ONLY the failures** — do not re-run the entire phase
3. **Re-run the gate** — verify the fix didn't introduce new failures
4. **If still failing after 3 retries** — STOP, report what's broken, ask user for guidance

For Prettier failures specifically, run `npx prettier --write <files>` as the fix, then re-check.

```
GATE LOOP:
  attempt = 0
  while attempt < 3:
    run gate checks
    if all pass → PROCEED to next phase
    else → fix failures, attempt++
  if attempt == 3 → STOP and report
```

**NEVER skip a gate. NEVER proceed to the next phase with failures.**

---

# Phase 0 — Discovery & Auto-Detection

## Step 0.1 — Read the service file

Read the entire service file. Collect:

```
BASELINE METRICS:
- File path: <path>
- Total lines: <n>
- Constructor injections: <n> (list each dependency)
- Public methods: <n> (list each with line range)
- Private methods: <n>
- .then() chains: <n> (list line numbers)
- .forEach(async ...) occurrences: <n> (list line numbers)
- .map(async ...) without Promise.all: <n> (list line numbers)
- throw new Error() occurrences: <n> (list line numbers)
- Raw .query() calls: <n> (list line numbers)
- Deprecated API usage: <n> (getConnection/getManager/getRepository — list line numbers)
- Missing return types on public methods: <n> (list method names)
- find()/findOne() calls without explicit relations: <n> (list line numbers)
- find()/findOne() calls with potentially over-fetched relations: <n> (list line numbers + relation names)
```

## Step 0.1b — Check for stored procedure duplication

For each raw `.query()` call with >50 lines of inline SQL, check if an equivalent stored procedure already exists:

```bash
# List all stored procedures
ls src/database/stored_procedures/*.sql 2>/dev/null

# Check for SP matching this module's entity name
ls src/database/stored_procedures/ | grep -i "<entityName>"
```

**For each match found:**

1. Read the stored procedure file and compare its logic to the inline SQL
2. If the SP performs the same query (pagination, filtering, joins on the same tables), flag it:

```
SP DUPLICATION CANDIDATES:
- Method: <methodName> (line <n>, ~<n> lines of inline SQL)
  Matching SP: src/database/stored_procedures/<sp-file>.sql
  Recommendation: Replace inline SQL with EXEC dbo.<SPName> @param1, @param2
  Risk: Verify SP output columns match current response mapping
```

3. If no matching SP exists, skip — do NOT create new stored procedures

> **IMPORTANT:** This step is discovery only. The actual SP migration happens in Phase 3 (Step 3.3b).
> Do NOT convert QueryBuilder or simple find() calls — only large inline `.query()` blocks.

## Step 0.1c — Audit relation loading in find/findOne calls

For each `find()`, `findOne()`, or `findAndCount()` call in the service:

```bash
grep -n "\.find\b\|\.findOne\b\|\.findAndCount\b" "<service-file-path>"
```

Classify each call:

| Category                   | Description                                                  | Action Needed                                                             |
| -------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| **No relations specified** | `this.repo.find({ where: { ... } })` with no `relations` key | Flag — needs explicit `relations: []` (even if empty, to document intent) |
| **Relations specified**    | `this.repo.find({ where: { ... }, relations: ['a', 'b'] })`  | Check if all listed relations are used in the response/logic below        |
| **Over-fetched**           | Relations listed but not referenced in subsequent code       | Flag for removal                                                          |

Record findings in the discovery report.

## Step 0.1d — Raw SQL complexity assessment

For each raw `.query()` call:

```bash
grep -n "\.query(" "<service-file-path>"
```

For each raw query, count JOIN keywords and classify complexity:

```
RAW SQL COMPLEXITY:
- Line <n>: <n> JOINs, <complexity: simple|moderate|complex> → recommend: <repo.find|QueryBuilder|keep raw>
  SQL Server-specific syntax: <yes/no — e.g., CROSS APPLY, FOR JSON, PIVOT>
```

| Complexity | Criteria                                                         | Recommended Approach                   |
| ---------- | ---------------------------------------------------------------- | -------------------------------------- |
| Simple     | 0-2 JOINs, basic WHERE, no aggregation                           | TypeORM `repo.find()` with `relations` |
| Moderate   | 2-4 JOINs, conditional WHERE, or pagination                      | QueryBuilder (`createQueryBuilder`)    |
| Complex    | 5+ JOINs, UNION, CTE, aggregation, or SQL Server-specific syntax | Keep as raw SQL but parameterize       |

## Step 0.2 — Identify concern groupings

Group methods by responsibility domain. Common groupings:

| Group             | Typical methods                                    |
| ----------------- | -------------------------------------------------- |
| CRUD              | create, findOne, update, remove, findAll           |
| Workflow          | updateStatus, getReviews, getWorkflowDetails       |
| Import/Export     | importFile, exportFile, parseRows                  |
| Query/List        | findAllV1, findAllV2, selectorList, options        |
| Assignment        | saveAssignment, updateAssignment, getAssignedUsers |
| Notification/Mail | sendMail, getMailDetails, getMessageBody           |
| Hierarchy         | validateParent, recursiveCheck, getChildren        |
| File Operations   | createZip, downloadLink, uploadFile                |
| Utility           | httpResponseObj, filters, getEntityType            |

List each group with its methods. A service with **>=3 distinct non-utility groups** is a decomposition candidate.

## Step 0.3 — Check cross-module consumers

```bash
# Find all imports of this service from OTHER modules
grep -rn "import.*<ServiceClassName>" src/modules/ --include="*.ts" -l | grep -v "src/modules/<serviceName>/"
```

Also check if the service is registered in:

- `src/shared/shared.module.ts` (cross-cutting provider)
- `src/modules/screen.module.ts` (unlikely but check)

Record the consumer count — high consumer count (>5 modules) means decomposition has higher impact and requires more careful consumer updates.

## Step 0.4 — Check if already-split sub-service

```bash
# Check if this file lives in a services/ subdirectory (indicates it's already a sub-service)
echo "<file-path>" | grep -c "/services/"
```

If the service is already a sub-service from a prior `/stabilize-module` run:

- **Print warning**: "This service appears to be an already-decomposed sub-service. Skipping decomposition (Phase 4). Quality fixes will still be applied."
- Force `--no-split` behavior regardless of flags.

## Step 0.5 — Auto-detect decomposition need

Apply these rules (unless overridden by flags):

| Condition                                                | Recommendation                               |
| -------------------------------------------------------- | -------------------------------------------- |
| >700 lines AND >=3 concern groups AND >=12 DI deps       | **RECOMMEND SPLIT**                          |
| >700 lines AND >=3 concern groups AND <12 DI deps        | **RECOMMEND SPLIT** (lighter split)          |
| >700 lines BUT <=2 concern groups (specialized/cohesive) | **RECOMMEND NO SPLIT** — quality fixes only  |
| <=700 lines                                              | **SKIP SPLIT**                               |
| `--no-split` flag                                        | **SKIP SPLIT**                               |
| `--force-split` flag                                     | **FORCE SPLIT** (override auto-detection)    |
| Already a sub-service (Step 0.4)                         | **SKIP SPLIT** (override even --force-split) |

## Step 0.6 — Print discovery report

Print the baseline metrics, concern groupings, consumer count, and decomposition recommendation to the user before proceeding.

If the service extends `BaseService` and defines `publicFieldMap` / `searchableFieldMap`, check for common workflow field entries that appear across many modules:

```bash
# Count how many services share the same field map entries
grep -rn "status.*workflowStatus\|workflowID.*workflowID" src/modules/ --include="*.service.ts" -l | wc -l
```

If the service contains common entries like `status: 'workflowStatus'`, `workflowID: 'workflowID'`, note it in the report:

```
FIELD MAP NOTE:
- This service's publicFieldMap contains <n> entries that are duplicated across <m> other modules
- Common entries: status -> workflowStatus, workflowID -> workflowID
- Consider extracting shared WORKFLOW_FIELD_MAP constant in a future cross-cutting effort
```

> **NOTE:** Do NOT extract the constant during this refactor — it affects multiple modules.
> This is informational only, to be acted on during a cross-module cleanup pass.

## Step 0.7 — Duplicate code scan

Scan for identical or near-identical logic within the service:

```bash
# Check ESLint SonarJS rule for identical functions
npx eslint "<service-file>" --rule '{"sonarjs/no-identical-functions": "error"}' --format json 2>/dev/null
```

Also manually scan for:

- Functions that repeat the same utility logic inline (e.g., date formatting, response mapping, array transformations)
- Check if `src/shared/utils/helpers.ts` or module-level utils already contain equivalent functions

```bash
# Check for existing module-level utils
ls src/modules/<moduleName>/utils/ 2>/dev/null
ls src/modules/<moduleName>/constants/ 2>/dev/null

# Check shared utils
grep -n "export function\|export const" src/shared/utils/helpers.ts 2>/dev/null | head -30
```

Record as:

```
DUPLICATE CODE CANDIDATES:
- Lines <n>-<n> and <n>-<n>: similar logic for <description>
  Existing util: src/shared/utils/helpers.ts#<functionName> (if exists)
  Recommendation: Extract to <module>.utils.ts / call existing util
```

## Step 0.8 — Inline interface scan

```bash
grep -n "^\s*interface \|^\s*type \w\+ =" "<service-file>"
```

Record count and line numbers. Flag interfaces with **3+ fields** or used in **2+ locations**. Single-use types with 2 or fewer fields can remain inline.

```
INLINE INTERFACES:
- Line <n>: interface <Name> { <n> fields } — used in <n> locations → EXTRACT / KEEP
```

## Step 0.9 — TODO comment audit

```bash
grep -n "TODO\|FIXME\|HACK\|XXX" "<service-file>"
```

Classify each:

```
TODO AUDIT:
- Line <n>: "TODO: <content>" — Status: RESOLVED | UNRESOLVED | STALE
  Context: <brief explanation of why this status was assigned>
```

- **RESOLVED**: The TODO describes something already done in the current code
- **UNRESOLVED**: Still needs work — will be cataloged in report
- **STALE**: References features/issues that no longer apply

## Step 0.10 — console.log scan

```bash
grep -n "console\.\(log\|warn\|error\|info\|debug\)" "<service-file>"
```

Record count and line numbers. Note: `no-console: 'error'` is already in ESLint, but explicit detection allows structured replacement with NestJS Logger.

## Step 0.11 — "any" type scan

```bash
grep -n ": any\b\|<any>\|as any" "<service-file>"
```

Classify each occurrence:

```
"ANY" TYPE USAGES:
- Line <n>: <category> — <context>
  Categories: PARAMETER | RETURN | VARIABLE | CAST | GENERIC
```

## Step 0.12 — Hardcoded string scan

```bash
# ESLint SonarJS duplicate string detection
npx eslint "<service-file>" --rule '{"sonarjs/no-duplicate-string": "error"}' --format json 2>/dev/null
```

Also manually scan for:

- User-facing error messages not using `TEXT` from `@str`
- Hardcoded status strings, entity names that repeat 2+ times
- Exception messages that should come from constants

```
HARDCODED STRING CANDIDATES:
- Line <n>: '<string>' — appears <n> times → extract to <target location>
```

## Step 0.13 — Unused imports/variables scan

```bash
npx eslint "<service-file>" --rule '{"@typescript-eslint/no-unused-vars": "error"}' --format json 2>/dev/null
```

Record count and list each unused import/variable with line number.

## Step 0.14 — Print cleanup metrics

After all discovery steps, print the cleanup metrics alongside the baseline:

```
CLEANUP METRICS:
- Duplicate code candidates: <n>
- Inline interfaces (extractable): <n>
- TODO comments: <n> (resolved: <n>, unresolved: <n>, stale: <n>)
- console.log occurrences: <n>
- "any" type usages: <n> (param: <n>, return: <n>, var: <n>, cast: <n>, generic: <n>)
- Hardcoded string candidates: <n>
- Unused imports/variables: <n>
- Raw SQL queries: <n> (simple: <n>, moderate: <n>, complex: <n>)
```

---

# Phase 1 — Async/Await Migration

Convert all promise chain patterns to modern async/await.

## Step 1.1 — Convert .then()/.catch() chains

For each `.then()` chain found in Step 0.1:

**Before:**

```typescript
this.repository
  .save(entity)
  .then((result) => {
    this.eventEmitter.emit('created', result);
  })
  .catch((error) => {
    this.logger.error(error);
  });
```

**After:**

```typescript
try {
  const result = await this.repository.save(entity);
  this.eventEmitter.emit('created', result);
} catch (error: unknown) {
  this.logger.error(getErrorMessage(error), getErrorStack(error));
}
```

**Rules:**

- Ensure the containing method is marked `async`
- Preserve all side effects from `.then()` callbacks
- Convert `.catch()` to try/catch with proper `error: unknown` typing
- Use `getErrorMessage(error)` and `getErrorStack(error)` from `@shared` in catch blocks
- If the `.then()` was returning a value, ensure `await` captures it in a variable

## Step 1.2 — Fix fire-and-forget .map(async ...)

**Before:**

```typescript
items.map(async (item) => {
  await this.repository.save(item);
});
```

**After:**

```typescript
await Promise.all(
  items.map(async (item) => {
    await this.repository.save(item);
  }),
);
```

## Step 1.3 — Fix .forEach(async ...)

**Before:**

```typescript
items.forEach(async (item) => {
  await this.processItem(item);
});
```

**After:**

```typescript
for (const item of items) {
  await this.processItem(item);
}
```

> **Note:** Use `for...of` (sequential) unless operations are independent, in which case use `Promise.all(items.map(...))` (parallel).

## Step 1.4 — Ensure method signatures are async

Any method that now contains `await` must have the `async` keyword. If the method previously returned a raw Promise (e.g., `return this.repository.save(entity)`), the `await` + `async` is still preferred for consistent error handling.

### GATE 1: Build + ESLint + Prettier

```bash
npm run build 2>&1 | tail -30
npx eslint "<service-file-path>" --format compact 2>&1
npx prettier --check "<service-file-path>" 2>&1
```

---

# Phase 2 — Code Cleanup

Clean up code quality issues detected in Phase 0 Steps 0.7–0.13. This phase runs after async/await migration to catch any dead code introduced by Phase 1 transformations.

## Step 2.1 — Remove unused imports and variables

Run first — eliminates dead code before other steps touch it.

**Rules:**

- Remove imports that are no longer used (especially after Phase 1 async/await changes)
- Remove declared but unused variables (respecting the `_` prefix convention for intentionally unused params)
- Remove unused private methods that are never called within the service
- Do NOT remove `@ts-ignore` or eslint-disable comments without checking if the underlying issue is resolved

```bash
# Verify unused items after removal
npx eslint "<service-file>" --rule '{"@typescript-eslint/no-unused-vars": "error"}' --format compact 2>&1
```

## Step 2.2 — Replace console.log with NestJS Logger

For each `console.log/warn/error/info/debug` found in Step 0.10:

If the service does not already have a Logger instance, add one:

```typescript
import { Logger } from '@nestjs/common';

// Add as first line in class body after constructor
private readonly logger = new Logger(ServiceName.name);
```

**Replacement mapping:**

| Before               | After                    |
| -------------------- | ------------------------ |
| `console.log(msg)`   | `this.logger.log(msg)`   |
| `console.error(msg)` | `this.logger.error(msg)` |
| `console.warn(msg)`  | `this.logger.warn(msg)`  |
| `console.debug(msg)` | `this.logger.debug(msg)` |
| `console.info(msg)`  | `this.logger.log(msg)`   |

If `Logger` is already imported from `@nestjs/common`, do not duplicate the import.

## Step 2.3 — Extract hardcoded strings to constants

For duplicate/hardcoded strings found in Step 0.12:

**Target locations by string type:**

| String Type                                                     | Extract To                                                                       |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Error/validation messages shared across modules                 | `src/shared/strings/text.string.ts` → `TEXT.<section>.<key>` (import via `@str`) |
| Error/validation messages module-specific                       | `src/modules/<module>/constants/<module>.constants.ts`                           |
| Status strings, entity names, repeated literals                 | `src/modules/<module>/constants/<module>.constants.ts`                           |
| Already exists in `@str` (`TEXT`, `DB_TABLE`, `MAIL`, `FOLDER`) | Replace inline with reference to existing constant                               |

**Rules:**

- Only extract strings that appear **2+ times** OR are **user-facing error messages**
- Do NOT extract SQL column names or TypeORM relation names (those are structural)
- Do NOT extract log message strings (developer-facing, benefit from being inline)
- Import from `@str` alias when using shared strings
- Use `UPPER_SNAKE_CASE` for constant names

**Example:**

```typescript
// Before:
throw new BadRequestException('Task not found');
// ... elsewhere in same file:
throw new BadRequestException('Task not found');

// After (in <module>.constants.ts):
export const TASK_MESSAGES = {
  NOT_FOUND: 'Task not found',
} as const;

// In service:
import { TASK_MESSAGES } from './constants/<module>.constants';
throw new BadRequestException(TASK_MESSAGES.NOT_FOUND);
```

## Step 2.4 — Extract inline interfaces to dedicated files

For each inline interface flagged in Step 0.8 (3+ fields or 2+ usage locations):

**Target location:** `src/modules/<module>/interfaces/`

**Rules:**

- If the module already has an `interfaces/` directory with an `index.ts`, add the new file and re-export from `index.ts`
- If no `interfaces/` directory exists, create it with an `index.ts` barrel
- Name the file after the interface: `ISomeName` → `some-name.interface.ts`
- Keep truly local types (2 fields or fewer, used once in the same method) inline — do not over-extract
- Update imports at the extraction site to use the new path
- If the interface is used by other modules too, place it in `src/shared/interfaces/` instead

**Example:**

```typescript
// Before (inline in service):
interface ITaskListResult {
  taskID: number;
  taskName: string;
  status: string;
  assignedTo: string;
}

// After (src/modules/task/interfaces/task-list-result.interface.ts):
export interface ITaskListResult {
  taskID: number;
  taskName: string;
  status: string;
  assignedTo: string;
}

// After (src/modules/task/interfaces/index.ts):
export * from './task-list-result.interface';
```

## Step 2.5 — Consolidate duplicate code to utils/helpers

For each duplicate code candidate from Step 0.7:

**Decision order:**

1. If an equivalent function already exists in `src/shared/utils/helpers.ts` or module utils → **call it** instead of duplicating
2. If the duplicate is within the same service (private method called identically in multiple spots) → **keep one copy**, have other call sites reference it
3. If no equivalent exists and logic is genuinely reusable → **create** a new utility:
   - Module-specific: `src/modules/<module>/utils/<module>.utils.ts`
   - Cross-module: `src/shared/utils/` (only if genuinely shared)

**Threshold:** 5+ lines of duplicated logic OR 3+ call sites.

**Rules:**

- New util functions must have return type annotations
- Do NOT extract code that will be restructured in Phase 3 (error handling) or Phase 4 (decomposition) — those phases may eliminate the duplication naturally
- Prefer pure functions for utils (no `this` dependency)

## Step 2.6 — Resolve TODO comments

For each TODO/FIXME from Step 0.9:

| Status         | Action                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------- |
| **RESOLVED**   | Remove the TODO comment (the work is already done in current code)                                |
| **STALE**      | Remove the comment; note in report what was removed                                               |
| **UNRESOLVED** | Leave in place; standardize format to `// TODO(<ticket-or-name>): description`; catalog in report |

### GATE 2: Build + ESLint + Prettier

```bash
npm run build 2>&1 | tail -30
npx eslint "<all-touched-files>" --format compact 2>&1
npx prettier --check "<all-touched-files>" 2>&1
```

---

# Phase 3 — Error Handling & SQL Safety

## Step 3.1 — Replace throw new Error()

For each `throw new Error()` found in Step 0.1, determine the appropriate NestJS exception:

| Context                        | Replace With                                                            |
| ------------------------------ | ----------------------------------------------------------------------- |
| Validation failure (bad input) | `throw new BadRequestException('message')`                              |
| Entity not found               | `throw new NotFoundException('message')`                                |
| Permission denied              | `throw new ForbiddenException('message')`                               |
| Conflict (duplicate, lock)     | `throw new ConflictException('message')`                                |
| External API failure           | `throw new ExternalApiException('service', 'operation', originalError)` |
| Generic/unknown                | `throw new InternalServerErrorException('message')`                     |

Import from `@nestjs/common` (or `@shared` for `ExternalApiException`).

## Step 3.2 — Audit catch blocks

For each catch block in the service:

- **If catch block only logs and does NOT re-throw** — add re-throw unless this is intentional fire-and-forget (e.g., notification side-effect that should not block the main flow)
- **If catch block is empty** — add logging + re-throw
- **If catch block uses `(error)` without type** — change to `(error: unknown)`
- **If catch block uses `error.message` directly** — use `getErrorMessage(error)` from `@shared`

## Step 3.3 — Parameterize unsafe raw SQL (injection safety ONLY)

For each raw `.query()` call found in Step 0.1, check if it uses string interpolation:

**Before (UNSAFE):**

```typescript
await this.entityManager.query(`SELECT * FROM table WHERE id = ${id} AND name = '${name}'`);
```

**After (SAFE):**

```typescript
await this.entityManager.query(`SELECT * FROM table WHERE id = @0 AND name = @1`, [id, name]);
```

## Step 3.3b — Replace duplicate inline SQL with existing stored procedures

For each SP duplication candidate identified in Step 0.1b:

**Before (inline SQL, ~200 lines):**

```typescript
async findAllV1(projectID, _module, page, limit) {
  const result = await this.entityManager.query(`
    SELECT t.taskID, t.taskName, ...
    FROM task t
    INNER JOIN workflow_status ws ON ...
    LEFT JOIN ...
    WHERE t.projectID = ${projectID}
    ORDER BY ...
    OFFSET ${(page - 1) * limit} ROWS
    FETCH NEXT ${limit} ROWS ONLY
  `);
  return result;
}
```

**After (stored procedure call):**

```typescript
async findAllV1(projectID: number, _module: string, page: number, limit: number): Promise<IRawTaskListResult[]> {
  const result = await this.entityManager.query(
    `EXEC dbo.GetTaskList @projectID = @0, @module = @1, @pageNumber = @2, @pageSize = @3`,
    [projectID, _module, page, limit],
  );
  return result;
}
```

**Rules:**

- Only replace when Phase 0 confirmed an existing SP matches the inline SQL logic
- Verify the SP output columns match the current response mapping (compare SELECT columns)
- If the SP returns additional/fewer columns, adjust the response mapping or skip the replacement
- Parameterize the SP call (use `@0, @1` syntax) — never interpolate parameters
- Add a typed result interface for the SP output (e.g., `IRawTaskListResult`)
- If column mismatches are too significant, leave the inline SQL but parameterize it (Step 3.3) and add a comment: `// TODO: Align with stored procedure dbo.<SPName>`

> **IMPORTANT:** Do NOT create new stored procedures. Only use SPs that already exist in `src/database/stored_procedures/`.

## Step 3.4 — Simplify complex SQL queries

For each raw `.query()` call classified in Step 0.1d, apply the best approach:

**Decision matrix:**

| Query Complexity                                    | Best Approach                                   | When to Use                                         |
| --------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------- |
| Simple (0-2 JOINs, basic WHERE)                     | TypeORM `repo.find()` with `relations`          | Straightforward entity loading, no computed columns |
| Moderate (2-4 JOINs, conditional WHERE, pagination) | QueryBuilder (`createQueryBuilder`)             | Need conditional joins, aliases, or subqueries      |
| Aggregation (COUNT, SUM, GROUP BY)                  | QueryBuilder with `.select()` + `.getRawMany()` | Computed results that don't map to entities         |
| Complex (5+ JOINs, UNION, CTE)                      | Keep as raw SQL but parameterize                | Too complex for QueryBuilder; readability matters   |
| SP exists                                           | `EXEC dbo.<SPName>` (covered by Step 3.3b)      | SP logic matches inline SQL                         |

**Converting to `repo.find()` (simple queries):**

```typescript
// Before:
const result = await this.entityManager.query(
  `SELECT t.* FROM task t INNER JOIN project p ON t.projectID = p.projectID WHERE t.projectID = @0`,
  [projectID],
);

// After:
const result = await this.taskRepository.find({
  where: { projectID },
  relations: ['project'],
});
```

**Converting to QueryBuilder (moderate queries):**

```typescript
// Before:
const result = await this.entityManager.query(
  `SELECT t.taskID, t.taskName, ws.statusName
   FROM task t
   INNER JOIN workflow_status ws ON t.workflowStatusID = ws.workflowStatusID
   LEFT JOIN task_assignment ta ON t.taskID = ta.taskID
   WHERE t.projectID = @0 AND t.deletedAt IS NULL
   ORDER BY t.createdAt DESC
   OFFSET @1 ROWS FETCH NEXT @2 ROWS ONLY`,
  [projectID, offset, limit],
);

// After:
const result = await this.taskRepository
  .createQueryBuilder('t')
  .innerJoin('t.workflowStatus', 'ws')
  .leftJoin('t.taskAssignment', 'ta')
  .select(['t.taskID', 't.taskName', 'ws.statusName'])
  .where('t.projectID = :projectID', { projectID })
  .andWhere('t.deletedAt IS NULL')
  .orderBy('t.createdAt', 'DESC')
  .skip(offset)
  .take(limit)
  .getRawMany<ITaskListResult>();
```

**Rules:**

- Always choose the approach that balances **query performance** and **type safety**
- When converting to QueryBuilder: use `.where()` with parameter binding (`:param`), never string interpolation
- When converting to `repo.find()`: use `relations` for joins, `where` for conditions
- For pagination queries: prefer QueryBuilder with `.skip()` / `.take()` over raw `OFFSET/FETCH`
- Add typed result interfaces for `getRawMany()` / `getRawOne()` results
- If a query uses SQL Server-specific syntax (e.g., `CROSS APPLY`, `FOR JSON`, `PIVOT`), keep as raw SQL — QueryBuilder doesn't support these
- If unsure about performance impact, keep as raw SQL but parameterize — correctness over elegance

### GATE 3: Build + ESLint + Prettier

```bash
npm run build 2>&1 | tail -30
npx eslint "<service-file-path>" --format compact 2>&1
npx prettier --check "<service-file-path>" 2>&1
```

---

# Phase 4 — Service Decomposition (Conditional)

**SKIP this phase if:**

- Auto-detection recommended NO SPLIT and `--force-split` was NOT passed
- `--no-split` flag was passed
- Service is an already-split sub-service (Step 0.4)

If skipping, print: "Phase 4 skipped — decomposition not needed for this service." and proceed to Phase 5.

## Step 4.1 — Design sub-service boundaries

Using the concern groupings from Phase 0, design the split:

**Naming convention** (from `/stabilize-module`):

- Use flat placement with module-prefix naming: `<module>-<concern>.service.ts`
- Place in `services/` subdirectory when the module will have 4+ service files
- If a `services/` subdirectory already exists, use it

**Target per sub-service:**

- Each sub-service should be <700 lines
- Each sub-service should have 4-8 constructor dependencies max
- Each sub-service should handle ONE concern group

**Common decomposition patterns:**

```
ReviewService (facade, ~150 lines)
  ├── ReviewCrudService (~500 lines) — create, findAll, findOne, update, remove
  ├── ReviewApprovalService (~400 lines) — updateReviewStatus, checkListStatus, punchListStatus
  ├── ReviewAssignmentService (~300 lines) — saveReviewAssignment, updateReviewAssignment, getAssignedUsers
  └── ReviewMailService (~200 lines) — getMailDetails, getMessageBody, sendNotification

PlanService (facade, ~150 lines)
  ├── PlanCrudService (~400 lines) — create, findAll, findOne, update, remove
  ├── PlanHierarchyService (~300 lines) — validateParentPlanId, recursiveCheck, updateDependency
  ├── PlanImportExportService (~300 lines) — importPlanFile, exportPlanFile
  └── PlanWorkflowService (~200 lines) — getReviews, getWorkflowStatus

TransmittalService (facade, ~150 lines)
  ├── TransmittalCrudService (~400 lines) — create, findAll, findOne, update, remove
  ├── TransmittalExportService (~350 lines) — createArchive, sendDownloadLink, buildArchiveFolder
  └── TransmittalQueryService (~300 lines) — complex filtering, SQL query builders
```

Print the proposed decomposition plan before executing.

## Step 4.2 — Create sub-service files

For each sub-service:

1. Create the file at the appropriate path
2. Add `@Injectable()` decorator
3. Move the relevant methods from the original service
4. Move the DI dependencies needed by those methods to the sub-service constructor
5. If the original service extends `BaseService` or a helper, the sub-service should also extend it (to inherit `filters()`, `requestService`, etc.)
6. Import all necessary types, entities, DTOs, constants
7. Move any interfaces extracted in Phase 2 (Step 2.4) to the appropriate sub-service's scope if they are only used by that sub-service

## Step 4.3 — Convert original service to facade

The original service becomes a thin orchestrator:

```typescript
@Injectable()
export class <Module>Service {
  constructor(
    private readonly crudService: <Module>CrudService,
    private readonly workflowService: <Module>WorkflowService,
    // ... other sub-services
  ) {}

  // Delegate each public method to the appropriate sub-service
  async create(dto: CreateDto): Promise<ResponseType> {
    return this.crudService.create(dto);
  }

  async findAll(): Promise<ResponseType> {
    return this.crudService.findAll();
  }

  // Methods that coordinate across sub-services stay in the facade
  async complexOperation(): Promise<ResponseType> {
    const result = await this.crudService.create(dto);
    await this.workflowService.initializeWorkflow(result.id);
    return result;
  }
}
```

**Facade guidelines:**

- Keep methods that genuinely coordinate across sub-services
- Pure delegation methods should be one-liners
- Target ~100-200 lines for the facade
- The facade is NOT a pass-through anti-pattern when it coordinates cross-cutting concerns (events, transactions, notifications)

## Step 4.4 — Update module registration

Edit `src/modules/<module>/<module>.module.ts`:

```typescript
// Add new sub-services to providers array
providers: [
  <Module>Service,        // facade (existing)
  <Module>CrudService,    // new
  <Module>WorkflowService, // new
  // ... other sub-services
],
```

## Step 4.5 — Update cross-module consumers

If the service is imported by other modules (found in Step 0.3):

1. If other modules import the **class directly** (e.g., `ReviewService`), the facade pattern means **no changes needed** — the facade delegates internally
2. If other modules import **specific methods** that moved to sub-services, update the imports
3. If the service is registered in `src/shared/shared.module.ts`, ensure the facade is still exported (sub-services stay internal to the feature module)

```bash
# Verify no broken imports
npm run build 2>&1 | tail -30
```

### GATE 4: Build + ESLint + Prettier

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/<module>/**/*.ts" --format compact 2>&1
npx prettier --check "src/modules/<module>/**/*.ts" 2>&1
```

**Common failures at this gate:**

- Module.ts `providers` missing new sub-services
- Sub-services missing imports for decorators or entities
- Facade creating unused imports from moved methods
- Circular dependency between facade and sub-services (sub-services must NOT import facade)

---

# Phase 5 — Type Safety & Comments

## Step 5.1 — Add return type annotations

For each public method missing a return type (found in Step 0.1):

```typescript
// Before:
async findAll() {
  return this.repository.find();
}

// After:
async findAll(): Promise<Entity[]> {
  return this.repository.find();
}
```

**Rules:**

- Use the actual return type, not `any` or `unknown`
- For methods returning `constructResponse()`, use `Promise<StandardResponseDto<T>>` or just the response shape
- For void methods (emit events, log, etc.), use `Promise<void>`
- If the return type is genuinely complex/union, it's OK to define a local type or interface

## Step 5.1b — Add explicit relation loading to find/findOne calls

For each find/findOne call flagged in Step 0.1c:

**If no relations specified:**

```typescript
// Before:
const entity = await this.repo.findOne({ where: { id } });

// After — add only relations used in the response mapping below:
const entity = await this.repo.findOne({
  where: { id },
  relations: ['project', 'assignedUsers'],
});
```

**If over-fetched relations:**

```typescript
// Before — loads 'attachments' but never uses it:
const entity = await this.repo.findOne({
  where: { id },
  relations: ['project', 'assignedUsers', 'attachments'],
});

// After — removed unused relation:
const entity = await this.repo.findOne({
  where: { id },
  relations: ['project', 'assignedUsers'],
});
```

**Rules:**

- Trace from each find call to the return statement / response mapping to determine which relations are actually accessed
- If a relation is accessed via `entity.relationName` anywhere before the method returns, keep it
- If a relation is never accessed, remove it
- For methods that return raw entities (not mapped to DTOs), keep relations that the controller/caller will need — check the calling code
- Add a brief inline comment for non-obvious relation chains: `// needed for response.projectName`

## Step 5.2 — Migrate deprecated TypeORM APIs

For each deprecated API usage found in Step 0.1:

| Deprecated              | Replacement                                                                   |
| ----------------------- | ----------------------------------------------------------------------------- |
| `getConnection()`       | Inject `DataSource` via constructor                                           |
| `getManager()`          | Inject `EntityManager` via constructor, or use `this.dataSource.manager`      |
| `getRepository(Entity)` | Inject `Repository<Entity>` via constructor using `@InjectRepository(Entity)` |

**Rules:**

- Add the new injection to the constructor
- Update all usages in the service
- If the service was decomposed in Phase 4, add the injection to the correct sub-service
- Register the repository in the module's `imports` if not already: `TypeOrmModule.forFeature([Entity])`

## Step 5.3 — Eliminate "any" types

For each `any` usage found in Step 0.11, apply the appropriate strategy:

| Pattern           | Replacement Strategy                                                                                                                                             |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parameter `: any` | Infer correct type from usage within the function body; use DTO type, entity type, or a type parameter `<T>`                                                     |
| Return `: any`    | Trace the return expression and type accordingly (builds on Step 5.1)                                                                                            |
| Variable `: any`  | Remove explicit annotation if TypeScript can infer; otherwise provide the correct type                                                                           |
| `as any` cast     | Determine why the cast exists: if hiding a type mismatch, fix the mismatch; if for a library limitation, use a more specific cast or `unknown` with a type guard |
| `<any>` generic   | Replace with the actual entity/type (e.g., `Repository<any>` → `Repository<SpecificEntity>`)                                                                     |

**Rules:**

- Do NOT blindly replace `any` with `unknown` everywhere — use actual types
- If the correct type is genuinely unknowable (e.g., third-party callback), use `unknown` with a type guard
- `Record<string, any>` for truly dynamic objects is acceptable but must have a comment explaining why
- After this step, the service should have zero `@typescript-eslint/no-explicit-any` warnings

**Example:**

```typescript
// Before:
async processItems(items: any[]): any {
  const result: any = {};
  items.forEach((item: any) => {
    result[item.id] = item as any;
  });
  return result;
}

// After:
async processItems(items: TaskItem[]): Promise<Record<string, TaskItem>> {
  const result: Record<string, TaskItem> = {};
  for (const item of items) {
    result[item.id] = item;
  }
  return result;
}
```

## Step 5.4 — Comment pass

After all type safety changes, add clarifying comments where logic is not self-evident:

**Where to add comments:**

- Complex TypeORM queries or QueryBuilder chains: explain _what_ the query fetches and _why_
- Non-obvious business logic: explain the business rule being enforced
- Workarounds or hacks: explain what is being worked around and link to ticket if known
- Guard clauses with non-obvious conditions: brief note on what is being guarded
- Public methods: JSDoc with brief description of purpose, params, and return

**Where NOT to add comments:**

- Do NOT restate the code (e.g., `// increment counter` above `counter++`)
- Do NOT add JSDoc to every private method — only complex ones
- Do NOT add comments to self-explanatory CRUD operations
- Do NOT add `@param` JSDoc for params with clear names and types

**Format:**

- Public method descriptions: `/** JSDoc */`
- Inline clarifications: `//` single-line comment
- Target density: roughly one comment per 30-50 lines of non-trivial logic

**Example:**

```typescript
/**
 * Fetches all tasks for a project with workflow status filtering.
 * Returns paginated results with assignee details for the list view.
 */
async findAll(projectID: number, page: number, limit: number): Promise<ITaskListResponse> {
  // Fetch active tasks only — soft-deleted tasks are excluded by global scope
  const query = this.taskRepository
    .createQueryBuilder('task')
    .innerJoin('task.workflowStatus', 'ws')
    // Left join: not all tasks have assignees, but we need the column for sorting
    .leftJoin('task.assignedUsers', 'au')
    .where('task.projectID = :projectID', { projectID });

  // ...
}
```

### GATE 5: Build + ESLint + Prettier

```bash
npm run build 2>&1 | tail -30
npx eslint "<all-touched-files>" --format compact 2>&1
npx prettier --check "<all-touched-files>" 2>&1
```

---

# Phase 6 — Report Generation

Generate a report file at: `docs/reports/refactor-<serviceName>-YYYY-MM-DD.md`

Use today's date for `YYYY-MM-DD`.

## Report Template

```markdown
# <ServiceName> Service Refactor Report — YYYY-MM-DD

## Summary

Refactored `src/modules/<module>/<serviceName>.service.ts`.
Phases applied: async/await migration, code cleanup, error handling & SQL safety,
[decomposition | decomposition skipped], type safety & comments.

All gate checks pass: build ✓, ESLint ✓, Prettier ✓.

---

## Baseline Metrics (Before)

| Metric                                      | Value |
| ------------------------------------------- | ----- |
| Total lines                                 | <n>   |
| Constructor injections                      | <n>   |
| Public methods                              | <n>   |
| .then() chains                              | <n>   |
| Fire-and-forget async                       | <n>   |
| throw new Error()                           | <n>   |
| Raw .query() calls                          | <n>   |
| Deprecated TypeORM APIs                     | <n>   |
| Missing return types                        | <n>   |
| find()/findOne() without explicit relations | <n>   |
| SP duplication candidates                   | <n>   |
| console.log occurrences                     | <n>   |
| "any" type usages                           | <n>   |
| Inline interfaces (extractable)             | <n>   |
| Duplicate code candidates                   | <n>   |
| Hardcoded string duplicates                 | <n>   |
| Unused imports/variables                    | <n>   |
| TODO comments                               | <n>   |

---

## Phase 1 — Async/Await Migration

| File   | Line   | Before                                | After                    |
| ------ | ------ | ------------------------------------- | ------------------------ |
| <file> | <line> | `.then()` chain                       | async/await              |
| <file> | <line> | `.map(async ...)` without Promise.all | `await Promise.all(...)` |
| <file> | <line> | `.forEach(async ...)`                 | `for...of` with await    |

---

## Phase 2 — Code Cleanup

### Unused Code Removed

| File   | Line   | What Was Removed                  |
| ------ | ------ | --------------------------------- |
| <file> | <line> | Unused import: `<import>`         |
| <file> | <line> | Unused variable: `<var>`          |
| <file> | <line> | Unused private method: `<method>` |

### console.log Replaced with Logger

| File   | Line   | Before               | After                    |
| ------ | ------ | -------------------- | ------------------------ |
| <file> | <line> | `console.error(...)` | `this.logger.error(...)` |

### Hardcoded Strings Extracted

| File   | Line   | String        | Extracted To                           |
| ------ | ------ | ------------- | -------------------------------------- |
| <file> | <line> | `'Not found'` | `TASK_MESSAGES.NOT_FOUND` in constants |

### Interfaces Extracted

| Interface         | From (inline)           | To (file)                                |
| ----------------- | ----------------------- | ---------------------------------------- |
| `ITaskListResult` | <service>.service.ts:45 | interfaces/task-list-result.interface.ts |

### Duplicate Code Consolidated

| Description           | Lines Affected | Extracted To                 |
| --------------------- | -------------- | ---------------------------- |
| Date formatting logic | 45-52, 120-127 | <module>.utils.ts#formatDate |

### TODO Comments Audit

| Line | Status             | Content                                |
| ---- | ------------------ | -------------------------------------- |
| 45   | RESOLVED (removed) | // TODO: add validation                |
| 120  | UNRESOLVED         | // TODO(PROJ-123): handle edge case... |
| 200  | STALE (removed)    | // FIXME: old feature flag             |

---

## Phase 3 — Error Handling & SQL Safety

| File   | Line   | Before                               | After                                  |
| ------ | ------ | ------------------------------------ | -------------------------------------- |
| <file> | <line> | `throw new Error('msg')`             | `throw new BadRequestException('msg')` |
| <file> | <line> | `catch (error)` untyped              | `catch (error: unknown)`               |
| <file> | <line> | Raw SQL string interpolation         | Parameterized @0, @1                   |
| <file> | <line> | ~200 lines inline SQL duplicating SP | `EXEC dbo.<SPName> @0, @1`             |

### SQL Query Simplifications

| File   | Line   | JOINs | Before         | After                             |
| ------ | ------ | ----- | -------------- | --------------------------------- |
| <file> | <line> | 2     | Raw `.query()` | `repo.find()` with relations      |
| <file> | <line> | 3     | Raw `.query()` | QueryBuilder with `.getRawMany()` |
| <file> | <line> | 6     | Raw `.query()` | Kept raw, parameterized           |

---

## Phase 4 — Service Decomposition

<!-- If decomposition was performed: -->

| Original Service     | Lines              | Sub-Services Created   | Lines Each    |
| -------------------- | ------------------ | ---------------------- | ------------- |
| <service>.service.ts | <n> → <n> (facade) | <sub1>, <sub2>, <sub3> | <n>, <n>, <n> |

<!-- If decomposition was skipped: -->

Skipped — service is [cohesive/specialized/already decomposed/--no-split flag].

---

## Phase 5 — Type Safety & Comments

### Return Type Annotations Added

| File   | Method    | Return Type Added   |
| ------ | --------- | ------------------- |
| <file> | findAll() | `Promise<Entity[]>` |

### Relation Loading Fixes

| File   | Method    | Line   | Change                                                   |
| ------ | --------- | ------ | -------------------------------------------------------- |
| <file> | findOne() | <line> | Added explicit `relations: ['project', 'assignedUsers']` |
| <file> | findAll() | <line> | Removed over-fetched relation `'attachments'`            |

### Deprecated API Migrations

| File   | Line   | Before                  | After                       |
| ------ | ------ | ----------------------- | --------------------------- |
| <file> | <line> | `getRepository(Entity)` | `@InjectRepository(Entity)` |

### "any" Types Eliminated

| File   | Line   | Category  | Before            | After                    |
| ------ | ------ | --------- | ----------------- | ------------------------ |
| <file> | <line> | PARAMETER | `items: any[]`    | `items: TaskItem[]`      |
| <file> | <line> | CAST      | `as any`          | `as ITaskResult`         |
| <file> | <line> | GENERIC   | `Repository<any>` | `Repository<TaskEntity>` |

### Comments Added

| File   | Line   | Type   | Description                                 |
| ------ | ------ | ------ | ------------------------------------------- |
| <file> | <line> | JSDoc  | Public method: `findAll()` purpose & params |
| <file> | <line> | Inline | Complex query: explains join reasoning      |

---

## Final Metrics (After)

| Metric                               | Before | After | Delta  |
| ------------------------------------ | ------ | ----- | ------ |
| Total lines                          | <n>    | <n>   | <+/-n> |
| Constructor injections               | <n>    | <n>   | <+/-n> |
| .then() chains                       | <n>    | 0     | -<n>   |
| Fire-and-forget async                | <n>    | 0     | -<n>   |
| throw new Error()                    | <n>    | 0     | -<n>   |
| Deprecated TypeORM APIs              | <n>    | 0     | -<n>   |
| Missing return types                 | <n>    | 0     | -<n>   |
| find() without explicit relations    | <n>    | 0     | -<n>   |
| SP duplication (inline SQL replaced) | <n>    | 0     | -<n>   |
| Raw .query() calls                   | <n>    | <n>   | -<n>   |
| console.log occurrences              | <n>    | 0     | -<n>   |
| "any" type usages                    | <n>    | <n>   | -<n>   |
| Inline interfaces                    | <n>    | 0     | -<n>   |
| Duplicate code candidates            | <n>    | 0     | -<n>   |
| Hardcoded string duplicates          | <n>    | 0     | -<n>   |
| Unused imports/variables             | <n>    | 0     | -<n>   |
| TODO comments (unresolved)           | <n>    | <n>   | <+/-n> |

---

## Gate Pass History

| Gate             | Attempts | Notes                               |
| ---------------- | -------- | ----------------------------------- |
| Gate 1 (Async)   | <n>/3    | <brief note if retries were needed> |
| Gate 2 (Cleanup) | <n>/3    | <brief note if retries were needed> |
| Gate 3 (Errors)  | <n>/3    | <brief note if retries were needed> |
| Gate 4 (Decomp)  | <n>/3    | <brief note if retries were needed> |
| Gate 5 (Types)   | <n>/3    | <brief note if retries were needed> |
| Gate 6 (Final)   | <n>/3    | <brief note if retries were needed> |

---

## Remaining Issues

- [ ] <n> raw .query() calls remain — complex SQL Server-specific syntax, kept parameterized
- [ ] <n> "any" types remain — genuinely unknowable types, documented with `unknown` + guard
- [ ] <n> TODO comments unresolved — tracked in backlog
- [ ] <n> field map entries duplicated across modules — extraction deferred to cross-module effort
- [ ] <any other issues flagged during refactoring>

---

## Impacted Files

| File   | Type of Change                  |
| ------ | ------------------------------- |
| <file> | Async/await migration           |
| <file> | Code cleanup (unused, logger)   |
| <file> | Constants extracted             |
| <file> | Interface extracted             |
| <file> | Utils extracted                 |
| <file> | Error handling                  |
| <file> | SQL query simplified            |
| <file> | New sub-service (Phase 4)       |
| <file> | Module registration updated     |
| <file> | Return types / "any" eliminated |
| <file> | Comments added                  |

---

## Verification Results

All verification gates passed.

**Final gate:**
```

npx prettier --check — ✓
npm run build — ✓ (0 errors)
npx eslint — ✓ (0 warnings on touched files)
npx jest — ✓ (tests pass or no tests exist)

```

```

---

# Final Comprehensive Gate (Gate 6)

After Phase 6 report is generated, run the comprehensive final gate on ALL touched files:

```bash
# 1. Prettier formatting (write + check)
npx prettier --write "<all-touched-files>"
npx prettier --check "<all-touched-files>"

# 2. TypeScript compilation (full project)
npm run build

# 3. ESLint on ALL modified files
npx eslint "<all-touched-files>" --format compact

# 4. Run tests (if they exist for this module)
npx jest src/modules/<module>/ --passWithNoTests
```

All 4 must pass in a single run. Max 3 full retries. If ANY check fails, re-run ALL 4 checks from the top (a fix for check #3 might break check #2).

---

# Completion Summary

After the final gate passes, print a concise summary to the user:

```
/refactor-service <serviceName> — COMPLETE

Changes:
- Async/await: <n> .then() chains → async/await, <n> fire-and-forget fixed
- Cleanup: <n> unused imports/vars removed, <n> console.log → Logger, <n> strings extracted
- Interfaces: <n> inline interfaces extracted to dedicated files
- Duplicate code: <n> functions consolidated to utils/helpers
- TODOs: <n> resolved, <n> stale removed, <n> unresolved (in report)
- Error handling: <n> throw Error → HttpException, <n> catch blocks fixed
- SQL safety: <n> raw queries parameterized
- SQL simplified: <n> queries converted to repo.find/QueryBuilder, <n> kept raw (complex)
- SP dedup: <n> inline SQL blocks replaced with existing stored procedures
- Decomposition: <decomposed into N sub-services | skipped (reason)>
- Type safety: <n> return types added, <n> deprecated APIs migrated
- "any" eliminated: <n> removed, <n> remaining (documented)
- Comments: <n> JSDoc + <n> inline comments added
- Formatting: all files pass Prettier check
- Report: docs/reports/refactor-<serviceName>-YYYY-MM-DD.md

All verification gates passed.
```
