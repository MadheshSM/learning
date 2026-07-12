# Learnings

A self-paced, **mentor-driven** learning workspace for four tracks I'm skilling up on. Each folder is a self-contained course: a written plan, a progress tracker, and a `CLAUDE.md` that turns [Claude Code](https://claude.com/claude-code) into a tutor that teaches, quizzes, and holds me accountable — one concept at a time. A shared [`dashboard/`](dashboard/) visualizes progress across all four.

## The four tracks

| Folder | Stack | Focus | Concepts |
|--------|-------|-------|:--------:|
| [`Python/`](Python/) | Python (async, FastAPI, Pydantic, pandas) | Read & extend a multi-agent construction-analytics backend | ~26 |
| [`Node/`](Node/) | **NestJS** + TypeScript + TypeORM | Build & refactor a backend feature module to spec | 39 |
| [`Angular/`](Angular/) | **Angular 19** (signals, RxJS, SCSS, i18n) | Build & refactor a frontend feature module to spec | 34 |
| [`cognizant_study/`](cognizant_study/) | Interview prep (Q&A format) | Cognizant AI/Data Science role prep — 13 topics, 2-year horizon | 87 |

`Node/` and `Angular/` are the two halves of the same production stack (the backend an API, the frontend its UI). `Python/` is a separate project. `cognizant_study/` is interview prep, not a codebase — it drills a Q&A study guide instead of reading real code.

## How each track works

Every folder follows the same three-part system:

- **`plan.md`** — a phased curriculum. The Node and Angular plans are *reverse-engineered from the coding-standard skills* in each `.claude/` folder, so every topic maps to a real rule those skills enforce. Each plan opens with a **"Done" definition** — the exact bar the code must meet.
- **`learning_tracker.xlsx`** — an Excel workbook with four sheets:
  - **Tracker** — one row per concept: Status, Practice Done, Self-Check Passed, dates, notes (dropdowns built in).
  - **Dashboard** — formula-driven progress (per-phase % complete + overall). Never edited by hand; it recalculates from the Tracker.
  - **Self-Assessment Checklist** — the "can I explain this unaided?" questions.
  - **Time Log** — Date / Hours Spent / Notes, logged per study session. Feeds the dashboard's pace and projected-completion estimate.
- **`CLAUDE.md`** — instructions that make Claude Code act as a strict mentor: it reads the plan, checks the tracker, teaches one concept, gives a hands-on exercise, quizzes me, and only marks a row `Done` once I've actually demonstrated it — then updates the tracker itself.
- **`.claude/`** — the real coding-standard **skills** (and, for Angular, **agents**) that define what "good code" looks like in each stack. These are the source of truth the plans teach toward:
  - `Node/.claude/backend/skills/` — `refactor-module`, `refactor-service`, `stabilize-module`
  - `Angular/.claude/skills/` — `refactor`, `stabilize-module`, `check-module` (+ `agents/`)

## How to use it

1. Open a track folder in **Claude Code** (`cd Node` and start a session). The `CLAUDE.md` there is picked up automatically.
2. Claude runs the **session-start ritual**: reads `plan.md`, opens `learning_tracker.xlsx`, tells you where you left off, and proposes what to cover.
3. Work through the **teaching loop** per concept: explanation → real-code example → your exercise → self-check → tracker update.
4. Track progress by opening `learning_tracker.xlsx` — the Dashboard shows % complete per phase.

You don't need Claude Code to read the material — `plan.md` stands alone as a curriculum, and the tracker works as a plain checklist. Claude Code just adds the accountable-tutor layer.

## Dashboard

[`dashboard/index.html`](dashboard/index.html) is a plain HTML/CSS/JS dashboard (open it directly in a browser, no server needed) with an overall view across all four tracks plus a standalone dashboard per track. It reads a generated snapshot of each `learning_tracker.xlsx`, not the workbook live — after updating a tracker in Excel, run:

```
python dashboard/scripts/generate_data.py
```

then reload the page.

## Pace

At a focused **1 hour/day**, the Node backend track is roughly **8 weeks** (~56 hours); Angular is comparable in scope. Bump to 1.5–2 hrs/day to roughly halve that. The tracker's per-phase hours are a starting estimate, not a deadline. `cognizant_study/` is different — it's a 2-year horizon with no fixed daily pace, where periodic review matters more than first-pass speed (see its `plan.md`).

## Repo layout

```
Learnings/
├── Python/           plan.md · learning_tracker.xlsx · CLAUDE.md · codebase/ · practice/
├── Node/              plan.md · learning_tracker.xlsx · CLAUDE.md · .claude/backend/skills/
├── Angular/           plan.md · learning_tracker.xlsx · CLAUDE.md · .claude/{skills,agents}/
├── cognizant_study/   plan.md · learning_tracker.xlsx · CLAUDE.md · study_guide.md
└── dashboard/         index.html · node.html · angular.html · python.html · cognizant.html
```
