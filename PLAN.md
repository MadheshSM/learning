# 4-Month Plan → Coding Independence + MNC AI/GenAI Engineer

**Start:** 1 Sep 2026 · **Applying from:** 17 Nov 2026 · **Plan ends:** 28 Dec 2026
**Budget:** 2 hrs/day × 7 days = **14 hrs/week ≈ 238 hrs**, plus ~4 hrs/week phone ([MOBILE.md](MOBILE.md))

---

## 0. The actual problem

Your words: *"I rely heavily on Claude Code and prompting. I understand many AI concepts conceptually,
but my Python fundamentals and mental model are weak. My biggest difficulty is understanding
programming problems and translating them from English → logic → pseudocode → Python independently."*

That is a precise diagnosis, and it is not a knowledge gap. You review AI-generated code every day, so
you can **recognise** correct code fluently. You just can't **produce** it. Recognition and production
are separate skills, and the tool that made you strong at the first is what stopped you developing the
second. Every time you prompt instead of thinking, you take the answer and skip the rep.

This is good news, actually. You don't need to learn AI — you already work in it. You need to convert
passive knowledge into active production. That is a *training* problem, and training problems respond
to volume and constraints, not to more material.

So this plan has one keystone habit and everything else hangs off it:

> **Every single day, for 17 weeks, you solve one problem start to finish with no AI assistance,
> following the English → logic → pseudocode → code pipeline in writing.**

Miss the topic of the day if you must. Never miss the drill.

### Your unfair advantage
You are in production AI code daily. Nobody studying this from a bootcamp has that. Two consequences:

1. **Your job is your curriculum.** The reverse drill (§3) turns work you already did into practice
   nobody else has access to.
2. **The AI concepts in the JD are mostly review for you.** So this plan spends 53% of its time on
   fundamentals and engineering — and treats RAG and agents as *implementation* exercises, not
   learning-from-scratch. You'll build them by hand precisely because you already understand them
   conceptually. That's what makes them good fundamentals practice.

### Target
MNC AI/GenAI Engineer roles, with Cognizant's **AI Customer Engineer** as the reference JD:
Google ADK / Copilot Studio / CrewAI agents · RAG pipelines · vector DBs · tokenization · prompt
engineering · LangChain · Hugging Face · OpenAI API · FastAPI · Docker · GitHub · microservices ·
cloud basics · **strong communication** (it's a client-facing role — that requirement is real).

Plus **SQL**, which your `cognizant_ai_study_guide.docx` flags with a `[CONFIRMED]` window-function
question from a real Cognizant loop. It was missing from my first draft. It's in Phase 2 now.

---

## 1. The AI-independence protocol

You cannot stop using Claude Code at work — you have a job. So the withdrawal is staged, and study
time is treated differently from work time.

### In study time (all 17 weeks): zero AI code generation
AI is allowed in exactly three roles, never a fourth:

| Allowed | Example |
|---|---|
| **Explainer** — *after* you've struggled | "Why does this traceback say list index out of range?" |
| **Reviewer** — *after* your code works | "Here's my solution. What would a senior engineer change?" |
| **Quizzer** | "Ask me five questions about generators and grade my answers." |

**Never:** "write me a function that…", "fix this for me", or accepting a completion you didn't
predict. Turn off inline autocomplete during study hours. It is the hardest habit here and the one
that matters most — autocomplete finishes your thought before you've had it.

### At work: staged withdrawal

| From | Rule at work |
|---|---|
| Week 1 | Before accepting any AI-written code, say out loud what every line does. If you can't, don't ship it. |
| Week 4 | Write the function signature, docstring and pseudocode comments yourself. Only then let AI fill in the body. |
| Week 8 | Write the first draft yourself. Use AI as reviewer, not author. |
| Week 12 | AI only for genuinely unfamiliar APIs and boilerplate — the way a senior engineer uses it. |

This is the real deliverable. A job offer is downstream of it.

---

## 2. The daily 2 hours

Same shape every day. The consistency is the point — you shouldn't have to decide what to do.

| Block | Time | What |
|---|---|---|
| **Recall** | 20 min | Anki, then reread yesterday's code and explain it out loud |
| **THE DRILL** | 20 min | One problem, no AI, written translation pipeline. **Never skipped.** |
| **Build** | 60 min | The week's topic and project work |
| **Close** | 20 min | Commit · add Anki cards for today's mistakes · one line in `LOG.md` |

The 20-minute close is not optional overhead. Writing down what confused you today is how tomorrow's
recall block knows what to test.

---

## 3. The drill, in detail

**The pipeline — write all four stages down, on paper or in a file. Every problem, every day.**

```
1. RESTATE   In one sentence, in my own words. What am I actually being asked for?
2. EXAMPLES  Two concrete input→output pairs, written by hand. Include one edge case.
3. LOGIC     The approach in plain English. What's the shape of the solution?
4. PSEUDOCODE  Numbered steps. No Python syntax allowed at this stage.
5. CODE      Translate each pseudocode line into Python.
6. VERIFY    Run against the examples from step 2 — the ones you wrote before coding.
```

Full method, a worked example, and a template you copy each day:
**[TRANSLATION-METHOD.md](TRANSLATION-METHOD.md)**

**Why writing it down matters:** the reason English → code feels impossible is that you're trying to do
comprehension, algorithm design and syntax recall simultaneously, in your head. Three hard things at
once feels like being bad at programming. It isn't — it's overload. Separate them onto paper and each
step is individually easy. Within about three weeks the stages start collapsing back together on their
own, and *that* is the mental model arriving.

**Difficulty ramp:**

| Weeks | Source | Volume |
|---|---|---|
| 1–4 | Exercism Python track, easy | 1/day, all 6 stages written |
| 5–9 | Exercism medium + the Python section of your Cognizant Q&A deck | 1/day, stages 1–4 written |
| 10–17 | Medium problems + real bugs from your own projects | 1/day, stages 1–2 written, rest mental |

By Week 10 you're allowed to shortcut the written stages — **only** because they've become automatic.
If you find yourself stuck, go back to writing all six. Always.

### The reverse drill — every Saturday, 30 min
Pick one function Claude Code wrote for you at work this week. Copy its docstring or description into
an empty file. **Delete the implementation. Rewrite it from scratch, no AI.** Then diff yours against
the original and write two lines in `LOG.md`: what you did differently, and which version is better
(sometimes yours will be — that's the point at which this starts working).

This is the single highest-value exercise in the plan. It's free, it uses code you already understand
the purpose of, and it directly attacks the dependency.

---

## 4. Phase map

| Phase | Weeks | Dates | Hrs | Focus | Ships |
|---|---|---|---|---|---|
| 1. Fundamentals + the translation skill | 1–5 | Sep 1 – Oct 5 | 70 | Execution model, decomposition | 4 CLI tools |
| 2. Engineering: Git, testing, SQL, FastAPI, Docker | 6–9 | Oct 6 – Nov 2 | 56 | Production practices | Tested, containerised API |
| 3. Rebuild the AI stack by hand | 10–13 | Nov 3 – Nov 30 | 56 | Implement what you already know | RAG service, from scratch |
| 4. Agents + capstone | 14–16 | Dec 1 – Dec 21 | 42 | ADK/CrewAI, deployment | Deployed agent app |
| 5. Interview consolidation | 17 | Dec 22 – Dec 28 | 14 | Explaining, positioning | Applications live |

**53% of the plan is Phases 1–2.** That's deliberate, and it's the opposite of how most AI study plans
are built. Yours is the right shape because your gap is fundamentals, not AI.

---

# PHASE 1 — Fundamentals and the translation skill
**Weeks 1–5 · Sep 1 – Oct 5 · 70 hrs**

Goal: understand what Python is *doing*, and be able to get from a paragraph of English to working
code without help.

### Week 1 (Sep 1–7) — The execution model
- Names, objects, references. `a = [1,2]; b = a; b.append(3)` — and why `a` changed
- Mutable vs immutable, and how it changes function behaviour
- Control flow, truthiness, why `if items:` beats `if len(items) > 0:`
- **Reading tracebacks bottom-up** — you will do this hundreds of times
- **Habit:** predict the output *before* running, every time. Wrong predictions are the lesson.
- **Tool:** [pythontutor.com](https://pythontutor.com), 10 min/day, watch the arrows move
- **Ship:** `guessing_game.py` — validation, attempt tracking, clean exit

### Week 2 (Sep 8–14) — Functions and decomposition
This week is the heart of problem-solving. Decomposition *is* the skill.
- Parameters, defaults, return vs print, why mutable defaults are a trap
- Scope: local, enclosing, global. Why your variable "disappeared"
- **Writing small functions that do one thing** — then composing them
- Practise splitting one 40-line script into six named functions. Notice it gets easier to think about.
- **Ship:** `text_analyser.py` — word counts, top-N, reading time — as 6+ small composed functions

### Week 3 (Sep 15–21) — Data structures as thinking tools
Most "I don't know how to solve this" is really "I picked the wrong data structure."
- List / dict / set / tuple: what each is *for*, not just its syntax
- Dict as the default answer to "group these by X" and "count these"
- Set for membership and dedup · `collections.Counter` and `defaultdict`
- Nested structures — lists of dicts, the shape of every JSON API response you'll ever meet
- Comprehensions, after you can write the loop version first
- **Drill focus:** for each problem, ask "what structure makes this easy?" *before* writing logic
- **Ship:** `sales_report.py` — nested JSON in, grouped and sorted summary out

### Week 4 (Sep 22–28) — Files, errors, modules
- `with open()`, context managers, why the file closes itself
- **JSON** — `load`/`loads`/`dump`/`dumps` and the difference. Daily bread from here on.
- Exceptions: catching specific ones, raising your own, `try/except/else/finally`
- **Defensive thinking:** what does this code do when the file is missing? Empty? Malformed?
- Modules, packages, imports, `if __name__ == "__main__":`
- **Ship:** `expense_tracker/` — multi-file package, JSON persistence, survives corrupt input

### Week 5 (Sep 29 – Oct 5) — Objects, generators, consolidation
- Classes: `__init__`, `self`, attributes, methods, `__repr__`. Enough to read library source and use
  Pydantic well. Not metaclasses. Not multiple inheritance.
- When a class beats a dict, and when it doesn't (usually it doesn't)
- Iterators and generators, `yield`, laziness
- Type hints — you'll need them for Pydantic and FastAPI
- **Consolidation:** reread all four Phase 1 projects. Refactor the worst one. Note what you'd do
  differently now — that gap is your progress.

### ⛳ Phase 1 exit test — Oct 5, 90 min, no AI, no notes
> Read a JSON file of orders. Group by customer, compute per-customer totals, find the top 3 by value,
> handle a missing/corrupt file gracefully, write a summary JSON, and include three tests.

Pass = you wrote it independently, even if slowly and ugly. If you can't, take one extra week — the
whole plan rests on this. Do not proceed to Phase 2 by pretending.

**Resources:** *Python Crash Course* Part I **or** [Automate the Boring Stuff](https://automatetheboringstuff.com/)
ch. 1–9 · [Exercism Python track](https://exercism.org/tracks/python) daily · pythontutor.com ·
[Real Python](https://realpython.com) for single-topic depth

---

# PHASE 2 — Engineering: Git, testing, SQL, FastAPI, Docker
**Weeks 6–9 · Oct 6 – Nov 2 · 56 hrs**

The gap between "writes Python" and "ships production code." You work in production, so some of this
is familiar — the goal is doing it yourself rather than watching it happen.

### Week 6 (Oct 6–12) — Git, environments, testing
- venv/uv, pip, `requirements.txt`, dependency pinning — and why
- Git properly: branch, merge, rebase basics, `.gitignore`, resolve a conflict deliberately.
  [Learn Git Branching](https://learngitbranching.js.org/) — 1 hour, worth it
- **pytest** — this is the big one. Writing tests forces you to state what the code *should* do, which
  is the same muscle as stage 2 of the drill. Fixtures, parametrize, assertions.
- **Rule from here on: every project gets tests.** Non-negotiable.
- **Ship:** Phase 1 projects on GitHub, with a test suite and a passing GitHub Action

### Week 7 (Oct 13–19) — SQL
Named in your Cognizant Q&A doc with a `[CONFIRMED]` window-function question. MNC AI interviews ask it.
- SELECT, WHERE, GROUP BY, HAVING, ORDER BY, and **WHERE vs HAVING**
- All four JOIN types, self-joins
- Aggregations, subqueries, CTEs
- **Window functions** — `RANK() OVER (PARTITION BY … ORDER BY …)`. Practise until fluent.
- Indexes and why a query is slow
- Python: `sqlite3`, then SQLAlchemy basics
- **Ship:** the expense tracker backed by SQLite instead of JSON, with 10 practice queries in the README

### Week 8 (Oct 20–26) — FastAPI
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/), typed out in order — no copy-paste
- Path/query params, request bodies, **Pydantic models** (why Week 5 mattered)
- Response models, status codes, `HTTPException`, dependency injection
- `async def` vs `def`: what actually blocks, and when it matters
- Testing endpoints with `TestClient`
- **Ship:** REST API over the SQLite expense tracker — full CRUD, validated, tested

### Week 9 (Oct 27 – Nov 2) — Docker, microservices, cloud
- Images vs containers · `Dockerfile` · layers and caching · slim bases · `.dockerignore`
- Env vars and secrets — never in the image
- `docker compose`: your API + Postgres
- **Microservices**: why split, service-to-service HTTP, statelessness, health checks, and the honest
  trade-offs against a monolith. Be able to argue *against* microservices too — that's the senior answer.
- Cloud vocabulary: container registry, managed container runtime, object storage, secrets manager
- **Ship:** containerised API + Postgres via compose, deployed to Render or Cloud Run

---

# PHASE 3 — Rebuild the AI stack by hand
**Weeks 10–13 · Nov 3 – Nov 30 · 56 hrs**

You already understand these concepts. That is exactly why this phase works: **you'll implement things
you can already explain, which isolates the production skill from the knowledge.** No LangChain until
Week 13. Building RAG from primitives when you already know what RAG is will teach you more Python
than twenty tutorials.

### Week 10 (Nov 3–9) — LLM APIs, from primitives
- Raw SDK calls. Messages, roles, streaming, token counting, cost
- Structured output: JSON out, validated by Pydantic, retried on failure
- Production concerns you can actually implement: retries with backoff, timeouts, rate limits,
  graceful degradation
- **Ship:** a document classification service — FastAPI, structured output, tested, handles API failure

### Week 11 (Nov 10–16) — Prompt engineering with evaluation
- System prompts, few-shot, chain-of-thought, delimiters, output constraints
- **Build an eval harness.** 20 test cases, score prompt versions, produce a results table. Most
  candidates cannot say "I A/B tested prompts against an eval set." You will be able to.
- Failure modes: hallucination, injection, truncation, drift
- **Ship:** `prompt-lab/` — 3 prompt versions, eval script, results table in the README

### Week 12 (Nov 17–23) — Embeddings and vector search, from scratch
- Embeddings, cosine similarity — **implement cosine similarity yourself in NumPy first**
- Chunking strategies and the quality/cost trade-off
- Build a naive vector store with a Python list and your own similarity search. *Then* use Chroma and
  see what it added.
- Compare Chroma / Qdrant / pgvector / FAISS well enough to defend a choice
- **Ship:** semantic search over 50 documents, no vector-DB library

### 📌 Also Week 12: applications open
Resume v1, LinkedIn updated, **5 applications/week from here on.** You have a production AI job and by
now a tested, deployed, containerised portfolio. You are more hireable than you feel. Interviews are
also the fastest possible feedback on which gaps are real.

### Week 13 (Nov 24–30) — RAG end to end, then LangChain
- Full pipeline by hand: ingest → chunk → embed → store → retrieve → assemble context → generate → cite
- **Then** rebuild it in LangChain and compare. Now you know exactly what the framework hides — and
  that comparison is an interview answer most candidates can't give.
- Hugging Face: the Hub, `transformers` pipelines, a small local model, when open beats API
- RAG failure modes: bad chunking, retrieval miss, context stuffing, stale index, no citations,
  lost-in-the-middle
- **Ship:** `rag-service/` — FastAPI + Chroma + LLM, cited, tested, containerised, with an eval set

---

# PHASE 4 — Agents and capstone
**Weeks 14–16 · Dec 1 – Dec 21 · 42 hrs**

### Week 14 (Dec 1–7) — The agent loop, hand-written
- An agent is an LLM + tool schemas + a loop + a stop condition. Write that loop yourself.
- Tool design: names, descriptions, parameter schemas, error returns, idempotency
- Guardrails: iteration caps, cost caps, timeouts, human-in-the-loop
- **Ship:** a hand-rolled agent with two tools and a hard iteration limit

### Week 15 (Dec 8–14) — Google ADK and CrewAI
- [Google ADK](https://google.github.io/adk-docs/) — the JD names it first, so it gets the weight.
  Agents, instructions, tools, sessions, state, multi-agent delegation.
- **CrewAI** — one focused project. Skim Autogen for vocabulary. If you can get Copilot Studio access,
  3 hours in it is high ROI since the JD lists it as an alternative.
- Memory, session persistence, observability, token/cost tracking
- **Ship:** a 2-agent ADK system + a written ADK vs CrewAI comparison

### Week 16 (Dec 15–21) — Capstone
> **Agentic assistant over a document corpus.** FastAPI · RAG retrieval as a tool · 2–3 agents ·
> Pydantic structured output · pytest suite · Docker · deployed public URL · eval set with results ·
> architecture diagram · 3-minute demo video.

This is the artifact you walk into interviews with. Build it to be *demoed*, not just to exist.

---

# PHASE 5 — Interview consolidation
**Week 17 · Dec 22–28 · 14 hrs**

Interview prep has been running since Week 1 through the Anki deck — this week is consolidation, not
a standing start.

- Work the `CONFIRMED` tag in [anki-cognizant-qa.txt](anki-cognizant-qa.txt) until it's cold-recall solid
- **Rehearse out loud, recorded:** explain RAG to a client, then to an architect · what an agent is and
  when it's the wrong choice · how you evaluate an LLM feature · why FastAPI · why containerise ·
  debug a wrong RAG answer · your capstone architecture
- Resume in the JD's vocabulary, bullets as **outcome + stack**:
  *"Built a Dockerised RAG service (FastAPI, Chroma, LangChain) over 500 documents with source
  citations; improved accuracy 40% on a 30-case eval set through chunking and prompt iteration."*
- **Your strongest story is the one you're living:** "I was an AI developer who could prompt but not
  program. I spent four months rebuilding my fundamentals — here's the RAG stack I wrote from
  primitives, and here's what I learned about what the frameworks hide." Interviewers remember that.
  Say it with the diff between your reverse-drill code and Claude's, if you kept the good ones.
- **Do a live demo out loud to a real person, twice.** For a client-facing role this outranks another
  project.

---

## 5. Checkpoints — answer honestly

| Date | Must be true | If not |
|---|---|---|
| Sep 28 | 28 consecutive drills done, all six stages written | Restart the streak. The streak is the plan. |
| Oct 5 | **Phase 1 exit test passed, unaided** | +1 week. Do not skip this gate. |
| Nov 2 | Tested, containerised, deployed API from your own GitHub | Repeat Week 9 before Phase 3 |
| Nov 17 | First 5 applications sent | Send them unready |
| Nov 30 | RAG service running, written from primitives | Extend a week; this is the portfolio centrepiece |
| Dec 21 | Capstone live on a public URL | Ship something smaller, but *live* |
| Dec 28 | You reach for AI *after* thinking, not instead of it | The real test. Everything else is proxy. |

---

## 6. Files

This folder is the `cogn` branch of `github.com/MadheshSM/learning`.

```
d:/Learnings/
├── README.md                    # branch front page
├── PLAN.md                      # this file
├── TRANSLATION-METHOD.md        # the English→logic→pseudocode→code method + worked examples
├── WORKFLOW.md                  # the two-device system: how phone + laptop keep the streak alive
├── MOBILE.md                    # what to study on the phone, per phase
├── CLAUDE.md                    # tutor contract — Claude explains/reviews/quizzes, never writes my code
├── LOG.md                       # drill streak + weekly reviews
├── drills/                      # one file per day (stages 0–4 often written on the phone)
├── reverse-drills/              # AI-written work functions, rewritten by hand, diffed
├── anki-phase1.txt              # 26 Python mental-model cards
├── anki-cognizant-qa.txt        # 87 interview Q&As, tagged (15 CONFIRMED)
├── AI_Developer_6_Month_Study_Plan.xlsx   # broader curriculum — see §7
├── cognizant_ai_study_guide.docx          # 2-year Q&A bank (already converted to Anki)
├── phase1-python/
├── phase2-engineering/
├── phase3-ai-stack/
└── phase4-agents/
```

**Minimum viable day:** 15 minutes on a phone — drill stages 0–4 committed from the GitHub mobile web
editor, plus 10 Anki cards. That still counts, and it exists so a brutal workday can't break the chain.
See [WORKFLOW.md](WORKFLOW.md).

---

## 7. What's cut, and what happens to the xlsx

**Cut from these 4 months:** ML algorithms, PyTorch, CNN/RNN, transformer internals, fine-tuning/LoRA,
math for AI, MoE/quantization/CUDA. Roughly weeks 4–13 and 27 of your xlsx — about 40% of it.

Not because it's bad. Because it's for a different role (Data Scientist / ML Engineer) and it does
nothing for your stated goal of coding independence. Transformer internals will not help you translate
English into Python.

**From January 2027**, once the fundamentals are solid and applications are running, pick the xlsx back
up at its Month 2 and work the ML/DL weeks as a slower background track. Nothing is wasted — it's
sequenced. Keep its Progress Tracker sheet; it's a good tracker.

**A note on coding problems:** my first draft cut LeetCode-style practice entirely, on the grounds that
this JD is client-facing. That was right for the JD and wrong for you. Your stated weakness *is*
independent code production, and MNC AI interviews do include coding rounds. So daily problems are now
the keystone habit — not as competitive-programming prep, but as translation reps.

---

*Rewritten 1 Sep 2026 after you described the real gap. Revisit at every checkpoint.*
