# The Two-Device System — never break the chain

The repo is the single source of truth. Laptop and phone both read and write it, so study never depends
on being at a desk.

---

## The problem this solves

You said it yourself: *"if I don't have a lot of time, I might not study right."*

That's the real risk — not motivation, not material. A 14-hour workday, a commute that runs long, a
family thing, and the day is gone. Then two days. Then the streak feels broken and the plan quietly
dies. This is how nearly every self-study plan ends, and it ends there because **the plan's minimum was
set at full effort**.

So the minimum is set somewhere you can actually reach on your worst day: **15 minutes, on a phone, in
bed.** The chain survives bad days by design rather than by willpower.

---

## Three kinds of day

| Day type | Where | Time | Minimum to count | Streak |
|---|---|---|---|---|
| **Full** | Laptop | 2 hrs | The four blocks in [PLAN.md](PLAN.md) §2 | ✅ |
| **Half** | Laptop or Termux | 45 min | Drill (all 6 stages) + commit | ✅ |
| **Phone** | Phone only | 15 min | Drill **stages 0–4** + 10 Anki cards | ✅ |
| Zero | — | — | — | ❌ |

**A phone day is not a lesser day.** Stages 0–4 — markup, restate, examples, logic, pseudocode — are
exactly the part you're weak at. Stage 5 (typing Python) is the part you can already do with a
reference open. So a phone day targets your actual gap more precisely than a lazy full day does.

Aim for 5 full days, 2 half/phone days a week. Log the type in `LOG.md`.

---

## The core mechanic: split the drill across devices

The drill has a thinking half and a typing half. They don't have to happen at the same time or on the
same machine.

```
   PHONE (commute, queue, bed)          LAPTOP (evening)
   ──────────────────────────           ────────────────
   drills/2026-09-01.md                 git pull
     0. Markup                    ──►   read your own pseudocode
     1. Restate                         5. Code
     2. Examples                        6. Verify
     3. Logic                           git commit
     4. Pseudocode
   commit from GitHub mobile web
```

This is better than doing it all at once. Writing pseudocode in the morning and coding it at night
forces you to write pseudocode a *stranger* could follow — because by evening you are that stranger.
Vague pseudocode fails loudly, which is exactly the feedback you need.

---

## How to actually write from your phone

### Option A — GitHub mobile web editor (zero setup, works today)
1. Open `github.com/MadheshSM/learning` in your phone browser, branch `cogn`
2. Navigate to `drills/`, tap **Add file → Create new file** (or open today's file and tap ✏️)
3. Paste the template from [TRANSLATION-METHOD.md](TRANSLATION-METHOD.md), fill stages 0–4
4. **Commit directly to `cogn`** at the bottom

That's your green square and your streak, from bed, in ten minutes. Note the GitHub **app** is
read-only for editing — use the **browser** (`github.com` in Chrome/Safari) when you need to write.

### Option B — Termux (Android, real git + Python)
Full offline capability. One-time setup:
```bash
pkg update && pkg install git python openssh
git config --global user.name "Madhesh S"
git config --global user.email "madhesh.s@krionconsulting.com"
git clone https://github.com/MadheshSM/learning.git
cd learning && git checkout cogn
```
Then daily:
```bash
cd ~/learning && git pull
python drills/solve.py      # you can actually run code
git add -A && git commit -m "drill: day 12" && git push
```
For a private repo, generate a GitHub **personal access token** and use it as the password, or set up
an SSH key with `ssh-keygen` and add the public key to GitHub.

*(iOS equivalent: **a-Shell** has git and Python, or use **Working Copy** — an excellent git client with
a built-in editor.)*

### Option C — GitHub Codespaces in the phone browser
Real VS Code on your actual repo, ~60 free hours/month. Best when you want to *run* something and
Termux feels cramped. Overkill for a drill, ideal for "I have 40 minutes and my laptop is at home."

---

## Reading on the phone
GitHub renders markdown natively, so `PLAN.md`, `TRANSLATION-METHOD.md` and `MOBILE.md` are readable
in the app with no setup, and stay cached offline once opened. Star the repo and pin it.

For the daily 15-minute read block, open tomorrow's topic from `PLAN.md` on the commute. Arriving at
the laptop already knowing what the topic is roughly doubles what that hour produces.

---

## The daily loop, end to end

```
morning    phone    Anki (10 min) · read tomorrow's topic
commute    phone    drill stages 0–4 → commit to drills/YYYY-MM-DD.md
evening    laptop   git pull → stages 5–6 → build block → update LOG.md → commit
bed        phone    read · check the streak table
```

**One commit minimum per day, from either device.** The GitHub contribution graph is your streak
tracker — it doesn't care which device it came from, and it doesn't let you lie to yourself.

---

## Saturday, additionally
The **reverse drill** ([PLAN.md](PLAN.md) §3): take a function Claude Code wrote for you at work,
delete the body, rewrite it unaided, diff. Store both versions in `reverse-drills/` — by December
you'll have a folder of side-by-side comparisons, which is both a progress record and genuinely good
interview material.

---

## Branch discipline

- `main` — your existing Angular / Node / Python tracks. Untouched.
- `cogn` — this plan. Everything here.

Keep them separate. When you want to work the old tracks, switch branches; don't merge them.
