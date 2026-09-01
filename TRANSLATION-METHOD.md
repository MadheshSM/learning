# English → Logic → Pseudocode → Python

The method for the daily drill in [PLAN.md](PLAN.md) §3. This file is the one to reread when a problem
feels impossible.

---

## Why the pipeline exists

When you read a problem and freeze, it feels like "I'm not good at programming." It almost never is.
You're trying to do four hard things at once, in your head:

1. Understand what's being asked
2. Decide on an approach
3. Choose data structures
4. Recall Python syntax

Any one of those is manageable. All four simultaneously, held in working memory, is not — for anyone.
Experienced programmers don't have bigger working memory; they've automated steps 3 and 4 so only 1 and
2 need active thought.

**The pipeline externalises the steps onto paper so each one is done alone.** That's the whole trick.
And after ~3 weeks the stages start merging on their own, without you deciding to merge them. That
merging *is* the mental model arriving. You can't skip to it — you get there by doing the slow version
enough times.

---

## Step 0 — Read the problem like an engineer

Before stage 1, mark up the problem statement. Three passes, 60 seconds:

- **Nouns → your data.** "list of *orders*", "each *customer*", "*total*" → these become variables and
  structures. Nouns tell you what shape the data is.
- **Verbs → your operations.** "*group* by", "*count*", "*sort*", "*filter*", "*find the top*" → these
  become the steps. Most problems are 3–4 verbs chained.
- **Constraints and edges → your tests.** "at most", "if empty", "ignoring case", "may contain
  duplicates". Also ask what the problem *didn't* say: what if the list is empty? What if there's a tie?

If you can't name the nouns and verbs, you don't understand the problem yet — and no amount of staring
at Python will fix that. Reread. This is comprehension, not coding.

---

## The six stages

```
1. RESTATE      One sentence, your own words. Not the problem's words — yours.
2. EXAMPLES     Two input→output pairs written by hand. One normal, one edge case.
3. LOGIC        The approach in plain English. 2-4 sentences.
4. PSEUDOCODE   Numbered steps. NO Python syntax allowed.
5. CODE         Translate each pseudocode line into Python.
6. VERIFY       Run against your step-2 examples. Then think about what else could break.
```

**Rules that make it work:**

- **Stage 2 comes before stage 5.** Writing the expected output by hand forces you to fully understand
  the problem, and it hands you your test cases for free. If you can't write the expected output, you
  cannot write the code — that's information, not failure.
- **No Python in stage 4.** If you write `for i in range(len(x))` in pseudocode, you've skipped ahead to
  syntax and lost the separation. Write "for each item in the list" instead.
- **Stage 5 is mechanical.** If it isn't — if you get stuck translating — your pseudocode was too vague.
  Go back to stage 4 and break that step into smaller steps. Stuck in stage 5 is *always* a stage 4
  problem.
- **Timebox to 20 minutes.** If you're over, stop and write down exactly which stage you stalled on.
  That note is more valuable than the solution. Look at the solution only after writing that note.

---

## Worked example 1 — warm-up

> **Problem:** Given a list of words, return the words that appear more than once, in alphabetical order.

**1. RESTATE**
Find the duplicated words in a list and give them back sorted, each listed once.

**2. EXAMPLES**
```
["b", "a", "b", "c", "a", "a"]  →  ["a", "b"]
["a", "b", "c"]                 →  []          (no duplicates — edge case)
[]                              →  []          (empty — edge case)
```

**3. LOGIC**
I need to know how many times each word appears, so I need a count per word. A dict maps word → count
naturally. Then keep only the words whose count is above 1, and sort them.

**4. PSEUDOCODE**
```
1. make an empty mapping of word to count
2. for each word in the input list:
       add one to that word's count
3. make an empty result list
4. for each word and count in the mapping:
       if the count is greater than 1, put the word in the result list
5. sort the result list
6. return it
```

**5. CODE**
```python
def find_duplicates(words):
    counts = {}                                   # 1
    for word in words:                            # 2
        counts[word] = counts.get(word, 0) + 1
    result = []                                   # 3
    for word, count in counts.items():            # 4
        if count > 1:
            result.append(word)
    return sorted(result)                         # 5, 6
```

**6. VERIFY**
```python
assert find_duplicates(["b","a","b","c","a","a"]) == ["a","b"]
assert find_duplicates(["a","b","c"]) == []
assert find_duplicates([]) == []
```

Note how each pseudocode number maps to one or two lines of Python. That one-to-one correspondence is
the sign that stage 4 was done at the right level of detail.

*(Only after it works: yes, `collections.Counter` does this in one line. Learn the shortcut second.
Writing the loop first is what builds the model; reaching for `Counter` first builds nothing.)*

---

## Worked example 2 — realistic

> **Problem:** You're given a list of server log lines in the format
> `"2026-09-01T14:23:11 192.168.1.5 LOGIN_FAILED"`. Find the 3 IP addresses with the most failed
> logins. Ignore any line that isn't a failed login. If fewer than 3 IPs have failures, return all of
> them. Break ties by IP address alphabetically.

**Step 0 markup**
- Nouns: log lines, IP address, failed logins, count → *list of strings in, list of IPs out*
- Verbs: filter (only failures), extract (the IP), count, sort, take top 3
- Constraints: fewer than 3 IPs possible · ties broken alphabetically · malformed lines?

**1. RESTATE**
Count failed logins per IP, then return the 3 IPs with the highest counts, ties broken by IP name.

**2. EXAMPLES**
```
[
 "2026-09-01T14:23:11 10.0.0.1 LOGIN_FAILED",
 "2026-09-01T14:23:12 10.0.0.2 LOGIN_OK",
 "2026-09-01T14:23:13 10.0.0.1 LOGIN_FAILED",
 "2026-09-01T14:23:14 10.0.0.3 LOGIN_FAILED",
]
→ ["10.0.0.1", "10.0.0.3"]      # only 2 IPs have failures, so return both
                                # 10.0.0.1 has 2, 10.0.0.3 has 1

[]  →  []                       # edge case
["2026-09-01T14:23:12 10.0.0.2 LOGIN_OK"]  →  []   # edge: no failures at all
```

Writing that second example is where I noticed I had to decide what "fewer than 3" means concretely.
That's stage 2 doing its job — it surfaces ambiguity before you've written code around a wrong guess.

**3. LOGIC**
Each line is a string with three space-separated fields. I only care about lines whose third field is
`LOGIN_FAILED`; from those I take the second field, the IP. Count IPs in a dict. Then I need the top 3
by count, with ties broken alphabetically by IP — so sort by count descending *and* IP ascending, and
take the first 3.

**4. PSEUDOCODE**
```
1. make an empty mapping of ip to failure count
2. for each line in the logs:
       split the line into parts by spaces
       if it doesn't have 3 parts, skip it
       if the third part is not "LOGIN_FAILED", skip it
       take the second part as the ip
       add one to that ip's count
3. turn the mapping into a list of (ip, count) pairs
4. sort that list by count highest-first, and by ip alphabetically when counts are equal
5. take the first 3 entries
6. return just the ips from those entries
```

**5. CODE**
```python
def top_failed_ips(log_lines, limit=3):
    counts = {}                                          # 1
    for line in log_lines:                               # 2
        parts = line.split()
        if len(parts) != 3:
            continue
        _timestamp, ip, event = parts
        if event != "LOGIN_FAILED":
            continue
        counts[ip] = counts.get(ip, 0) + 1

    pairs = list(counts.items())                          # 3
    pairs.sort(key=lambda pair: (-pair[1], pair[0]))      # 4
    top = pairs[:limit]                                   # 5
    return [ip for ip, _count in top]                     # 6
```

**6. VERIFY**
Run the stage-2 examples. Then push further: what about a line with extra spaces? A duplicate
timestamp? An IP appearing with both OK and FAILED events? Each answer is another test.

**The one line worth studying:** `key=lambda pair: (-pair[1], pair[0])`. Sorting by a tuple sorts by the
first element, then uses the second to break ties — and negating the count flips that one to descending
while leaving the IP ascending. This is a genuinely non-obvious Python idiom, and notice that the
*pseudocode* line ("sort by count highest-first, and by ip alphabetically when counts are equal") was
easy to write in English before you knew the trick. That's the pipeline earning its keep: stage 4 let
you specify the behaviour without knowing the syntax yet, so stage 5 became one lookup instead of a wall.

---

## Daily template

Copy this into `phase1-python/drills/YYYY-MM-DD.md` each day.

```markdown
# Drill — 2026-09-__
**Problem source:**
**Time started:**

## 0. Markup
- Nouns (data):
- Verbs (operations):
- Constraints / edge cases:

## 1. Restate (one sentence, my words)

## 2. Examples (written BEFORE any code)
| Input | Expected output | Why |
|---|---|---|
|  |  | normal |
|  |  | edge |

## 3. Logic (plain English, 2-4 sentences)

## 4. Pseudocode (numbered, NO Python)
1.
2.
3.

## 5. Code

## 6. Verify
- [ ] Passes example 1
- [ ] Passes example 2
- [ ] Other cases I thought of:

---
**Time taken:**
**Which stage did I stall on?**
**What do I now know that I didn't at the start?**
**Anki card to add:**
```

The last four lines are the ones that compound. Fill them in even on days the problem was easy.

---

## When you're stuck

Diagnose by stage — the cure is different for each:

| Stuck at | What it means | Do this |
|---|---|---|
| **1. Restate** | You don't understand the problem | Reread. Do the step-0 markup. Explain it out loud to nobody. |
| **2. Examples** | The problem is ambiguous, or you're guessing | Find the ambiguity and pick an interpretation *explicitly*. Write it down. |
| **3. Logic** | You don't know an approach | Do it by hand on the example, slowly, and narrate what you're doing. Your narration *is* the logic. |
| **4. Pseudocode** | Your logic was too vague | Take the vaguest sentence and break it into 3 steps. Repeat. |
| **5. Code** | Missing syntax, or pseudocode too coarse | If truly syntax: look it up, that's allowed and always was. If not: back to stage 4. |
| **6. Verify** | It's wrong and you don't know why | Print the value at each step. Compare to what you expected at that point. The first divergence is your bug. |

**Stage 3 is the one that feels most like failure and is most fixable.** "Do it by hand and narrate"
sounds too simple to work. Do it anyway — if you can solve the example on paper, you have an algorithm,
and if you can't, no amount of Python knowledge would have helped.

**When you finally look something up:** never paste a whole solution. Read it, close it, wait ten
minutes, then write it from memory. If you can't, you didn't understand it — reread and repeat. Copying
a working answer into your file produces working code and zero learning, and you already have a tool
that does that faster than you can.
