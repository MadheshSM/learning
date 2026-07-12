# Cognizant AI Roles — 2-Year Study Guide (Q&A Format)

Prepared for Maddy — AI Developer, Krion. 13 topics · 87 questions · mapped to Year 1 / Year 2 prep.

Plain-text mirror of `cognizant_ai_study_guide.docx`, generated so Claude Code sessions (and anything
else that can't parse `.docx`) can read the material directly. The `.docx` is the original; this file
is kept in sync with it by hand if the source guide is ever revised.

## How to read this guide

Most of these Q&As are standard, well-established AI/ML concepts — accurate and stable regardless of
which year you study them. A small number of items carry a **[CONFIRMED]** tag because they came
directly out of real Cognizant candidate interview reports found during research, not just general
best practice — those are worth extra attention. Everything else is solid general industry prep for
this role family, not a guaranteed Cognizant question bank.

Timing tags: **Year 1** = build this first. **Year 2** = deepen or add this. Most topics span both
years at increasing depth.

---

## 1. Python & Coding Fundamentals
*Suggested timing: Year 1*

**1.1 — How do you find missing elements in a list of consecutive integers?**
Compare against the full expected range: `set(range(min(lst), max(lst)+1)) - set(lst)`. For exactly
one missing number, the faster trick is `expected_sum - actual_sum` using the arithmetic series formula.

**1.2 — Difference between a list and a tuple?**
Lists are mutable; tuples are immutable. Tuples are slightly faster and, if their contents are
immutable, can be used as dictionary keys or set members — lists can't.

**1.3 — How do you check if a string is a palindrome?**
`s == s[::-1]` is the simplest. A two-pointer approach (compare characters from both ends moving
inward) is the more "I understand what's happening" version interviewers want to hear you explain.

**1.4 — How does Python handle "pointers" compared to C/C++?**
Python has no explicit pointers or pointer arithmetic. Variables are names bound to objects in memory.
Passing a mutable object into a function passes a reference to that same object — similar effect to a
pointer, but you can't manipulate addresses directly.

**1.5 — How do you merge two dictionaries?**
`dict1 | dict2` (Python 3.9+), `{**dict1, **dict2}`, or `dict1.update(dict2)` for an in-place merge.

**1.6 — Shallow copy vs. deep copy?**
`copy.copy()` duplicates the outer object but nested objects are still shared references.
`copy.deepcopy()` recursively copies everything, so nested objects are fully independent.

**1.7 — List comprehension vs. generator expression?**
A list comprehension builds the whole list in memory immediately. A generator expression (parentheses
instead of brackets) produces values lazily, one at a time — much more memory-efficient for large or
streamed data.

**1.8 — What do `*args` and `**kwargs` do?**
`*args` collects extra positional arguments into a tuple; `**kwargs` collects extra keyword arguments
into a dict — both let a function accept a flexible, unspecified number of arguments.

**1.9 — Threading vs. multiprocessing for CPU-bound ML work?**
Python's Global Interpreter Lock (GIL) means threads don't get true parallelism on CPU-bound code.
Multiprocessing spawns separate processes with separate interpreters to bypass the GIL — generally the
right choice for CPU-bound training/inference. Threading is fine for I/O-bound work like API calls.

---

## 2. SQL
*Suggested timing: Year 1*

**2.1 — INNER JOIN vs. LEFT JOIN?**
INNER JOIN returns only rows with matches in both tables. LEFT JOIN returns all rows from the left
table plus matched rows from the right (NULLs where there's no match).

**2.2 — Write a query to find duplicate rows.**
`SELECT col, COUNT(*) FROM table GROUP BY col HAVING COUNT(*) > 1`

**2.3 — WHERE vs. HAVING?**
WHERE filters individual rows before aggregation. HAVING filters groups after a GROUP BY/aggregation
has been applied.

**2.4 — Explain a window function with an example.** `[CONFIRMED]`
*Why flagged: Cognizant Data Scientist interviews reportedly included SQL query rounds focused on
joins/core query skills.*
Window functions compute a value across a set of related rows without collapsing them into groups.
Example: `RANK() OVER (PARTITION BY dept ORDER BY salary DESC)` ranks employees within each department
by salary while still returning every row.

**2.5 — What is a self-join, and when would you use one?**
A table joined to itself — useful for comparing rows within the same table, e.g., finding employees
who share the same manager.

**2.6 — How do you optimize a slow query on a large dataset?**
Index the columns used in filters/joins, avoid `SELECT *`, filter as early as possible, avoid wrapping
indexed columns in functions inside WHERE clauses, check the query execution plan, and consider
partitioning very large tables.

---

## 3. Statistics & Core ML
*Suggested timing: Year 1*

**3.1 — What is regularization, and why use it?** `[CONFIRMED]`
*Why flagged: Directly referenced in Cognizant's general data science interview prep material.*
A technique that adds a penalty term to the loss function (L1/Lasso or L2/Ridge) to discourage overly
large coefficients, preventing the model from fitting noise in the training data — i.e., reducing
overfitting.

**3.2 — Explain the bias-variance tradeoff.**
Bias = error from overly simplistic assumptions (underfitting). Variance = error from sensitivity to
training-data fluctuations (overfitting). Reducing one often increases the other; the goal is the model
complexity that minimizes total expected error.

**3.3 — Precision vs. recall — when do you prioritize one over the other?** `[CONFIRMED]`
*Why flagged: Directly referenced in real Cognizant interview reports.*
Precision = TP/(TP+FP) — of predicted positives, how many were correct. Recall = TP/(TP+FN) — of actual
positives, how many were caught. Prioritize precision when false positives are costly (e.g., a spam
filter blocking real mail). Prioritize recall when false negatives are costly (e.g., disease screening,
fraud detection).

**3.4 — What is a confusion matrix?** `[CONFIRMED]`
*Why flagged: Directly referenced in real Cognizant interview reports.*
A table of true positives, false positives, true negatives, and false negatives for a classifier, used
to derive accuracy, precision, recall, and F1-score.

**3.5 — How do you properly validate a predictive model?**
Split into training and validation/test sets (or use k-fold cross-validation), train only on the
training data, evaluate on data the model hasn't seen, and check for consistent performance across
folds to catch overfitting.

**3.6 — Supervised vs. unsupervised vs. self-supervised learning?**
Supervised trains on labeled input-output pairs. Unsupervised finds structure in unlabeled data
(clustering, dimensionality reduction). Self-supervised generates its own labels from the data itself
(e.g., predicting a masked word) — this is how most modern LLMs are pretrained.

**3.7 — Key assumptions of linear regression?**
Linearity between predictors and target, independence of errors, homoscedasticity (constant error
variance), roughly normal error distribution, and no severe multicollinearity among predictors.

**3.8 — What is a hash collision, and how is it resolved?** `[CONFIRMED]`
*Why flagged: Directly referenced in real Cognizant interview reports.*
When two different keys hash to the same slot. Resolved via chaining (store multiple entries per slot
as a linked list) or open addressing (probe for the next free slot).

**3.9 — How do you handle missing or messy data before modeling?**
Identify the missingness pattern, then choose imputation (mean/median/mode or model-based) or removal
depending on volume and whether data is missing at random. Also handle outliers, inconsistent formats,
and duplicates.

**3.10 — Feature engineering vs. feature selection?**
Feature engineering creates new features from raw data (transformations, aggregations, encodings).
Feature selection chooses a useful subset of existing features, often to reduce overfitting and
training time.

---

## 4. Deep Learning Fundamentals
*Suggested timing: Year 1*

**4.1 — CNN vs. RNN — when would you use each?**
CNNs use convolutional filters suited to spatial data like images (local pattern detection, translation
invariance). RNNs (and LSTM/GRU variants) process sequences by maintaining a hidden state over time,
traditionally used for text/time series — though transformers have largely replaced RNNs for sequence
tasks now.

**4.2 — What is backpropagation?**
The algorithm that trains neural networks by computing the gradient of the loss with respect to each
weight (via the chain rule), propagating error backward from output to earlier layers, then updating
weights via gradient descent.

**4.3 — Vanishing/exploding gradient problem?**
In deep networks, gradients can shrink toward zero (vanishing) or grow uncontrollably (exploding) as
they propagate backward through many layers. Mitigated with careful weight initialization, batch
normalization, residual/skip connections, and gradient clipping.

**4.4 — Why does dropout help?**
It randomly "turns off" a fraction of neurons during each training pass, preventing the network from
over-relying on any single neuron — reducing overfitting.

**4.5 — Batch vs. mini-batch vs. stochastic gradient descent?**
Batch GD uses the whole dataset per update (stable, slow). SGD updates after each single example (fast,
noisy). Mini-batch (the common default) updates after small batches — balancing speed and stability.

**4.6 — GANs vs. VAEs — how do they differ?** `[CONFIRMED]`
*Why flagged: Cognizant's Gen AI Engineer postings explicitly name both.*
A GAN pits a generator against a discriminator in adversarial training — the generator tries to fool
the discriminator into thinking fake samples are real. A VAE learns a probabilistic latent
representation and generates new samples by sampling from that latent space, optimizing reconstruction
quality plus a regularization term that keeps the latent space well-structured.

**4.7 — What is transfer learning?**
Reusing a model pretrained on a large dataset (ImageNet for vision, a general LLM for text) and
fine-tuning it on a smaller, task-specific dataset — far more data- and compute-efficient than training
from scratch.

---

## 5. NLP & Computer Vision Basics
*Suggested timing: Year 1–Year 2*

At Cognizant, these skills mostly live inside Data Scientist postings rather than standalone titles —
but they're explicitly named requirements there.

**5.1 — Word-level vs. subword (BPE) vs. character-level tokenization?**
Word-level uses whole words but struggles with rare/unseen words. Character-level handles any input but
loses semantic chunking. Subword methods (Byte Pair Encoding, WordPiece) split words into frequent
subunits — balancing vocabulary size against the ability to represent rare or novel words.

**5.2 — Stemming vs. lemmatization?**
Stemming crudely chops word endings with rules (can produce non-words, e.g., "studies" → "studi").
Lemmatization uses vocabulary/grammar knowledge to return the proper dictionary base form ("studies" →
"study") — more accurate, more expensive.

**5.3 — How do embeddings differ from one-hot encoding?**
One-hot encoding gives each word a sparse vector with a single 1, with no notion of similarity between
words. Embeddings represent words as dense vectors where semantically similar words sit close together
in the space.

**5.4 — NER vs. text classification?**
NER identifies and labels specific spans of text as entities (person, organization, date). Text
classification assigns one label (or set of labels) to an entire document or sentence.

**5.5 — What's a convolutional filter actually doing in image recognition?** `[CONFIRMED]`
*Why flagged: OpenCV is explicitly named in multiple Cognizant Data Scientist postings.*
It slides over the image detecting local patterns — edges, textures, shapes — at each position.
Stacking many convolutional layers lets the network build from simple local features up to complex,
high-level representations.

**5.6 — Classification vs. object detection vs. semantic segmentation?**
Classification assigns one label to a whole image. Object detection finds and labels multiple objects
with bounding boxes. Semantic segmentation labels every pixel, giving pixel-level understanding.

---

## 6. Generative AI / LLMs
*Suggested timing: Year 1–Year 2*

**6.1 — What is a transformer, and what replaced recurrence?** `[CONFIRMED]`
*Why flagged: Cognizant Data Scientist interview reports specifically mention LLM and Hugging Face
questions.*
A transformer processes all tokens in a sequence in parallel using self-attention instead of recurrent
networks' sequential processing. Self-attention lets every token directly attend to every other token
to determine relevance.

**6.2 — Explain Query, Key, and Value in self-attention.**
Each token is projected into three vectors: Query (what this token is "looking for"), Key (what it
"offers" to others), and Value (the content passed along). Attention scores compare Query against all
Keys, and those scores weight a sum over the Values to produce the token's updated representation.

**6.3 — Why do transformers need positional encoding?**
Self-attention has no inherent sense of order — it treats the sequence as a set. Positional encodings
inject position information so the model can use word order, not just word identity.

**6.4 — What is multi-head attention?**
Several attention computations run in parallel ("heads"), each with its own learned projections,
letting the model attend to different types of relationships (e.g., syntax vs. coreference)
simultaneously, then combining the results.

**6.5 — Zero-shot vs. one-shot vs. few-shot prompting?**
Zero-shot gives only the instruction. One-shot gives a single example. Few-shot gives several examples
in the prompt — all without updating model weights.

**6.6 — What is chain-of-thought prompting, and why does it help?**
Asking the model to externalize intermediate reasoning steps before the final answer. This tends to
improve multi-step reasoning performance because the model can build on its own intermediate steps
rather than jumping straight to an answer.

**6.7 — What causes LLM hallucination, and how do you mitigate it?**
LLMs generate the statistically most plausible next tokens, not facts checked against ground truth — so
they can produce fluent, confident, false statements. Mitigation: ground answers with RAG, add a
verification layer, lower temperature for fact-heavy tasks, and instruct the model to cite sources or
say "I don't know."

**6.8 — What is RLHF?**
Reinforcement Learning from Human Feedback. Human raters rank model outputs; that preference data
trains a reward model; the LLM is then fine-tuned with reinforcement learning to maximize the reward
model's score — generally making outputs more helpful and aligned with what people actually want.

**6.9 — Fine-tuning vs. RAG — when do you pick each?**
Fine-tuning updates model weights on a domain-specific dataset, baking in style/behavior but requiring
retraining as knowledge changes. RAG keeps the model frozen and retrieves relevant external documents at
inference time. Pick RAG for frequently-changing, auditable, or private knowledge; pick fine-tuning to
change tone, format, or task behavior.

**6.10 — What is a context window, and what's the "lost in the middle" problem?**
The max tokens (input + output) a model can process per call. "Lost in the middle" describes models
attending less reliably to information placed in the middle of a long context versus the start or end —
a bigger window doesn't guarantee the model actually uses everything well.

**6.11 — What are LoRA and QLoRA?**
LoRA fine-tunes a small number of additional low-rank weight matrices instead of updating all
parameters, cutting fine-tuning compute/memory cost drastically. QLoRA adds quantizing the base model
to lower precision (e.g., 4-bit), making it feasible to fine-tune large models on much more modest
hardware.

**6.12 — What is model quantization, and what's the tradeoff?**
Reducing the numerical precision of stored weights (e.g., 32-bit float → 8-bit or 4-bit integer),
shrinking memory footprint and speeding inference — at the cost of some accuracy/quality loss that
grows as precision drops further.

---

## 7. RAG Systems
*Suggested timing: Year 2*

**7.1 — Walk through a complete RAG pipeline end to end.** `[CONFIRMED]`
*Why flagged: Cognizant interview reports specifically mention sentence transformers and AWS/MLOps
deployment questions for Data Scientist/AI roles.*
Offline: documents are cleaned, split into chunks, embedded, and stored in a vector database. Online:
the user query is embedded, the vector database returns top-k similar chunks, an optional reranker
reorders them, the retrieved chunks go into the prompt with the query, and the LLM generates a grounded
answer — ideally with citations back to source chunks.

**7.2 — What is chunking, and why does chunk size matter?**
Splitting documents into pieces before embedding/indexing, since retrieval works at the chunk level.
Too-large chunks dilute relevance and waste context space; too-small chunks lose surrounding context.
Strategies include fixed-size, recursive, and semantic chunking (splitting at natural topic boundaries).

**7.3 — Why use a reranker after initial vector retrieval?**
Initial retrieval (cosine similarity or BM25) is fast but approximate and can surface
topically-similar-but-not-actually-best chunks. A reranker — typically a more expensive cross-encoder —
rescoring top candidates improves precision of what reaches the LLM, at added latency cost.

**7.4 — What is hybrid search in RAG?**
Combining sparse keyword-based retrieval (BM25) with dense embedding-based semantic retrieval, then
merging/reranking — keyword search catches exact terms (codes, names) embeddings miss; embeddings catch
semantic similarity keyword search misses.

**7.5 — How do you evaluate whether a RAG system is working well?**
Faithfulness (are claims in the answer actually supported by retrieved context, or hallucinated),
context relevance/precision (are retrieved chunks actually relevant), context recall (did retrieval
find everything needed), and answer relevance (does the final answer address the user's actual
question).

**7.6 — Retrieval finds relevant chunks but the LLM still hallucinates — what's wrong?**
Usually a generation-side issue: the prompt may not instruct the model strongly enough to stick to
context, the context may be too long/diluted ("lost in the middle"), or the model fills gaps with prior
knowledge when context is incomplete. Fix with tighter prompt instructions, explicit "only use provided
context" guardrails, trimming irrelevant chunks, and a post-hoc faithfulness check.

**7.7 — How would you handle PDFs with tables and complex layouts in RAG ingestion?**
Standard text-extraction pipelines often mangle tables. Better: layout-aware parsing that preserves
structure, converting tables to a structured format (markdown tables, key-value pairs) before chunking,
and sometimes treating tables as separate retrievable units from surrounding prose.

---

## 8. AI Agents & Multi-Agent Systems
*Suggested timing: Year 2*

This maps directly onto your own multi-agent construction analytics codebase work (see the `Python/`
track) — worth treating this section as both interview prep and a lens for explaining your own project.

**8.1 — What is an AI agent vs. a single LLM call?** `[CONFIRMED]`
*Why flagged: Multi-agent orchestration and MCP/A2A protocols are explicitly named in Cognizant's AI
Developer postings.*
A single LLM call takes input and produces output once. An agent wraps an LLM in a loop where it can
reason about a goal, decide to use tools (search, code execution, APIs), observe results, and iterate —
taking multiple autonomous steps rather than answering in one shot.

**8.2 — Explain the ReAct (Reasoning + Acting) pattern.**
The agent alternates between explicit reasoning ("Thought") and taking an action (calling a tool), then
observes the result and feeds it into the next reasoning step — interleaving thinking and acting rather
than planning everything upfront.

**8.3 — Single-agent vs. multi-agent — why choose multi-agent?**
A single agent handles the whole task itself. Multi-agent splits work across specialized agents
(researcher, writer, critic) that communicate and hand off — useful for specialization, parallelism, or
when one agent checking another's work improves reliability, at the cost of coordination complexity.

**8.4 — How do you design tools for an agent to use?**
Clear, narrow purpose per tool; a precise description (the model uses this to decide when to call it);
well-typed inputs/outputs; predictable, informative failure modes. Overly broad or overlapping tools
confuse the model about which to pick.

**8.5 — An agent gets stuck in an infinite loop calling the same tool — how do you debug it?**
Check whether the tool's output is informative enough for the agent to recognize completion —
vague/unchanged output makes the model think it needs to retry. Add a hard iteration limit as a safety
net, log the full reasoning trace to find where the logic breaks, and add explicit "if this fails
twice, try a different approach or stop" guidance.

**8.6 — What is MCP (Model Context Protocol), conceptually?**
A standardized protocol letting an LLM-based application connect to external tools, data sources, and
services consistently, instead of needing custom one-off integration code for each — similar in spirit
to a common API standard avoiding bespoke glue code per connection.

**8.7 — What does "state management" mean for an agent, and why is it hard?**
Tracking what the agent has already done/decided across multiple steps so it doesn't repeat work,
contradict itself, or lose the original goal. Hard because context windows are limited — the agent
needs a strategy (summarization, memory stores, explicit task trackers) for what to keep, compress, or
discard.

---

## 9. MLOps & Deployment
*Suggested timing: Year 2*

**9.1 — What does MLOps cover that DevOps doesn't?** `[CONFIRMED]`
*Why flagged: MLOps and deployment knowledge specifically came up in Cognizant Data Scientist technical
interviews.*
Everything DevOps does (CI/CD, infrastructure, monitoring) plus ML-specific concerns: data versioning,
model versioning, experiment tracking/reproducibility, monitoring for data drift and performance decay
over time (not just uptime), and retraining pipelines.

**9.2 — What is data/model drift, and how do you detect it?**
Drift is when incoming data's statistical properties (data drift) or the input-output relationship
(concept drift) change relative to training data, degrading performance even though the model itself
hasn't changed. Detect via monitoring feature distributions over time, tracking live accuracy against
ground truth where available, and statistical tests comparing recent data to training data.

**9.3 — What's Docker's role in deploying an ML model?**
It packages the model, dependencies, and configuration into a portable container that runs the same way
across dev, test, and production — avoiding environment mismatch problems.

**9.4 — Batch vs. real-time inference?**
Batch processes large input sets together on a schedule, tolerating higher latency for higher
throughput. Real-time serves predictions one request at a time with low latency requirements (e.g., a
live chatbot), needing an optimized serving layer.

**9.5 — How would you set up basic monitoring for a deployed model in production?**
Input/output logging (with privacy handling), latency and error rate tracking, task-specific quality
metrics (accuracy where ground truth exists, user feedback for generative systems), and alerting
thresholds so degradation is flagged before major downstream impact.

**9.6 — What does a basic ML CI/CD pipeline look like?**
On code/data changes: automated data validation and unit tests run, the model is retrained/re-evaluated
against a held-out set, results are compared against the current production model, and if it passes
quality gates, it's deployed — often staged (canary/shadow) rather than an immediate full switch.

---

## 10. Cloud Platforms
*Suggested timing: Year 2*

Azure-leaning, since it showed up most often in Cognizant's India AI postings.

**10.1 — What is Azure OpenAI Service, and how does it differ from calling OpenAI's API directly?** `[CONFIRMED]`
*Why flagged: Cognizant's India-based Gen AI/Data Scientist postings repeatedly name Azure OpenAI
Service.*
It provides access to OpenAI's models hosted within Azure's infrastructure, letting enterprises use them
under Azure's existing security, compliance, and data residency framework instead of going through
OpenAI directly — relevant for clients with strict enterprise compliance needs.

**10.2 — Azure Container Apps vs. AKS — when do you pick each?**
Container Apps is simpler, more managed, serverless-style — good for event-driven or lighter workloads
without managing Kubernetes directly. AKS gives full Kubernetes control at the cost of more operational
complexity — pick it when you need that level of control.

**10.3 — What is a vector database, and name a few examples?**
A database optimized for storing and searching high-dimensional embedding vectors via similarity
(nearest-neighbor) search rather than exact-match queries. Examples: Pinecone, Weaviate, pgvector.

**10.4 — What's the difference between a platform like Azure AI Foundry and a vector database in a RAG system?**
A vector database handles storage and similarity search over embeddings specifically. A broader platform
manages the wider lifecycle — model catalog/selection, prompt flow design and evaluation, deployment,
governance — orchestrating the pieces (including the vector DB, the LLM, and app logic) rather than
replacing any single component.

---

## 11. AI System Design
*Suggested timing: Year 2*

**11.1 — Design a customer support ticket triage system using an LLM.**
Intent/category classification (often a smaller, cheaper model) routes tickets; for complex cases, RAG
against a knowledge base of past resolutions/policies drafts a response; a confidence/escalation
threshold routes low-confidence or sensitive cases to a human; everything is logged for continuous
improvement of both retrieval and classification.

**11.2 — How would you scale a RAG system from a small knowledge base to millions of documents?**
Move to approximate nearest neighbor (ANN) indexing for sub-linear search, shard the vector index across
nodes if needed, add metadata filtering to narrow the search space before similarity search, cache
frequent queries, and add reranking to maintain precision as recall-oriented retrieval pulls in more
candidates.

**11.3 — Design a basic content moderation layer for a generative AI product.**
A tiered approach: fast/cheap keyword filters catch obvious violations first, a fine-tuned classifier
handles a second tier of less clear-cut cases, and an LLM judge or human review queue handles remaining
ambiguous edge cases — balancing speed and thoroughness.

**11.4 — How do you decide between a single prompt and a multi-step chain/agent for a task?**
Default to the simplest approach — a single well-crafted prompt — and move to a chain/agent only when
there's a concrete, observed quality problem a single prompt can't fix (genuinely distinct stages, need
for intermediate validation, reliable failure on complex multi-part requests). Chains/agents add
latency, cost, and failure points.

---

## 12. Behavioral / HR
*Suggested timing: Year 2 — intensify months 18–24*

**12.1 — "Tell me about yourself" — what should this actually cover?**
A short, structured answer: where you are now (current role, what you actually do), how you got there,
one or two concrete accomplishments, and why you're looking at this next move — about a minute, leading
naturally into why this role interests you.

**12.2 — "Describe a time you disagreed with a teammate. How did you handle it?"** `[CONFIRMED]`
*Why flagged: This exact theme came up in Cognizant Data Scientist interview reports.*
Use the situation → action → result structure: briefly set up the disagreement, focus most of the
answer on what you specifically did to address it, end with the outcome and what you'd repeat or
change. Avoid framing it as "who was right" — interviewers are listening for self-awareness and
conflict-handling.

**12.3 — "Tell me about a time you were under a lot of pressure."** `[CONFIRMED]`
*Why flagged: This theme also appeared in real Cognizant interview reports.*
Same structure. Pick an example with a real stake (deadline, technical blocker, conflicting priorities)
and be concrete about what you actually did, not just that you "stayed calm."

**12.4 — "Why do you want to work at Cognizant?"**
Strongest answers connect something specific and true about the role/company (its Gen AI investment,
client-facing consulting model, project scale) to something specific and true about your own goals —
generic enthusiasm reads as generic.

**12.5 — "Are you willing to work [specific shift / relocate / hybrid arrangement]?"**
Answer directly and honestly — this is a logistics-fit question, and review data suggests mismatches
here cause late-stage drop-offs even after strong technical rounds. Surface real constraints early
rather than after an offer.

**12.6 — "Walk me through a project from your resume."** `[CONFIRMED]`
*Why flagged: This is something interviewers explicitly probe for in real Cognizant reports.*
Problem/business context first (not just the tech) → your specific contribution (precise about what you
did vs. the team) → approach and key technical decisions → outcome/impact, quantified where possible →
one honest limitation or thing you'd improve. That last part signals maturity.

---

## 13. Cognizant-Specific
*Suggested timing: Year 2*

**13.1 — What does Cognizant actually do?**
A US-headquartered, NASDAQ-listed IT services and consulting company that helps other businesses
modernize technology, run operations, and increasingly build/deploy AI solutions for them — a
services/consulting model, not a consumer AI product company.

**13.2 — How does the general AI/Data Science delivery track differ from Cognizant's AI Labs (Neuro AI) team?**
Delivery roles (most Data Scientist/Gen AI Engineer postings) build and ship AI solutions directly for
client projects on client timelines. The AI Labs/Neuro AI team is positioned as more research-oriented,
exploring multi-agent and decision-AI techniques with closer ties to academia — a smaller, more
exploratory track.

**13.3 — How hard is the Cognizant AI/Data Science interview, realistically?**
*Low–medium confidence — based on a small, self-reported sample.*
Candidate-reported difficulty has sat around 2.8 out of 5, with roughly 60% of experiences rated
positive — slightly below Cognizant's company-wide average. That suggests a moderate, not extreme, bar,
but not a rubber stamp either.

---

## How to use this with your existing setup

This pairs naturally with the `CLAUDE.md` mentor file in this folder: have it quiz you cold on the
`[CONFIRMED]` questions especially, since those map to things real candidates were actually asked.
Track progress the same way as the other tracks — a tab per topic, revisited periodically so review
naturally resurfaces topics you haven't touched in a while (see `plan.md`'s review cadence).
