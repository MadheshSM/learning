# Phone Study Layer

Companion to [PLAN.md](PLAN.md). Adds ~4 hrs/week from commute, queues, lunch and bedtime — taking
you from 14 to ~18 hrs/week over 17 weeks.

**The one thing the phone cannot do is the daily drill.** That needs paper or a keyboard and 20
uninterrupted minutes. Everything below is the recall-and-absorb layer around it, never a substitute.

---

## The one rule that makes this work

**Laptop = producing. Phone = absorbing and recalling.**

The plan says 70% fingers-on-keyboard. Phone time counts toward the *other* 30% — it does not replace
keyboard hours. A week with 6 phone hours and 3 laptop hours is a **failed week**, not a good one.

**Never try to build a project on your phone.** You will fight the keyboard, the screen and the file
manager, produce nothing, and conclude you're bad at this. Running a 10-line snippet on your phone:
fine. Building the RAG service on your phone: no.

---

## The five phone modes

| Mode | Block size | When | What |
|---|---|---|---|
| **1. Recall** | 10 min | Every morning, non-negotiable | Anki flashcards — highest-leverage phone activity by far |
| **2. Read** | 15–30 min | Commute, bedtime | Book chapters, docs, Real Python articles |
| **3. Drill** | 5–10 min | Queues, lunch, waiting | Syntax practice apps, Exercism in browser |
| **4. Explain out loud** | 5 min | Walking | Voice-memo yourself explaining a concept |
| **5. Watch** | ≤25% of phone time | Commute only | Video. Cap it hard — it *feels* like learning |

Mode 4 is the sleeper. This is a **customer-facing** role: being able to say "a RAG pipeline works
like this…" fluently, out loud, unprepared, is a scored part of the interview. Record a 2-minute
explanation while walking, play it back, notice where you stumble. Nobody does this. It works.

---

## Apps and tools

### Spaced repetition — set this up first
- **Android:** AnkiDroid (free)
- **iOS:** AnkiMobile (paid, ~₹2,000) — or just use **ankiweb.net** in Safari for free
- Two decks are ready to import (tab-separated, tags included — Anki reads them as-is):
  - [anki-phase1.txt](anki-phase1.txt) — 26 cards on the Phase 1 Python mental model. Start here.
  - [anki-cognizant-qa.txt](anki-cognizant-qa.txt) — 87 cards built from your `cognizant_ai_study_guide.docx`,
    tagged by topic. 15 carry a `CONFIRMED` tag — those came from real Cognizant candidate reports.
    **Suspend all but the Python/SQL tags until you reach the relevant phase**, or you'll be drilling
    LoRA before you can write a for loop. Unsuspend a tag as each phase opens.
- **Add a card every time you get something wrong on the laptop.** Your own mistakes make the best deck.

### Running actual Python on the phone
- **Android:** **Termux** — real Linux, `pkg install python git`, pip works, you can even run FastAPI
  locally. The serious option. Or **Pydroid 3** for a simpler offline IDE.
- **iOS:** **a-Shell** (free, Python + Unix tools) or **Pythonista 3** (paid, excellent).
- **Either, needs internet:** **Google Colab** in the mobile browser — works surprisingly well, and is
  genuinely useful in Phase 3 for embeddings and Hugging Face experiments.
- **GitHub Codespaces** in a mobile browser gives you real VS Code on your actual repo (free tier
  ~60 hrs/month). Best option for looking at your own project away from the laptop.
- **claude.ai/code** works in a mobile browser — ask questions about code you already wrote.

### Reading and drilling
- Save articles offline before you leave the house (browser reading list, or Pocket/Instapaper)
- **Exercism** and **Learn Git Branching** both work in a mobile browser
- **Programiz** / **Sololearn** / **Mimo** for syntax drills — useful in Weeks 1–4 only, then drop them.
  They plateau fast and start feeling productive without being productive.
- **GitHub mobile app** — review your own commits and diffs; also your daily-streak accountability

---

## What to do on the phone, per phase

**Phase 1 (Sep 1 – Oct 5) — Fundamentals and the translation skill**
Anki mental-model cards daily. Read Python Crash Course / Automate the Boring Stuff chapters. Run tiny
snippets in Termux or a-Shell to test a hunch ("does this actually mutate the original?") — prediction
first, then run. Do stages 0–3 of a drill in a notes app while commuting, then code it at the laptop:
the thinking half of the pipeline is genuinely phone-friendly, and arriving with the pseudocode already
written makes the laptop hour twice as productive.
*Do not* attempt the weekly projects on the phone.

**Phase 2 (Oct 6 – Nov 2) — Git, testing, SQL, FastAPI, Docker**
Read the FastAPI tutorial pages before you type them at the laptop — arriving pre-read doubles your
throughput. Learn Git Branching works in a mobile browser. Review your own diffs in the GitHub app.
Anki cards for HTTP status codes, Docker commands, git commands, and **SQL** — unsuspend the
`Cognizant::SQL` tag during Week 7 and drill the window-function card until it's automatic.

**Phase 3 (Nov 3 – Nov 30) — LLMs, prompting, RAG ← best phone fit in the whole plan**
**Prompt engineering can be done almost entirely on a phone.** Iterate prompts in the Claude or
ChatGPT app during your commute, note which phrasing wins, paste the winners into `prompt-lab/` that
evening. Colab in the browser for embedding experiments. Read the Anthropic prompt engineering guide
and LangChain docs in reading blocks.

**Phase 4 (Dec 1 – Dec 21) — Agents**
Read the Google ADK and CrewAI docs. Sketch agent architectures and tool schemas in a notes app —
design thinking works fine on a phone; implementation doesn't. Voice-memo yourself explaining
"what is an agent, and when is it the wrong choice."

**Phase 5 (Dec 22–28) — Portfolio and interview**
Almost 100% phone-compatible. Rehearse the ten interview answers out loud on walks. Review flashcards.
Edit LinkedIn, send applications, and read job descriptions — all from the phone.

---

## Revised daily rhythm

| When | Where | Time | What |
|---|---|---|---|
| Morning / commute | Phone | 15 min | Anki, then read |
| Lunch or a queue | Phone | 10 min | Drill stages 0–3 in a notes app, or reread yesterday's concept |
| Evening | **Laptop** | **2 hrs** | The four blocks from PLAN.md §2 — unchanged |
| Walking / errands | Phone | 5 min | Explain one concept out loud, recorded |
| Bed | Phone | 15 min | Read tomorrow's material |

≈ **45 extra minutes a day**, all from time that was already gone.

---

## Two failure modes to watch for

1. **Substitution.** Phone learning feels like progress and asks nothing of you. If you notice a week
   where you did a lot of reading and shipped nothing, you've substituted. Check `LOG.md` — the
   "Shipped" line and the drill streak are the only honest signals.
   **A phone session never counts as the daily drill.** Reading about problem-solving is not
   problem-solving, and it's the most tempting substitution available to you.
2. **The phone winning.** You open Termux, a notification arrives, forty minutes vanish. Use a focus
   mode / Do Not Disturb for study blocks, or the phone layer costs you more time than it adds.
