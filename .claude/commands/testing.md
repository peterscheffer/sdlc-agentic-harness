---
description: Assist user in proceeding through the Testing stage of the SDLC pipeline.
---

## Phase 0.0: Auto-Accept Detection (Dark Factory Mode)
Before any interactive phase, determine whether this run is in auto-accept mode:
1. Run:
   ```bash
   python3 -c "import json,os;print(json.load(open('.sdlc_state.json')).get('auto_accept',False) if os.path.exists('.sdlc_state.json') else False)"
   ```
2. Auto-accept is active if that prints `True`, OR the user's invocation includes `--auto-accept`.
3. If auto-accept is active: **SKIP every interactive questioning phase in this skill.** Answer each discovery question yourself using best-practice defaults inferred from the PRD, prior artefacts, and the repository. Record every decision you made in the context file under a heading `## Auto-Accepted Decisions`. Then proceed directly to the context-export and script-execution phase, appending `--auto-accept` to the `python3` command. Do not ask the user anything.


## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read:
   - `sdlc/planning/PRD.md`
   - `sdlc/requirements/REQUIREMENTS.md`
   - All spec artifacts under `sdlc/requirements/` (`.feature` files, `TEST_CASES.md`, `openapi.yaml` — whichever the selected spec profiles produced)
   - The source code files that were generated or modified in the coding stage
2. Absorb the product requirements, spec artifacts, and current implementation. Check `spec_profiles` in `.sdlc_state.json` to see which deterministic verifiers will run.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Test Strategy Discovery (Dynamic Questioning)
Your objective is to interview the user to determine the testing scope and focus areas.

* **Goal:** Collect enough direction to run the correct tests and validate behaviour.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on testing decisions:
  * **Test Scope:** Run all tests or focus on specific feature areas?
  * **Edge Cases:** Are there specific edge cases or failure scenarios to prioritise?
  * **Coverage Goals:** Are there minimum coverage thresholds or critical paths that must pass?
  * **Environment:** Any special environment setup or configuration needed for tests?
* **Test Types** Ask the user what type of testing to include; integration, unit, functional, etc. Explain to them if needed.


## Phase 2: The Gate (Validation)
Iterate on the testing questions until you have a clear testing direction. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have a defined test scope **AND** the user explicitly indicates they are ready to proceed (e.g., "I'm ready", "Run the tests", "Verify compliance").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the testing discussions directory exists:
   ```bash
   mkdir -p discussions/testing
   ```
2. Save the full testing conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/testing/$(date +%Y%m%d_%H%M%S)-testing-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological testing conversation history, chosen test scope, and focus areas here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the testing stage:
   ```bash
   python3 .scripts/sdlc_harness.py --stage testing --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the test results — how many tests passed/failed, plus the per-profile spec verification results from `sdlc/testing/TEST_REPORT.md`. Each selected spec profile is verified deterministically by running its verifier command (behave/cucumber-js/cucumber-jvm for gherkin-bdd, pytest/jest/vitest/JUnit for unit-tests, schemathesis for openapi-contract, `design_tokens.py check` against the Stitch screen exports for stitch-ui); ALL must exit 0 for the gate to pass. No LLM judgment is involved in spec verification.
2. **Clear Context:** From this point forward, treat the prior testing discussion as deprecated noise to optimize current memory constraints.
3. **Trigger Next Stage:** Prompt the user that the testing stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "Testing complete. The project test suite and every spec-profile verifier exited 0. To review the changes and prepare the PR, run: /review"
4. CRITICAL: Hold the line here. Do NOT automatically fix failing tests, modify code, or skip ahead to the next stage yourself. Wait for human review and the next explicit command invocation.
