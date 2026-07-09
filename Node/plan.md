# Node.js → NestJS Backend Learning Plan

> **Reoriented to the real stack.** The `.claude/` skills in this folder reveal that "Node" here
> means a specific production **backend** stack: **NestJS + TypeScript + TypeORM (SQL Server)**
> (the Krion / ti-backend / krionb6i codebases).
>
> So this plan doesn't teach generic Express. It teaches the exact patterns the
> `/refactor-module`, `/refactor-service`, and `/stabilize-module` skills enforce — so that by
> the end you understand *why* every rule those skills apply exists.
>
> The **Angular 19 frontend** half of the stack lives in the sibling `../Angular/` folder — its
> own plan, tracker, and skills. This plan is backend-only.

**Goal:** Read, build, and refactor a NestJS feature module (controller → service → DTO → entity)
to the same standard the skills in `.claude/backend/` demand.

**You already program** (see the Python `codebase/` next door — agents, providers, data layer).
This skips fundamentals and focuses on what's new: TypeScript, the Node async model, and NestJS.

**Pace:** ~1 topic per session. Check boxes as you go. Log progress at the bottom.

---

## The Target: What "Done" Looks Like

Before learning, know what you're aiming at. A module is "done" (per `stabilize-module`) when:

- Zero `any` types (or justified `eslint-disable` with a reason)
- No `console.log` — uses `this.logger` (NestJS `Logger`)
- All `@Body()` params are DTO classes with `class-validator` decorators
- Every endpoint has Swagger decorators (`@ApiTags`, `@ApiOperation`, `@ApiResponse`)
- Errors use `HttpException` subclasses (`NotFoundException`, `BadRequestException`, …), never `throw new Error()`
- `catch (error: unknown)` + `getErrorMessage(error)` from `@shared`
- No SQL injection — raw `.query()` calls parameterized (`@0`, `@1`)
- No `eager: true`, no N+1 queries, no fire-and-forget async
- Interfaces extracted to `interfaces/`, magic strings to `constants/`, imports use path aliases
- Services >700 lines decomposed into a facade + sub-services

Keep this list open. Every phase below teaches a slice of it.

---

## Phase 0 — Setup & the Node Mental Model (0.5 day)

- [ ] Install Node LTS via [nvm-windows](https://github.com/coreybutler/nvm-windows)
- [ ] Verify `node -v`, `npm -v`
- [ ] Understand the event loop: single-threaded, non-blocking I/O (libuv). Nothing blocks unless you make it.
- [ ] `process.env`, `process.argv`, exit codes
- [ ] Run code 3 ways: REPL, `node file.js`, `node -e "..."`

---

## Phase 1 — TypeScript First (3–4 sessions) ⭐ non-negotiable

The whole stack is TypeScript with **zero `any`**. Master this before NestJS.

- [ ] `tsc`, `tsconfig.json`, strict mode
- [ ] Primitives, arrays, tuples, `interface` vs `type`
- [ ] Union & intersection types, literal types, enums
- [ ] Generics — `Repository<T>`, `Promise<T>`, `Observable<T>` all depend on this
- [ ] `unknown` vs `any` vs `never` — **why `unknown` is the safe default in catch blocks**
- [ ] Type narrowing / type guards (`if (typeof x === ...)`, `in`, custom `is` guards)
- [ ] Utility types: `Partial<T>`, `Pick`, `Omit`, `Record<string, T>`, `DeepPartial<T>` (TypeORM uses this)
- [ ] Decorators (experimental) — the foundation of all of NestJS (`@Injectable`, `@Controller`, `@Column`)
- [ ] Path aliases in `tsconfig.json` (`@shared`, `@entities`) — the skills require these over relative imports

**Practice:** Port one Python class from `../Python/practice/classes.py` to a typed TS class.

---

## Phase 2 — JavaScript Async & Modern JS (2 sessions)

The parts of JS that trip up Python devs, focused on what NestJS uses constantly.

- [ ] `let`/`const`, arrow functions, `this` binding
- [ ] Destructuring, spread/rest, optional chaining `?.`, nullish coalescing `??`
- [ ] **async/await deeply** — the #1 thing the refactor skills fix:
  - [ ] `Promise.all` for parallel independent work
  - [ ] Why `.forEach(async …)` is a bug → use `for...of` (sequential) or `Promise.all(map(...))` (parallel)
  - [ ] Converting `.then()` chains to `async/await` with `try/catch`
- [ ] `import`/`export` (ESM) vs `require` (CommonJS)
- [ ] Array methods: `map`, `filter`, `reduce`, `find`, `some`, `every`

---

## Phase 3 — Core Node.js (2 sessions)

- [ ] `package.json`, npm scripts, `npm` vs `npx`, semver (`^`, `~`), lockfiles
- [ ] Built-ins: `fs/promises`, `path`, `crypto`, `os`
- [ ] `EventEmitter` (NestJS's `@nestjs/event-emitter` builds on this — the skills reference `eventEmitter.emit`)
- [ ] Error handling: uncaught exceptions, unhandled promise rejections
- [ ] Dev tooling the skills assume: **ESLint**, **Prettier**, `nodemon`/`node --watch`

**Mini-project:** A small CLI that reads a folder and prints file stats — pure Node, no framework.

---

## Phase 4 — NestJS Fundamentals (4–6 sessions) ⭐ core

This is the actual backend framework. Build the mental model of its building blocks.

- [ ] Why NestJS: opinionated, DI-driven, decorator-based, Angular-like architecture
- [ ] `@nestjs/cli` — `nest new`, `nest g module/controller/service`
- [ ] **Modules** (`@Module`) — `imports`, `controllers`, `providers`, `exports`
- [ ] **Controllers** (`@Controller`, `@Get/@Post/@Put/@Patch/@Delete`, `@Param`, `@Query`, `@Body`)
  - [ ] Keep controllers *thin* — delegate all logic to services (a skill rule)
- [ ] **Providers & Dependency Injection** (`@Injectable`, constructor injection)
- [ ] **DTOs + validation** — `class-validator` (`@IsString`, `@IsNumber`, `@IsOptional`) + `class-transformer`
- [ ] **Pipes** — `ParseIntPipe` on numeric route params, custom pipes (the `ParseModulePipe` allowlist pattern)
- [ ] **Exception handling** — built-in `HttpException` subclasses; when to use each (see the "Done" list)
- [ ] **Logger** — `new Logger(ClassName.name)`, `this.logger.log/warn/error`
- [ ] **Guards** (`@UseGuards(AuthGuard)`) & custom decorators (`@Permission()`) — for auth/RBAC
- [ ] **Swagger** (`@nestjs/swagger`) — `@ApiTags`, `@ApiOperation`, `@ApiResponse`, `@ApiProperty` on DTOs
- [ ] Config with `@nestjs/config` + `.env`

**Project:** Scaffold a `notes` module with full CRUD — controller + service + DTOs + Swagger,
following the file layout in [.claude/backend/skills/refactor-module/references/project-conventions.md](.claude/backend/skills/refactor-module/references/project-conventions.md).

---

## Phase 5 — TypeORM & the Database Layer (3–4 sessions) ⭐ core

The skills are dense with TypeORM specifics — this is where real bugs live.

- [ ] `@nestjs/typeorm`, `TypeOrmModule.forRoot` / `forFeature([Entity])`
- [ ] **Entities** — `@Entity`, `@Column`, `@PrimaryGeneratedColumn`, relations (`@ManyToOne`, `@OneToMany`)
- [ ] **Repository pattern** — `@InjectRepository(Entity)`, `Repository<Entity>`
- [ ] `find` / `findOne` / `findAndCount` + the `relations: []` option
  - [ ] **`eager: true` is a performance trap** — load relations explicitly per query (a whole skill phase)
  - [ ] Avoiding over-fetched relations (only load what the response uses)
- [ ] `@DeleteDateColumn` soft-delete — auto-adds `WHERE deletedAt IS NULL` (so manual filters are redundant)
- [ ] **QueryBuilder** — `.createQueryBuilder()`, `.where(':p', {p})`, `.getRawMany<T>()`
- [ ] **Raw queries safely** — parameterized `@0/@1`, never string interpolation (SQL injection)
- [ ] The decision matrix: `repo.find()` (simple) → QueryBuilder (moderate) → raw SQL (complex/SQL-Server-specific)
- [ ] **N+1 fixes** — batch with `In(ids)` instead of querying in a loop
- [ ] Transactions — `queryRunner` with `startTransaction/commit/rollback` for batch/import ops
- [ ] Migrations & (read-only awareness of) stored procedures

**Practice:** Add a Postgres or SQLite DB to your `notes` module. Write one `find` with explicit
relations, one QueryBuilder query, and one parameterized raw query.

---

## Phase 6 — Read & Refactor a Real Module (2–3 sessions) ⭐ the payoff

Now connect learning to the skills. This is why the plan exists.

- [ ] Read [.claude/backend/skills/stabilize-module/SKILL.md](.claude/backend/skills/stabilize-module/SKILL.md) end to end — it's a checklist of everything that makes NestJS code good or bad
- [ ] Read [.claude/backend/skills/refactor-service/SKILL.md](.claude/backend/skills/refactor-service/SKILL.md) — the async/await, error-handling, and decomposition phases
- [ ] Intentionally write a "bad" service in your `notes` module: `any` types, `console.log`,
      `throw new Error()`, a `.forEach(async)`, an inline interface, a magic string
- [ ] Fix each by hand using the skill's rules — this cements the *why*
- [ ] Learn **service decomposition**: facade + sub-services pattern (when a service >700 lines)
- [ ] Learn the **verification gate** discipline: `npm run build` → `eslint` → `prettier` after every change

---

## Phase 7 — Testing & Quality (2 sessions)

- [ ] **Jest** (NestJS default) — unit tests for services
- [ ] `@nestjs/testing` — `Test.createTestingModule`, mocking providers/repositories
- [ ] `supertest` — integration tests against controllers
- [ ] Debugging: `node --inspect`, VS Code debugger
- [ ] The full gate: `build` + `eslint` + `prettier` + `jest` (what the skills run before "done")

---

## Capstone

Build a small backend feature to your own standard, then run the skills on it:

1. **NestJS API** — one feature module (CRUD + auth guard + DTOs + Swagger + TypeORM), clean per the "Done" list
2. Run `/stabilize-module <name>` (or do it by hand) and see how many criteria you already pass

> Stretch goal that connects to your Python work: a NestJS service that calls the Claude API —
> mirrors the LLM/agent work in `../Python/codebase/`. See the `claude-api` reference.
>
> Full-stack stretch: build the Angular 19 UI for this feature — that track lives in `../Angular/`.

---

## Reference Resources

- **Read first (in this repo):** the three backend `SKILL.md` files + `project-conventions.md`
- [NestJS docs](https://docs.nestjs.com/) — the primary source
- [TypeORM docs](https://typeorm.io/)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [class-validator](https://github.com/typestack/class-validator)
- [The Modern JavaScript Tutorial](https://javascript.info/)

---

## Progress Log

| Date | Phase | What I learned / built |
|------|-------|------------------------|
|      |       |                        |
