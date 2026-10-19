# FloodSaathi — Agent Rulebook (AGENTS.md)

> Every AI coding agent working on FloodSaathi must read and follow this file first.

---

## Project Summary (5 lines)

FloodSaathi is a Python/Streamlit decision-support tool for flood emergencies in India.
It shows a risk map, 48-hour rain/river forecasts, triages help requests (Hindi/English/Hinglish)
using Claude, and matches each request to the nearest shelter, hospital, and volunteer.
All data is synthetic; no real personal data is ever stored.
The project targets a 24–48 hour hackathon timeline with four MVP features.

---

## Read These Docs First (in order)

1. [`PRD.md`](PRD.md) — vision, personas, user stories, 4 MVP features, non-goals, metrics
2. [`DESIGN.md`](DESIGN.md) — color system, wireframes, components, accessibility
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — system diagram, folder structure, data flows, caching
4. [`DATABASE.md`](DATABASE.md) — ER diagram, table schemas, indexes, seed plan
5. [`API.md`](API.md) — internal service functions, Pydantic models, external API limits

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill environment variables
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY

# Initialise database and seed data
python src/db/init_db.py

# Run the app
streamlit run app.py

# Run all tests
pytest tests/ -v

# Run linter
ruff check src/ pages/ tests/

# Format code
black src/ pages/ tests/

# Run triage accuracy benchmark
pytest tests/test_triage.py -v -k "accuracy"
```

---

## Code Style

| Rule | Detail |
|------|--------|
| **Type hints** | All functions must have type hints on parameters and return values |
| **Docstrings** | Every public function and class gets a one-line docstring minimum |
| **Function size** | Keep functions under 40 lines; extract helpers freely |
| **Formatter** | `black` (line length 100) |
| **Linter** | `ruff` — fix all `E`, `F`, `W` violations; `I` (import sort) enforced |
| **Naming** | `snake_case` for variables and functions; `PascalCase` for classes |
| **Constants** | ALL_CAPS at module level; never magic numbers inline |
| **Imports** | Standard library → third-party → local; sorted by `ruff --fix` |

---

## Rules

### 1. Work in Small Steps
One feature or bug fix per task. Do not combine unrelated changes.
Commit after each working increment.

### 2. One Feature per Task
Do not implement two MVP features in the same coding session.
Start with the lowest-level module (data fetcher) and work up to the UI page.

### 3. Run the App and Tests After Each Change
```bash
streamlit run app.py   # check no import errors
pytest tests/ -v       # check nothing regressed
```
Do not submit a change that breaks existing tests.

### 4. Never Hardcode API Keys
All secrets come from `.env` via `python-dotenv`.
Never write `api_key = "sk-..."` in source code.
Use `config.py` getters that raise `ValueError` with a clear message if the key is missing.

### 5. Never Commit `.env`
`.env` is in `.gitignore`. Commit only `.env.example` with placeholder values.

### 6. Always Add a Cached Fallback for External Calls
Every function that calls an external API must:
1. Try the live API with `timeout=5`.
2. On failure, log the error and read from `data/cache/<name>_cache.json`.
3. If the cache is also missing, return `None` and let the caller show an error banner.

Do not let a demo fail because an API is down.

### 7. Never Store Real Personal Data
All citizen records are synthetic. Do not add a form that collects real names,
phone numbers, Aadhaar IDs, or real GPS coordinates of real people.
The `help_requests.raw_text` field holds demo messages only.

### 8. Do Not Add New Dependencies Without Asking
Check `requirements.txt` before importing a new library.
If you need something not listed, ask the human first and explain why.

### 9. Update Docs When Behaviour Changes
If you change a function signature, endpoint, schema column, or config key,
update the relevant doc (API.md, DATABASE.md, ARCHITECTURE.md) in the same commit.

---

## Definition of Done Checklist

Before marking any task complete, verify:

- [ ] Feature matches the acceptance criteria in `PRD.md`.
- [ ] All new functions have type hints and a docstring.
- [ ] `black` and `ruff` pass with zero errors.
- [ ] `pytest tests/` passes with no failures.
- [ ] External API call has timeout, retry, and cached fallback.
- [ ] No API keys appear in source code.
- [ ] No real personal data is introduced.
- [ ] Relevant doc (API.md / DATABASE.md / ARCHITECTURE.md) is updated if needed.
- [ ] The Streamlit page renders without exceptions on `streamlit run app.py`.
- [ ] Empty, loading, and error states are handled (per `DESIGN.md`).

---

## When Stuck

1. **Read the error message carefully** — most errors are self-explanatory.
2. **Reproduce in isolation** — write a minimal script in `src/db/scratch/` that triggers the bug.
3. **Fix the root cause** — do not suppress exceptions or add bare `except: pass`.
4. **Check the docs** — re-read the relevant section of `ARCHITECTURE.md` or `API.md`.
5. **Try once more** with a different approach.
6. **Only after 2 failed attempts**, ask the human:
   - Share the exact error traceback.
   - Share what you tried and why it failed.
   - Propose a specific question, not a vague "what should I do?"

---

## Common Pitfalls

| Pitfall | Prevention |
|---------|-----------|
| Streamlit reruns breaking SQLite writes | Use WAL mode; single-writer pattern in `queries.py` |
| Nominatim rate-limit (1 req/s) | Cache geocodes for 7 days; `time.sleep(1)` between calls |
| Claude returning malformed JSON | Validate with `TriageResult.model_validate_json()`; fall back to `fallback.py` |
| Folium map not updating on rerun | Use `st.session_state` to store the map object; call `st_folium()` once |
| Hindi text displaying as boxes | Ensure `utf-8` encoding everywhere; use `st.markdown()` not `st.write()` for Devanagari |
| `.env` not loaded in tests | Add `load_dotenv()` to `tests/conftest.py` |
