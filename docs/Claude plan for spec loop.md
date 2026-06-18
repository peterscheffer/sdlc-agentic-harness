# Plan: Applying 3-Layer Spec Framework to MoM

## Context

**What:** Evaluate whether MoM can adopt a "spec-as-source-of-truth" architecture where:
- Layer 1 (Domain/Intent) = business logic in readable form (Gherkin, decision tables)
- Layer 2 (Contract/Topology) = formalized interfaces (OpenAPI, JSON Schema, state machines)  
- Layer 3 (Reality/Mechanics) = implementation constraints and deviations (discovered during build, formalized back into specs)
- Code treated as regenerable artifacts, not the source of truth

**Why:** The current MoM pipeline is strong on orchestration but weak on:
1. Formal contracts (Layer 2 doesn't exist; ARCH.md is narrative)
2. Deterministic verification (all checks are LLM self-grading, not rule-driven)
3. Spec-code bidirectionality (test failures and code drift don't flow back into specs)
4. Implementation drift detection (no automated reconciliation of actual vs. specified)

**Goal:** Determine whether extending MoM's current architecture is feasible, or if portions need fundamental redesign.

---

## Assessment: Fit Analysis (Can MoM Be Extended?)

### ✓ What MoM Already Has (60% Fit)

**Orchestration backbone:**
- Stateful state machine with sequence enforcement (planning → ui-design → architecture → requirements → coding → testing → review → pr)
- Per-stage gate checks that block advancement
- Persistent state to `.sdlc_state.json`, enabling resume across sessions
- Audit trail (every LLM call logged to `sdlc/logs/`)
- Configuration-driven (per-stage models, timeouts, test commands in `sdlc.config.json`)

**Layer 1 (Domain) artifacts:**
- PRD generation with intent capture (executive summary, goals, non-goals, acceptance criteria, tasks)
- Gherkin feature files for business-readable scenarios (`requirements.py`)
- REQUIREMENTS.md with functional/non-functional/behavioral requirements

**Layer 3 (Reality) tracking (partial):**
- Test execution with pass/fail parsing
- Coverage tracking
- Iteration logging for coding loop
- Gate check results captured in state

**Versioning & updates:**
- `prd_updater.py` already does PRD versioning
- Conditional PRD updates on stage completion

### ✗ What's Missing (40% Gap)

**Layer 2 (Contract/Topology):**
- No JSON Schema generation for state objects, request/response payloads
- No OpenAPI/AsyncAPI/GraphQL SDL extraction or generation
- No component interface specs (props, events, states)
- No dataflow diagrams or service topology
- No database schema formalization
- No event/message contract definitions
- ARCH.md is pure narrative Markdown; target files table exists but no semantic validation

**Deterministic verification:**
- Gherkin compliance check is LLM-based (`_check_gherkin_compliance()` sends full feature + code to LLM)
- Review is LLM-based narrative (`review.py` asks LLM to judge conformance)
- PRINCIPLES compliance checks are stubs (`principles_checker.py` has unimplemented validation)
- Code generation lacks semantic validation (regex extraction, no AST parsing or type checking)
- No rule-driven checklist verification

**Spec-code bidirectionality (no `/truth` workflow):**
- Test failures don't update specs (capture only pass/fail counts, not root cause analysis)
- Code drift not detected or formalized (no comparison of implemented vs. specified)
- Architecture violations not flagged (no automated check that code matches ARCH.md target files)
- Repeated failures don't generate error handling specs
- Coverage gaps don't update requirements

**Drift detection:**
- No automated comparison of:
  - Implemented files vs. ARCH.md target files table
  - Generated APIs vs. architectural design decisions
  - Test coverage vs. Gherkin scenarios
  - Exception patterns in code vs. error handling spec
- Code output validated only at regex level, not semantic

**Formalized business rules:**
- No decision tables, state machines, or explicit rule definitions in Layer 1
- Error handling is Markdown prose, not machine-readable

---

## Recommended Path Forward: Extension vs. Replacement

### Verdict: **Extension + Partial Refactor of Verification**

MoM's orchestration and Layer 1 generation are solid. The framework can be extended by:

1. **Add Layer 2 (Contract) generation** — new stages or sub-steps in existing stages
2. **Replace LLM-based verification with deterministic checks** — significant refactor of `review.py` and `testing.py`
3. **Implement `/truth` feedback loop** — new stage or hook into `prd_updater.py`
4. **Formalize Layer 3 capture** — structured error/constraint specs, not prose

**Do NOT scrap and rebuild.** The state machine, gate checks, and PRD generation are load-bearing. Modify in place.

---

## Detailed Extension Plan

### Phase 1: Layer 2 (Contract) Generation

**Goal:** Generate formal interface specs from architectural intent.

**Changes:**
- **In `architecture.py`**: After ARCH.md generation, extract:
  - OpenAPI 3.1 spec (if service/API endpoints mentioned)
  - JSON Schema for state objects mentioned in design
  - Component interface definitions (if UI components listed)
  - State machine definitions (XState format or ASL)
  
  Output to `sdlc/architecture/API.openapi.yaml`, `sdlc/architecture/SCHEMA.json`, etc.

- **In `ui_design.py`**: After DESIGN.md, extract:
  - Component prop types (JSON Schema)
  - Event definitions (which events each component emits?)
  - Accessibility contract (ARIA roles, keyboard nav)
  
  Output to `sdlc/ui-design/COMPONENTS.schema.json`, `sdlc/ui-design/ACCESSIBILITY.md`

- **New helper:** `utils/spec_extractors.py` with functions:
  - `extract_openapi_from_architecture(arch_md)` → OpenAPI object
  - `extract_json_schema_from_requirements(req_md, prd)` → JSON Schema
  - `extract_state_machine_from_architecture(arch_md)` → XState config or ASL
  - `extract_component_contracts_from_design(design_md)` → props + events

**Effort:** ~200 lines; reuse LLM extraction (not rejection) for first pass, validate with Pydantic schemas.

**Gate:** Verify Layer 2 specs are valid JSON/YAML (parse-able) and non-empty.

---

### Phase 2: Deterministic Verification (Major Refactor)

**Goal:** Replace LLM self-grading with rule-driven checks.

**Changes:**

#### In `testing.py`:
- **Gherkin compliance** — replace LLM-based check with:
  1. Parse `.feature` files with `behave` or `pytest-bdd` library
  2. Extract scenario titles and Given/When/Then steps
  3. Run tests with `pytest --collect-only` to get test function signatures
  4. Map step definitions to test functions (by name or ID)
  5. Check: every scenario has a corresponding test function (deterministic string match)
  6. Output: compliance matrix (scenario → test function → pass/fail)
  
  **Replaces:** `_check_gherkin_compliance()` LLM call (line 260–330)
  
- **Test coverage vs. requirements:**
  1. Parse test names/docstrings to extract requirement IDs
  2. Parse REQUIREMENTS.md to extract requirement IDs
  3. Check: every requirement has at least one test
  4. Output: coverage matrix (requirement → test → pass/fail)

#### In `review.py`:
- **ARCH.md vs. code** — replace LLM narrative with:
  1. Parse ARCH.md Target Files table → expected_files
  2. Parse git diff → changed_files
  3. Check: all changed_files in expected_files OR explicitly marked as "deferred" or "out-of-scope"
  4. For each changed file: AST parse (Python) or grep (JS/Go/etc.) to extract top-level functions/classes
  5. Check: new functions match function names in ARCH.md design decisions
  6. Output: checklist (file ✓/✗, functions ✓/✗, deviations flagged)
  
  **Replaces:** LLM review (lines 1–100)

- **PRINCIPLES compliance** — fix the stubs in `principles_checker.py`:
  1. `_check_forbidden_pattern()` — grep for hardcoded secrets, eval(), exec(), etc.
  2. `_check_missing_type_hints()` — AST parse to verify all function args have type annotations (Python)
  3. `_check_test_coverage()` — fail if coverage% below threshold
  
  **Replaces:** stubs returning False (currently unimplemented)

- **Output:** Machine-readable checklist (JSON or YAML) with pass/fail per rule, not narrative.

**Effort:** ~400 lines; requires AST/regex parsing but no new dependencies (ast, re, yaml already available).

**Rationale:** Non-deterministic LLM review introduces "I might have different opinion tomorrow" risk. Deterministic checks are auditable, repeatable, and can be fixed (if a check is wrong, fix the check, not the LLM prompt).

---

### Phase 3: Layer 3 (Reality) Capture & Backchannel (`/truth` workflow)

**Goal:** Write implementation deviations and constraints back into specs.

**New stage or hook:**
- **After `testing` stage**, before `review` stage: new `reconciliation` stage or hook in `testing.py`
  
  **Captures:**
  1. Test failures → root cause analysis:
     - Parse pytest JSON report (use `--json-report` plugin)
     - Extract failed assertion messages
     - LLM does ONE THING: "what's the simplest spec change that would capture this failure?"
     - Result: candidate PRD/ARCH/REQ edits
     - **Human review required** (append to approval queue)
  
  2. Code-spec drift:
     - Compare generated code to ARCH.md design decisions
     - Flag: if code deviates (e.g., different API structure), generate deviation spec
     - Output: `DEVIATIONS.md` (Layer 3 spec) with entries like:
       ```
       ## Deviation: Auth timeout vs. specification
       - Spec said: 30-second timeout
       - Code implements: 60 seconds (to reduce prod incidents)
       - Rationale: Too many false negatives on slow networks
       - Approved: [human decision]
       ```
  
  3. Repeated gate failures → error spec:
     - If a gate fails 3+ times on the same criterion, generate explicit error handling rule
     - Example: "Linter fails on line 42; trying 3 fixes. This is a recurring pattern → add to PRINCIPLES.md"
  
  4. Coverage gaps:
     - If code covers only 60% of REQUIREMENTS.md scenarios, flag which scenarios are untested
     - Generate new test requirements for Layer 1

**Output:** 
- `sdlc/reconciliation/DEVIATIONS.md` (Layer 3)
- `sdlc/reconciliation/TEST_FAILURE_ANALYSIS.json` (structured)
- Update PRD version if changes are approved

**Effort:** ~300 lines (mostly test report parsing).

**Gate:** Manual approval required for any spec changes (prevents drift-by-default).

---

### Phase 4: Formalize Layer 1 Business Rules

**Goal:** Move from prose to structured decision tables and state machines.

**In `planning.py`** (after PRD generation):
- LLM extracts decision tables from Acceptance Criteria
  - Input: acceptance criteria prose
  - Output: decision_table.json with columns (condition, action, outcome)
- LLM extracts state machines from requirements
  - Input: workflow description in PRD
  - Output: state_machine.yaml (XState format)

**Validation:** Pydantic schemas for decision_table.json and state_machine.yaml

**Output:** Committed to `sdlc/planning/` alongside PRD.md

**Effort:** ~150 lines (LLM extraction + Pydantic validation).

**Why:** Makes Layer 1 machine-verifiable. Gherkin scenarios can be compared against state machine (are all paths tested?).

---

## New Commands / Workflow Changes

### `/spec` (refactor existing `/planning`)
- Already exists as planning stage
- Add: extraction of decision tables + state machine (Phase 4)
- Prompt: "Understand intent, emit Layer 1 spec (PRD + decision tables + state machines + Gherkin)"

### `/edge` (new stage, optional)
- Adversarial pass: "Given this spec, what did we miss?"
- Runs after planning, before coding
- LLM generates edge cases, security risks, scale issues not in PRD
- Output: `sdlc/planning/EDGE_CASES.md`
- Gate: human review + approval to proceed to architecture

### `/verify` (refactor existing `testing` + `review`)
- Already runs tests
- Add: deterministic checks (ARCH match, PRINCIPLES compliance, Gherkin mapping)
- Output: machine-readable checklist, not narrative
- Gate: no LLM self-grading; only deterministic checks block advancement

### `/truth` (new stage, Phase 3)
- After testing, before review
- Captures deviations: test failures → Layer 3, code drift → DEVIATIONS.md
- Output: candidate spec changes for human approval
- Gate: human must approve each Layer 3 change before PR submission

### Pipeline order (updated):
1. planning (`/spec`)
2. edge-cases (`/edge`) — OPTIONAL
3. ui-design (`/ui-design`)
4. architecture (`/architecture`)
5. requirements (`/requirements`)
6. coding (`/coding`)
7. testing (`/testing`)
8. reconciliation (`/truth`) — NEW
9. review (`/review`) — refactored to deterministic
10. pr (`/pr`)

---

## Files to Modify / Create

### Core Changes:
| File | Change | Effort |
|------|--------|--------|
| `nodes/architecture.py` | Add Layer 2 extraction (OpenAPI, JSON Schema, state machines) | ~200 lines |
| `nodes/planning.py` | Add decision table + state machine extraction | ~150 lines |
| `nodes/testing.py` | Replace LLM gherkin compliance with deterministic mapping | ~200 lines |
| `nodes/review.py` | Replace LLM narrative with rule-driven checklist | ~200 lines |
| `nodes/reconciliation.py` | NEW: test failure analysis + drift capture + backchannel | ~300 lines |
| `nodes/edge.py` | NEW: adversarial spec review (optional) | ~100 lines |
| `utils/spec_extractors.py` | NEW: helpers for Layer 2 extraction | ~200 lines |
| `utils/deterministic_checks.py` | NEW: ARCH match, PRINCIPLES validation, Gherkin mapping | ~250 lines |
| `principles_checker.py` | Implement stubs for forbidden patterns, type hints, coverage | ~100 lines |
| `langgraph_sdlc.py` | Add `/edge` and `/truth` command routing | ~50 lines |
| `gates/gate_runner.py` | Add new gates for Layer 2, reconciliation approval | ~100 lines |
| `tests/test_reconciliation.py` | NEW: test fixture + mocks for failure analysis | ~150 lines |
| `tests/test_deterministic_checks.py` | NEW: test ARCH matching, PRINCIPLES, Gherkin mapping | ~200 lines |
| `.opencode/commands/` | Add edge.md, reconciliation.md command defs | ~50 lines |

**Total:** ~2,000 lines of new/modified code.

### No changes needed:
- State machine core (`state.py`, `langgraph_sdlc.py` routing is minimal)
- Test harness (`conftest.py`)
- Git integration (`git.py`)
- LLM abstraction (`llm.py`) — still used, just for different tasks

---

## Critical Design Decisions

### 1. Deterministic Checks Only, No LLM Grading
- **Decision:** `review.py` → checklist (pass/fail per rule), not narrative
- **Why:** Non-determinism introduces "opinion drift" risk; deterministic checks are auditable and reproducible
- **Cost:** Requires AST/regex parsing instead of "ask LLM"
- **Tradeoff:** Lose narrative context (why did it fail?) but gain audit trail

### 2. Layer 3 Capture Requires Human Approval
- **Decision:** `/truth` writes deviations back to specs, but every change needs human sign-off
- **Why:** Prevents runaway spec mutation; keeps human in control of "source of truth"
- **Cost:** Adds approval queue/workflow (not built yet; could be simple Markdown checklist)
- **Tradeoff:** Slower (require human decision) but safer

### 3. Layer 2 Generated from Layer 1 Intent, Not Reversed-Engineered
- **Decision:** Extract OpenAPI/schema from ARCH.md intent, not from code
- **Why:** Code-to-spec reverse engineering is lossy and brittle; spec-first preserves intent
- **Cost:** Requires LLM to extract contracts from narrative prose (still AI-assisted, but one-direction)
- **Tradeoff:** Contracts are aspirational (code must match them), not descriptive (code was true, now extract)

### 4. Keep `/edge` Optional
- **Decision:** `/edge` adversarial pass is a separate command, not automatic
- **Why:** Not every project needs it; adds latency; some teams prefer to discover edge cases during design/code
- **Cost:** User must opt-in
- **Tradeoff:** Flexibility vs. pipeline discipline

---

## Verification & Testing Plan

### Unit Tests:
- `test_spec_extractors.py` — does OpenAPI extraction parse valid YAML? Does state machine extraction produce valid XState?
- `test_deterministic_checks.py` — ARCH matching, PRINCIPLES checks, Gherkin mapping
- `test_reconciliation.py` — test failure analysis, drift detection, DEVIATIONS.md generation

### Integration Tests:
- `test_e2e_3layer.py` — end-to-end run with Layer 1/2/3 generation + `/truth` backchannel
- Verify PRD + OpenAPI + state machine are consistent (no contradictions)
- Verify test failures generate Layer 3 entries

### Spot-Checks:
- Run on MoM itself (dogfooding): does MoM's orchestration code match its own ARCH.md spec?
- Generate DEVIATIONS.md for actual drift (e.g., "PR routing added a new gate check not in ARCH.md")
- Manually review `/truth` output for sensibility

---

## Open Questions for Alignment

1. **Layer 2 Formalism:** Should OpenAPI be generated for all services, or only documented ones?
   - Full rigor: all endpoints have OpenAPI specs (breaks projects without clear API boundaries)
   - Pragmatic: OpenAPI for external APIs only, internal calls can stay loose

2. **Approval Workflow:** Where do `/truth` approvals live?
   - GitHub PR branch?
   - Separate `.sdlc_state.json` approval queue?
   - Slack/email + manual git commit?

3. **Scope:** Does this apply only to MoM's own development, or is the goal to make MoM a tool that **enforces** this pattern for user projects?
   - Self-application: MoM becomes a spec-driven orchestrator for itself
   - User-facing: MoM helps developers apply this to their own projects (bigger scope)

4. **Edge Cases:** How adversarial should `/edge` be?
   - Lightweight: check spec against common risks (security, scale, compliance)
   - Deep: differential implementation (ask different model to implement same spec, compare)

---

## Success Criteria

1. ✓ Layer 2 specs (OpenAPI, JSON Schema) are valid and non-empty
2. ✓ Verification is deterministic (same input → same pass/fail, no LLM grading)
3. ✓ `/truth` captures deviations; humans can approve/reject changes
4. ✓ Test failures flow into specs (Layer 3) without bloating Layer 1
5. ✓ Code can be regenerated from specs and pass verification
6. ✓ Spec gaps are explicit (DEVIATIONS.md documents what's aspirational vs. real)

---

## Next Steps (If Approved)

1. **Phase 1** — Layer 2 extraction (architecture.py + planning.py): ~1-2 days
2. **Phase 2** — Deterministic verification (testing.py + review.py): ~2-3 days (includes AST parsing)
3. **Phase 3** — Reconciliation stage + `/truth` workflow: ~2 days
4. **Phase 4** — Layer 1 formalization (decision tables, state machines): ~1 day
5. **Integration & dogfooding**: ~2 days
6. **Total:** ~8-10 days (or ~3-4 days if parallel)

**Hold point:** Before Phase 2, clarify Layer 2 formalism (question 1 above) to avoid rework.
