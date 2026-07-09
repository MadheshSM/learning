# Learning Plan — Multi-Agent Construction Analytics Backend

**Purpose:** Build enough working knowledge to read, debug, and extend this codebase confidently.
**Format:** 5 phases, roughly in dependency order (each phase leans on the one before it). Pace is yours — the day counts are a starting suggestion, not a deadline.

> A note on sources before you start: this plan is built entirely from the concept breakdown you shared, not from reading the actual repo. File names (`base_agent.py`, `orchestrator.py`, etc.) come from your document, so they should be accurate — but I haven't verified line numbers, exact signatures, or current behavior myself. Treat every "go look at X" instruction as a *pointer*, not a guarantee, and adjust if what you find differs. [I have not inspected this code directly — verify specifics against the real files.]

---

## How to Use This Plan

For each concept you'll find four things:
1. **Learn** — the specific sub-topics to actually read up on (not "learn async," but the precise pieces you need).
2. **Why it's here** — the concrete reason this concept exists in *this* project, not a generic justification.
3. **Find it** — where to look in the repo (per your breakdown).
4. **Practice** — a small, standalone exercise (write real code, separate from the repo) before you go hunting in the real files. Doing the concept in isolation first makes reading it in 1900-line `main.py` much less intimidating.

Each phase ends with a **checkpoint**: a question you should be able to answer out loud, unaided, before moving on.

---

## Suggested Timeline

| Phase | Focus | Tiers from your doc | Rough pace |
|---|---|---|---|
| 1 | Python core foundations | Tier 1 (#1–5) | 4–5 days |
| 2 | Frameworks & libraries | Tier 2 (#6–11) | 5–7 days |
| 3 | Design patterns | Tier 3 (#12–17) | 4–5 days |
| 4 | Cross-cutting concerns | Tier 4 (#18–21) | 3–4 days |
| 5 | Domain & project-specific | Tier 5 (#22–25) | 2–3 days |
| — | Capstone: trace one request | All of the above | 1–2 days |

Total: roughly 3–4 weeks at a steady pace, less if you're already comfortable with parts of Tier 1–2.

---

## Phase 1: Python Core Foundations

This phase is non-negotiable — everything else sits on top of it. Don't skip to FastAPI before this feels solid.

### 1.1 Abstract Base Classes & Inheritance
- **Learn:** `from abc import ABC, abstractmethod`, `@property`, method overriding, `super().__init__()`, the "template method" pattern (base class owns the control flow loop; subclasses fill in specific steps).
- **Why it's here:** `BaseAgent(ABC)` defines the contract every specialist agent must satisfy. This is *the* organizing idea of the codebase — if you understand this, the rest of the agent layer reads like a checklist, not a maze.
- **Find it:** `base_agent.py` (the ABC + abstract methods: `name`, `description`, `capabilities`, `_register_tools()`, `_execute_tool()`), and the same pattern repeated in `llm_providers/base.py` and the cache `base.py`.
- **Practice:** Write a tiny `BaseShape(ABC)` with abstract `area()` and a concrete `describe()` method that calls `self.area()`. Implement `Circle` and `Square`. Confirm Python refuses to instantiate `BaseShape` directly and refuses to instantiate a subclass that's missing `area()`.
- **Self-check:** *Why does `BaseAgent` define the loop and not each subclass? What breaks if `SafetyAgent` tried to override `process()` instead of just `_execute_tool()`?*

### 1.2 async/await and asyncio
- **Learn:** what a coroutine actually is (a function that can pause), `await`, why `await self.llm.chat(...)` is required, `async with httpx.AsyncClient() as client:`, `asyncio.sleep`, `async def` route handlers in FastAPI.
- **Why it's here:** Every I/O-bound operation (LLM calls, HTTP calls to Autodesk/Krion6d, the cache) is a coroutine. Forgetting an `await` is, per your doc, the single most common bug source — so this is worth over-learning.
- **Find it:** `main.py`, the agent loop in `base_agent.py`, every API client, the cache layer.
- **Practice:** Write two async functions that each `await asyncio.sleep(1)` and print a message. Run them with `asyncio.gather()` and confirm they finish in ~1 second total, not 2. Then write a version where you forget an `await` on purpose and observe what Python actually does (a coroutine object, not a result) — this is the exact failure mode you're trying to recognize on sight.
- **Self-check:** *What's the difference between `result = my_async_func()` and `result = await my_async_func()`? What type is `result` in each case?*

### 1.3 Type hints & typing
- **Learn:** `Optional[X]` (same as `X | None`), `List[Dict]`, `Dict[str, Any]`, `Union[dict, list]`, and reading a real signature like `def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse`.
- **Why it's here:** These aren't decoration — Pydantic and FastAPI actually enforce them at request/response boundaries. Misreading a type hint here can mean misunderstanding what's actually guaranteed to be present.
- **Find it:** Everywhere — agent methods, tool signatures, FastAPI route handlers.
- **Practice:** Write a function `def summarize(rows: List[Dict[str, Any]], limit: Optional[int] = None) -> str:` with a real (if simple) body, and call it both correctly and with a wrong type. Type hints alone don't enforce anything at runtime in plain Python — confirm that for yourself, then go check how Pydantic changes that story in Phase 2.
- **Self-check:** *Does a plain Python function with type hints raise an error if you pass the wrong type? Does a Pydantic model?*

### 1.4 @dataclass
- **Learn:** `@dataclass`, default values, `field(default_factory=...)`, and adding ordinary methods (like `to_dict()`) to a dataclass.
- **Why it's here:** The internal data-transfer objects — `AgentResponse`, `ChartConfig`, `ToolCall`, `LLMResponse`, `Message` — are all dataclasses. They're the "shape" of data as it moves between agents, tools, and providers.
- **Find it:** `base_agent.py`, `llm_providers/base.py`.
- **Practice:** Write a `@dataclass class ToolCall` with `name: str`, `arguments: Dict[str, Any] = field(default_factory=dict)`, and a `to_dict()` method. Instantiate it two ways: with explicit arguments, and relying on the default factory. Confirm the two instances don't share the same dict object (this is *why* `field(default_factory=dict)` exists instead of `arguments: Dict = {}`).
- **Self-check:** *Why is a mutable default value like `{}` directly on a dataclass field dangerous, and what does `default_factory` fix?*

### 1.5 Dictionaries, lists & JSON
- **Learn:** `.get()` with defaults (used constantly for safe access), comprehensions (`[r.get("count") for r in rows]`), `json.loads`, `json.dumps(..., default=str)`.
- **Why it's here:** Dicts are the lingua franca — tool inputs/outputs, LLM messages, chart configs, API responses are all nested dicts/lists. A lot of code parses raw LLM text *back* into JSON.
- **Find it:** Look for `_parse_final_response` as a concrete example of "LLM text → JSON" parsing.
- **Practice:** Take a small nested dict resembling a chart config (`{"type": "bar", "data": [{"label": "A", "value": 1}, ...]}`), write a one-line comprehension to pull out just the labels, then round-trip it through `json.dumps`/`json.loads`. Then deliberately feed `json.loads` a malformed string and handle the `json.JSONDecodeError` — this is exactly the failure mode `_parse_final_response`-style code has to defend against when an LLM doesn't return clean JSON.
- **Self-check:** *Why does almost every dict access in this codebase use `.get("key")` instead of `["key"]`? What happens differently when the key is missing?*

**Phase 1 checkpoint:** Open `base_agent.py` (once you have repo access) and read just the class signature and abstract method list, without reading any method bodies. You should be able to say, in your own words, what every subclass is *forced* to provide, and what `async` tells you about how those methods will be called.

---

## Phase 2: Frameworks & Libraries

### 2.1 FastAPI
- **Learn:** `@app.post("/api/query")`, path/query params (`Query(...)`), the `Request` object, `HTTPException`, lifespan startup/shutdown (`@asynccontextmanager`), `StaticFiles`/`FileResponse`, CORS middleware.
- **Why it's here:** This is the web layer — `main.py` is ~1900 lines of it, per your doc. Auto-generated docs live at `/docs` once the server is running, which is genuinely useful for exploring the API surface without reading all 1900 lines at once.
- **Practice:** Build a minimal FastAPI app (a handful of lines) with one `POST` route that accepts a Pydantic model and returns a dict. Run it, hit `/docs`, and send a request through the interactive UI. Then add an `HTTPException(status_code=400, ...)` path and trigger it on purpose.
- **Self-check:** *What's the difference between a path parameter, a query parameter, and a request body field — and how does FastAPI know which is which from a function signature?*

### 2.2 Pydantic (v2)
- **Learn:** `class X(BaseModel)`, field defaults, `Optional` fields, how Pydantic auto-validates incoming JSON and serializes outgoing responses.
- **Why it's here:** `QueryRequest`, `QueryResponse`, `FilterQueryRequest`, etc. are the request/response contracts at the API boundary. This is the "Phase 1.3 type hints, but enforced" payoff.
- **Find it:** Note the deliberate split your doc calls out: **dataclasses** for internal data, **Pydantic models** for the API boundary. Know *why* both exist rather than just one — it's a real design decision, not redundancy.
- **Practice:** Define a Pydantic model with a required `str` field and an `Optional[int]` field. Try constructing it with a missing required field and watch the validation error. Then construct it with a string where you declared an `int` and see whether Pydantic coerces or rejects it (v2 behavior here is worth confirming for yourself rather than assuming).
- **Self-check:** *If a dataclass and a Pydantic model can both hold the same fields, what does the Pydantic one give you that the dataclass doesn't?*

### 2.3 The LLM SDKs & tool-calling protocol
- **Learn:** the general shape of LLM tool/function calling: you send the model a list of tool schemas (`{"name", "description", "input_schema"}`), it replies with either text or a request to call a tool, you execute that tool and feed the result back, and you loop. This is the mechanism behind the `for iteration in range(self.max_iterations)` loop in `BaseAgent.process()`.
- **Why it's here:** This is the actual product — agents reason by repeatedly calling tools rather than producing a single answer in one shot.
- **Find it:** `llm_providers/claude_provider.py` — specifically how the abstract `chat()`/`_convert_tools()`/`_convert_messages()` map onto a real provider API.
- **A flag from your own doc, worth taking seriously:** it notes the model IDs in `factory.py` are outdated. Model identifiers and SDK details change frequently enough that I'd rather not state a specific "current" model string here with confidence — when you touch that code, check Anthropic's own current documentation (docs.anthropic.com) rather than trusting any model name you find in older code or in my training data. [Low confidence on any specific model ID I might otherwise guess — please verify directly.]
- **Practice:** Without touching the real provider code yet, sketch the loop yourself in pseudocode: `messages = [...]`; loop while the model's response contains tool calls: execute each tool, append the *result* as a new message, send the updated `messages` list back. Getting this loop shape into your hands first makes `BaseAgent.process()` recognizable rather than novel.
- **Self-check:** *What signals to the loop that the agent is "done" and should stop iterating?*

### 2.4 pandas
- **Learn:** `DataFrame`, `Series`, `.iloc`, `.dropna()`, `.to_dict('records')`, boolean-mask filtering, `groupby`, reading CSV/Excel (`read_csv`, `openpyxl`).
- **Why it's here:** `QueryEngine` and the `data_layer/*_loader.py` files are built on DataFrames. The tools in `agents/tools/` (data, aggregation, chart tools) are essentially pandas wrappers exposed as LLM-callable functions.
- **Practice:** Load a small CSV (even one you make up — a few rows of `project, cost, status`), filter it with a boolean mask, group by `status` and aggregate `cost`, then convert the result to `.to_dict('records')` — that exact output shape is what an LLM tool would typically return.
- **Self-check:** *Why convert a DataFrame to `.to_dict('records')` before sending it back through a tool result, instead of sending the DataFrame itself?*

### 2.5 httpx (async HTTP client)
- **Learn:** async GET/POST, headers/bearer tokens, `resp.json()`, `resp.raise_for_status()`, status-code handling, `httpx.RequestError`.
- **Why it's here:** All external API calls — Autodesk ACC, Krion6d, APS GraphQL — go through it: `async with httpx.AsyncClient(timeout=30) as client: resp = await client.get(...)`.
- **Practice:** Write an async function that hits any public test API (e.g. a simple JSON-returning endpoint) with `httpx.AsyncClient`, sets a timeout, and handles both an `httpx.RequestError` and a non-200 status via `raise_for_status()`.
- **Self-check:** *What's the practical difference between a network failure (`httpx.RequestError`) and a successful response with an error status code — and why does the code need to handle both separately?*

### 2.6 Environment config — python-dotenv + os.getenv
- **Learn:** the 12-factor "config in environment" pattern, `load_dotenv()`, `os.getenv("X", default)`.
- **Why it's here:** API keys, `LLM_PROVIDER`, data directories, APS auth all come from `.env` (see `.env.example`).
- **Practice:** Create a small `.env` file with one variable, `load_dotenv()` it, and read it with `os.getenv("YOUR_VAR", "fallback")`. Then delete the variable from `.env` and confirm the fallback kicks in.
- **Self-check:** *Why keep secrets in environment variables instead of hardcoding them in source — and why is `.env.example` checked in while `.env` itself usually isn't?*

**Phase 2 checkpoint:** Without looking at the repo, describe the full path of one request: a JSON body arrives at a FastAPI route → gets validated into a Pydantic model → eventually an agent calls an LLM with tool schemas → a tool wraps a pandas operation → the result becomes JSON again. If you can narrate that from memory, Phase 2 has done its job.

---

## Phase 3: Design Patterns ("why it's shaped this way")

These patterns are *why* the code is organized the way it is, not new syntax — Phase 1–2 covered the syntax.

### 3.1 Factory Pattern
- **Learn:** factory method, registry dict, `Enum` (`class LLMProviderType(str, Enum)`).
- **Why it's here:** `LLMProviderFactory.create_from_env()` picks a provider class from a string at runtime; a `_providers` dict maps an enum value to a class.
- **Find it:** `llm_providers/factory.py`.
- **Practice:** Write a tiny factory: an `Enum` with `CIRCLE`/`SQUARE`, a dict mapping each enum value to a class, and a `create(shape_type: str)` function that looks up and instantiates the right one. Add a third shape later and notice you only touch the dict, not any calling code.

### 3.2 Strategy / Provider abstraction
- **Why it's here:** LLM providers and cache backends are interchangeable strategies behind one interface (`BaseLLMProvider`/`BaseCache`). Code depends on the abstraction, never a concrete class — so swapping Claude↔GPT↔Gemini or memory↔Redis shouldn't require touching agent code.
- **Self-check:** *If you wanted to add a fourth LLM provider tomorrow, which files would you expect to touch, and which files should you NOT need to touch?*

### 3.3 Orchestrator / Router pattern
- **Learn:** the dispatcher pattern, and graceful degradation (LLM routing fails → fall back to keyword routing → fall back to a default agent).
- **Why it's here:** `orchestrator.py` decides which agent(s) handle a query (`_analyze_and_route()`, with a `_default_routing()` keyword fallback and short-circuit routing by data source), then `_synthesize_responses()` merges multi-agent output.
- **Practice:** Sketch (in pseudocode or real code) a `route(query: str) -> str` that first tries an LLM-style classification, catches a failure, and falls back to simple keyword matching (`if "safety" in query.lower(): return "safety_agent"`). This three-tier fallback shape — primary, fallback, default — repeats throughout this codebase (see also 3.4 and Tier 4's error handling).

### 3.4 The Agentic Loop (the project's signature pattern)
- **Learn:** `BaseAgent.process()` as a bounded loop (`max_iterations = 8`): call LLM → if tool calls, execute and append results to `messages` → repeat → when no tool calls, parse the final JSON answer.
- **Watch for four specific things while reading the real code:**
  - message accumulation (the growing `messages` list across system/user/assistant/tool turns)
  - result truncation (`_truncate_result_for_llm` — keeps context small)
  - auto-injection of `project_id` into tool inputs
  - per-turn state reset (`_reset_turn_state`)
- **Why it's here:** This *is* the product's core mechanism, combining 2.3's tool-calling concept with a hard iteration cap so a confused agent can't loop forever.

### 3.5 Dependency Injection (constructor injection)
- **Learn:** receiving dependencies (`llm_provider`, `query_engine`) through `__init__` rather than an object creating its own dependencies.
- **Why it's here:** `initialize_system()` in `main.py` is the composition root — it wires everything together once. Your doc flags one spot as subtle and a common breakage point: the `/api/query` handler hot-swaps `query_engine` into agents per-request for different data sources, then restores it in a `finally` block.
- **Self-check:** *Why use a `finally` block for the restore step specifically, rather than just restoring at the end of the normal code path?* (Think about what happens if the request raises an exception partway through.)

### 3.6 Adapter / Normalizer
- **Why it's here:** `_convert_messages`/`_convert_tools` adapt your common internal format to each vendor's specific API shape; `_normalize_table_charts` and `aps_service/normalizer.py` adapt messy external data into the shape the frontend expects.
- **Self-check:** *What would break in the frontend if `_normalize_table_charts` didn't exist — i.e., what assumption does the frontend get to make because of it?*

**Phase 3 checkpoint:** Pick any one pattern above and explain, without code, what problem it solves *if it were removed*. (E.g., "without the Factory, swapping LLM providers would mean...")

---

## Phase 4: Cross-Cutting Concerns

### 4.1 Caching (with TTL) + Null Object pattern
- **Learn:** TTL/expiry, cache key design, basic Redis concepts.
- **Why it's here:** `cache/base.py`, `memory_cache.py`, `redis_cache.py`. Results are cached by `(query, project_id)`. Note the deliberate choice: live sources (Krion6d, viewer, ERP, BIM) **skip** caching entirely.
- **Self-check:** *Why would you deliberately refuse to cache live data sources, even though caching everything would be simpler code?*

### 4.2 Authentication: JWT + OAuth 2.0
- **Learn:** bearer tokens, token expiry/refresh, the OAuth authorization-code flow, the `postMessage` popup-callback trick.
- **Find it:** `verify_bearer_token()` decodes `Authorization: Bearer` tokens via `jwt.decode(..., algorithms=["HS256"])`, handling `ExpiredSignatureError`. The Autodesk ACC 3-legged flow runs through `/api/acc/login` → popup → `/api/acc/callback` (see `ACCAuthManager`). APS also has 2-legged/service-account auth in `aps_service/ssa_auth.py`.
- **Practice:** Even without building a full OAuth flow, write a tiny script using `PyJWT` to encode a token with a short expiry, decode it immediately (works), wait past expiry, decode again, and catch the `ExpiredSignatureError`. That single exception is exactly what `verify_bearer_token()` has to handle gracefully.

### 4.3 Logging & tracing
- **Learn:** `logging.getLogger(__name__)`, log levels, the idea of a per-request trace object.
- **Why it's here:** Standard `logging` throughout, plus a custom `interaction_logger` (`get_tracer`/`reset_tracer`) recording every routing decision, tool call, and result — this feeds the frontend's "how it was answered" view.
- **Self-check:** *Why would a per-request trace object need to be reset between requests rather than reused as a global?*

### 4.4 Error handling & resilience
- **Learn:** converting exceptions to `HTTPException`, `finally` cleanup blocks, fallback data sources (e.g., a Krion6d dashboard fallback when list endpoints fail), custom exception mapping (`PermissionError` → 401).
- **Why it's here:** Per your doc, maintaining this codebase is largely about *not breaking these safety nets* — so before changing any function, ask what exception path you might be removing.

**Phase 4 checkpoint:** Find (or imagine, if you haven't read the code yet) one `try/except` block and explain what specifically fails if that block didn't exist — not generically "an error would happen," but what user-facing behavior breaks.

---

## Phase 5: Domain & Project-Specific

### 5.1 The layered architecture (mental model)
Internalize this request flow — every change you make lands somewhere on it:

```
Frontend (vanilla JS)
   → FastAPI route (main.py)
      → Orchestrator (route + synthesize)
         → Specialist Agent (agentic loop)
            → Tools (agents/tools/*) + Service layer (aps_service/*)
               → Data Layer (QueryEngine / loaders / API clients)
```

### 5.2 Construction/BIM domain vocabulary
You'll be lost in the routing logic without these terms: **ACC** (Autodesk Construction Cloud), **APS** (Autodesk Platform Services), **BIM**, RFI/RFA/submittals/transmittals, issues/punch lists/checklists, BOM/BOQ, WBS, clashes, hub/project/model view, and **GraphQL** (used for AEC element queries). The `data/` folder's CSV names should mirror this vocabulary — a quick skim of those filenames is a fast way to learn the domain.

### 5.3 The chart/response contract
- **Learn:** the frontend only renders when `charts` is a non-empty array of a specific shape (bar/pie/line/table/kpi) — defined in the large prompt inside `_build_system_prompt`. `_supplement_charts_if_missing` rebuilds charts when the LLM forgets to produce them.
- **Why it matters:** Know this contract *before* touching any agent's output — it's the thing most likely to silently break the UI if violated.

### 5.4 Project layout & packaging
- **Learn:** Python packages via `__init__.py`, intra-project imports (`from agents.base_agent import ...`), the module groupings (`agents/`, `llm_providers/`, `data_layer/`, `aps_service/`, `cache/`, `export/`), `requirements.txt`.
- Your doc mentions a `plan.md` already exists in the repo documenting the BIM-agent integration — worth reading once you have repo access, since it's project history you can't get from the code alone.

---

## Capstone Exercise: Trace One Request End-to-End

This is the single highest-value exercise in this whole plan, and it's explicitly recommended in your original breakdown — do it with a debugger, not just by reading:

1. Pick the simplest plausible query (e.g., "how many open RFIs are there").
2. Set a breakpoint at the top of the `/api/query` handler in `main.py`.
3. Step through into the orchestrator's routing decision — watch *why* it picks the agent it picks.
4. Step into that agent's `process()` loop — watch one full LLM call → tool call → result-append cycle.
5. Step into the actual tool function and watch the pandas operation happen.
6. Step back out and watch the final response get parsed and shaped into the chart contract.
7. Watch it land back at the frontend.

Write down, in your own words, every place a dict changed shape along that path. That list *is* your mental model of the system.

---

## Self-Assessment Checklist

- [ ] I can explain why `BaseAgent` is an ABC and what subclassing actually buys the project.
- [ ] I can explain, without notes, what happens if you call an async function without `await`.
- [ ] I can explain why dataclasses and Pydantic models *both* exist in this codebase.
- [ ] I can describe the agentic loop's stopping condition from memory.
- [ ] I can explain the three-tier fallback shape (primary → fallback → default) and name at least two places it appears.
- [ ] I can explain why live data sources skip the cache.
- [ ] I can describe the full request path from frontend to data layer and back, without looking it up.
- [ ] I've completed the end-to-end debugger trace at least once.

---

## A Few Notes on Trusting This Plan

- File paths, function names, and behaviors above are drawn directly from the breakdown you provided, not from me reading the repository myself — I haven't verified any of it against the actual source. [I have not inspected this code directly.]
- The note about outdated model IDs in `factory.py` is *your* document's claim, repeated here as a flag, not something I independently confirmed. For current Anthropic model identifiers specifically, check Anthropic's own documentation rather than older code or my say-so. [Low confidence — please verify directly against current docs.]
- The external documentation links below are to stable top-level doc sites I'm reasonably confident exist as named; I haven't fetched them just now, so if a specific sub-page has moved, that's expected over time, not a sign you misread something. [Medium confidence on exact current page structure — the top-level sites themselves I'm confident about.]

**Reference docs (official sources only):**
- Python: `abc`, `asyncio`, `typing`, `dataclasses`, `json` — docs.python.org
- FastAPI — fastapi.tiangolo.com
- Pydantic v2 — docs.pydantic.dev
- pandas — pandas.pydata.org/docs
- httpx — python-httpx.org
- PyJWT — pyjwt.readthedocs.io
- Anthropic API / tool use — docs.anthropic.com

If anything in this plan turns out to not match the actual repo once you're in it, that's the repo correcting the plan, not the other way around — update your own notes as you go rather than forcing the code to match this document.
