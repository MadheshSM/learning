---
name: stabilize-module
description: >
  Comprehensive module stabilization with verification gates: ESLint cleanup, security audit,
  interface extraction, DTO hardening, Swagger coverage, eager loading removal, N+1 fixes,
  error handling, soft-delete audit, notification centralization, service decomposition,
  and change report generation. Each major phase has a build+lint gate with auto-fix loop.
  Usage: /stabilize-module <module-name>
---

Stabilize a NestJS feature module. The target module is: {{ARGS}}

---

# CRITICAL: Verification Gate Protocol

**Every phase ends with a verification gate.** This is the core mechanism that prevents the
"fix one thing, break another" cascade that required multiple runs before.

## Gate Definition

A **verification gate** runs these checks in order:

```bash
# 1. TypeScript compilation
npm run build 2>&1 | tail -30

# 2. ESLint on module + all files touched in this phase
npx eslint "src/modules/{{ARGS}}/**/*.ts" <other-touched-files> --format compact 2>&1

# 3. Prettier check
npx prettier --check "src/modules/{{ARGS}}/**/*.ts" <other-touched-files> 2>&1
```

## Gate Failure → Self-Healing Loop (max 3 retries)

If ANY gate check fails:

1. **Read the error output** — identify exactly which file:line:rule failed
2. **Fix ONLY the failures** — do not re-run the entire phase
3. **Re-run the gate** — verify the fix didn't introduce new failures
4. **If still failing after 3 retries** — STOP, report what's broken, ask user for guidance

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

# Phase 0 — Discovery & Baseline

## Step 0.1 — Identify module files

Locate all source files belonging to this module:

```bash
# Module source files
find src/modules/{{ARGS}}/ -name "*.ts" -not -name "*.spec.ts" | sort

# Spec / test files
find src/modules/{{ARGS}}/ -name "*.spec.ts" | sort
```

Next, read the module's service files to identify which **entities** are injected via
`@InjectRepository(...)`. Search the entities directory for those files:

```bash
grep -rn "@InjectRepository" src/modules/{{ARGS}}/ | grep -oP '\(\K[^)]+' | sort -u
```

Record two lists for later steps:

- **Module files** — all `.ts` files under `src/modules/{{ARGS}}/`
- **Related entity files** — matching files in `src/shared/entities/`

## Step 0.2 — ESLint baseline scan

Run ESLint scoped to the module and capture the full output:

```bash
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format stylish 2>&1
```

Count violations by rule:

```bash
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format json 2>/dev/null | \
  node -e "
    const d=require('fs').readFileSync('/dev/stdin','utf8');
    const j=JSON.parse(d); const c={};
    j.forEach(f=>f.messages.forEach(m=>{ c[m.ruleId]=(c[m.ruleId]||0)+1; }));
    Object.entries(c).sort((a,b)=>b[1]-a[1]).forEach(([r,n])=>console.log(n,r));
  "
```

> **Windows note**: If `/dev/stdin` fails, write JSON to a temp file first and read from disk.

Record the **before** counts — these go into the final report.

## Step 0.3 — Build baseline

```bash
npm run build 2>&1 | tail -20
```

Record whether build passes BEFORE any changes. If it fails, note existing errors so you don't
chase pre-existing issues later.

---

# Phase 1 — ESLint Cleanup + Interface Extraction

## Step 1.1 — Auto-fix pass

```bash
npx eslint "src/modules/{{ARGS}}/**/*.ts" --fix
```

## Step 1.2 — Manual fixes (by rule)

For each remaining violation, apply the established fix pattern:

| Rule                                 | Fix                                                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `eqeqeq`                             | `==` → `===`, `!=` → `!==`                                                                           |
| `@typescript-eslint/no-unused-vars`  | Remove unused imports; prefix unused locals/params with `_`                                          |
| `prefer-const`                       | `let` → `const` where variable is never reassigned                                                   |
| `no-console`                         | Replace `console.log/warn/error` with NestJS `Logger` (inject or use static `Logger`)                |
| `@typescript-eslint/no-explicit-any` | Replace `any` with a proper type or `unknown` (see 1.4 for details)                                  |
| `import/no-cycle`                    | Break circular imports — use `forwardRef()` or restructure                                           |
| `import/order`                       | Reorder imports: builtin → external → internal → parent → sibling → index, blank line between groups |
| `sonarjs/cognitive-complexity`       | Extract helper methods to reduce nesting                                                             |
| `sonarjs/no-duplicate-string`        | Extract repeated strings into constants                                                              |
| `sonarjs/no-identical-functions`     | Extract shared logic into a reusable private method                                                  |
| Other sonarjs rules                  | Follow rule-specific guidance from eslint output                                                     |

## Step 1.2b — Remove dead code

After fixing rule violations, also remove dead code (often flagged by `@typescript-eslint/no-unused-vars`):

- **Unused imports** — delete them entirely
- **Unused private methods/variables** — delete; don't just comment out
- **Unused parameters** — prefix with `_` only if required by an interface/override signature; otherwise remove entirely
- **Unused injected services** — remove constructor params or `inject()` calls never referenced in the class

**`eslint-disable` comments** — when suppression is truly necessary, always explain WHY on the same line:

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party SDK returns untyped response
```

Never suppress without a reason. If you can't explain why, fix the violation instead.

## Step 1.3 — Extract interfaces to `interfaces/` folder

**All interfaces defined inline in service/controller/helper files MUST be extracted to a
dedicated `interfaces/` subfolder within the module.**

### 1.3a — Find all inline interfaces

```bash
grep -rn "^export interface\|^interface " src/modules/{{ARGS}}/ --include="*.ts" \
  | grep -v "interfaces/" | grep -v "dto/" | grep -v ".spec.ts"
```

### 1.3b — Create the interfaces directory

```bash
mkdir -p src/modules/{{ARGS}}/interfaces
```

### 1.3c — Extract each interface

For each interface found:

1. **Create a file** in `interfaces/` following the naming convention:

   - `src/modules/{{ARGS}}/interfaces/<interface-name>.interface.ts`
   - Use kebab-case for filenames: `IRawTaskResult` → `raw-task-result.interface.ts`
   - Group related interfaces in a single file if they're always used together

2. **Create a barrel file** `src/modules/{{ARGS}}/interfaces/index.ts` that re-exports all:

   ```typescript
   export { IRawTaskResult } from './raw-task-result.interface';
   export { IAttachmentData, IImageData } from './attachment-data.interface';
   ```

3. **Update imports** in the original files to use the new path:

   ```typescript
   // Before (inline in service file)
   interface IRawTaskResult {
     taskID: number;
     title: string;
   }

   // After (extracted)
   import { IRawTaskResult } from './interfaces';
   ```

### 1.3d — Interface naming conventions

| Type                      | Convention           | Example                                   |
| ------------------------- | -------------------- | ----------------------------------------- |
| Raw query result          | `I<Entity>RawResult` | `IRfiRawResult`, `ITaskCountResult`       |
| Service method params     | `I<Method>Params`    | `ICreateTaskParams`, `IFilterOptions`     |
| Internal data structures  | `I<Purpose>Data`     | `IAttachmentInsertData`, `IImportRowData` |
| Response shapes (non-DTO) | `I<Entity>Response`  | `IRfiListResponse`                        |
| Configuration/options     | `I<Feature>Options`  | `IExportOptions`, `IQueryOptions`         |

### 1.3e — What NOT to extract

- **DTOs** — these stay in `dto/` (they have class-validator decorators, they're classes not interfaces)
- **Single-property type aliases** — `type ID = number` is fine inline
- **Generic utility types** — if used across modules, put in `@shared`, not the module's `interfaces/`

## Step 1.4 — Fix `@typescript-eslint/no-explicit-any` warnings

This is typically the largest category. For each `any` in the module, classify and apply the appropriate fix:

| Pattern                                                                                                  | Fix                                                                      | Example                                                                                            |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `getUser() as any` on createdBy/modifiedBy                                                               | **Remove the cast** — `User` satisfies the TypeORM column type           | `createdBy: this.requestService.getUser()`                                                         |
| `{ ...fields } as any` for partial entity saves                                                          | **Use `DeepPartial<Entity>`** from typeorm                               | `const entity: DeepPartial<Task> = { ... }`                                                        |
| `.getRawMany()` / `.query()` result typed `any[]`                                                        | **Define a result interface** in `interfaces/` folder                    | `interface IRawTaskResult { taskID: number; title: string; }`                                      |
| `(item: any) =>` in `.map()` / `.forEach()` callbacks                                                    | **Infer from parent array type**, or use the entity/DTO type             | `(item: Task) => item.id`                                                                          |
| External API response (AI, Vault, Autodesk)                                                              | **`eslint-disable-next-line`** with explanation                          | `// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Vault API returns untyped JSON` |
| `catch (error: any)`                                                                                     | **Use `unknown`** + error utility from `src/shared/utils/error.utils.ts` | `catch (error: unknown) { getErrorMessage(error) }`                                                |
| Entity ManyToOne field typed as `User`/`Organization` but is actually a number at runtime (eager: false) | **Use `Number()` cast** at call site to convert to number                | `Number(entity.createdBy)`, `Number(entity.organizationID)`                                        |

**Guidelines:**

- Prefer concrete types over `unknown` — `unknown` is a last resort, not the default
- For raw query results, define an interface in the `interfaces/` folder (created in Step 1.3)
- When adding `DeepPartial`, import from `typeorm`: `import { DeepPartial } from 'typeorm'`
- For `@InjectRepository` entity types, the entity class itself is the correct type for most operations

## Step 1.5 — Suppress security false positives

**`security/detect-object-injection`** — bracket notation on internal data:

- **String-literal bracket access** (`obj['parentId']`): Convert to dot notation (`obj.parentId`)
- **Variable bracket access** (`obj[key]`, `data[index]`): Add suppression comment:
  ```typescript
  // eslint-disable-next-line security/detect-object-injection -- SAFE: key is developer-controlled, not user input
  const value = obj[key];
  ```

**`security/detect-non-literal-fs-filename`** — dynamic path in fs operations:

- All paths in this codebase are constructed from `path.join()` with server-side variables. Add:
  ```typescript
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- SAFE: path built from server-side config
  fs.readFileSync(filePath);
  ```

**`security/detect-unsafe-regex`** — ReDoS-vulnerable patterns:

- Review the regex — if it's on trusted internal data, suppress with explanation
- If it processes user input, rewrite the regex to be safe (avoid nested quantifiers)

**`security/detect-non-literal-regexp`** — dynamic RegExp:

- If the pattern is from internal/trusted source: suppress with comment
- If from user input: sanitize with `escapeRegExp()` or use string methods instead

## Step 1.6 — Fix sonarjs warnings

| Rule                                   | Fix                                                                                                                                     |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `sonarjs/no-duplicate-string`          | Extract repeated string (3+ uses) to a `const` at top of file. For TypeORM alias strings, define `const ALIAS = 'entity_alias'`         |
| `sonarjs/cognitive-complexity`         | Extract sub-logic into private helper methods: validation, notification dispatch, activity event emission. Target: below threshold (15) |
| `sonarjs/no-collapsible-if`            | Merge nested `if` into single `if (a && b)`                                                                                             |
| `sonarjs/prefer-single-boolean-return` | Replace `if (x) return true; return false;` with `return x;`                                                                            |
| `sonarjs/no-duplicated-branches`       | Merge identical if/else branches or extract shared logic                                                                                |
| `sonarjs/no-identical-functions`       | Extract duplicate function body into a shared private method                                                                            |
| `sonarjs/no-useless-catch`             | Remove catch block that only rethrows (let error propagate naturally)                                                                   |
| `sonarjs/no-gratuitous-expressions`    | Remove always-true/false conditions                                                                                                     |
| `sonarjs/no-small-switch`              | Convert 1-case switch to if/else                                                                                                        |

## Step 1.7 — Fix remaining TypeScript warnings

| Rule                           | Fix                                                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `@typescript-eslint/ban-types` | Replace `Object` → `object`, `Function` → `(...args: unknown[]) => unknown`, `{}` → `Record<string, unknown>` |
| `import/namespace`             | Fix namespace imports — e.g., `import * as uuid from 'uuid'` → `import { v4 as uuidv4 } from 'uuid'`          |

---

### GATE 1: ESLint + Build Verification

```bash
# 1. Build
npm run build 2>&1 | tail -30

# 2. ESLint on module
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format compact 2>&1

# 3. Prettier
npx prettier --check "src/modules/{{ARGS}}/**/*.ts" 2>&1
```

**Target**: Zero ESLint errors. Zero build errors. Only acceptable warnings: `import/no-cycle` (structural).

**If gate fails**: Read errors, fix them, re-run gate. Max 3 retries.

**IMPORTANT**: If fixing a gate failure introduces NEW warnings/errors (e.g., removing an import
causes an unused-var in another file), fix those too before re-running the gate. Follow the chain.

---

# Phase 2 — Database & Performance

## Step 2.1 — Remove `eager: true` from entity relations

For each entity identified in Phase 0, search for `eager: true`:

```bash
grep -n "eager: true" src/shared/entities/<entity-file>.ts
```

**For every occurrence:**

1. **Remove** `eager: true` from the relation decorator (or set `eager: false`)
2. **Search the module's service files** for queries on that entity:
   ```bash
   grep -rn "find\|findOne\|findAndCount\|createQueryBuilder" src/modules/{{ARGS}}/
   ```
3. **Add explicit `relations: ['relationName']`** only where the relation data is actually
   used in the response or business logic. Example:

   ```typescript
   // Before (eager: true on entity — loads relation on EVERY query)
   const doc = await this.docRepo.findOne({ where: { id } });

   // After (eager removed — explicit relation only where needed)
   const doc = await this.docRepo.findOne({
     where: { id },
     relations: ['project', 'folder'],
   });
   ```

4. For `createQueryBuilder` calls, add `.leftJoinAndSelect()` only where needed.

**Why this matters**: `eager: true` on BaseEntity's `createdBy`/`modifiedBy` alone forces
2 extra User LEFT JOINs on every query across 125+ entities. Cascading eager loads produce
18-22+ JOINs for a single `findOne()`. Removing them yields 40-60% query time reduction.

> **Caution**: Do NOT remove `eager: true` from entities outside this module's scope unless
> you verify no other module depends on the eager load. Check cross-module usage:
>
> ```bash
> grep -rn "EntityName" src/modules/ --include="*.ts" | grep -v "{{ARGS}}" | head -20
> ```

## Step 2.2 — Fix N+1 database query patterns

Search the module's services for common N+1 patterns:

### 2.2a — Loop-based DB queries

```bash
grep -n "\.forEach\|\.map\|for (" src/modules/{{ARGS}}/**/*.service.ts | \
  grep -i "find\|query\|save\|update\|delete"
```

**Fix pattern**: Replace per-item queries with batch operations:

```typescript
// BAD — N+1: one query per item
for (const id of ids) {
  const item = await this.repo.findOne({ where: { id } });
  results.push(item);
}

// GOOD — single batch query
const results = await this.repo.find({
  where: { id: In(ids) },
});
```

### 2.2b — Fire-and-forget async patterns

```bash
grep -n "\.forEach(async\|\.map(async" src/modules/{{ARGS}}/**/*.ts
```

**Fix pattern**: Wrap in `Promise.all()`:

```typescript
// BAD — fire-and-forget, silent failures
items.forEach(async (item) => {
  await this.repo.save(item);
});

// GOOD — awaited, errors propagate
await Promise.all(
  items.map(async (item) => {
    await this.repo.save(item);
  }),
);
```

### 2.2c — Unbatched save/update operations

Look for `.save()` or `.update()` inside loops — replace with bulk operations:

```typescript
// BAD
for (const entity of entities) {
  await this.repo.save(entity);
}

// GOOD
await this.repo.save(entities); // TypeORM .save() accepts arrays
```

## Step 2.3 — Soft-delete filter audit

### 2.3a — Check which entities extend BaseEntity

For each entity injected via `@InjectRepository` in this module:

```bash
grep -n "extends BaseEntity" src/shared/entities/<entity>.entity.ts
```

**BaseEntity has `@DeleteDateColumn`**, which means TypeORM **automatically** adds `WHERE deletedAt IS NULL` to all `find*()` calls on entities that extend it.

### 2.3b — Remove redundant manual filters

For entities that **extend BaseEntity**, search for manual `deletedAt` filters:

```bash
grep -rn "deletedAt.*IsNull\|deletedAt.*null\|deletedAt: null" src/modules/{{ARGS}}/ --include="*.ts"
```

**Remove** all redundant `deletedAt: IsNull()` and `deletedAt: null` conditions — they're already handled by `@DeleteDateColumn`.

### 2.3c — Verify entities that do NOT extend BaseEntity

For entities that do **NOT** extend BaseEntity but have a `deletedAt` column (plain `@Column`):

- The manual `deletedAt` filter is **NOT redundant** — keep it
- Document in the report which entities lack auto-filtering

**Important**: Do NOT modify entities outside this module's scope. If widespread `deletedAt` cleanup is needed, flag it for a separate PR.

---

### GATE 2: Build + ESLint after DB/Performance changes

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/{{ARGS}}/**/*.ts" <entity-files-touched> --format compact 2>&1
```

**Why this gate matters**: Removing `eager: true` often causes runtime property access on
`undefined` relations. The build may not catch these (TypeScript can't know runtime query
shapes), but ESLint + type checks catch many. Also, removing `deletedAt` filters or changing
queries can introduce new unused-import warnings.

**If gate fails**: Fix, re-run. Max 3 retries.

---

# Phase 3 — Security Hardening

## Step 3.1 — SQL injection in raw queries

Search for raw SQL with string interpolation:

```bash
grep -rn "\.query(" src/modules/{{ARGS}}/ --include="*.ts"
grep -rn "template literal\|\\${\|string interpolation" src/modules/{{ARGS}}/ --include="*.ts"
```

**For every `.query()` call:**

1. Check if user input or request body data is interpolated into SQL strings
2. Replace string interpolation with positional parameters (`@0`, `@1`, `@2`):

```typescript
// BAD — SQL injection via string interpolation
const result = await this.dataSource.query(
  `SELECT * FROM task WHERE projectID = ${projectId} AND module = '${module}'`,
);

// GOOD — parameterized query
const result = await this.dataSource.query(
  `SELECT * FROM task WHERE projectID = @0 AND module = @1`,
  [projectId, module],
);
```

3. For `JSON.stringify()` interpolated into SQL `DECLARE` statements, pass as a parameter instead
4. For dynamic temp table names (`#Tmp_${variable}`), use static names (MSSQL temp tables are session-scoped)

## Step 3.2 — Route parameter validation

Check controller for unvalidated route params:

```bash
grep -rn "@Param(" src/modules/{{ARGS}}/ --include="*.controller.ts"
```

**Apply these validations:**

| Param pattern                           | Required validation           | Example                                               |
| --------------------------------------- | ----------------------------- | ----------------------------------------------------- |
| `:projectId`, `:taskId`, any numeric ID | `ParseIntPipe`                | `@Param('projectId', ParseIntPipe) projectId: number` |
| `:module`                               | `ParseModulePipe` (allowlist) | `@Param('module', ParseModulePipe) module: string`    |
| Any string param used in SQL            | Validate/sanitize before use  | Allowlist or regex check                              |

**`ParseModulePipe`** validates against an allowlist of valid module slugs. If it doesn't exist yet, create `src/shared/pipes/parse-module.pipe.ts`:

```typescript
import { PipeTransform, Injectable, BadRequestException } from '@nestjs/common';

const VALID_MODULES = [
  'design',
  'construction',
  'commissioning',
  'task',
  'rfa',
  'rfi',
  'issue',
  'plan',
  'submittal',
  'transmittal',
  'bom',
  'punch-list',
  'check-list',
  'document',
  'ticket',
  'meeting',
  'form',
  'hour',
] as const;

@Injectable()
export class ParseModulePipe implements PipeTransform<string, string> {
  transform(value: string): string {
    if (!VALID_MODULES.includes(value as typeof VALID_MODULES[number])) {
      throw new BadRequestException('Invalid module parameter');
    }
    return value;
  }
}
```

## Step 3.3 — Transaction boundaries for batch/import operations

Search for import or batch operations without transaction wrapping:

```bash
grep -rn "import\|batch\|bulk" src/modules/{{ARGS}}/ --include="*.service.ts" -i
```

**If the module has import/batch operations** that create/update multiple records:

1. Check if they use `queryRunner.startTransaction()` / `commitTransaction()` / `rollbackTransaction()`
2. If not, wrap in a transaction to ensure atomicity:

```typescript
const queryRunner = this.dataSource.createQueryRunner();
await queryRunner.connect();
await queryRunner.startTransaction();
try {
  for (const row of importedRows) {
    await queryRunner.manager.save(Entity, row);
  }
  await queryRunner.commitTransaction();
} catch (error) {
  await queryRunner.rollbackTransaction();
  throw error;
} finally {
  await queryRunner.release();
}
```

---

### GATE 3: Build + ESLint after Security changes

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format compact 2>&1
```

**If gate fails**: Fix, re-run. Max 3 retries. Security changes often introduce new imports
(`ParseIntPipe`, `DataSource`) — verify they're used and not duplicated.

---

# Phase 4 — DTO Hardening + Swagger

## Step 4.1 — Replace inline `@Body()` types with proper DTOs

Search for inline type annotations on `@Body()` parameters:

```bash
grep -rn "@Body()" src/modules/{{ARGS}}/ --include="*.controller.ts"
```

**Replace any inline types with proper DTO classes:**

```typescript
// BAD — inline types, no validation
@Post('bulk-delete')
async remove(@Body() idLst: { task: number[] }) { }

@Post('attachments')
async getAttachments(@Body() data: { type?: string }) { }

// GOOD — proper DTOs with class-validator decorators
@Post('bulk-delete')
async remove(@Body() dto: TaskBulkDeleteDto) { }

@Post('attachments')
async getAttachments(@Body() dto: GetAttachmentsDto) { }
```

**DTO requirements:**

- Every field has `@IsString()`, `@IsNumber()`, `@IsArray()`, `@IsOptional()`, etc. from `class-validator`
- Every field has `@ApiProperty({ description: '...' })` from `@nestjs/swagger`
- Array fields use `{ each: true }` validation: `@IsNumber({}, { each: true })`
- Optional fields use `@IsOptional()` before other validators
- Place DTOs in `dto/` subdirectory, organized as `dto/request/` and `dto/response/` if >4 DTOs

## Step 4.2 — Fix existing DTO validation gaps

Check for commented-out validators in existing DTOs:

```bash
grep -rn "// @Is\|// @IsNot\|//@Is" src/modules/{{ARGS}}/dto/ --include="*.ts"
```

For each commented-out validator:

1. Check the DB schema (is the column nullable?)
2. Check frontend usage (does the form always send this field?)
3. Either **re-enable** the validator or **remove the dead code** with a comment explaining why

## Step 4.3 — Split large DTO files

If any DTO file exceeds 150 lines, split by purpose:

| Before                                  | After                                                                   |
| --------------------------------------- | ----------------------------------------------------------------------- |
| `task-response.dto.ts` (400+ lines)     | `dto/response/task-list-item.dto.ts`, `dto/response/task-detail.dto.ts` |
| Shared sub-DTOs duplicated across files | `dto/shared/attachment.dto.ts`, `dto/shared/assigned-user.dto.ts`       |

## Step 4.4 — Swagger decorator audit

Check every controller endpoint for complete Swagger coverage:

```bash
grep -rn "@ApiOperation\|@ApiResponse\|@ApiTags\|@ApiParam\|@ApiBody" src/modules/{{ARGS}}/ --include="*.controller.ts"
```

**Required decorators per endpoint:**

| Decorator                                                  | Where                      | Required?                 |
| ---------------------------------------------------------- | -------------------------- | ------------------------- |
| `@ApiTags('ModuleName')`                                   | Class level                | Yes — every controller    |
| `@ApiOperation({ summary: '...' })`                        | Every handler              | Yes                       |
| `@ApiResponse({ status: 200, type: StandardResponseDto })` | Every handler              | Yes (one per status code) |
| `@ApiParam({ name: 'projectId', type: Number })`           | Handlers with route params | Yes                       |
| `@ApiBody({ type: SomeDto })`                              | Handlers with `@Body()`    | Yes                       |

**Fix duplicate `@ApiResponse`** — only one per status code per endpoint:

```bash
# Find duplicates: same decorator appears twice on adjacent lines
grep -n "@ApiResponse" src/modules/{{ARGS}}/ --include="*.controller.ts" -A1
```

---

### GATE 4: Build + ESLint after DTO/Swagger changes

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format compact 2>&1
```

**Common failures at this gate:**

- New DTO files with missing imports (class-validator, swagger)
- Unused old inline type imports after switching to DTOs
- DTO property type mismatches with service expectations

**If gate fails**: Fix, re-run. Max 3 retries.

---

# Phase 5 — Error Handling + Code Quality

## Step 5.1 — Replace `.then()` chains with async/await

```bash
grep -rn "\.then(" src/modules/{{ARGS}}/ --include="*.service.ts"
grep -rn "\.then(" src/modules/{{ARGS}}/ --include="*.controller.ts"
```

Convert all `.then()` chains to `async/await`:

```typescript
// BAD
this.repo
  .save(entity)
  .then((result) => {
    this.eventEmitter.emit('activity', result);
  })
  .catch((err) => {
    console.error(err);
  });

// GOOD
try {
  const result = await this.repo.save(entity);
  this.eventEmitter.emit('activity', result);
} catch (error: unknown) {
  this.logger.error(getErrorMessage(error), getErrorStack(error));
}
```

## Step 5.2 — Fix silent catch blocks

```bash
grep -rn "catch" src/modules/{{ARGS}}/ --include="*.service.ts" -A3
```

**For every `catch` block:**

1. Use `catch (error: unknown)` — never `catch (error: any)` or `catch (e)`
2. Use error utilities from `src/shared/utils/error.utils.ts`: `getErrorMessage(error)`, `getErrorStack(error)`
3. Either **rethrow** as a proper NestJS exception or **log with context**
4. Never silently swallow errors without a documented reason

```typescript
// BAD — silent catch
catch (e) {
  console.log(e);
}

// GOOD — typed, logged, and re-thrown or handled
catch (error: unknown) {
  this.logger.error(
    `Failed to update task ${taskId}: ${getErrorMessage(error)}`,
    getErrorStack(error),
  );
  throw new InternalServerErrorException('Failed to update task');
}
```

## Step 5.3 — Standardize exception types

Ensure consistent NestJS exception usage:

| Scenario               | Exception               | Status |
| ---------------------- | ----------------------- | ------ |
| Entity not found       | `NotFoundException`     | 404    |
| Validation failure     | `BadRequestException`   | 400    |
| Permission/lock denial | `ForbiddenException`    | 403    |
| Duplicate detection    | `ConflictException`     | 409    |
| Unauthorized           | `UnauthorizedException` | 401    |

**Do NOT** use generic `HttpException(message, statusCode)` when a specific exception class exists.

## Step 5.4 — Audit fire-and-forget calls

```bash
grep -rn "void\|// fire-and-forget\|\.emit(" src/modules/{{ARGS}}/ --include="*.service.ts"
```

For any async call that is intentionally not awaited, add an explicit `void` prefix with a comment:

```typescript
// fire-and-forget: notification failure should not block task creation
void this.notificationGateway.sendNotification(payload);
```

## Step 5.5 — Extract magic strings/numbers to constants

### 5.5a — Magic strings → constants or enums

**Check existing constants first** — reuse if one already exists:

- Entity name strings repeated in queries (e.g., `'task'`, `'document'`)
- TypeORM alias strings (e.g., `'doc'`, `'prj'`) — define `const ALIAS = 'entity_alias'` at top of file
- Error messages repeated across methods — extract to a `MESSAGES` const object
- Event names (e.g., `'create_activity'`, `'update_activity'`) — use existing `CreateActivityEvent` etc.

**What to extract:**

- Repeated string literals used in comparisons (`=== 'edit'`, `=== 'admin'`) — create a local const or enum
- SQL query fragments repeated across methods — extract to a `const` at top of file
- Configuration values (paths, URLs, header keys) — extract to module-level constants
- Hardcoded entity field names used in `QueryBuilder` calls — extract to a fields const if repeated 3+ times

**What NOT to extract:**

- Unique one-off strings (an error message used exactly once is fine inline)
- TypeORM relation names in `relations: [...]` arrays (they mirror entity property names)
- Single-use SQL alias strings in QueryBuilder chains

### 5.5b — Magic numbers → named constants

- Hardcoded numbers like `50` (timeout), `1000` (limit), `30` (days) — extract to named constants if they represent a domain concept
- Array indices, `findIndex !== -1` checks — acceptable as-is
- Page sizes, limits — should use config or environment variables

### 5.5c — Boolean/conditional patterns

- Replace `condition ? true : false` with just `condition` (or `!!condition` if coercion needed)
- Replace `value === true` with `value`, `value === false` with `!value`

## Step 5.6 — Variable naming, spelling, and code style audit

### 5.6a — Naming conventions

Verify every identifier follows NestJS/TypeScript conventions:

| Type                             | Convention                               | Example                                       |
| -------------------------------- | ---------------------------------------- | --------------------------------------------- |
| Classes/Interfaces/Enums         | `PascalCase`                             | `TaskService`, `ITaskResult`, `ProjectEntity` |
| Variables/properties/methods     | `camelCase`                              | `taskId`, `getTaskList`, `isLoading`          |
| Constants (module-level)         | `camelCase` or `UPPER_SNAKE_CASE`        | `defaultPageSize`, `MAX_RETRIES`              |
| Private fields                   | Prefix with `_` for injected services    | `private readonly _taskRepo`                  |
| Boolean properties               | Prefix with `is`, `has`, `can`, `should` | `isActive`, `hasPermission`, `canEdit`        |
| Interfaces for raw query results | Prefix with `I`                          | `IRawTaskResult`, `ITaskCountResult`          |

**Flag and fix:**

- Abbreviated names that are unclear: `res` → `response`, `req` → `request` (except in standard NestJS controller params), `e` → `error`, `x` → descriptive name
- Single-letter variables outside of arrow functions with obvious context
- Inconsistent naming within the same file (e.g., `detail` vs `taskDetail` for the same concept)

### 5.6b — Spelling check

Scan all identifiers (variable names, method names, property names, interface fields) for obvious misspellings:

- Common project misspellings: `attachmnet` → `attachment`, `premission` → `permission`, `conformation` → `confirmation`, `destory` → `destroy`
- Check string literals in error messages and log statements for typos
- **Do NOT rename shared entities or columns** that have misspelled names — these require a database migration. Flag them but do not fix.

### 5.6c — Comments audit

- **`eslint-disable` lines** — MUST always explain WHY (e.g., `// eslint-disable-next-line ... -- third-party SDK returns untyped response`)
- **Workarounds or hacks** — add a brief comment explaining why
- **Complex business logic** — add comment if not clear from variable/method names
- **Do NOT add comments that restate what the code does** (e.g., `// Get task by ID` above `getTaskById()`)
- **Do NOT add JSDoc to every method** — only where the signature alone is ambiguous

---

### GATE 5: Build + ESLint after Error Handling + Code Quality

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format compact 2>&1
npx prettier --check "src/modules/{{ARGS}}/**/*.ts" 2>&1
```

**Common failures at this gate:**

- `.then()` → `async/await` conversion introduces missing `await` or changes return type
- New `Logger` imports added but NestJS Logger not properly instantiated
- Constants extracted but old string literal still referenced somewhere
- Variable renames break references in other methods within same file

**If gate fails**: Fix, re-run. Max 3 retries.

---

# Phase 6 — Structural Changes

## Step 6.1 — Notification centralization audit

Check whether the module's services bypass the centralized notification system by building notification
objects inline or writing directly to `notificationRepository`.

### 6.1a — Scan for inline notification patterns

```bash
# Direct notificationRepository usage (bypass pattern)
grep -rn "notificationRepository\.\(save\|insert\|create\)" src/modules/{{ARGS}}/ --include="*.ts"

# Inline notification object construction (assignedUser + metaData + createdBy pattern)
grep -rn "assignedUser.*metaData\|metaData.*assignedUser" src/modules/{{ARGS}}/ --include="*.ts"

# Direct bulkNotificationCreate / singleNotificationCreate calls that build objects inline
grep -rn "bulkNotificationCreate\|singleNotificationCreate" src/modules/{{ARGS}}/ --include="*.ts" -A 5
```

### 6.1b — Refactor to use NotificationOrchestrationService

For each inline notification block found, determine which service method to use:

| Pattern                               | Service method                                                                              |
| ------------------------------------- | ------------------------------------------------------------------------------------------- |
| Single user notification              | `notificationService.notifySingleUser(userId, params)`                                      |
| Multiple specific user IDs            | `notificationService.notifyUsers(userIds, params)`                                          |
| All project users + owner             | `notificationService.notifyProjectUsers(projectId, module, orgId, params)`                  |
| Need recipients list for custom logic | `notificationService.resolveProjectRecipients(projectId, module, orgId)` then `notifyUsers` |
| Contains USER_GROUP entries to expand | `notificationService.expandUserGroups(assignments)` then `notifyUsers`                      |

**NotifyParams interface:**

```typescript
import { NotifyParams } from '@shared/interfaces/notification.interface';

// params object shape:
{
  title: string;
  entityType: string;
  entityID: number;
  message: string | null;
  metaData: string | object;
  createdBy: any;
  organizationID: any;
}
```

**Refactoring rules:**

1. Replace `notificationRepository.save({...})` with the appropriate service method
2. Replace inline `.map(userId => ({ title, entityType, ... assignedUser: userId }))` + `bulkNotificationCreate()` with `notifyUsers(userIds, params)`
3. Replace manual project-user resolution (`projectUserService.findAll` + user-group expansion + project-owner append + dedup) with `notifyProjectUsers(projectId, module, orgId, params)`
4. If the service doesn't inject `NotificationOrchestrationService`, add it:
   ```typescript
   constructor(
     private readonly notificationService: NotificationOrchestrationService,
     // ... existing deps
   ) {}
   ```
5. Remove `@InjectRepository(Notification)` if it was only used for inline notification saves
6. Remove unused imports (`Notification` entity, `ProjectUserService` if only used for notification recipient resolution)
7. **Delete duplicate helper methods** — services often have private `getUserIDs()` and `getProjectUserDetails()` methods that duplicate `NotificationOrchestrationService.expandUserGroups()` and `resolveProjectRecipients()`. Delete them after migrating callers.
8. Remove `@InjectRepository(UserGroupMember)` if it was only used by the deleted helper methods (check for other usages first)

### 6.1c — Check ActivityListener handlers for this module's events

```bash
# Find event names emitted by this module
grep -rn "eventEmitter\.emit\|this\.emitter\.emit" src/modules/{{ARGS}}/ --include="*.ts" | grep -oP "'[^']+'" | sort -u
```

## Step 6.2 — Service decomposition (if needed)

### File size thresholds

| Threshold   | File type        | Action                                                                                     |
| ----------- | ---------------- | ------------------------------------------------------------------------------------------ |
| > 700 lines | `.service.ts`    | **Decompose** using facade + injectable sub-services pattern (see below)                   |
| > 500 lines | `.service.ts`    | Review — consider extracting into a helper file or splitting by responsibility             |
| > 200 lines | `.controller.ts` | Review — consider splitting into sub-controllers by responsibility                         |
| > 150 lines | `.helper.ts`     | Review — may be fine if many pure functions, but check for logic that belongs in a service |
| > 100 lines | `.dto.ts`        | Review — consider splitting into separate DTO files per endpoint                           |

**Service decomposition pattern (for services >700 lines):**

When a service exceeds 700 lines and has clearly separable concerns (CRUD, import/export, workflow, etc.):

1. **Create sub-services** in a `services/` subdirectory — each gets its own constructor dependencies
2. **Keep the original service as a facade** (~200 lines) that delegates to sub-services
3. **Controller interface stays unchanged** — no other module needs to change
4. **Each sub-service** should be <700 lines with 4-8 constructor dependencies max
5. **Register sub-services** in the module's `providers` array

```
// Example decomposition:
ModuleService (facade, ~200 lines)
  ├── delegates to: ModuleCrudService (~600 lines)
  ├── delegates to: ModuleImportExportService (~500 lines)
  └── delegates to: ModuleWorkflowService (~200 lines)
```

**Facade justification**: The facade orchestrates cross-cutting concerns (activity events, notifications, transaction coordination). It is NOT a pass-through anti-pattern when it genuinely coordinates between sub-services.

**Do NOT split files just to meet a threshold.** Only split when there is a clear separation of concerns. Flag large files in the report with a brief assessment of whether splitting is warranted.

**Controller splitting pattern (for controllers >200 lines):**

Split by responsibility domain:

| Controller                             | Purpose                | Example endpoints                        |
| -------------------------------------- | ---------------------- | ---------------------------------------- |
| `{{ARGS}}.controller.ts`               | CRUD + core operations | findAll, findOne, create, update, delete |
| `{{ARGS}}-import-export.controller.ts` | Import/export          | importFile, exportFile                   |
| `{{ARGS}}-lock.controller.ts`          | Entity locking         | lock, unlock, checkLock                  |

## Step 6.3 — Controller decorator cleanup

Check for opportunities to use shared decorators:

```bash
grep -rn "@UseGuards(AuthGuard, ValidateProjectGuard)" src/modules/{{ARGS}}/ --include="*.controller.ts"
```

**Replace with `@ProjectScoped()`** composite decorator (from `@decorators`):

```typescript
// Before (repeated on 15+ controllers):
@UseGuards(AuthGuard, ValidateProjectGuard)

// After:
@ProjectScoped()
```

> **Caution**: Do NOT apply `@ProjectScoped()` at class level if some endpoints intentionally skip project validation (e.g., cross-project references, lock endpoints). Keep per-method placement in those cases.

---

### GATE 6: Build + ESLint after Structural changes

```bash
npm run build 2>&1 | tail -30
npx eslint "src/modules/{{ARGS}}/**/*.ts" --format compact 2>&1
```

**Common failures at this gate:**

- Service decomposition breaks DI — module.ts `providers` missing new sub-services
- Notification refactoring removes a repository that's still used for non-notification queries
- Service decomposition creates new unused imports in the facade
- New sub-services missing imports for decorators or entities

**If gate fails**: Fix, re-run. Max 3 retries.

---

# Phase 7 — Final Sweep + Unused Code

## Step 7.1 — Unused code final sweep

Run a comprehensive check for unused code across the entire module:

```bash
# Check for unused imports/vars (ESLint catches most)
npx eslint "src/modules/{{ARGS}}/**/*.ts" --quiet --rule '{"@typescript-eslint/no-unused-vars": "error"}'

# Check if module exports are imported anywhere else in the project
grep -rn "from.*{{ARGS}}" --include="*.ts" src/ | grep -v node_modules | grep -v "src/modules/{{ARGS}}/"
```

**Checklist:**

- [ ] No unused imports in any `.ts` file
- [ ] No unused class properties (declared but never read)
- [ ] No unused methods (defined but never called from controller, other service, or event listener)
- [ ] No unused injected services (constructor params or `@InjectRepository()` never referenced)
- [ ] No empty methods (empty constructor bodies are OK if DI params exist)
- [ ] No commented-out code blocks (delete them — git has the history)
- [ ] No `console.log`, `console.warn`, `console.error` calls (use NestJS `Logger`)
- [ ] No duplicate type declarations (same interface defined in multiple files)
- [ ] No unused DTO properties (fields defined but never validated or consumed)

## Step 7.2 — Code simplification pass

After all stabilization edits are complete, run the **code-simplifier** agent on all modified files in the module.

**Invoke the code-simplifier agent:**

```
Use the Agent tool with subagent_type="pr-review-toolkit:code-simplifier"
Prompt: "Simplify and refine all recently modified code in src/modules/{{ARGS}}/ for clarity, consistency, and maintainability while preserving all functionality."
```

**What the simplifier checks:**

- Redundant or duplicated logic that can be consolidated
- Overly complex expressions that can be simplified
- Opportunities to reuse existing shared utilities from `@shared`
- Unnecessary type assertions or casts
- Verbose patterns that have cleaner TypeScript/NestJS idioms
- Dead branches or unreachable code paths
- Inconsistent patterns within the same file (e.g., mixing `if/else` and early returns)

**What it does NOT do:**

- Does NOT add new features or change behavior
- Does NOT restructure files or move code between files
- Does NOT modify test files

**Review the simplifier's output** — accept changes that improve clarity, reject changes that alter behavior or add unnecessary abstraction.

---

### GATE 7 (FINAL GATE): Full verification

This is the comprehensive final check. ALL must pass.

```bash
# 1. Prettier formatting
npx prettier --write "src/modules/{{ARGS}}/**/*.ts"
npx prettier --check "src/modules/{{ARGS}}/**/*.ts"

# 2. TypeScript compilation (full project)
npm run build

# 3. ESLint on ALL modified files (module + entities + shared)
npx eslint "src/modules/{{ARGS}}/**/*.ts" <all-other-touched-files> --format compact

# 4. Run tests
npx jest src/modules/{{ARGS}}/ --passWithNoTests

# 5. Application startup check (verify no DI errors)
timeout 15 npm run start:dev 2>&1 | tail -20
```

Look for `Nest application successfully started` in the output. If you see
`Nest can't resolve dependencies`, a relation or import was broken — fix it.

**If ANY check fails**: Fix the issue, then re-run ALL 5 checks from the top (not just the failed one).
A fix for check #3 might break check #2. Max 3 full retries.

**Module is NOT done until ALL 5 checks pass in a single run.**

---

# Phase 8 — Report + Commit

## Step 8.1 — Generate change report

Create a report file at:

```
docs/reports/stabilize-{{ARGS}}-YYYY-MM-DD.md
```

Use today's date. The report must follow this template:

```markdown
# Module Stabilization Report: {{ARGS}}

**Date**: YYYY-MM-DD
**Branch**: <current git branch>

---

## Summary

<2-3 sentence summary of what was done and why>

---

## ESLint Violations Fixed (Errors + Warnings)

| Rule      | Before      | After       | Delta        |
| --------- | ----------- | ----------- | ------------ |
| <rule-id> | <count>     | <count>     | -<count>     |
| ...       | ...         | ...         | ...          |
| **Total** | **<total>** | **<total>** | **-<total>** |

---

## Interfaces Extracted

| Interface Name | Source File (before)  | New Location                         |
| -------------- | --------------------- | ------------------------------------ |
| `IRawResult`   | `<module>.service.ts` | `interfaces/raw-result.interface.ts` |
| ...            | ...                   | ...                                  |

---

## Security Fixes

| File   | Line   | Issue                     | Fix Applied                        |
| ------ | ------ | ------------------------- | ---------------------------------- |
| <file> | <line> | SQL injection via interp. | Parameterized with @0/@1           |
| <file> | <line> | Unvalidated :module param | Added ParseModulePipe              |
| <file> | <line> | Missing ParseIntPipe      | Added to :projectId/:taskId params |
| ...    | ...    | ...                       | ...                                |

---

## DTO Hardening

| Before (inline type)     | After (DTO class)      | Validators Added             |
| ------------------------ | ---------------------- | ---------------------------- |
| `@Body() data: { x: y }` | `@Body() dto: SomeDto` | @IsNumber, @IsOptional, etc. |
| ...                      | ...                    | ...                          |

---

## Swagger Coverage

| Fix Type                     | Count | Details           |
| ---------------------------- | ----- | ----------------- |
| Missing @ApiTags added       | <n>   | <controller list> |
| Missing @ApiOperation added  | <n>   | <endpoint list>   |
| Duplicate @ApiResponse fixed | <n>   | <endpoint list>   |
| Missing @ApiParam added      | <n>   | <param list>      |

---

## Eager Loading Removals

| Entity File        | Relation Field | Target Entity  | Explicit `relations` Added In           |
| ------------------ | -------------- | -------------- | --------------------------------------- |
| <entity>.entity.ts | <field>        | <TargetEntity> | <service-file>:<line> (or "Not needed") |
| ...                | ...            | ...            | ...                                     |

---

## N+1 Query Fixes

| File   | Line   | Pattern            | Fix Applied                 |
| ------ | ------ | ------------------ | --------------------------- |
| <file> | <line> | forEach(async ...) | Promise.all(map(async ...)) |
| <file> | <line> | find() in loop     | Batch query with In()       |
| ...    | ...    | ...                | ...                         |

---

## Error Handling Fixes

| File   | Line   | Before                      | After                                     |
| ------ | ------ | --------------------------- | ----------------------------------------- |
| <file> | <line> | `.then()` chain             | async/await                               |
| <file> | <line> | `catch (e) { console.log }` | `catch (error: unknown) { logger.error }` |
| <file> | <line> | Generic HttpException       | NotFoundException                         |
| ...    | ...    | ...                         | ...                                       |

---

## Soft-Delete Filter Audit

| Entity       | Extends BaseEntity? | Manual filters removed | Manual filters kept (reason)   |
| ------------ | ------------------- | ---------------------- | ------------------------------ |
| <EntityName> | Yes / No            | <count>                | <count> — no @DeleteDateColumn |
| ...          | ...                 | ...                    | ...                            |

---

## Service Decomposition (if applicable)

| Original Service    | Lines | Sub-Services Created   | Lines Each    |
| ------------------- | ----- | ---------------------- | ------------- |
| <module>.service.ts | <n>   | <sub1>, <sub2>, <sub3> | <n>, <n>, <n> |

---

## Magic Strings/Numbers Extracted

| File   | Before (hardcoded)   | After (constant/enum)          |
| ------ | -------------------- | ------------------------------ |
| <file> | `'entity_alias'` x 5 | `const ALIAS = 'entity_alias'` |
| ...    | ...                  | ...                            |

---

## Naming/Spelling Fixes

| File   | Before | After      | Reason  |
| ------ | ------ | ---------- | ------- |
| <file> | `res`  | `response` | Clarity |
| ...    | ...    | ...        | ...     |

---

## File Size Flags

| File   | Lines | Threshold | Assessment                              |
| ------ | ----- | --------- | --------------------------------------- |
| <file> | <n>   | >700      | Decomposed into facade + 3 sub-services |
| <file> | <n>   | >500      | OK — many HTTP methods / Needs split    |
| ...    | ...   | ...       | ...                                     |

---

## Impacted Files

| File                                   | Type of Change              |
| -------------------------------------- | --------------------------- |
| src/modules/{{ARGS}}/<file>.ts         | ESLint fixes                |
| src/modules/{{ARGS}}/<file>.ts         | Security: SQL parameterized |
| src/modules/{{ARGS}}/<file>.ts         | DTO hardening               |
| src/modules/{{ARGS}}/<file>.ts         | Error handling              |
| src/modules/{{ARGS}}/interfaces/\*.ts  | Interface extraction        |
| src/shared/entities/<entity>.entity.ts | Removed eager: true         |
| ...                                    | ...                         |

---

## Verification Results

| Check                   | Result                  |
| ----------------------- | ----------------------- |
| `npm run build`         | PASS / FAIL             |
| ESLint (modified files) | 0 errors, 0 warnings    |
| Prettier                | 0 differences           |
| `npx jest`              | PASS / FAIL (<n> tests) |
| Application startup     | PASS / FAIL             |

---

## Gate Pass History

| Gate   | Attempts | Notes                               |
| ------ | -------- | ----------------------------------- |
| Gate 1 | <n>/3    | <brief note if retries were needed> |
| Gate 2 | <n>/3    | <brief note if retries were needed> |
| Gate 3 | <n>/3    | <brief note if retries were needed> |
| Gate 4 | <n>/3    | <brief note if retries were needed> |
| Gate 5 | <n>/3    | <brief note if retries were needed> |
| Gate 6 | <n>/3    | <brief note if retries were needed> |
| Gate 7 | <n>/3    | <brief note if retries were needed> |

---

_Generated by `/stabilize-module {{ARGS}}` on YYYY-MM-DD_
```

## Step 8.2 — Commit

Stage only the files changed during stabilization — never use `git add -A`:

```bash
git add src/modules/{{ARGS}}/
git add src/shared/entities/<any-entity-files-touched>.ts
git add src/shared/pipes/<any-new-pipes>.ts
git add src/shared/decorators/<any-modified-decorators>.ts
git add docs/reports/stabilize-{{ARGS}}-*.md
```

Commit using **conventional commit format** (enforced by commitlint):

```bash
git commit -m "refactor: stabilize {{ARGS}} module"
```

Allowed types: `feat` `fix` `chore` `docs` `refactor` `test` `perf` `ci` `revert`

**Hook flow** (all run automatically — never bypass with `--no-verify`):
| Hook | What runs |
|------|-----------|
| pre-commit | `lint-staged` (eslint --fix + prettier --write on staged .ts files) + trufflehog secret scan |
| commit-msg | `commitlint` — validates conventional commit format |
| pre-push | `type-check` (tsc --noEmit) + `test:ci` (jest --ci) |

**If commit fails**: read the hook output, fix the issue, re-stage, and create a **NEW commit** — never `git commit --amend` after a failed commit.

**If pre-push fails**: fix the type-check or test failure before pushing; do not force-push.

---

# Phase 9 — Done

**Module is "Done" when ALL gates passed and all checks below are confirmed:**

- [ ] Zero ESLint errors AND zero warnings (except `import/no-cycle` structural warnings)
- [ ] Zero `any` (or justified `eslint-disable` with explanation)
- [ ] All interfaces extracted to `interfaces/` folder with barrel index
- [ ] All `catch` blocks use `: unknown` + error utilities from `src/shared/utils/error.utils.ts`
- [ ] No dead code (unused imports, variables, methods, injected services, commented-out code)
- [ ] No `console.log/warn/error` calls (use NestJS `Logger`)
- [ ] No magic strings/numbers — repeated values extracted to constants
- [ ] Proper variable naming (camelCase, PascalCase conventions) and no misspellings
- [ ] File sizes reviewed — large files decomposed or flagged
- [ ] `eager: true` removed from entity relations (explicit `relations` added where needed)
- [ ] No N+1 query patterns (no DB calls inside loops, no fire-and-forget async)
- [ ] No SQL injection (all `.query()` calls parameterized, route params validated)
- [ ] Transaction boundaries on batch/import operations
- [ ] All `@Body()` params use proper DTOs with class-validator decorators
- [ ] Swagger decorators on every endpoint (@ApiTags, @ApiOperation, @ApiResponse)
- [ ] No duplicate `@ApiResponse` decorators
- [ ] Consistent exception types (NotFoundException, BadRequestException, etc.)
- [ ] Redundant `deletedAt: IsNull()` removed from BaseEntity queries
- [ ] Route params validated (ParseIntPipe on IDs, ParseModulePipe on :module)
- [ ] Services >700 lines decomposed (facade + sub-services) or justified
- [ ] Notification dispatch uses NotificationOrchestrationService (no inline builds)
- [ ] All 7 gates passed (documented in report)
- [ ] Prettier formatting passes
- [ ] `npm run build` passes
- [ ] ESLint passes on all modified files
- [ ] Tests pass (`npx jest src/modules/{{ARGS}}/`)
- [ ] Application starts without DI errors

Output a summary to the conversation:

```
Module stabilization complete for: {{ARGS}}

Gates: 7/7 passed (retries: Gate1=<n>, Gate2=<n>, ..., Gate7=<n>)

- ESLint: <before> violations → <after> violations (-<delta>)
- Interfaces: <n> extracted to interfaces/ folder
- Security: <n> SQL injection fixes, <n> route param validations added
- DTOs: <n> inline types replaced with proper DTOs
- Swagger: <n> missing decorators added, <n> duplicates removed
- Eager loading: removed from <n> entity relations
- N+1 fixes: <n> patterns resolved
- Error handling: <n> .then() chains → async/await, <n> silent catches fixed
- Soft-delete: <n> redundant filters removed
- Magic strings/numbers: <n> extracted to constants
- Dead code removed: <n> unused imports/methods/services
- Service decomposition: <decomposed or N/A>
- File size flags: <list any files flagged>
- Report: docs/reports/stabilize-{{ARGS}}-YYYY-MM-DD.md

All verification checks passed in a single run.
```

If any verification check failed, clearly state what failed and what needs manual attention.
